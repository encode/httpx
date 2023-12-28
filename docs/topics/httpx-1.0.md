**TODO**: Let's use this space to document and explain 1.0 API changes.

* ...
* timing

## SSL

* The `verify` and `cert` keyword arguments are removed, and should instead be used on an `httpx.SSLContext(verify=..., cert=...)` configuration instance.
* The `SSL_CERT_FILE`, `SSL_CERT_DIR`, `SSLKEYLOGFILENAME` environment variables are no longer automatically handled.

## URLs

...