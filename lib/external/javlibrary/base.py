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
    _lang = "cn"

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
        """
        Fetch meta info of JAV, supported fields:
            - serial_no
            - title
            - casts
            - publish_date
            - thumbnail
            - length
            - maker
            - publisher

        Args:
            serial_no_reg: str
                regularized serial number
            with_thumbnail: bool
                whether to download thumbnail of cover

        Returns:

        """

        if len(records := await self.search_by_keyword(serial_no_reg)) == 0:
            return None

        record = records[0]
        if record.keyword != serial_no_reg:
            return None

        resp_video_detail = await self._get_video_detail(record.url)

        root = etree.HTML(resp_video_detail.text)
        title = root.xpath(".//div[@id='video_title']//a[@rel='bookmark']/text()")[0]

        et_video_infos = root.xpath("//div[@id='video_info']/div")
        attrs = {}
        for element in et_video_infos:
            match (key := element.get("id")):
                case "video_id" | "video_date":
                    attrs[key] = element.xpath(".//td/text()")[1]
                case "video_length":
                    attrs[key] = element.xpath(".//td/span/text()")[0]
                case "video_director":
                    attrs[key] = element.xpath(".//td//text()")[1].strip("-")
                case "video_maker" | "video_label":
                    attrs[key] = element.xpath(".//td//a/text()")[0]
                case "video_cast":
                    attrs[key] = self.strip_all(element.xpath(".//td//a/text()"))

        url_thumbnail = root.xpath(".//img[@id='video_jacket_img']/@src")[0]
        if not url_thumbnail.startswith("https:"):
            url_thumbnail = f"https:{url_thumbnail}"
        thumbnail = await self._make_request_image(url_thumbnail) if with_thumbnail else None

        jav = JavInfo(
            serial_no=attrs["video_id"],
            title=title,
            casts=sorted(attrs["video_cast"]),
            publish_date=attrs["video_date"],
            thumbnail=thumbnail,
            length=attrs["video_length"] * 60,
            maker=attrs["video_maker"].upper(),
            publisher=attrs["video_label"].upper(),
            source=self.source,
        )
        return jav
