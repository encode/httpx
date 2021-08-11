# Announcing HTTPX 1.0

HTTPX is a fully featured HTTP client for Python, which offers both HTTP/1.1 and HTTP/2 support. Learning from all of the functionality and ease of use that the fantastic `requests` library provides, while bringing additional features and keeping pace with HTTP as it evolves.

* An API that is broadly compatible with `requests`.
* Fully supports all the features that the `requests` package provides.
* Both HTTP/1.1 and HTTP/2 support.
* Strict request timeouts enabled by default.
* Support for the asyncio and trio concurrency environments.
* A fully type annotated interface, with 100% code coverage.
* Development & maintenance that's backed by a sustainable and transparent business model.

HTTPX is the *only Python HTTP client with HTTP/1.1 and HTTP/2 support*, as well as being the *only client providing both sync and async support*. We'd like to continue pushing the project forward, and we're asking for sponsors to help us in building the foundation of modern HTTP stack for Python.

## Sponsorship plans

We offer a number of sponsorship plans

[Sign up as a sponsor](https://github.com/sponsors/encode){ .md-button }

## Roadmap

### HTTPX 1.1

Released alongside a new version of `httpcore`, which will expose a lower-level API onto the core networking. This will allow users to dig further into the underlying behaviour, such as inspecting the state of the connection pool. Support for custom network transports will allow functionality such as record/replay to be elegantly implemented. This version will also add SOCKs proxy support.

### HTTPX 1.2

This version will add an integrated command line client to HTTPX, allowing for developers to easily switch between debugging HTTP requests from the console, and within their own codebases. You'll be able to switch easily between the two, with a consistent interface onto both sets of tools.

### HTTPX 1.3 & beyond...

Resource limits for the total download time, and maximum allowed download size. Support for WebSockets which run transparently over either HTTP/1.1 or HTTP/2. Documentation for using advanced functionality such as HTTP/2 bi-directional streaming, or working with network streams established using CONNECT or Upgrade requests. Support for a URLLib3 backend, which will aid projects that want upgrade from requests but still keep the underlying networking changes to an absolute minimum.

### Meticulous attention to detail throughout

A world-class HTTP client ought to serve both as a tool and as a learning resource. Having a sustainable business model for the development of HTTPX will allow us to continue to dedicate an exceptional level of quality to the package throughout, both within the documentation, and the codebase.

* Documentation that guides users through every aspect of the HTTPX library, and how it all fits together, while being accessible to both newcomers and experienced developers.
* Ensuring that any error messages guide users towards resolution with clarity and precision.
* Every object within HTTPX ought to provide informative `__repr__` messages, helping developers fully understand the state of any instances they're working with.
* Comprehensive logging that will allow users to dig into a fuller understanding of every part of the HTTP request/response cycle.
* Exposing a low level networking API, allowing developers to drop into the library at whatever level of detail and precision is required. This will allow the development of features such as record/replay of network traffic, customisation of DNS lookups, and alternate connection pooling strategies.

### A sustainable and transparent business model

Throughout the project we'll be issuing weekly progress reports, to give your businesses confidence that

We'll also be delivering monthly finance reports, giving complete transparency onto the business operating costs, revenue, and balance.
