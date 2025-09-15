use crate::cli_types::*;
use log::{debug, error, info};
use serde_json;
use std::path::PathBuf;
use std::process::Stdio;
use std::time::Duration;
use thiserror::Error;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::Command;
use tokio::time::timeout;

#[derive(Error, Debug)]
pub enum CliError {
    #[error("CLI executable not found: {0}")]
    ExecutableNotFound(String),
    #[error("Schema version mismatch: expected {expected}, got {actual}")]
    SchemaMismatch { expected: String, actual: String },
    #[error("Process execution failed: {0}")]
    ProcessFailed(String),
    #[error("Process timeout after {seconds} seconds")]
    Timeout { seconds: u64 },
    #[error("JSON parsing error: {0}")]
    JsonError(#[from] serde_json::Error),
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
    #[error("CLI returned error: {code} - {message}")]
    CliError { code: String, message: String },
    #[error("Invalid parameters: {0}")]
    InvalidParameters(String),
}

pub struct CliIntegration {
    cli_path: PathBuf,
    version_info: Option<VersionInfo>,
}

impl CliIntegration {
    /// Create a new CLI integration instance
    pub fn new() -> Result<Self, CliError> {
        let cli_path = Self::discover_cli_executable()?;
        info!("Found CLI executable at: {:?}", cli_path);
        
        Ok(CliIntegration {
            cli_path,
            version_info: None,
        })
    }
    
    /// Discover the CLI executable path
    /// In production: look for taxglide.exe in the same directory as GUI
    /// In development: use python main.py in the parent directory with venv
    fn discover_cli_executable() -> Result<PathBuf, CliError> {
        let current_exe = std::env::current_exe()
            .map_err(|e| CliError::ExecutableNotFound(format!("Cannot determine current executable: {}", e)))?;
        
        let exe_dir = current_exe.parent()
            .ok_or_else(|| CliError::ExecutableNotFound("Cannot determine executable directory".to_string()))?;
        
        // First try: production executable (taxglide.exe in same directory)
        let production_exe = exe_dir.join("taxglide.exe");
        if production_exe.exists() {
            info!("Found production CLI executable: {:?}", production_exe);
            return Ok(production_exe);
        }
        
        // Second try: development mode (main.py in parent directory)
        // GUI is in TaxGlide/gui/src-tauri/target/debug/, CLI is in TaxGlide/
        let dev_main_py = exe_dir
            .parent() // target
            .and_then(|p| p.parent()) // src-tauri
            .and_then(|p| p.parent()) // gui
            .and_then(|p| p.parent()) // TaxGlide
            .map(|p| p.join("main.py"));
        
        if let Some(ref main_py) = dev_main_py {
            if main_py.exists() {
                info!("Found development CLI script: {:?}", main_py);
                return Ok(main_py.clone());
            }
        }
        
        // Third try: look for main.py in current directory (fallback)
        let current_main_py = exe_dir.join("main.py");
        if current_main_py.exists() {
            info!("Found CLI script in current directory: {:?}", current_main_py);
            return Ok(current_main_py);
        }
        
        Err(CliError::ExecutableNotFound(format!(
            "Cannot find CLI executable. Searched for: {:?}, {:?}", 
            production_exe, 
            dev_main_py.unwrap_or_else(|| PathBuf::from("main.py"))
        )))
    }
    
    /// Find the Python executable from virtual environment
    /// Try to find python.exe in .venv/Scripts/ relative to the CLI script
    fn find_venv_python(main_py_path: &PathBuf) -> Option<PathBuf> {
        let project_root = main_py_path.parent()?;
        
        // Check for .venv/Scripts/python.exe (Windows)
        let venv_python = project_root.join(".venv").join("Scripts").join("python.exe");
        if venv_python.exists() {
            info!("Found virtual environment python: {:?}", venv_python);
            return Some(venv_python);
        }
        
        // Check for venv/Scripts/python.exe (alternate Windows location)
        let venv_python_alt = project_root.join("venv").join("Scripts").join("python.exe");
        if venv_python_alt.exists() {
            info!("Found virtual environment python (venv): {:?}", venv_python_alt);
            return Some(venv_python_alt);
        }
        
        info!("No virtual environment python found, will use system python");
        None
    }
    
    /// Check version compatibility with the CLI
    pub async fn check_compatibility(&mut self) -> Result<VersionInfo, CliError> {
        debug!("Checking CLI compatibility...");
        
        let response: CliResponse<VersionInfo> = self
            .execute_command(&["version", "--json", "--schema-version"], Duration::from_secs(10))
            .await?;
        
        match response.payload {
            CliPayload::Success { data } => {
                // Validate schema version
                if data.schema_version != SCHEMA_VERSION {
                    return Err(CliError::SchemaMismatch {
                        expected: SCHEMA_VERSION.to_string(),
                        actual: data.schema_version.clone(),
                    });
                }
                
                info!("CLI compatibility check passed: version {}, schema {}", 
                      data.version, data.schema_version);
                self.version_info = Some(data.clone());
                Ok(data)
            }
            CliPayload::Error { error } => Err(CliError::CliError {
                code: error.code,
                message: error.message,
            }),
        }
    }
    
    /// Execute a CLI command with timeout
    async fn execute_command<T>(&self, args: &[&str], timeout_duration: Duration) 
        -> Result<CliResponse<T>, CliError> 
    where
        T: serde::de::DeserializeOwned,
    {
        debug!("Executing CLI command: {:?}", args);
        
        let mut command = if self.cli_path.extension() == Some(std::ffi::OsStr::new("py")) {
            // Python script - try to use virtual environment python, fallback to system python
            let python_exe = Self::find_venv_python(&self.cli_path)
                .unwrap_or_else(|| PathBuf::from("python"));
            
            let mut cmd = Command::new(python_exe);
            cmd.arg(&self.cli_path);
            cmd.args(args);
            cmd
        } else {
            // Executable
            let mut cmd = Command::new(&self.cli_path);
            cmd.args(args);
            cmd
        };
        
        command
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .stdin(Stdio::null());
        
        // On Windows, hide the console window when spawning CLI process
        #[cfg(target_os = "windows")]
        {
            const CREATE_NO_WINDOW: u32 = 0x08000000;
            use std::os::windows::process::CommandExt;
            command.creation_flags(CREATE_NO_WINDOW);
        }
        
        let result = timeout(timeout_duration, async {
            let mut child = command.spawn()?;
            
            // Read stdout and stderr
            let stdout = child.stdout.take().ok_or_else(|| {
                std::io::Error::new(std::io::ErrorKind::Other, "Failed to capture stdout")
            })?;
            let stderr = child.stderr.take().ok_or_else(|| {
                std::io::Error::new(std::io::ErrorKind::Other, "Failed to capture stderr")
            })?;
            
            let mut stdout_reader = BufReader::new(stdout);
            let mut stderr_reader = BufReader::new(stderr);
            
            let mut stdout_lines = Vec::new();
            let mut stderr_lines = Vec::new();
            
            // Read all output
            let mut stdout_line = String::new();
            while stdout_reader.read_line(&mut stdout_line).await? > 0 {
                stdout_lines.push(stdout_line.trim().to_string());
                stdout_line.clear();
            }
            
            let mut stderr_line = String::new();
            while stderr_reader.read_line(&mut stderr_line).await? > 0 {
                stderr_lines.push(stderr_line.trim().to_string());
                stderr_line.clear();
            }
            
            let status = child.wait().await?;
            
            Ok::<(Vec<String>, Vec<String>, std::process::ExitStatus), std::io::Error>((stdout_lines, stderr_lines, status))
        }).await;
        
        let (stdout_lines, stderr_lines, status) = match result {
            Ok(Ok(output)) => output,
            Ok(Err(e)) => return Err(CliError::IoError(e)),
            Err(_) => return Err(CliError::Timeout { 
                seconds: timeout_duration.as_secs() 
            }),
        };
        
        // Join stdout lines to get JSON response
        let stdout_text = stdout_lines.join("\n");
        
        if !status.success() {
            let error_msg = if stderr_lines.is_empty() {
                format!("CLI command failed with exit code: {}", status.code().unwrap_or(-1))
            } else {
                stderr_lines.join("\n")
            };
            
            error!("CLI command failed: {}", error_msg);
            return Err(CliError::ProcessFailed(error_msg));
        }
        
        if stdout_text.trim().is_empty() {
            return Err(CliError::ProcessFailed("CLI returned empty output".to_string()));
        }
        
        debug!("CLI command succeeded, parsing JSON response");
        let response: CliResponse<T> = serde_json::from_str(&stdout_text)?;
        Ok(response)
    }
    
    /// Build command arguments from parameters
    fn build_calc_args(&self, params: &CalcParams) -> Vec<String> {
        let mut args = vec![
            "calc".to_string(),
            "--json".to_string(),
            "--year".to_string(),
            params.year.to_string(),
        ];
        
        // Income parameters
        if let Some(income) = params.income {
            args.extend(["--income".to_string(), income.to_string()]);
        } else if let (Some(income_sg), Some(income_fed)) = (params.income_sg, params.income_fed) {
            args.extend([
                "--income-sg".to_string(), income_sg.to_string(),
                "--income-fed".to_string(), income_fed.to_string(),
            ]);
        }
        
        // Filing status
        if let Some(ref filing_status) = params.filing_status {
            args.extend(["--filing-status".to_string(), filing_status.clone()]);
        }
        
        // Multiplier picks and skips
        for pick in &params.pick {
            args.extend(["--pick".to_string(), pick.clone()]);
        }
        for skip in &params.skip {
            args.extend(["--skip".to_string(), skip.clone()]);
        }
        
        args
    }
    
    fn build_optimize_args(&self, params: &OptimizeParams) -> Vec<String> {
        let mut args = vec![
            "optimize".to_string(),
            "--json".to_string(),
            "--year".to_string(),
            params.year.to_string(),
            "--max-deduction".to_string(),
            params.max_deduction.to_string(),
        ];
        
        // Income parameters
        if let Some(income) = params.income {
            args.extend(["--income".to_string(), income.to_string()]);
        } else if let (Some(income_sg), Some(income_fed)) = (params.income_sg, params.income_fed) {
            args.extend([
                "--income-sg".to_string(), income_sg.to_string(),
                "--income-fed".to_string(), income_fed.to_string(),
            ]);
        }
        
        // Optional parameters
        if let Some(step) = params.step {
            args.extend(["--step".to_string(), step.to_string()]);
        }
        if let Some(ref filing_status) = params.filing_status {
            args.extend(["--filing-status".to_string(), filing_status.clone()]);
        }
        if let Some(tolerance_bp) = params.tolerance_bp {
            args.extend(["--tolerance-bp".to_string(), tolerance_bp.to_string()]);
        }
        if params.disable_adaptive == Some(true) {
            args.push("--disable-adaptive".to_string());
        }
        
        // Multiplier picks and skips
        for pick in &params.pick {
            args.extend(["--pick".to_string(), pick.clone()]);
        }
        for skip in &params.skip {
            args.extend(["--skip".to_string(), skip.clone()]);
        }
        
        args
    }
    
    fn build_scan_args(&self, params: &ScanParams) -> Vec<String> {
        let mut args = vec![
            "scan".to_string(),
            "--json".to_string(),
            "--year".to_string(),
            params.year.to_string(),
            "--max-deduction".to_string(),
            params.max_deduction.to_string(),
        ];
        
        // Income parameters
        if let Some(income) = params.income {
            args.extend(["--income".to_string(), income.to_string()]);
        } else if let (Some(income_sg), Some(income_fed)) = (params.income_sg, params.income_fed) {
            args.extend([
                "--income-sg".to_string(), income_sg.to_string(),
                "--income-fed".to_string(), income_fed.to_string(),
            ]);
        }
        
        // Optional parameters
        if let Some(d_step) = params.d_step {
            args.extend(["--d-step".to_string(), d_step.to_string()]);
        }
        if let Some(ref filing_status) = params.filing_status {
            args.extend(["--filing-status".to_string(), filing_status.clone()]);
        }
        // include_local_marginal is true by default in CLI
        // For typer boolean flags, we use the --no-include-local-marginal form when false
        if params.include_local_marginal == Some(false) {
            args.push("--no-include-local-marginal".to_string());
        }
        
        // Multiplier picks and skips
        for pick in &params.pick {
            args.extend(["--pick".to_string(), pick.clone()]);
        }
        for skip in &params.skip {
            args.extend(["--skip".to_string(), skip.clone()]);
        }
        
        args
    }
    
    fn build_compare_brackets_args(&self, params: &CompareBracketsParams) -> Vec<String> {
        let mut args = vec![
            "compare-brackets".to_string(),
            "--json".to_string(),
            "--year".to_string(),
            params.year.to_string(),
        ];
        
        // Income parameters
        if let Some(income) = params.income {
            args.extend(["--income".to_string(), income.to_string()]);
        } else if let (Some(income_sg), Some(income_fed)) = (params.income_sg, params.income_fed) {
            args.extend([
                "--income-sg".to_string(), income_sg.to_string(),
                "--income-fed".to_string(), income_fed.to_string(),
            ]);
        }
        
        // Optional deduction
        if let Some(deduction) = params.deduction {
            args.extend(["--deduction".to_string(), deduction.to_string()]);
        }
        
        // Filing status
        if let Some(ref filing_status) = params.filing_status {
            args.extend(["--filing-status".to_string(), filing_status.clone()]);
        }
        
        args
    }
    
    fn build_validate_args(&self, params: &ValidateParams) -> Vec<String> {
        vec![
            "validate".to_string(),
            "--json".to_string(),
            "--year".to_string(),
            params.year.to_string(),
        ]
    }
    
    // Public API methods
    
    pub async fn calc(&self, params: CalcParams) -> Result<CalcResult, CliError> {
        // Validate parameters
        if params.income.is_none() && (params.income_sg.is_none() || params.income_fed.is_none()) {
            return Err(CliError::InvalidParameters(
                "Must provide either income or both income_sg and income_fed".to_string()
            ));
        }
        
        let args = self.build_calc_args(&params);
        let args_str: Vec<&str> = args.iter().map(|s| s.as_str()).collect();
        
        let response: CliResponse<CalcResult> = self
            .execute_command(&args_str, Duration::from_secs(30))
            .await?;
        
        match response.payload {
            CliPayload::Success { data } => Ok(data),
            CliPayload::Error { error } => Err(CliError::CliError {
                code: error.code,
                message: error.message,
            }),
        }
    }
    
    pub async fn optimize(&self, params: OptimizeParams) -> Result<OptimizeResult, CliError> {
        // Validate parameters
        if params.income.is_none() && (params.income_sg.is_none() || params.income_fed.is_none()) {
            return Err(CliError::InvalidParameters(
                "Must provide either income or both income_sg and income_fed".to_string()
            ));
        }
        
        let args = self.build_optimize_args(&params);
        let args_str: Vec<&str> = args.iter().map(|s| s.as_str()).collect();
        
        let response: CliResponse<OptimizeResult> = self
            .execute_command(&args_str, Duration::from_secs(60))
            .await?;
        
        match response.payload {
            CliPayload::Success { data } => Ok(data),
            CliPayload::Error { error } => Err(CliError::CliError {
                code: error.code,
                message: error.message,
            }),
        }
    }
    
    pub async fn scan(&self, params: ScanParams) -> Result<ScanResult, CliError> {
        // Validate parameters
        if params.income.is_none() && (params.income_sg.is_none() || params.income_fed.is_none()) {
            return Err(CliError::InvalidParameters(
                "Must provide either income or both income_sg and income_fed".to_string()
            ));
        }
        
        let args = self.build_scan_args(&params);
        let args_str: Vec<&str> = args.iter().map(|s| s.as_str()).collect();
        
        let response: CliResponse<ScanResult> = self
            .execute_command(&args_str, Duration::from_secs(60))
            .await?;
        
        match response.payload {
            CliPayload::Success { data } => Ok(data),
            CliPayload::Error { error } => Err(CliError::CliError {
                code: error.code,
                message: error.message,
            }),
        }
    }
    
    pub async fn compare_brackets(&self, params: CompareBracketsParams) -> Result<CompareBracketsResult, CliError> {
        // Validate parameters
        if params.income.is_none() && (params.income_sg.is_none() || params.income_fed.is_none()) {
            return Err(CliError::InvalidParameters(
                "Must provide either income or both income_sg and income_fed".to_string()
            ));
        }
        
        let args = self.build_compare_brackets_args(&params);
        let args_str: Vec<&str> = args.iter().map(|s| s.as_str()).collect();
        
        let response: CliResponse<CompareBracketsResult> = self
            .execute_command(&args_str, Duration::from_secs(30))
            .await?;
        
        match response.payload {
            CliPayload::Success { data } => Ok(data),
            CliPayload::Error { error } => Err(CliError::CliError {
                code: error.code,
                message: error.message,
            }),
        }
    }
    
    pub async fn validate(&self, params: ValidateParams) -> Result<ValidateResult, CliError> {
        let args = self.build_validate_args(&params);
        let args_str: Vec<&str> = args.iter().map(|s| s.as_str()).collect();
        
        let response: CliResponse<ValidateResult> = self
            .execute_command(&args_str, Duration::from_secs(30))
            .await?;
        
        match response.payload {
            CliPayload::Success { data } => Ok(data),
            CliPayload::Error { error } => Err(CliError::CliError {
                code: error.code,
                message: error.message,
            }),
        }
    }
    
    /// Get version information (cached after first compatibility check)
    pub fn get_version_info(&self) -> Option<&VersionInfo> {
        self.version_info.as_ref()
    }
}
