# Request content

...

## Binary and text content

```python
client.post(content=...)
```

## Form data

### URL encoded forms

```python
client.post(data=...)
```

### Multipart forms

```python
client.post(data=..., files=...)
```

## JSON

```python
client.post(json=...)
```

## Streaming binary data

```python
client.post(stream=...)
```
