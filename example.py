import httpx
import time
import requests

url = "https://httpbin.org/stream-bytes/50000000"

start = time.time()
r = requests.get(url)
print("requests %.1f s" % (time.time() - start))

for http_version in ["HTTP/1.1", "HTTP/2"]:
    client = httpx.Client(http_versions=http_version)

    start = time.time()
    r = client.get(url)
    print("httpx %s %.1f s" % (http_version, time.time() - start))
    print(r.http_version)
