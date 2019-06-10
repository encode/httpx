# QuickStart

First start by importing LiveWire:

```
>>> import livewire
```

Now, let’s try to get a webpage. For this example, let’s get GitHub’s public timeline:

```python
>>> r = livewire.get('https://api.github.com/events')
```

Similarly, to make an HTTP POST request:

```python
>>> r = livewire.post('https://httpbin.org/post', data={'key': 'value'})
```

The PUT, DELETE, HEAD, and OPTIONS requests all follow the same style:

```python
>>> r = livewire.put('https://httpbin.org/put', data={'key': 'value'})
>>> r = livewire.delete('https://httpbin.org/delete')
>>> r = livewire.head('https://httpbin.org/get')
>>> r = livewire.options('https://httpbin.org/get')
```

## Passing Parameters in URLs

To include URL query parameters in the request, use the `params` keyword:

```python
>>> params = {'key1': 'value1', 'key2': 'value2'}
>>> r = livewire.get('https://httpbin.org/get', params=params)
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
>>> r = livewire.get('https://httpbin.org/get', params=params)
>>> r.url
URL('https://httpbin.org/get?key1=value1&key2=value2&key2=value3')
```
