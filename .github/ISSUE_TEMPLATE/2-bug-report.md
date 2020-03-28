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

<!--
Provide steps to reproduce the bug locally.

An example is provided below, feel free to adapt it.
-->

1. Create and start a local server:

```python
# $ pip install starlette uvicorn
import uvicorn
from starlette import Starlette
from starlette.routing import Route
from starlette.responses import PlainTextResponse

async def home(request):
    return PlainTextResponse("Hello, world!")

app = Starlette(route=[Route("/", home)])

uvicorn.run(app)
```

2. Create a test script:

```python
import httpx

r = httpx.get("http://localhost:8000")
print(r)
```

4. Run the test script.
5. It raises an error (see traceback below).

### Expected behavior

<!-- A clear and concise description of what you expected to happen. -->

### Actual behavior

<!-- A clear and concise description of what actually happens. -->

### Additional material

<!--
Any tracebacks, screenshots, etc. that can help understanding the problem.

NOTE: if relevant, consider turning on DEBUG or TRACE logs for additional detail.
See: https://www.python-httpx.org/environment_variables/#httpx_log_level
-->

### Environment

- OS: <!-- eg Linux/Windows/macOS. -->
- Python version: <!-- eg 3.8.2 (get it with `$ python -V`). -->
- HTTPX version: <!-- eg 0.12.0 (get it with `$ pip show httpx`). -->
- HTTP proxies: <!-- yes/no/irrelevant, if yes please try reproducing without first. -->
- Custom certificates: <!-- yes/no/irrelevant, if yes please try reproducing without first. -->

### Additional context

<!--
Any additional information that can help understanding the problem,
eg. linked issues, or a description of what you were trying to achieve.
-->
