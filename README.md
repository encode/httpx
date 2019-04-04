# HTTPCore

I started to dive into implementation and API design here.

I know this isn't what you were suggesting with `requests-core`, but it'd be
worth you taking a slow look at this and seeing if there's anything that you
think is a no-go.

`httpcore` provides the same proposed *functionality* as requests-core, but at a slightly
lower abstraction level.

Rather than returning `Response` models, it returns the minimal possible
interface. There's no `response.text` or any other cleverness, `response.headers`
are plain byte-pair lists, rather than a headers datastructure etc...

**The proposal here is that `httpcore` would be a silent-partner dependency of `requests3`,
taking the place of the existing `urllib3` dependency.**

---

The benefits to my mind of this level of abstraction are that it is as
agnostic as possible to whatever request/response models are built on top
of it, and exposes only plain datastructures that reflect the network response.

* An `encode/httpcore` package would be something I'd gladly maintain. The naming
  makes sense to me, as there's no strictly implied relationship to `requests`,
  although it would fulfil all the requirements for `requests3` to build on,
  and would have a strict semver policy.
* An `encode/httpcore` package is something that would play in well to the
  collaboratively sponsored OSS story that Encode is pitching. It'd provide what
  you need for `requests3` without encroaching on the `requests` brand.
  We'd position it similarly to how `urllib3` is positioned to `requests` now.
  A focused, low-level networking library, that `requests` then builds the
  developer-focused API on top of.
* The current implementation includes all the async API points.
  The `PoolManger.request()` and `PoolManager.close()` methods are currently
  stubbed-out. All the remaining implementation hangs off of those two points.
* Take a quick look over the test cases or the package itself to get a feel
  for it. It's all type annotated, and should be easy to find your way around.
* I've not yet added corresponding sync API points to the implementation, but
  they will come.
* There's [a chunk of implmentation work towards connection pooling in `requests-async`](https://github.com/encode/requests-async/blob/5ec2aa80bd4499997fa744f3be19a0bdeccbaeed/requests_async/connections.py). I've not had enough time to nail it yet, but it's got the broad brush-strokes, and given me enough to get a rough feel for how much work there is to do.
* We would absolutely want to implement HTTP/2 support.
* Trio support is something that could *potentially* come later, but it needs to
  be a secondary consideration.
* I think all the functionality required is stubbed out in the API, with two exceptions.
  (1) I've not yet added any proxy configuration API. Haven't looked into that enough
  yet. (2) I've not yet added any retry configuration API, since I havn't really
  looked enough into which side of requests vs. urllib3 that sits on, or exactly how
  urllib3 tackles retries, etc.
* I'd be planning to prioritize working on this from Mon 15th April. I don't think
  it'd take too long to get it to a feature complete and API stable state.
  (With the exception of the later HTTP/2 work, which I can't really assess yet.)
  I probably don't have any time left before then - need to focus on what I'm
  delivering to DjangoCon Europe over the rest of this week.
* To my mind the killer app for `requests3`/`httpcore` is a high-performance
  proxy server / gateway service in Python. Pitching the growing ASGI ecosystem
  is an important part of that story.
* I think there's enough headroom before PyCon to have something ready to pitch by then.
  I could be involved in sprints remotely if there's areas we still need to fill in,
  anyplace.

```python
import httpcore

response = await httpcore.request('GET', 'http://example.com')
assert response.status_code == 200
assert response.body == b'Hello, world'
```

Top-level API...

```python
response = await httpcore.request(method, url, [headers], [body], [stream])
```

Explicit PoolManager...

```python
async with httpcore.PoolManager([ssl], [timeout], [limits]) as pool:
    response = await pool.request(method, url, [headers], [body], [stream])
```

Streaming...

```python
response = await httpcore.request(method, url, stream=True)
async for part in response.stream():
    ...
```
