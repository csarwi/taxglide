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
    
    // Validate parameters to prevent integer overflow
    validate_income_params(params.income, params.income_sg, params.income_fed)?;
    
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
    
    // Validate parameters to prevent integer overflow
    validate_income_params(params.income, params.income_sg, params.income_fed)?;
    validate_deduction_params(params.max_deduction, params.step)?;
    
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

/// Validate numeric parameters to prevent integer overflow
fn validate_income_params(income: Option<i32>, income_sg: Option<i32>, income_fed: Option<i32>) -> Result<(), String> {
    // Check for i32 overflow (2,147,483,647 is the max)
    let max_reasonable_income = 2_000_000_000; // 2 billion CHF - still absurd but prevents overflow
    
    if let Some(inc) = income {
        if inc < 0 {
            return Err("Income cannot be negative. Even tax authorities aren't that generous!".to_string());
        }
        if inc > max_reasonable_income {
            return Err("🤑 You're too freaking rich, just pay your taxes! (Income exceeds system limits)".to_string());
        }
    }
    
    if let Some(inc_sg) = income_sg {
        if inc_sg < 0 {
            return Err("Cantonal income cannot be negative. Even tax authorities aren't that generous!".to_string());
        }
        if inc_sg > max_reasonable_income {
            return Err("🤑 You're too freaking rich, just pay your taxes! (Cantonal income exceeds system limits)".to_string());
        }
    }
    
    if let Some(inc_fed) = income_fed {
        if inc_fed < 0 {
            return Err("Federal income cannot be negative. Even tax authorities aren't that generous!".to_string());
        }
        if inc_fed > max_reasonable_income {
            return Err("🤑 You're too freaking rich, just pay your taxes! (Federal income exceeds system limits)".to_string());
        }
    }
    
    Ok(())
}

fn validate_deduction_params(max_deduction: i32, d_step: Option<i32>) -> Result<(), String> {
    let max_reasonable_deduction = 2_000_000_000; // 2 billion CHF
    
    if max_deduction < 0 {
        return Err("Max deduction cannot be negative. That would be... weird.".to_string());
    }
    
    if max_deduction > max_reasonable_deduction {
        return Err("🤑 You're too freaking rich, just pay your taxes! (Max deduction exceeds system limits)".to_string());
    }
    
    if let Some(step) = d_step {
        if step <= 0 {
            return Err("Deduction step must be positive. Zero steps won't get you anywhere!".to_string());
        }
        if step > max_reasonable_deduction {
            return Err("🤑 Deduction step is ridiculously large. Just pay your taxes!".to_string());
        }
    }
    
    Ok(())
}

/// Scan deduction ranges
#[tauri::command]
pub async fn scan(state: State<'_, CliState>, params: ScanParams) -> Result<ScanResult, String> {
    info!("Processing scan command: {:?}", params);
    
    // Validate parameters to prevent integer overflow
    validate_income_params(params.income, params.income_sg, params.income_fed)?;
    validate_deduction_params(params.max_deduction, params.d_step)?;
    
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
    
    // Validate parameters to prevent integer overflow
    validate_income_params(params.income, params.income_sg, params.income_fed)?;
    if let Some(deduction) = params.deduction {
        validate_deduction_params(deduction, None)?;
    }
    
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

/// Get available cantons and municipalities
#[tauri::command]
pub async fn get_available_locations(
    state: State<'_, CliState>
) -> Result<crate::cli_types::AvailableLocations, String> {
    info!("Loading available cantons and municipalities from CLI...");
    
    let cli_lock = state.cli.read().await;
    let cli = cli_lock
        .as_ref()
        .ok_or_else(|| "CLI not initialized. Call init_cli first.".to_string())?;
    
    // Call CLI locations command
    let result = cli.get_available_locations().await.map_err(|e| {
        error!("Get locations command failed: {}", e);
        format!("Get locations failed: {}", e)
    })?;
    
    info!("Available locations loaded successfully from CLI");
    Ok(result)
}

#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct CliStatusInfo {
    pub initialized: bool,
    pub version_info: Option<VersionInfo>,
    pub error: Option<String>,
}
