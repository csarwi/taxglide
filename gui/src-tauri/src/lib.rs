// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/

mod cli_integration;
mod cli_types;
mod tauri_commands;

use tauri_commands::CliState;
use log::info;

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Initialize logging
    env_logger::init();
    
    info!("Starting TaxGlide GUI...");
    
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .manage(CliState::new())
        .invoke_handler(tauri::generate_handler![
            greet,
            tauri_commands::init_cli,
            tauri_commands::get_version_info,
            tauri_commands::calc,
            tauri_commands::optimize,
            tauri_commands::scan,
            tauri_commands::compare_brackets,
            tauri_commands::validate_config,
            tauri_commands::is_cli_ready,
            tauri_commands::get_cli_status,
            tauri_commands::get_available_locations,
            // Config management commands
            tauri_commands::list_years,
            tauri_commands::get_config_summary,
            tauri_commands::create_year,
            tauri_commands::update_federal_brackets,
            tauri_commands::create_canton,
            tauri_commands::update_canton,
            tauri_commands::delete_canton,
            tauri_commands::create_municipality,
            tauri_commands::update_municipality,
            tauri_commands::get_federal_segments,
            tauri_commands::cli_get_canton,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
