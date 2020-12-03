import httpx


if __name__ == '__main__':
    r = httpx.get('https://www.example.org/')
    r.cookies.set(name="foo", value="bar", domain="http://blah.com")
    r.cookies.set(name="fizz", value="buzz", domain="http://hello.com")
    print(repr(r.cookies))
