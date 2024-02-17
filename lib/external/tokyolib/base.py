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

    async def get_video_detail(self, serial_no_reg: str, with_thumbnail=False) -> Optional[JavInfo]:
        if len(records := await self.search_by_keyword(serial_no_reg)) == 0:
            return None

        resp = await self._make_request(records[0].url)

        et = etree.HTML(resp.text)
        et_info = et.xpath("//div[@class='info']")[0]

        serial_no, _, publish_date = self.strip_all(
            et_info.xpath(".//div[@class='attributes']//dt/text()")[:3]
        )
        publisher, director, brand = self.strip_all(
            et_info.xpath(".//div[@class='attributes']//dt/a/text()")[:3]
        )
        serial_no = serial_no.split()[0].upper()
        casts = sorted(self.strip_all(et_info.xpath(".//a[@class='actress']/text()"), drop_empty_str=True))
        title = et.xpath("//h1[@class='title is-4']/text()")[0]

        jav = JavInfo(
            serial_no=serial_no,
            title=title,  # there is only Chinese title
            casts=casts,
            publish_date=publish_date,
            thumbnail=None,
            publisher=publisher,
            director=director,
            maker=brand,  # not sure if it's correct
        )
        return jav
