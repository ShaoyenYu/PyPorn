import re
from io import BytesIO
from typing import List, Optional

from PIL import Image
from lxml import etree

from lib.external.base import BaseApi, JavInfo, JavRecord

__all__ = ["JavLibraryApi"]


class JavLibraryApi(BaseApi):
    source = "JavLibrary"
    url_domain = "https://www.javlibrary.com"

    patt_video_id = re.compile(r"\./\?v=(.*)")

    def _get_video_detail(self, video_id):
        url_video_detail = f"{self.url_domain_lang}/?v={video_id}"
        return self._make_request(url_video_detail)

    async def search_by_keyword(self, keyword: str, page_no=1) -> List[JavRecord]:
        url_video_list = f"{self.url_domain_lang}/vl_searchbyid.php?keyword={keyword}&page={page_no}"
        resp = await self._make_request(url_video_list, follow_redirects=False)

        if resp.status_code == 200:  # which means found multiple results by keyword
            et_videos = etree.HTML(resp.text).xpath(".//div[@class='videos']/div[@class='video']/a")
            res = [
                JavRecord(
                    keyword=(serial_title := element.get("title").split(" ", maxsplit=1))[0],
                    title=serial_title[1],
                    url=self.patt_video_id.match(element.get("href")).group(1)
                )
                for element in et_videos
            ]
        elif resp.status_code == 302:  # which means found only one video and get redirected
            video_id = self.patt_video_id.match(resp.headers["location"]).group(1)
            res = [
                JavRecord(keyword=keyword, title="", url=video_id)
            ]
        else:
            raise
        return res

    async def get_video_detail(self, serial_no_reg, with_thumbnail=False) -> Optional[JavInfo]:
        if len(records := await self.search_by_keyword(serial_no_reg)) == 0:
            return None

        record = records[0]
        assert record.keyword == serial_no_reg, f"Not Found {serial_no_reg}"
        resp_video_detail = await self._get_video_detail(record.url)

        root = etree.HTML(resp_video_detail.text)
        title = root.xpath(".//div[@id='video_title']//a[@rel='bookmark']/text()")[0]

        video_infos = dict(zip(
            ("serial_no", "publish_date", "length", "director", "maker", "publisher", "review", "category", "cast"),
            root.xpath(".//div[@id='video_info']/div")
        ))
        serial_no = video_infos["serial_no"].xpath(".//td[@class='text']/text()")[0]
        issue_date = video_infos["publish_date"].xpath(".//td[@class='text']/text()")[0]
        length = video_infos["length"].xpath(".//span[@class='text']/text()")[0]
        maker = video_infos["maker"].xpath(".//td[@class='text']/span/a/text()")[0].strip()
        publisher = video_infos["publisher"].xpath(".//td[@class='text']/span/a/text()")[0]
        casts = video_infos["cast"].xpath(".//td[@class='text']//span[@class='star']/a[@rel='tag']/text()")

        url_thumbnail = root.xpath(".//img[@id='video_jacket_img']/@src")[0]
        if not url_thumbnail.startswith("https:"):
            url_thumbnail = f"https:{url_thumbnail}"
        thumbnail = Image.open(BytesIO(
            (await self._make_request(url_thumbnail)).content
        )) if with_thumbnail else None

        jav = JavInfo(
            serial_no=serial_no,
            title=title,
            casts=sorted(casts),
            publish_date=issue_date,
            thumbnail=thumbnail,
            length=length,
            maker=maker,
            publisher=publisher
        )
        return jav
