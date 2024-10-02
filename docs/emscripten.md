# Emscripten Support

httpx has support for running on Webassembly / Emscripten using [pyodide](https://github.com/pyodide/pyodide/). 

In Emscripten, all network connections are handled by the enclosing Javascript runtime. As such, there is limited control over various features. In particular:

- Proxy servers are handled by the runtime, so you cannot control them.
- httpx has no control over connection pooling.
- Certificate handling is done by the browser, so you cannot modify it.
- Requests are constrained by cross-origin isolation settings in the same way as any request that is originated by Javascript code.
- On browsers, timeouts will not work in the main browser thread unless your browser supports [Javascript Promise Integration](https://github.com/WebAssembly/js-promise-integration/blob/main/proposals/js-promise-integration/Overview.md). This is currently behind a flag on chrome, and not yet supported by non-chromium browsers.
- On node.js, synchronous requests will only work if you enable Javascript Promise Integration. You can do this using the `--experimental-wasm-stack-switching` flag when you run the node executable.

