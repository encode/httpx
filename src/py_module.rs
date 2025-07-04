use pyo3::prelude::*;

#[pymodule]
mod _httpx {
    #[pymodule_export]
    use crate::{
        models::utils::unquote,
        urlparse::{normalize_path, quote},
        urls::QueryParams,
    };
}
