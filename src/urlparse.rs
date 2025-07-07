use pyo3::prelude::*;

use crate::err::InvalidUrl;

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

const UNRESERVED_CHARS: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~";

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
        if s[i] == b'%' && i + 2 < s.len() && is_percent_encoded(&s[i..i + 3]) {
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

#[pyfunction]
pub fn find_ascii_non_printable(s: &str) -> Option<usize> {
    s.chars()
        .position(|c| c.is_ascii() && !c.is_ascii_graphic() && c != ' ')
}

pub(crate) trait PercentEncoded {
    fn percent_encoded(&self, safe: &str) -> String;
}

impl PercentEncoded for String {
    fn percent_encoded(&self, safe: &str) -> String {
        quote(self, safe)
    }
}

impl PercentEncoded for &str {
    fn percent_encoded(&self, safe: &str) -> String {
        quote(self, safe)
    }
}

#[pyfunction]
pub fn validate_path(path: &str, has_scheme: bool, has_authority: bool) -> PyResult<()> {
    if has_authority && !path.is_empty() && !path.starts_with('/') {
        return Err(InvalidUrl::new("For absolute URLs, path must be empty or begin with '/'").into());
    }

    if !has_scheme && !has_authority {
        if path.starts_with("//") {
            return Err(InvalidUrl::new("Relative URLs cannot have a path starting with '//'").into());
        }
        if path.starts_with(':') {
            return Err(InvalidUrl::new("Relative URLs cannot have a path starting with ':'").into());
        }
    }

    Ok(())
}
