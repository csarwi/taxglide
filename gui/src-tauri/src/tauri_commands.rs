use crate::cli_integration::CliIntegration;
use crate::cli_types::*;
use log::{error, info};
use std::sync::Arc;
use tauri::State;
use tokio::sync::RwLock;

/// Global state for CLI integration
pub struct CliState {
    pub cli: Arc<RwLock<Option<CliIntegration>>>,
}

impl CliState {
    pub fn new() -> Self {
        Self {
            cli: Arc::new(RwLock::new(None)),
        }
    }
}

/// Initialize CLI integration and check compatibility
#[tauri::command]
pub async fn init_cli(state: State<'_, CliState>) -> Result<VersionInfo, String> {
    info!("Initializing CLI integration...");
    
    let mut cli_integration = CliIntegration::new()
        .map_err(|e| format!("Failed to create CLI integration: {}", e))?;
    
    let version_info = cli_integration
        .check_compatibility()
        .await
        .map_err(|e| format!("CLI compatibility check failed: {}", e))?;
    
    // Store the CLI integration in state
    {
        let mut cli_lock = state.cli.write().await;
        *cli_lock = Some(cli_integration);
    }
    
    info!("CLI integration initialized successfully");
    Ok(version_info)
}

/// Get CLI version information (if already initialized)
#[tauri::command]
pub async fn get_version_info(state: State<'_, CliState>) -> Result<Option<VersionInfo>, String> {
    let cli_lock = state.cli.read().await;
    
    match cli_lock.as_ref() {
        Some(cli) => Ok(cli.get_version_info().cloned()),
        None => Ok(None),
    }
}

/// Calculate taxes
#[tauri::command]
pub async fn calc(state: State<'_, CliState>, params: CalcParams) -> Result<CalcResult, String> {
    info!("Processing calc command: {:?}", params);
    
    let cli_lock = state.cli.read().await;
    let cli = cli_lock
        .as_ref()
        .ok_or_else(|| "CLI not initialized. Call init_cli first.".to_string())?;
    
    let result = cli.calc(params).await.map_err(|e| {
        error!("Calc command failed: {}", e);
        format!("Calculation failed: {}", e)
    })?;
    
    info!("Calc command completed successfully");
    Ok(result)
}

/// Optimize tax deductions
#[tauri::command]
pub async fn optimize(state: State<'_, CliState>, params: OptimizeParams) -> Result<OptimizeResult, String> {
    info!("Processing optimize command: {:?}", params);
    
    let cli_lock = state.cli.read().await;
    let cli = cli_lock
        .as_ref()
        .ok_or_else(|| "CLI not initialized. Call init_cli first.".to_string())?;
    
    let result = cli.optimize(params).await.map_err(|e| {
        error!("Optimize command failed: {}", e);
        format!("Optimization failed: {}", e)
    })?;
    
    info!("Optimize command completed successfully");
    Ok(result)
}

/// Scan deduction ranges
#[tauri::command]
pub async fn scan(state: State<'_, CliState>, params: ScanParams) -> Result<ScanResult, String> {
    info!("Processing scan command: {:?}", params);
    
    let cli_lock = state.cli.read().await;
    let cli = cli_lock
        .as_ref()
        .ok_or_else(|| "CLI not initialized. Call init_cli first.".to_string())?;
    
    let result = cli.scan(params).await.map_err(|e| {
        error!("Scan command failed: {}", e);
        format!("Scan failed: {}", e)
    })?;
    
    info!("Scan command completed successfully");
    Ok(result)
}

/// Compare tax brackets
#[tauri::command]
pub async fn compare_brackets(
    state: State<'_, CliState>, 
    params: CompareBracketsParams
) -> Result<CompareBracketsResult, String> {
    info!("Processing compare_brackets command: {:?}", params);
    
    let cli_lock = state.cli.read().await;
    let cli = cli_lock
        .as_ref()
        .ok_or_else(|| "CLI not initialized. Call init_cli first.".to_string())?;
    
    let result = cli.compare_brackets(params).await.map_err(|e| {
        error!("Compare brackets command failed: {}", e);
        format!("Compare brackets failed: {}", e)
    })?;
    
    info!("Compare brackets command completed successfully");
    Ok(result)
}

/// Validate configuration
#[tauri::command]
pub async fn validate_config(
    state: State<'_, CliState>, 
    params: ValidateParams
) -> Result<ValidateResult, String> {
    info!("Processing validate command: {:?}", params);
    
    let cli_lock = state.cli.read().await;
    let cli = cli_lock
        .as_ref()
        .ok_or_else(|| "CLI not initialized. Call init_cli first.".to_string())?;
    
    let result = cli.validate(params).await.map_err(|e| {
        error!("Validate command failed: {}", e);
        format!("Validation failed: {}", e)
    })?;
    
    info!("Validate command completed successfully");
    Ok(result)
}

/// Check if CLI is initialized and ready
#[tauri::command]
pub async fn is_cli_ready(state: State<'_, CliState>) -> Result<bool, String> {
    let cli_lock = state.cli.read().await;
    Ok(cli_lock.is_some())
}

/// Get CLI status information
#[tauri::command]
pub async fn get_cli_status(state: State<'_, CliState>) -> Result<CliStatusInfo, String> {
    let cli_lock = state.cli.read().await;
    
    match cli_lock.as_ref() {
        Some(cli) => {
            let version_info = cli.get_version_info().cloned();
            Ok(CliStatusInfo {
                initialized: true,
                version_info,
                error: None,
            })
        }
        None => Ok(CliStatusInfo {
            initialized: false,
            version_info: None,
            error: Some("CLI not initialized".to_string()),
        }),
    }
}

#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct CliStatusInfo {
    pub initialized: bool,
    pub version_info: Option<VersionInfo>,
    pub error: Option<String>,
}
