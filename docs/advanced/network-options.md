There are several advanced network options that are made available through the `httpx.NetworkOptions` configuration class.

```python
# Configure an HTTPTransport with some specific network options.
network_options = httpx.NetworkOptions(
    connection_retries=1,
    local_address="0.0.0.0",
)
transport = httpx.HTTPTransport(network_options=network_options)

# Instantiate a client with the configured transport.
client = httpx.Client(transport=transport)
```

## Configuration

The options available on this class are...

### `connection_retries`

Configure a number of retries that may be attempted when initially establishing a TCP connection. Defaults to `0`.

### `local_address`

Configure the local address that the socket should be bound too. The most common usage is for enforcing binding to either IPv4 `local_address="0.0.0.0"` or IPv6 `local_address="::"`.

### `socket_options`

*TODO: Example*

### `uds`

Connect to a Unix Domain Socket, rather than over the network. Should be a string providing the path to the UDS.