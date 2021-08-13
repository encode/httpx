# Contributing

Thank you for being interested in contributing to HTTPX.
There are many ways you can contribute to the project:

- Try HTTPX and [report bugs/issues you find](https://github.com/encode/httpx/issues/new)
- [Implement new features](https://github.com/encode/httpx/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
- [Review Pull Requests of others](https://github.com/encode/httpx/pulls)
- Write documentation
- Participate in discussions

## Reporting Bugs or Other Issues

Found something that HTTPX should support?
Stumbled upon some unexpected behaviour?

Contributions should generally start out with [a discussion](https://github.com/encode/httpx/discussions).
Possible bugs may be raised as a "Potential Issue" discussion, feature requests may
be raised as an "Ideas" discussion. We can then determine if the discussion needs
to be escalated into an "Issue" or not, or if we'd consider a pull request.

Try to be more descriptive as you can and in case of a bug report,
provide as much information as possible like:

- OS platform
- Python version
- Installed dependencies and versions (`python -m pip freeze`)
- Code snippet
- Error traceback

You should always try to reduce any examples to the *simplest possible case*
that demonstrates the issue.

Some possibly useful tips for narrowing down potential issues...

- Does the issue exist on HTTP/1.1, or HTTP/2, or both?
- Does the issue exist with `Client`, `AsyncClient`, or both?
- When using `AsyncClient` does the issue exist when using `asyncio` or `trio`, or both?

## Development

To start developing HTTPX create a **fork** of the
[HTTPX repository](https://github.com/encode/httpx) on GitHub.

Then clone your fork with the following command replacing `YOUR-USERNAME` with
your GitHub username:

```shell
$ git clone https://github.com/YOUR-USERNAME/httpx
```

You can now install the project and its dependencies using:

```shell
$ cd httpx
$ scripts/install
```

## Testing and Linting

We use custom shell scripts to automate testing, linting,
and documentation building workflow.

To run the tests, use:

```shell
$ scripts/test
```

!!! warning
    The test suite spawns testing servers on ports **8000** and **8001**.
    Make sure these are not in use, so the tests can run properly.

Any additional arguments will be passed to `pytest`. See the [pytest documentation](https://docs.pytest.org/en/latest/how-to/usage.html) for more information.

For example, to run a single test script:

```shell
$ scripts/test tests/test_multipart.py
```

To run the code auto-formatting:

```shell
$ scripts/lint
```

Lastly, to run code checks separately (they are also run as part of `scripts/test`), run:

```shell
$ scripts/check
```

## Documenting

Documentation pages are located under the `docs/` folder.

To run the documentation site locally (useful for previewing changes), use:

```shell
$ scripts/docs
```

## Resolving Build / CI Failures

Once you've submitted your pull request, the test suite will automatically run, and the results will show up in GitHub.
If the test suite fails, you'll want to click through to the "Details" link, and try to identify why the test suite failed.

<p align="center" style="margin: 0 0 10px">
  <img src="https://raw.githubusercontent.com/encode/httpx/master/docs/img/gh-actions-fail.png" alt='Failing PR commit status'>
</p>

Here are some common ways the test suite can fail:

### Check Job Failed

<p align="center" style="margin: 0 0 10px">
  <img src="https://raw.githubusercontent.com/encode/httpx/master/docs/img/gh-actions-fail-check.png" alt='Failing GitHub action lint job'>
</p>

This job failing means there is either a code formatting issue or type-annotation issue.
You can look at the job output to figure out why it's failed or within a shell run:

```shell
$ scripts/check
```

It may be worth it to run `$ scripts/lint` to attempt auto-formatting the code
and if that job succeeds commit the changes.

### Docs Job Failed

This job failing means the documentation failed to build. This can happen for
a variety of reasons like invalid markdown or missing configuration within `mkdocs.yml`.

### Python 3.X Job Failed

<p align="center" style="margin: 0 0 10px">
  <img src="https://raw.githubusercontent.com/encode/httpx/master/docs/img/gh-actions-fail-test.png" alt='Failing GitHub action test job'>
</p>

This job failing means the unit tests failed or not all code paths are covered by unit tests.

If tests are failing you will see this message under the coverage report:

`=== 1 failed, 435 passed, 1 skipped, 1 xfailed in 11.09s ===`

If tests succeed but coverage doesn't reach our current threshold, you will see this
message under the coverage report:

`FAIL Required test coverage of 100% not reached. Total coverage: 99.00%`

## Releasing

*This section is targeted at HTTPX maintainers.*

Before releasing a new version, create a pull request that includes:

- **An update to the changelog**:
    - We follow the format from [keepachangelog](https://keepachangelog.com/en/1.0.0/).
    - [Compare](https://github.com/encode/httpx/compare/) `master` with the tag of the latest release, and list all entries that are of interest to our users:
        - Things that **must** go in the changelog: added, changed, deprecated or removed features, and bug fixes.
        - Things that **should not** go in the changelog: changes to documentation, tests or tooling.
        - Try sorting entries in descending order of impact / importance.
        - Keep it concise and to-the-point. 🎯
- **A version bump**: see `__version__.py`.

For an example, see [#1006](https://github.com/encode/httpx/pull/1006).

Once the release PR is merged, create a
[new release](https://github.com/encode/httpx/releases/new) including:

- Tag version like `0.13.3`.
- Release title `Version 0.13.3`
- Description copied from the changelog.

Once created this release will be automatically uploaded to PyPI.

If something goes wrong with the PyPI job the release can be published using the
`scripts/publish` script.

## Development proxy setup

To test and debug requests via a proxy it's best to run a proxy server locally.
Any server should do but HTTPCore's test suite uses
[`mitmproxy`](https://mitmproxy.org/) which is written in Python, it's fully
featured and has excellent UI and tools for introspection of requests.

You can install `mitmproxy` using `pip install mitmproxy` or [several
other ways](https://docs.mitmproxy.org/stable/overview-installation/).

`mitmproxy` does require setting up local TLS certificates for HTTPS requests,
as its main purpose is to allow developers to inspect requests that pass through
it. We can set them up follows:

1. [`pip install trustme-cli`](https://github.com/sethmlarson/trustme-cli/).
2. `trustme-cli -i example.org www.example.org`, assuming you want to test
connecting to that domain, this will create three files: `server.pem`,
`server.key` and `client.pem`.
3. `mitmproxy` requires a PEM file that includes the private key and the
certificate so we need to concatenate them:
`cat server.key server.pem > server.withkey.pem`.
4. Start the proxy server `mitmproxy --certs server.withkey.pem`, or use the
[other mitmproxy commands](https://docs.mitmproxy.org/stable/) with different
UI options.

At this point the server is ready to start serving requests, you'll need to
configure HTTPX as described in the
[proxy section](https://www.python-httpx.org/advanced/#http-proxying) and
the [SSL certificates section](https://www.python-httpx.org/advanced/#ssl-certificates),
this is where our previously generated `client.pem` comes in:

```
import httpx

proxies = {"all": "http://127.0.0.1:8080/"}

with httpx.Client(proxies=proxies, verify="/path/to/client.pem") as client:
    response = client.get("https://example.org")
    print(response.status_code)  # should print 200
```

Note, however, that HTTPS requests will only succeed to the host specified
in the SSL/TLS certificate we generated, HTTPS requests to other hosts will
raise an error like:

```
ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate
verify failed: Hostname mismatch, certificate is not valid for
'duckduckgo.com'. (_ssl.c:1108)
```

If you want to make requests to more hosts you'll need to regenerate the
certificates and include all the hosts you intend to connect to in the
seconds step, i.e.

`trustme-cli -i example.org www.example.org duckduckgo.com www.duckduckgo.com`
