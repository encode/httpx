use pyo3::prelude::*;

#[pyfunction]
pub fn unquote(value: &str) -> String {
    if value.starts_with('"') && value.ends_with('"') {
        value[1..value.len() - 1].to_string()
    } else if value.starts_with('\'') && value.ends_with('\'') {
        value[1..value.len() - 1].to_string()
    } else {
        value.to_string()
    }
}
