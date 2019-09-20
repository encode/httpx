# httpxprof

A tool for profiling [HTTPX](https://github.com/encode/httpx) using cProfile and [SnakeViz](https://jiffyclub.github.io/snakeviz/).

## Usage

```bash
httpxprof 
# Start the supporting server:
httpxprof serve

# In another terminal, run a benchmark:
httpxprof run async

# View benchmark results:
httpxprof view async
```

You can ask for `--help` on `httpxprof` and any of the subcommands.

## Installation

```bash
# From the HTTPX project root directory:
pip install -e tools/httpxprof

# From this directory:
pip install -e .
```

`httpxprof` assumes it can `import httpx`, so you need to have HTTPX installed (either from local or PyPI).
