use pyo3::prelude::*;

#[pymodule]
mod _httpx {
    #[pymodule_export]
    use crate::urls::QueryParams;
}
