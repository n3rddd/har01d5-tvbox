# coding=utf-8
import re
import sys
from urllib.parse import quote, urljoin

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "路漫漫"
        self.host = "https://www.lmm85.com"
        self.mobile_ua = (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 "
            "Mobile/15E148 Safari/604.1"
        )
        self.headers = {
            "User-Agent": self.mobile_ua,
            "Referer": "http://www.lmm50.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        self.classes = [
            {"type_id": "6", "type_name": "日本动漫"},
            {"type_id": "7", "type_name": "国产动漫"},
            {"type_id": "8", "type_name": "欧美动漫"},
            {"type_id": "3", "type_name": "日本动画电影"},
            {"type_id": "4", "type_name": "国产动画电影"},
            {"type_id": "5", "type_name": "欧美动画电影"},
        ]

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def homeContent(self, filter):
        return {"class": self.classes}

    def _abs_url(self, value):
        raw = str(value or "").strip()
        if not raw:
            return ""
        return urljoin(self.host + "/", raw)

    def _encode_vod_id(self, href):
        raw = str(href or "").strip()
        matched = re.search(r"(/vod/detail/[^?#]+\.html)", raw)
        return matched.group(1).lstrip("/") if matched else raw.lstrip("/")

    def _clean_text(self, text):
        return re.sub(r"\s+", " ", str(text or "")).strip()

    def _get_html(self, url, headers=None):
        request_headers = dict(self.headers)
        if headers:
            request_headers.update(headers)
        response = self.fetch(url, headers=request_headers, timeout=15, verify=False)
        if response.status_code != 200:
            return ""
        return response.text or ""

    def _parse_cards(self, html):
        root = self.html(html)
        if root is None:
            return []
        items = []
        seen = set()
        for box in root.xpath("//*[contains(@class,'video-img-box')]"):
            href = self._clean_text((box.xpath(".//a[1]/@href") or [""])[0])
            title = self._clean_text("".join(box.xpath(".//*[contains(@class,'title')][1]//text()")))
            pic = self._clean_text(
                (box.xpath(".//img[1]/@data-src") or box.xpath(".//img[1]/@src") or [""])[0]
            )
            remarks = self._clean_text("".join(box.xpath(".//*[contains(@class,'label')][1]//text()")))
            vod_id = self._encode_vod_id(href)
            if not vod_id or not title or vod_id in seen:
                continue
            seen.add(vod_id)
            items.append(
                {
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": self._abs_url(pic),
                    "vod_remarks": remarks,
                }
            )
        return items

    def homeVideoContent(self):
        return {"list": self._parse_cards(self._get_html(self.host + "/"))[:20]}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg)
        extend = extend or {}
        path = f"/vod/show/id/{tid}"
        path += str(extend.get("年代", "") or "")
        path += str(extend.get("排序", "") or "")
        path += f"/page/{page}.html"
        items = self._parse_cards(self._get_html(self.host + path))
        return {"page": page, "total": len(items), "list": items}

    def searchContent(self, key, quick, pg="1"):
        page = int(pg)
        keyword = self._clean_text(key)
        if not keyword:
            return {"page": page, "total": 0, "list": []}
        url = f"{self.host}/vod/search/page/{page}/wd/{quote(keyword)}.html"
        items = self._parse_cards(self._get_html(url))
        return {"page": page, "total": len(items), "list": items[:10] if quick else items}
