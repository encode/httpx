use pyo3::prelude::*;

#[pymodule]
mod _httpx {
    #[pymodule_export]
    use crate::{
        urlparse::{encode_percent, normalize_path},
        urls::QueryParams,
    };
}
