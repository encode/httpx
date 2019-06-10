# QuickStart

First start by importing HTTP3:

```
>>> import http3
```

Now, let’s try to get a webpage. For this example, let’s get GitHub’s public timeline:

```python
>>> r = http3.get('https://api.github.com/events')
```

Similarly, to make an HTTP POST request:

```python
>>> r = http3.post('https://httpbin.org/post', data={'key': 'value'})
```

The PUT, DELETE, HEAD, and OPTIONS requests all follow the same style:

```python
>>> r = http3.put('https://httpbin.org/put', data={'key': 'value'})
>>> r = http3.delete('https://httpbin.org/delete')
>>> r = http3.head('https://httpbin.org/get')
>>> r = http3.options('https://httpbin.org/get')
```

## Passing Parameters in URLs

To include URL query parameters in the request, use the `params` keyword:

```python
>>> params = {'key1': 'value1', 'key2': 'value2'}
>>> r = http3.get('https://httpbin.org/get', params=params)
```

To see how the values get encoding into the URL string, we can inspect the
resulting URL that was used to make the request:

```python
>>> r.url
URL('https://httpbin.org/get?key2=value2&key1=value1')
```

You can also pass a list of items as a value:

```python
>>> params = {'key1': 'value1', 'key2': ['value2', 'value3']}
>>> r = http3.get('https://httpbin.org/get', params=params)
>>> r.url
URL('https://httpbin.org/get?key1=value1&key2=value2&key2=value3')
```
