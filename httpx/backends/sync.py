import time


class SyncBackend:
    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)
