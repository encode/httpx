import typing


class LookupDict(dict):
    """Dictionary lookup object."""

    def __init__(self, name: str = None) -> None:
        self.name = name
        super(LookupDict, self).__init__()

    def __repr__(self) -> str:
        return "<lookup '%s'>" % (self.name)

    def __getitem__(self, key: typing.Any) -> typing.Any:
        # We allow fall-through here, so values default to None

        return self.__dict__.get(key, None)

    def get(self, key: typing.Any, default: typing.Any = None) -> typing.Any:
        return self.__dict__.get(key, default)
