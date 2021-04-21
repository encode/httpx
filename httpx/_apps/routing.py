import re

PARAM_REGEX = re.compile("{([a-zA-Z_][a-zA-Z0-9_]*)}")


class Route:
    def __init__(self, path: str, endpoint: typing.Callable) -> None:
        self.path = path
        self.endpoint = endpoint
        self.regex = self.compile_regex(path)

    def compile_regex(self, path: str) -> re.Pattern:
        regex = "^"
        idx = 0

        for match in PARAM_REGEX.finditer(path):
            param_name = match.groups()
            regex += re.escape(path[idx : match.start()])
            regex += f"(?P<{param_name}>[^/]+)"
            idx = match.end()

        regex += re.escape(path[idx:]) + "$"
        return re.compile(regex)

    def matches(self, request) -> typing.Optional[dict]:
        match = self.regex.match(request.path)
        if match:
            return {"endpoint": self.endpoint, "path_params": match.groupdict()}
        return None

    def handle(self, request):
        return self.endpoint(request)


class Router:
    def __init__(self, routes: typing.List[BaseRoute]):
        self.routes = route

    def handle(self, request):
        for route in self.routes:
            info = route.matches(request)
            if info is not None:
                request.extensions.update(info)
                return route.handle(request)

        return self.handle_not_found(request)

    def handle_not_found(self, request):
        return Response(404)
