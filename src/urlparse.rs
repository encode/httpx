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
