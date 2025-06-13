use pyo3::prelude::*;

#[pyfunction]
pub fn normalize_path(path: &str) -> String {
    if !path.contains(".") {
        return path.to_string();
    }

    let components = path.split('/').collect::<Vec<&str>>();
    let mut normalized_components = Vec::with_capacity(components.len());

    for component in components {
        if component == "." {
            continue;
        } else if component == ".." {
            if !normalized_components.is_empty() && (&normalized_components != &[""]) {
                normalized_components.pop();
            }
        } else {
            normalized_components.push(component);
        }
    }

    normalized_components.join("/")
}

const UNRESERVED_CHARS: &[u8] =
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~";

#[pyfunction]
pub fn encode_percent(string: &str, safe: &str) -> String {
    let safe = safe.as_bytes();
    string
        .bytes()
        .map(|b| {
            if UNRESERVED_CHARS.contains(&b) || safe.contains(&b) {
                (b as char).to_string()
            } else {
                format!("%{:02X}", b)
            }
        })
        .collect::<String>()
}
