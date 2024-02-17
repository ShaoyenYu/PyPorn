import datetime as dt
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Tuple

import httpx
from PIL.Image import Image

__all__ = ["BaseApi", "BaseClient", "JavInfo", "JavRecord", "SerialNoParser"]


@dataclass
class JavRecord:
    keyword: str
    title: str
    url: str


@dataclass
class JavInfo:
    def __init__(
            self,
            serial_no: str,
            title: Optional[str] = "",
            casts: Optional[List[str]] = None,
            publish_date: Optional[str] = "",
            thumbnail: Optional[Image] = None,
            length: Optional[int] = 0,

            maker: Optional[str] = "",
            publisher: Optional[str] = "",
            director: Optional[str] = "",
    ):
        self.serial_no = serial_no
        self._title, self._title_original = None, title
        self.casts = casts
        self.publish_date = publish_date
        self.thumbnail = thumbnail
        self.length = length
        self.maker = maker
        self.publisher = publisher
        self.director = director

    @property
    def title(self) -> str:
        if self._title is None:
            self._title = self._title_original.replace(self.serial_no, "").strip()
        return self._title

    def show_info(self):
        print(self.__repr__())

    def __repr__(self):
        s = "\n".join((
            f"Publish Date: {self.publish_date}",
            f"Serial No   : {self.serial_no}",
            f"Publisher   : {self.publisher}",
            f"Title       : {self.title}",
            f"Casts       : {self.casts}",
        ))
        return s

    def __str__(self):
        return f"{self.publish_date} {self.serial_no} {self.title} ({'&'.join(self.casts)})"


class BaseApi(ABC):
    source = ""
    url_domain = ""
    _lang = "ja"

    def __init__(self, session: httpx.AsyncClient):
        self.session = session

    @property
    def lang(self):
        return self._lang

    @lang.setter
    def lang(self, value):
        assert value in {"zh", "cn", "ja"}
        self._lang = value

    @property
    def url_domain_lang(self):
        return f"{self.url_domain}/{self.lang}"

    @staticmethod
    def strip_all(strings: List[str], drop_empty_str=False) -> List[str]:
        if drop_empty_str:
            return [x_strip for x in strings if (x_strip := x.strip()) != ""]
        return [x.strip() for x in strings]

    def _make_request(self, url: str, **kwargs):
        resp = self.session.get(url, **kwargs)
        return resp

    @abstractmethod
    def search_by_keyword(self, keyword: str) -> List[JavRecord]:
        pass

    @abstractmethod
    def get_video_detail(self, serial_no: str) -> JavInfo:
        pass


class BaseClient(ABC):
    def __init__(self, **session_args):
        self.session = self.prepare_session(**session_args)

    default_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36",
        "Proxy-Connection": "keep-alive",
    }

    def prepare_session(self, **session_args):
        session = httpx.AsyncClient(
            proxies=session_args.get("proxies"),
            headers=self.default_headers,
        )
        return session


class SerialNoParser:
    tmp = set()
    # General
    split = r"[ -_]"
    split_possible = f"{split}??"
    split_must = f"{split}{{1}}"

    # 01. FC2
    serial_no_fc2 = r"\d{6,7}"
    prefixes_fc2 = "|".join((
        f"FC2{split_possible}PPV",
        f"FC{split_possible}PPV",
        f"FC2",
        f"FC",
    ))
    patt_fc2 = re.compile(f"({prefixes_fc2}){split_possible}({serial_no_fc2})")

    # 02. Censored
    serial_prefix_censored = "[A-Z]{3,5}"
    serial_no_censored = r"(?<![\d])\d{3,4}"
    patt_censored = re.compile(f"(?<![a-zA-Z])({serial_prefix_censored}){split_possible}({serial_no_censored})")

    # 03. UnCensored (1PONDO, CARIBBEAN)
    year_suffix = f"{dt.date.today().year}"[-2:]
    serial_prefix_dpr = r"[0-1]\d[0-3]{1}\d[0-3]\d"  # mmddyy
    serial_no_dpr = r"(?<![\d])\d{3}"
    patt_dpr = re.compile(f"(?<![0-9])({serial_prefix_dpr}){split_must}({serial_no_dpr})")

    @staticmethod
    def clean_serial_no(serial_no: str) -> str:
        return serial_no.strip().upper()

    @classmethod
    def parse_serial_no(cls, serial_no: str, extend_fc2_from_no: bool = False) -> Optional[str]:
        serial_no_clean = cls.clean_serial_no(serial_no)

        if (res := cls._parse_serial_no_fc2(serial_no_clean, extend_fc2_from_no)) is not None:
            # print(res, "<" + "-" * 5, serial_no_clean)
            return res

        if (res := cls._parse_serial_no_general(serial_no_clean)) is not None:
            # print(res, "<" + "-" * 5, serial_no_clean)
            return res

        if (res := cls._parse_serial_no_dpr(serial_no_clean)) is not None:
            # print(res, "<" + "-" * 5, serial_no_clean)
            return res

        # print(f"False: {serial_no}")
        return None

    @staticmethod
    def _parse_by_pattern(serial_no, pattern) -> Tuple[Optional[str], Optional[str]]:
        if (matched := pattern.search(serial_no)) is not None:
            prefix, number = matched.groups()[0:2]
            return prefix, number
        return None, None

    @classmethod
    def _parse_serial_no_general(cls, serial_no: str) -> Optional[str]:
        prefix, number = cls._parse_by_pattern(serial_no, cls.patt_censored)
        return f"{prefix}-{number}" if prefix is not None else None

    @classmethod
    def _parse_serial_no_dpr(cls, serial_no: str) -> Optional[str]:
        prefix, number = cls._parse_by_pattern(serial_no, cls.patt_dpr)
        if prefix is None:
            return None

        if (last_two_digit := prefix[-2:]).isnumeric() and last_two_digit[-2:] > cls.year_suffix:
            print(prefix, serial_no)
            return None
        return f"{prefix}_{number}" if prefix is not None else None

    @classmethod
    def _parse_serial_no_fc2(cls, serial_no: str, extend_fc2_from_no: bool = False) -> Optional[str]:
        prefix, number = cls._parse_by_pattern(serial_no, cls.patt_fc2)

        if number is not None:
            return f"FC2-PPV-{number}" if prefix is not None else None

        if extend_fc2_from_no and (6 <= len(serial_no) <= 7) and serial_no.isnumeric():
            return f"FC2-PPV-{serial_no}"
        return None


class SerialNo:
    def __init__(self, prefix, no, publisher=None):
        self.prefix, self.no = prefix, no
