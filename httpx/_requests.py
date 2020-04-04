import importlib
import httpx


def from_requests(session) -> httpx.AsyncClient:
    """
    Converts session object from requests libarary to AsyncClient
        :param session: session object of type requests.Session
        :return: httpx.AsyncClient
    """
    requests_spec = importlib.util.find_spec("requests")
    if not requests_spec:
        raise Exception("requrests library is requried for this functionality")

    import requests

    if not isinstance(session, requests.Session):
        raise Exception("session is not an instance of requests.Session")

    headers = dict(session.headers)
    cookies = httpx.Cookies()
    for c in session.cookies:
        cookies.set(name=c.name, value=c.value, domain=c.domain, path=c.path)

    return httpx.AsyncClient(
        headers=headers,
        cookies=cookies,
        verify=session.verify,
        trust_env=session.trust_env,
    )
