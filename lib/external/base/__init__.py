from .common import JavInfo, JavRecord, BaseApi, BaseClient, SerialNoParser

default_proxies = {
    "http://": "http://127.0.0.1:10809",
    "https://": "http://127.0.0.1:10809",
}
