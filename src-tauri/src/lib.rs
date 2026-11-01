use rand::RngCore;
use std::sync::Mutex;
use zeroize::Zeroizing;

struct SessionToken(Mutex<Zeroizing<String>>);

#[tauri::command]
fn session_token(state: tauri::State<'_, SessionToken>) -> Result<String, String> {
    state.0.lock().map(|v| v.to_string()).map_err(|_| "session unavailable".into())
}

pub fn run() {
    let mut bytes = [0_u8; 32]; rand::rng().fill_bytes(&mut bytes);
    let token = Zeroizing::new(bytes.iter().map(|b| format!("{b:02x}")).collect());
    tauri::Builder::default()
        .manage(SessionToken(Mutex::new(token)))
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .invoke_handler(tauri::generate_handler![session_token])
        .run(tauri::generate_context!()).expect("failed to run application");
}
