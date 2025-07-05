use pyo3::prelude::*;

#[pymodule]
mod _httpx {
    #[pymodule_export]
    use crate::{
        models::utils::unquote,
        urlparse::{find_ascii_non_printable, normalize_path, quote},
        urls::QueryParams,
    };
}
