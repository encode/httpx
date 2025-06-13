use pyo3::prelude::*;

#[pymodule]
mod _httpx {
    #[pymodule_export]
    use crate::{
        urlparse::{percent_encoded, normalize_path},
        urls::QueryParams,
    };
}
