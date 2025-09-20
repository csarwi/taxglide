use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};

/// Schema version for CLI-GUI contract compatibility
pub const SCHEMA_VERSION: &str = "1.0";

/// Standard response envelope from CLI
#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct CliResponse<T> {
    pub success: bool,
    pub schema_version: String,
    pub timestamp: DateTime<Utc>,
    #[serde(flatten)]
    pub payload: CliPayload<T>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
#[serde(untagged)]
pub enum CliPayload<T> {
    Success { data: T },
    Error { error: CliError },
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct CliError {
    pub code: String,
    pub message: String,
    pub details: Option<serde_json::Value>,
}

/// Version information response
#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct VersionInfo {
    pub version: String,
    pub platform: String,
    pub schema_version: String,
    pub build_date: DateTime<Utc>,
}

/// Tax calculation result
#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct CalcResult {
    pub income_sg: Option<i32>,
    pub income_fed: Option<i32>,
    pub income: Option<i32>, // For backward compatibility
    pub federal: f64,
    pub sg_simple: f64,
    pub sg_after_mult: f64,
    pub total: f64,
    pub avg_rate: f64,
    pub marginal_total: f64,
    pub marginal_federal_hundreds: f64,
    pub picks: Vec<String>,
    pub filing_status: String,
    pub feuer_warning: Option<String>,
    pub canton_name: Option<String>,
    pub canton_key: Option<String>,
    pub municipality_name: Option<String>,
    pub municipality_key: Option<String>,
}

/// Tax optimization result
#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct OptimizeResult {
    pub base_total: f64,
    pub best_rate: Option<OptimizeRateInfo>,
    pub plateau_near_max_roi: Option<PlateauInfo>,
    pub sweet_spot: Option<SweetSpot>,
    pub federal_100_nudge: Option<FederalNudge>,
    pub adaptive_retry_used: Option<AdaptiveRetry>,
    pub adaptive_retry_info: Option<serde_json::Value>,
    pub multipliers_applied: Vec<String>,
    pub tolerance_info: Option<ToleranceInfo>,
    pub canton_name: Option<String>,
    pub canton_key: Option<String>,
    pub municipality_name: Option<String>,
    pub municipality_key: Option<String>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct OptimizeRateInfo {
    pub deduction: i32,
    pub new_income: f64,
    pub total: f64,
    pub saved: f64,
    pub savings_rate: f64,
    pub savings_rate_percent: f64,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct PlateauInfo {
    pub min_d: i32,
    pub max_d: i32,
    pub roi_min_percent: f64,
    pub roi_max_percent: f64,
    pub tolerance_bp: f64,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct SweetSpot {
    pub deduction: i32,
    pub new_income: f64,
    pub total_tax_at_spot: f64,
    pub tax_saved_absolute: f64,
    pub tax_saved_percent: f64,
    pub federal_tax_at_spot: Option<f64>,
    pub sg_tax_at_spot: Option<f64>,
    pub baseline: Option<BaselineInfo>,
    pub explanation: String,
    pub income_details: Option<IncomeDetails>,
    pub multipliers: Option<MultiplierInfo>,
    pub optimization_summary: Option<OptimizationSummary>,
    pub utilization_warning: Option<UtilizationWarning>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct BaselineInfo {
    pub total_tax: f64,
    pub federal_tax: Option<f64>,
    pub sg_tax: Option<f64>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct IncomeDetails {
    pub original_sg: i32,
    pub original_fed: i32,
    pub after_deduction_sg: f64,
    pub after_deduction_fed: f64,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct MultiplierInfo {
    pub applied: Vec<String>,
    pub total_rate: f64,
    pub feuer_warning: Option<String>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct OptimizationSummary {
    pub roi_percent: f64,
    pub plateau_width_chf: i32,
    pub federal_bracket_changed: bool,
    pub marginal_rate_percent: f64,
    pub notes: Option<Vec<String>>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct UtilizationWarning {
    #[serde(rename = "type")]
    pub warning_type: String,
    pub utilization_percent: f64,
    pub roi_percent: Option<f64>,
    pub message: String,
    pub technical_note: String,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct FederalNudge {
    pub nudge_chf: i32,
    pub estimated_federal_saving: f64,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct AdaptiveRetry {
    pub original_tolerance_bp: f64,
    pub chosen_tolerance_bp: f64,
    pub roi_improvement: f64,
    pub utilization_improvement: f64,
    pub selection_reason: String,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct ToleranceInfo {
    pub tolerance_used_bp: f64,
    pub tolerance_percent: f64,
    pub tolerance_source: String,
    pub explanation: String,
}

/// Scan result (array of deduction scenarios)
pub type ScanResult = Vec<ScanRow>;

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct ScanRow {
    pub deduction: i32,
    pub new_income: f64,
    pub total_tax: f64,
    pub saved: f64,
    pub roi_percent: f64,
    pub sg_simple: f64,
    pub sg_after_multipliers: f64,
    pub federal: f64,
    pub federal_from: i32,
    pub federal_to: Option<i32>,
    pub federal_per100: f64,
    pub local_marginal_percent: Option<f64>,
    pub new_income_sg: Option<f64>,
    pub new_income_fed: Option<f64>,
}

/// Compare brackets result
#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct CompareBracketsResult {
    pub original_sg_income: i32,
    pub original_fed_income: i32,
    pub adjusted_sg_income: f64,
    pub adjusted_fed_income: f64,
    pub deduction_amount: i32,
    pub federal_bracket_before: BracketInfo,
    pub federal_bracket_after: BracketInfo,
    pub federal_bracket_changed: bool,
    pub sg_bracket_before: SgBracketInfo,
    pub sg_bracket_after: SgBracketInfo,
    pub sg_bracket_changed: bool,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct BracketInfo {
    pub from: i32,
    pub to: Option<i32>,
    pub per100: f64,
    pub at_income: i32,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct SgBracketInfo {
    pub lower: i32,
    pub upper: i32,
    pub rate_percent: f64,
}

/// Validation result
#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct ValidateResult {
    pub status: String,
    pub year: i32,
    pub message: String,
}

/// Input parameters for CLI commands
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct CalcParams {
    pub year: i32,
    pub income: Option<i32>,
    pub income_sg: Option<i32>,
    pub income_fed: Option<i32>,
    pub filing_status: Option<String>,
    pub pick: Vec<String>,
    pub skip: Vec<String>,
    pub canton: Option<String>,
    pub municipality: Option<String>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct OptimizeParams {
    pub year: i32,
    pub income: Option<i32>,
    pub income_sg: Option<i32>,
    pub income_fed: Option<i32>,
    pub max_deduction: i32,
    pub step: Option<i32>,
    pub filing_status: Option<String>,
    pub pick: Vec<String>,
    pub skip: Vec<String>,
    pub tolerance_bp: Option<f64>,
    pub disable_adaptive: Option<bool>,
    pub canton: Option<String>,
    pub municipality: Option<String>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ScanParams {
    pub year: i32,
    pub income: Option<i32>,
    pub income_sg: Option<i32>,
    pub income_fed: Option<i32>,
    pub max_deduction: i32,
    pub d_step: Option<i32>,
    pub filing_status: Option<String>,
    pub pick: Vec<String>,
    pub skip: Vec<String>,
    pub include_local_marginal: Option<bool>,
    pub canton: Option<String>,
    pub municipality: Option<String>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct CompareBracketsParams {
    pub year: i32,
    pub income: Option<i32>,
    pub income_sg: Option<i32>,
    pub income_fed: Option<i32>,
    pub deduction: Option<i32>,
    pub filing_status: Option<String>,
    pub canton: Option<String>,
    pub municipality: Option<String>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ValidateParams {
    pub year: i32,
}

/// Available locations response
#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct AvailableLocations {
    pub cantons: Vec<Canton>,
    pub defaults: LocationDefaults,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Canton {
    pub name: String,
    pub key: String,
    pub municipalities: Vec<Municipality>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Municipality {
    pub name: String,
    pub key: String,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct LocationDefaults {
    pub canton: String,
    pub municipality: String,
}

// Config management types

/// List available years response
#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct AvailableYears {
    pub available_years: Vec<i32>,
    pub count: usize,
}

/// Configuration summary response
#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct ConfigSummary {
    pub year: i32,
    pub schema_version: String,
    pub country: String,
    pub currency: String,
    pub canton_count: usize,
    pub cantons: Vec<CantonSummary>,
    pub defaults: LocationDefaults,
    pub federal_filing_statuses: Vec<String>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct CantonSummary {
    pub key: String,
    pub name: String,
    pub abbreviation: String,
    pub bracket_count: usize,
    pub municipality_count: usize,
    pub municipalities: Vec<MunicipalitySummary>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct MunicipalitySummary {
    pub key: String,
    pub name: String,
    pub multiplier_count: usize,
}

/// Create/update year result
#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct YearOperationResult {
    pub source_year: Option<i32>,
    pub target_year: i32,
    pub success: bool,
    pub message: String,
    pub archive_file: Option<String>,
}

/// Canton operation result
#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct CantonOperationResult {
    pub success: bool,
    pub canton_key: String,
    pub canton_name: String,
    pub message: String,
    pub archive_file: Option<String>,
}

/// Municipality operation result
#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct MunicipalityOperationResult {
    pub success: bool,
    pub canton_key: String,
    pub municipality_key: String,
    pub municipality_name: String,
    pub message: String,
    pub archive_file: Option<String>,
}

/// Federal brackets operation result
#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct FederalBracketsOperationResult {
    pub success: bool,
    pub filing_status: String,
    pub segments_count: usize,
    pub message: String,
    pub archive_file: Option<String>,
}

// Configuration data structures for editing

/// Tax bracket definition
#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct TaxBracket {
    pub lower: i32,
    pub width: i32,
    pub rate_percent: f64,
}

/// Rounding configuration
#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct RoundingConfig {
    pub taxable_step: i32,
    pub tax_round_to: i32,
    pub scope: String,
}

/// Tax multiplier definition
#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct TaxMultiplier {
    pub name: String,
    pub code: String,
    pub kind: String,
    pub rate: f64,
    pub optional: Option<bool>,
    pub default_selected: bool,
}

/// Full canton configuration
#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct CantonConfig {
    pub name: String,
    pub abbreviation: String,
    pub model: Option<String>,
    pub rounding: RoundingConfig,
    pub brackets: Vec<TaxBracket>,
    pub override_config: Option<serde_json::Value>,
    pub notes: Option<String>,
    pub municipalities: std::collections::HashMap<String, MunicipalityConfig>,
}

/// Full municipality configuration
#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct MunicipalityConfig {
    pub name: String,
    pub multipliers: std::collections::HashMap<String, TaxMultiplier>,
    pub multiplier_order: Vec<String>,
}

/// Federal tax segment
#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct FederalTaxSegment {
    #[serde(rename = "from")]
    pub from_: i32,
    pub to: Option<i32>,
    pub at_income: i32,
    pub base_tax_at: f64,
    pub per100: f64,
}

// Config management command parameters

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ListYearsParams {
    // No parameters needed
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ConfigSummaryParams {
    pub year: i32,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct CreateYearParams {
    pub source_year: i32,
    pub target_year: i32,
    pub overwrite: Option<bool>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct CreateCantonParams {
    pub year: i32,
    pub canton_key: String,
    pub canton_config: CantonConfig,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct UpdateCantonParams {
    pub year: i32,
    pub canton_key: String,
    pub canton_config: CantonConfig,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct DeleteCantonParams {
    pub year: i32,
    pub canton_key: String,
    pub confirm: Option<bool>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct CreateMunicipalityParams {
    pub year: i32,
    pub canton_key: String,
    pub municipality_key: String,
    pub municipality_config: MunicipalityConfig,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct UpdateMunicipalityParams {
    pub year: i32,
    pub canton_key: String,
    pub municipality_key: String,
    pub municipality_config: MunicipalityConfig,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct DeleteMunicipalityParams {
    pub year: i32,
    pub canton_key: String,
    pub municipality_key: String,
    pub confirm: Option<bool>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct UpdateFederalBracketsParams {
    pub year: i32,
    pub filing_status: String,
    pub segments: Vec<FederalTaxSegment>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct GetFederalSegmentsParams {
    pub year: i32,
    pub filing_status: String,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct FederalSegmentsResult {
    pub year: i32,
    pub filing_status: String,
    pub segments: Vec<FederalTaxSegment>,
    pub segments_count: usize,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct GetCantonParams {
    pub year: i32,
    pub canton_key: String,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct CantonDetailsResult {
    pub name: String,
    pub abbreviation: String,
    pub brackets: Vec<TaxBracket>,
    pub rounding: RoundingConfig,
    pub municipalities: std::collections::HashMap<String, MunicipalityConfig>,
}
