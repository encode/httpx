use pyo3::prelude::*;

#[pymodule(gil_used = false)]
mod _httpx {}
