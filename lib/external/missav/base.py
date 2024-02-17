from io import BytesIO
from typing import List, Optional

from PIL import Image
from lxml import etree

from lib.external.base import BaseApi, JavInfo, JavRecord

__all__ = ['MissAvApi']


class MissAvApi(BaseApi):
    source = "MissAV"
    url_domain = "https://missav.com"

    _keys = {
        "zh": {
            "serial_no": "番號",
            "title": "標題",
            "casts": "女優",
            "publish_date": "發行日期",
            "publisher": "發行商",
        },
        "cn": {
            "serial_no": "番号",
            "title": "标题",
            "casts": "女优",
            "publish_date": "发行日期",
            "publisher": "发行商",
        },
        "ja": {
            "serial_no": "品番",
            "title": "標題",
            "casts": "女優",
            "publish_date": "配信開始日",
            "publisher": "メーカー",
        },
    }

    @property
    def keys(self):
        return self._keys[self.lang]

    async def get_video_screenshot(self, serial_no: str) -> Image.Image:
        """

        Args:
            serial_no: str
                serial number string. e.g. "FC2-PPV-3076281"

        Returns:

        """

        url = f"https://eightcha.com/{serial_no.lower()}/cover.jpg"
        resp = await self._make_request(url)
        return Image.open(BytesIO(resp.content))

    async def search_by_keyword(self, keyword, page_no=1) -> List[JavRecord]:
        url = f"{self.url_domain_lang}/search/{keyword}?page={page_no}"
        resp = await self._make_request(url)

        elements = etree.HTML(resp.text).xpath(
            "//div[@x-data]/div/div/div[@class='my-2 text-sm text-nord4 truncate']/a")

        records = [
            JavRecord(
                keyword=element.get("alt"),
                title=element.text.strip(),
                url=element.get("href")
            ) for element in elements
        ]

        return records

    async def get_video_detail(self, serial_no_reg: str, with_thumbnail=False) -> Optional[JavInfo]:
        url_video_detail = f"{self.url_domain_lang}/{serial_no_reg}"
        resp = await self._make_request(url_video_detail, follow_redirects=True)
        if resp.status_code == 404:
            return None

        elements = (et := etree.HTML(resp.text)).xpath("//div[@class='space-y-2']/div")
        tmp = {
            (kvs := element.xpath("./*"))[0].text[:-1]: kvs[1].text for element in elements
        }

        # this title will change accordingly with language
        title_gen = et.xpath("//div[@class='mt-4']/h1/text()")[0].replace("\u3000", " ")
        casts = sorted(self.strip_all(tmp.get(self.keys["casts"], "").split(","), drop_empty_str=True))

        jav = JavInfo(
            serial_no=tmp[self.keys["serial_no"]],
            title=tmp.get(self.keys["title"], title_gen),  # FC2 prefer to use the title
            casts=casts,
            publish_date=tmp[self.keys["publish_date"]],
            thumbnail=(await self.get_video_screenshot(serial_no_reg)) if with_thumbnail else None,
        )
        return jav
