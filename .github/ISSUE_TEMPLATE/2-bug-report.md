---
name: Bug report
about: Report a bug to help improve this project
---

### Checklist

<!-- Please make sure you check all these items before submitting your bug report. -->

- [ ] The bug is reproducible against the latest release and/or `master`.
- [ ] There are no similar issues or pull requests to fix it yet.

### Describe the bug

<!-- A clear and concise description of what the bug is. -->

### To reproduce

<!-- Provide a *minimal* example with steps to reproduce the bug locally.

NOTE: try to keep any external dependencies *at an absolute minimum* (servers, proxies, certificates...).
In other words, remove anything that doesn't make the bug go away.

If you need a local server to replicate against, you can build one using eg. Starlette [0] and Uvicorn [1], or any tool you feel comfortable with. Check out other issues for examples and remember to share setup instructions here. :-)

[0]: https://www.starlette.io
[1]: https://www.uvicorn.org
-->

### Expected behavior

<!-- A clear and concise description of what you expected to happen. -->

### Actual behavior

<!-- A clear and concise description of what actually happens. -->

### Debugging material

<!-- Any tracebacks, screenshots, etc. that can help understanding the problem.

NOTE:
- Please list tracebacks in full (don't truncate them).
- If relevant, consider turning on DEBUG or TRACE logs for additional details (see https://www.python-httpx.org/environment_variables/#httpx_log_level).
- Consider using `<details>` to make tracebacks/logs collapsible if they're very large (see https://gist.github.com/ericclemmons/b146fe5da72ca1f706b2ef72a20ac39d).
-->

### Environment

- OS: <!-- eg Linux/Windows/macOS. -->
- Python version: <!-- eg 3.8.2 (get it with `$ python -V`). -->
- HTTPX version: <!-- eg 0.12.0 (get it with `$ pip show httpx`). -->
- Async environment: <!-- eg asyncio/trio. If using asyncio, include whether the bug reproduces on trio (and vice versa). -->
- HTTP proxy: <!-- yes/no, if yes please try reproducing without it. -->
- Custom certificates: <!-- yes/no, if yes please try reproducing without them. If the bug is related to SSL/TLS, you can setup HTTPS on a local server using these instructions: https://www.python-httpx.org/advanced/#making-https-requests-to-a-local-server. -->

### Additional context

<!-- Any additional information that can help understanding the problem.

Eg. linked issues, or a description of what you were trying to achieve. -->
