use pyo3::prelude::*;

#[pymodule(gil_used = false)]
mod _httpx {
    use super::*;

    #[pymodule]
    mod urlparse {
        #[pymodule_export]
        use crate::urlparse::ParseResult;
    }
}
