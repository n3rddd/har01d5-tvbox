# coding=utf-8
import json
import re
import sys
from urllib.parse import quote, urljoin

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "凡客TV"
        self.host = "https://fktv.me"
        self.cookie = "_did=57nTmEknMZ146xw4KXGHDCHk1MjshRyY"
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0"
        )
        self.classes = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "剧集"},
            {"type_id": "4", "type_name": "动漫"},
            {"type_id": "3", "type_name": "综艺"},
            {"type_id": "8", "type_name": "短剧"},
            {"type_id": "6", "type_name": "纪录片"},
            {"type_id": "7", "type_name": "解说"},
            {"type_id": "5", "type_name": "音乐"},
        ]

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def homeContent(self, filter):
        return {"class": self.classes}

    def homeVideoContent(self):
        return {"list": []}

    def _clean_text(self, value):
        return re.sub(r"\s+", " ", str(value or "").replace("\xa0", " ")).strip()

    def _abs_url(self, value):
        raw = str(value or "").strip()
        if not raw:
            return ""
        if raw.startswith(("http://", "https://")):
            return raw
        if raw.startswith("//"):
            return "https:" + raw
        return urljoin(self.host + "/", raw)

    def _page_headers(self, referer=""):
        headers = {"User-Agent": self.user_agent, "Referer": referer or self.host + "/"}
        if self.cookie:
            headers["Cookie"] = self.cookie
        return headers

    def _request_html(self, url, headers=None):
        response = self.fetch(url, headers=headers or self._page_headers(), timeout=10, verify=False)
        if response.status_code != 200:
            return ""
        return str(response.text or "")

    def _extract_cards(self, html):
        root = self.html(html or "")
        if root is None:
            return []
        items = []
        seen = set()
        nodes = root.xpath("//*[contains(@class,'meta-wrap')]/.. | //*[contains(@class,'hover-wrap')]")
        for node in nodes:
            href = self._clean_text(
                "".join(
                    node.xpath(
                        ".//a[contains(@class,'normal-title') or contains(@class,'hover-title')][1]/@href"
                    )
                )
            )
            matched = re.search(r"/movie/detail/([0-9A-Za-z]+)", href)
            if not matched:
                continue
            vod_id = matched.group(1)
            if vod_id in seen:
                continue
            seen.add(vod_id)
            title = self._clean_text(
                "".join(
                    node.xpath(
                        ".//a[contains(@class,'normal-title') or contains(@class,'hover-title')][1]/@title"
                    )
                )
            ) or self._clean_text(
                "".join(
                    node.xpath(
                        ".//a[contains(@class,'normal-title') or contains(@class,'hover-title')][1]//text()"
                    )
                )
            )
            pic = self._clean_text("".join(node.xpath(".//*[contains(@class,'lazy-load')][1]/@data-src")))
            tags = [
                self._clean_text("".join(tag.xpath(".//text()")))
                for tag in node.xpath(".//*[contains(@class,'tag')]")
            ]
            tags = [tag for tag in tags if tag]
            if not title:
                continue
            items.append(
                {
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": self._abs_url(pic),
                    "vod_remarks": " | ".join(tags),
                    "type_name": tags[0] if tags else "",
                }
            )
        return items

    def categoryContent(self, tid, pg, filter, extend):
        page = max(1, int(pg))
        url = self.host + f"/channel?page={page}&cat_id={tid}&page_size=32&order=new"
        items = self._extract_cards(self._request_html(url))
        return {"page": page, "limit": len(items), "total": len(items), "list": items}

    def searchContent(self, key, quick, pg="1"):
        page = max(1, int(pg))
        keyword = self._clean_text(key)
        if not keyword:
            return {"page": page, "limit": 0, "total": 0, "list": []}
        url = self.host + "/search?keyword=" + quote(keyword)
        items = self._extract_cards(self._request_html(url))
        return {"page": page, "limit": len(items), "total": len(items), "list": items}

    def _encode_play_id(self, payload):
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    def _decode_play_id(self, value):
        try:
            decoded = json.loads(str(value or "").strip())
        except Exception:
            decoded = {}
        return decoded if isinstance(decoded, dict) else {}
