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

pub fn percent_encoded(string: &str, safe: &str) -> String {
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

fn is_percent_encoded(s: &[u8]) -> bool {
    s.len() == 3 && s[0] == b'%' && s[1].is_ascii_hexdigit() && s[2].is_ascii_hexdigit()
}

#[pyfunction]
pub fn quote(string: &str, safe: &str) -> String {
    let s = string.as_bytes();
    let mut result = String::with_capacity(s.len());

    let mut start = 0;
    let mut i = 0;
    while i < s.len() {
        if i + 2 < s.len() && s[i] == b'%' && is_percent_encoded(&s[i..i + 3]) {
            if start < i {
                result.push_str(&percent_encoded(&string[start..i], safe));
            }
            result.push_str(&string[i..i + 3]);
            i += 3;
            start = i;
        } else {
            i += 1;
        }
    }

    if start < s.len() {
        result.push_str(&percent_encoded(&string[start..], safe));
    }

    result
}
