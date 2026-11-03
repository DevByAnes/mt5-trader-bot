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
    let inherited = std::env::var("AURUM_SESSION_TOKEN").ok();
    let token = Zeroizing::new(match inherited {
        Some(value) if value.len() >= 32 && value.is_ascii() && !value.bytes().any(|b| b.is_ascii_whitespace()) => value,
        Some(_) => panic!("invalid inherited local session"),
        None => bytes.iter().map(|b| format!("{b:02x}")).collect(),
    });
    std::env::remove_var("AURUM_SESSION_TOKEN");
    tauri::Builder::default()
        .manage(SessionToken(Mutex::new(token)))
        .invoke_handler(tauri::generate_handler![session_token])
        .run(tauri::generate_context!()).expect("failed to run application");
}
