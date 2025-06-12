use pyo3::prelude::*;

#[pymodule]
mod _httpx {
    #[pymodule_export]
    use crate::{urlparse::normalize_path, urls::QueryParams};
}
