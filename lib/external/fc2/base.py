from io import BytesIO
from typing import List, Optional

from PIL import Image
from lxml import etree

from lib.external.base import BaseApi, JavInfo, JavRecord

__all__ = ["FC2Api"]


class FC2Api(BaseApi):
    source = "FC2"
    url_domain = "https://adult.contents.fc2.com"

    async def search_by_keyword(self, keyword: str, page_no=1) -> List[JavRecord]:
        raise NotImplementedError("Not implemented")

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

        if not serial_no_reg.startswith("FC2-PPV-"):
            return None
        api_url = f"{self.url_domain}/article/{serial_no_reg.split("-")[-1]}/"
        resp = await self._make_request(api_url, follow_redirects=False)

        if resp.status_code != 200:
            return None

        et = etree.HTML(resp.text)
        et_header = et.xpath("//div[@class='items_article_headerInfo']")[0]
        title = et_header.xpath("./h3/text()")[-1]  # sometimes there is also a tag
        publisher = et_header.xpath("./ul//@href")[-1].strip("/").split("/")[-1]
        publish_date = et_header.xpath(".//div[@class='items_article_Releasedate']//text()")[0].split(" : ")[-1]
        publish_date = publish_date.replace("/", "-")

        url_image = et.xpath("//div[@class='items_article_MainitemThumb']//img/@src")[0]
        hours, minutes, seconds = et.xpath("//div[@class='items_article_MainitemThumb']//text()")[0].split(":")
        length = int(hours) * 3600 + int(minutes) * 60 + int(seconds)
        thumbnail = await self._make_request_image(f"https:{url_image}")

        jav = JavInfo(
            serial_no=serial_no_reg,
            title=title,
            publish_date=publish_date,
            thumbnail=thumbnail,
            length=length,
            publisher=publisher,
            source=self.source,
        )
        return jav
