use pyo3::{exceptions::PyException, prelude::*};

#[pyclass(extends=PyException, name = "InvalidURL", subclass)]
pub struct InvalidUrl {
    #[pyo3(get)]
    message: String,
}

#[pymethods]
impl InvalidUrl {
    #[new]
    pub fn new(message: &str) -> Self {
        Self {
            message: message.to_string(),
        }
    }
}

impl From<InvalidUrl> for PyErr {
    fn from(err: InvalidUrl) -> Self {
        PyErr::new::<InvalidUrl, _>(err.message)
    }
}

#[pyclass(extends=PyException, subclass)]
pub struct CookieConflict {
    #[pyo3(get)]
    message: String,
}

#[pymethods]
impl CookieConflict {
    #[new]
    pub fn new(message: &str) -> Self {
        Self { message: message.to_string() }
    }
}

impl From<CookieConflict> for PyErr {
    fn from(err: CookieConflict) -> Self {
        PyErr::new::<CookieConflict, _>(err.message)
    }
}
