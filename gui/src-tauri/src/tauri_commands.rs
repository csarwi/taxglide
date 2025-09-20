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

// Config management commands

/// List available tax years
#[tauri::command]
pub async fn list_years(
    state: State<'_, CliState>
) -> Result<crate::cli_types::AvailableYears, String> {
    info!("Loading available tax years from CLI...");
    
    let cli_lock = state.cli.read().await;
    let cli = cli_lock
        .as_ref()
        .ok_or_else(|| "CLI not initialized. Call init_cli first.".to_string())?;
    
    let result = cli.list_years().await.map_err(|e| {
        error!("List years command failed: {}", e);
        format!("List years failed: {}", e)
    })?;
    
    info!("Available years loaded successfully from CLI");
    Ok(result)
}

/// Get configuration summary for a year
#[tauri::command]
pub async fn get_config_summary(
    state: State<'_, CliState>,
    params: crate::cli_types::ConfigSummaryParams
) -> Result<crate::cli_types::ConfigSummary, String> {
    info!("Loading configuration summary for year {} from CLI...", params.year);
    
    let cli_lock = state.cli.read().await;
    let cli = cli_lock
        .as_ref()
        .ok_or_else(|| "CLI not initialized. Call init_cli first.".to_string())?;
    
    let result = cli.get_config_summary(params).await.map_err(|e| {
        error!("Get config summary command failed: {}", e);
        format!("Get config summary failed: {}", e)
    })?;
    
    info!("Configuration summary loaded successfully from CLI");
    Ok(result)
}

/// Create new tax year
#[tauri::command]
pub async fn create_year(
    state: State<'_, CliState>,
    params: crate::cli_types::CreateYearParams
) -> Result<crate::cli_types::YearOperationResult, String> {
    info!("Creating tax year {} from {} via CLI...", params.target_year, params.source_year);
    
    let cli_lock = state.cli.read().await;
    let cli = cli_lock
        .as_ref()
        .ok_or_else(|| "CLI not initialized. Call init_cli first.".to_string())?;
    
    let result = cli.create_year(params).await.map_err(|e| {
        error!("Create year command failed: {}", e);
        format!("Create year failed: {}", e)
    })?;
    
    info!("Tax year created successfully via CLI");
    Ok(result)
}

/// Update federal tax brackets
#[tauri::command]
pub async fn update_federal_brackets(
    state: State<'_, CliState>,
    params: crate::cli_types::UpdateFederalBracketsParams
) -> Result<crate::cli_types::FederalBracketsOperationResult, String> {
    info!("Updating federal brackets for {} filing status in year {} via CLI...", params.filing_status, params.year);
    
    let cli_lock = state.cli.read().await;
    let cli = cli_lock
        .as_ref()
        .ok_or_else(|| "CLI not initialized. Call init_cli first.".to_string())?;
    
    let result = cli.update_federal_brackets(params).await.map_err(|e| {
        error!("Update federal brackets command failed: {}", e);
        format!("Update federal brackets failed: {}", e)
    })?;
    
    info!("Federal brackets updated successfully via CLI");
    Ok(result)
}

/// Create new canton
#[tauri::command]
pub async fn create_canton(
    state: State<'_, CliState>,
    params: crate::cli_types::CreateCantonParams
) -> Result<crate::cli_types::CantonOperationResult, String> {
    info!("Creating canton {} in year {} via CLI...", params.canton_key, params.year);
    
    let cli_lock = state.cli.read().await;
    let cli = cli_lock
        .as_ref()
        .ok_or_else(|| "CLI not initialized. Call init_cli first.".to_string())?;
    
    let result = cli.create_canton(params).await.map_err(|e| {
        error!("Create canton command failed: {}", e);
        format!("Create canton failed: {}", e)
    })?;
    
    info!("Canton created successfully via CLI");
    Ok(result)
}

/// Update existing canton
#[tauri::command]
pub async fn update_canton(
    state: State<'_, CliState>,
    params: crate::cli_types::UpdateCantonParams
) -> Result<crate::cli_types::CantonOperationResult, String> {
    info!("Updating canton {} in year {} via CLI...", params.canton_key, params.year);
    
    let cli_lock = state.cli.read().await;
    let cli = cli_lock
        .as_ref()
        .ok_or_else(|| "CLI not initialized. Call init_cli first.".to_string())?;
    
    let result = cli.update_canton(params).await.map_err(|e| {
        error!("Update canton command failed: {}", e);
        format!("Update canton failed: {}", e)
    })?;
    
    info!("Canton updated successfully via CLI");
    Ok(result)
}

/// Delete canton
#[tauri::command]
pub async fn delete_canton(
    state: State<'_, CliState>,
    params: crate::cli_types::DeleteCantonParams
) -> Result<crate::cli_types::CantonOperationResult, String> {
    info!("Deleting canton {} from year {} via CLI...", params.canton_key, params.year);
    
    let cli_lock = state.cli.read().await;
    let cli = cli_lock
        .as_ref()
        .ok_or_else(|| "CLI not initialized. Call init_cli first.".to_string())?;
    
    let result = cli.delete_canton(params).await.map_err(|e| {
        error!("Delete canton command failed: {}", e);
        format!("Delete canton failed: {}", e)
    })?;
    
    info!("Canton deleted successfully via CLI");
    Ok(result)
}

/// Create new municipality
#[tauri::command]
pub async fn create_municipality(
    state: State<'_, CliState>,
    params: crate::cli_types::CreateMunicipalityParams
) -> Result<crate::cli_types::MunicipalityOperationResult, String> {
    info!("Creating municipality {} in canton {} for year {} via CLI...", params.municipality_key, params.canton_key, params.year);
    
    let cli_lock = state.cli.read().await;
    let cli = cli_lock
        .as_ref()
        .ok_or_else(|| "CLI not initialized. Call init_cli first.".to_string())?;
    
    let result = cli.create_municipality(params).await.map_err(|e| {
        error!("Create municipality command failed: {}", e);
        format!("Create municipality failed: {}", e)
    })?;
    
    info!("Municipality created successfully via CLI");
    Ok(result)
}

/// Update existing municipality
#[tauri::command]
pub async fn update_municipality(
    state: State<'_, CliState>,
    params: crate::cli_types::UpdateMunicipalityParams
) -> Result<crate::cli_types::MunicipalityOperationResult, String> {
    info!("Updating municipality {} in canton {} for year {} via CLI...", params.municipality_key, params.canton_key, params.year);
    
    let cli_lock = state.cli.read().await;
    let cli = cli_lock
        .as_ref()
        .ok_or_else(|| "CLI not initialized. Call init_cli first.".to_string())?;
    
    let result = cli.update_municipality(params).await.map_err(|e| {
        error!("Update municipality command failed: {}", e);
        format!("Update municipality failed: {}", e)
    })?;
    
    info!("Municipality updated successfully via CLI");
    Ok(result)
}

/// Get federal tax segments
#[tauri::command]
pub async fn get_federal_segments(
    state: State<'_, CliState>,
    params: crate::cli_types::GetFederalSegmentsParams
) -> Result<crate::cli_types::FederalSegmentsResult, String> {
    info!("Getting federal segments for {} filing status in year {} via CLI...", params.filing_status, params.year);
    
    let cli_lock = state.cli.read().await;
    let cli = cli_lock
        .as_ref()
        .ok_or_else(|| "CLI not initialized. Call init_cli first.".to_string())?;
    
    let result = cli.get_federal_segments(params).await.map_err(|e| {
        error!("Get federal segments command failed: {}", e);
        format!("Get federal segments failed: {}", e)
    })?;
    
    info!("Federal segments loaded successfully via CLI");
    Ok(result)
}

/// Get canton details
#[tauri::command]
pub async fn cli_get_canton(
    state: State<'_, CliState>,
    year: i32,
    canton_key: String
) -> Result<String, String> {
    info!("Getting canton details for {} in year {} via CLI...", canton_key, year);
    
    let cli_lock = state.cli.read().await;
    let cli = cli_lock
        .as_ref()
        .ok_or_else(|| "CLI not initialized. Call init_cli first.".to_string())?;
    
    let params = crate::cli_types::GetCantonParams {
        year,
        canton_key: canton_key.clone(),
    };
    
    let result = cli.get_canton(params).await.map_err(|e| {
        error!("Get canton command failed: {}", e);
        format!("Get canton failed: {}", e)
    })?;
    
    // Return JSON string for easy consumption by frontend
    serde_json::to_string(&result).map_err(|e| {
        error!("Failed to serialize canton details: {}", e);
        format!("Serialization failed: {}", e)
    })
}

#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct CliStatusInfo {
    pub initialized: bool,
    pub version_info: Option<VersionInfo>,
    pub error: Option<String>,
}
