# Contributing

You are welcome to contribute with **HTTPX**, read this guide carefully to
understand how to setup your environment.

## Development

To start developing **HTTPX** create a **fork** of the
[httpx repository](https://github.com/encode/httpx) on GitHub.

Then clone your fork with the following command replacing `YOUR-USERNAME` with
your GitHub username:

```shell
$ git clone https://github.com/YOUR-USERNAME/httpx
```

## Testing

We use [nox](https://nox.thea.codes/en/stable/) as testing tool, so before
testing make sure you have it installed at your system.

You can install nox with:

```shell
$ python3 -m pip install --user nox
```

Or if you prefer to keep it into an isolated environment you can install it
using [pipx](https://github.com/pipxproject/pipx):

```shell
$ pipx install nox
```

Now with nox installed you can run the tests by running:

```shell
$ nox
```

!!! warning
    The test suite spawns a testing server at the port **8000**.
    Make sure this isn't being used, so the tests can run properly.
