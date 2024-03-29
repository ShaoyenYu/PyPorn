from typing import List, Optional

from lxml import etree

from lib.external.base import BaseApi, JavInfo, JavRecord

__all__ = ['TokyoLibApi']


class TokyoLibApi(BaseApi):
    source = "TokyoLib"
    url_domain = "https://tokyolib.com"

    async def search_by_keyword(self, keyword, search_type="id") -> List[JavRecord]:
        """

        Args:
            keyword:
            search_type: str, optional {"id", "actress"}

        Returns:

        """

        if search_type == "actress":
            raise NotImplementedError()

        url_video_detail = f"{self.url_domain}/search?type={search_type}&q={keyword}"
        resp = await self._make_request(url_video_detail)

        elements = etree.HTML(resp.text).xpath("//div[@class='works']/a[@class='work']")
        records = [
            JavRecord(
                keyword=element.xpath("./h4[@class='work-id']/text()")[0],
                title=element.xpath("./h4[@class='work-title']/text()")[0],
                url=f"{self.url_domain}{element.get('href')}",
            ) for element in elements
        ]
        return records

    async def get_video_detail(self, serial_no_reg: str) -> Optional[JavInfo]:
        """
        Fetch meta info of JAV, supported fields:
            - serial_no
            - title
            - casts
            - publish_date
            - thumbnail
            - publisher
            - director
            - maker

        Args:
            serial_no_reg: str
                regularized serial number

        Returns:

        """

        if len(records := await self.search_by_keyword(serial_no_reg)) == 0:
            return None

        resp = await self._make_request(records[0].url)

        et = etree.HTML(resp.text)
        et_info = et.xpath("//div[@class='info']")[0]

        et_attrs = et_info.xpath(".//div[@class='attributes']/dl")[0]
        attrs = {}
        for key, et_value in zip(et_attrs.xpath("./dd/text()"), et_attrs.xpath("./dt")):
            if key.endswith("番号"):
                attrs["serial_no"] = et_value.xpath("./text()")[0].split()[0].upper()
            elif key.endswith("发行时间"):
                attrs["publish_date"] = et_value.xpath("./text()")[0].split()[0].upper()
            elif key.endswith("系列"):
                attrs["serie"] = et_value.xpath(".//text()")[0].strip()
            elif key.endswith("片商"):
                attrs["maker"] = et_value.xpath(".//text()")[0].strip()
            elif key.endswith("厂牌"):
                attrs["publisher"] = et_value.xpath(".//text()")[0].strip()
            elif key.endswith("导演"):
                attrs["director"] = et_value.xpath(".//text()")[0].strip()

        title = et.xpath("//h1[@class='title is-4']/text()")[0]
        casts = sorted(self.strip_all(et_info.xpath(".//a[@class='actress']/text()"), drop_empty_str=True))

        jav = JavInfo(
            serial_no=attrs["serial_no"],
            title=title,  # there is only Chinese title
            casts=casts,
            publish_date=attrs["publish_date"],
            thumbnail=None,
            publisher=attrs["publisher"].upper(),
            maker=attrs["maker"].upper(),  # not sure if it's correct
            director=attrs.get("director", ""),
            source=self.source,
        )
        return jav
