# coding=utf-8
import re
import sys
from urllib.parse import urljoin

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "世纪音乐"
        self.host = "https://www.4c44.com"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": self.host + "/",
        }
        self.classes = [
            {"type_id": "home", "type_name": "首页推荐"},
            {"type_id": "rank_list", "type_name": "排行榜"},
            {"type_id": "playlist", "type_name": "歌单"},
            {"type_id": "singer", "type_name": "歌手"},
            {"type_id": "mv", "type_name": "MV"},
        ]
        self.rank_list = [
            ("rise", "音乐飙升榜"),
            ("new", "新歌排行榜"),
            ("top", "Top热歌榜"),
        ]

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def _build_url(self, path):
        return urljoin(self.host + "/", str(path or "").strip())

    def _clean_text(self, text):
        return re.sub(r"\s+", " ", str(text or "")).strip()

    def _load_html(self, html):
        return self.html(str(html or "").strip() or "<html></html>")

    def _fetch_html(self, path):
        response = self.fetch(self._build_url(path), headers=dict(self.headers), timeout=10, verify=False)
        return response.text if getattr(response, "status_code", 0) == 200 else ""

    def _encode_vod_id(self, href):
        href = str(href or "")
        if "/mp3/" in href:
            return "song:" + self._extract_site_id(href, "mp3")
        if "/mp4/" in href:
            return "mv:" + self._extract_site_id(href, "mp4")
        if "/playlist/" in href:
            return "playlist:" + self._extract_site_id(href, "playlist")
        if "/singer/" in href:
            return "singer:" + self._extract_site_id(href, "singer")
        return ""

    def _extract_site_id(self, href, prefix):
        text = str(href or "")
        marker = f"/{prefix}/"
        if marker not in text:
            return ""
        return text.split(marker, 1)[1].split(".html", 1)[0].split("/", 1)[0]

    def _build_filters(self):
        return {"singer": [], "mv": [], "playlist": []}

    def _parse_home_items(self, html):
        root = self._load_html(html)
        items = []
        for node in root.xpath("//*[@id='datalist']//li | //*[contains(@class,'video_list')]//li"):
            href = "".join(node.xpath(".//a[1]/@href")).strip()
            vod_id = self._encode_vod_id(href)
            if not vod_id:
                continue
            name = self._clean_text("".join(node.xpath(".//div[contains(@class,'name')]//a[1]//text()")))
            singer = self._clean_text("".join(node.xpath(".//*[contains(@class,'singer')][1]//text()")))
            pic = self._build_url("".join(node.xpath(".//img[1]/@src")))
            if vod_id.startswith("song:") and singer:
                name = f"{singer} - {name}"
            items.append(
                {
                    "vod_id": vod_id,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": "",
                }
            )
        return items

    def _page_result(self, items, pg):
        page = int(pg)
        return {"page": page, "limit": len(items), "total": len(items), "list": items}

    def _parse_list_cards(self, html, expected_prefixes):
        root = self._load_html(html)
        items = []
        seen = set()
        for node in root.xpath("//li"):
            href = "".join(node.xpath(".//a[1]/@href")).strip()
            vod_id = self._encode_vod_id(href)
            if not vod_id or vod_id in seen:
                continue
            if expected_prefixes and not any(vod_id.startswith(prefix) for prefix in expected_prefixes):
                continue
            seen.add(vod_id)
            items.append(
                {
                    "vod_id": vod_id,
                    "vod_name": self._clean_text(
                        "".join(node.xpath(".//div[contains(@class,'name')]//text()"))
                        or "".join(node.xpath(".//a[1]//text()"))
                    ),
                    "vod_pic": self._build_url("".join(node.xpath(".//img[1]/@src"))),
                    "vod_remarks": "",
                }
            )
        return items

    def homeContent(self, filter):
        items = self._parse_home_items(self._fetch_html("/"))
        return {"class": list(self.classes), "filters": self._build_filters(), "list": items}

    def homeVideoContent(self):
        return {"list": self.homeContent(False).get("list", [])}

    def categoryContent(self, tid, pg, filter, extend):
        if tid == "home":
            return self._page_result(self.homeContent(False).get("list", []), 1)
        if tid == "rank_list":
            return self._page_result(
                [
                    {
                        "vod_id": f"rank:{rank_id}",
                        "vod_name": title,
                        "vod_pic": "",
                        "vod_remarks": "排行榜",
                    }
                    for rank_id, title in self.rank_list
                ],
                pg,
            )
        if tid == "playlist":
            return self._page_result(
                self._parse_list_cards(self._fetch_html("/playlists/index.html"), ["playlist:"]),
                pg,
            )
        if tid == "singer":
            return self._page_result(
                self._parse_list_cards(self._fetch_html("/singerlist/huayu/girl/index.html"), ["singer:"]),
                pg,
            )
        if tid == "mv":
            return self._page_result(
                self._parse_list_cards(self._fetch_html("/mvlist/index/index/new.html"), ["mv:"]),
                pg,
            )
        return {"page": 1, "limit": 0, "total": 0, "list": []}

    def searchContent(self, key, quick, pg="1"):
        keyword = self._clean_text(key)
        if not keyword:
            return {"page": 1, "limit": 0, "total": 0, "list": []}
        items = self._parse_list_cards(
            self._fetch_html(f"/so.php?wd={keyword}&page={pg}"),
            ["song:", "mv:", "playlist:", "singer:"],
        )
        return self._page_result(items, pg)
