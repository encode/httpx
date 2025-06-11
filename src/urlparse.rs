use pyo3::prelude::*;

#[pyclass]
pub struct ParseResult {
    scheme: String,
    userinfo: String,
    host: String,
    port: Option<String>,
    path: String,
    query: Option<String>,
    fragment: Option<String>,
}

#[pymethods]
impl ParseResult {
    #[new]
    pub fn new(
        scheme: String,
        userinfo: String,
        host: String,
        port: Option<String>,
        path: String,
        query: Option<String>,
        fragment: Option<String>,
    ) -> Self {
        ParseResult {
            scheme,
            userinfo,
            host,
            port,
            path,
            query,
            fragment,
        }
    }

    #[getter]
    pub fn authority(&self) -> String {
        let mut authority = String::new();
        if !self.userinfo.is_empty() {
            authority.push_str(&format!("{}@", &self.userinfo));
        }
        authority.push_str(&self.netloc());
        authority
    }

    #[getter]
    pub fn netloc(&self) -> String {
        let mut netloc = String::new();
        if self.host.contains(":") {
            netloc.push_str(&format!("[{}]", &self.host));
        } else {
            netloc.push_str(&self.host);
        }
        if let Some(port) = &self.port {
            netloc.push_str(&format!(":{}", port));
        }
        netloc
    }

    pub fn __str__(&self) -> String {
        let mut result = String::new();
        if !self.scheme.is_empty() {
            result.push_str("//")
        } else {
            result.push_str(&self.scheme);
            result.push_str("://");
        }
        result.push_str(&self.authority());
        result.push_str(&self.path);

        if let Some(query) = &self.query {
            result.push_str(&format!("?{}", query));
        }

        if let Some(fragment) = &self.fragment {
            result.push_str(&format!("#{}", fragment));
        }

        result
    }
}
