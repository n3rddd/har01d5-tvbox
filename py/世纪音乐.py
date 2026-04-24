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

    def _decode_vod_id(self, vod_id):
        raw = str(vod_id or "").strip()
        if ":" not in raw:
            return "", ""
        prefix, value = raw.split(":", 1)
        if prefix == "rank":
            return prefix, f"/list/{value}.html"
        if prefix == "song":
            return prefix, f"/mp3/{value}.html"
        if prefix == "mv":
            return prefix, f"/mp4/{value}.html"
        if prefix == "playlist":
            return prefix, f"/playlist/{value}.html"
        if prefix == "singer":
            return prefix, f"/singer/{value}.html"
        return "", ""

    def _encode_play_id(self, kind, value):
        if kind == "music":
            return f"music:{value}"
        if kind == "vplay":
            return f"vplay:{value}:1080"
        return ""

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

    def _build_episode_rows(self, html):
        root = self._load_html(html)
        rows = []
        for node in root.xpath("//*[contains(@class,'play_list')]//li"):
            href = "".join(node.xpath(".//a[1]/@href")).strip()
            song_id = self._extract_site_id(href, "mp3")
            if not song_id:
                continue
            rows.append(
                self._clean_text("".join(node.xpath(".//a[1]//text()")))
                + "$"
                + self._encode_play_id("music", song_id)
            )
        return rows

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

    def detailContent(self, ids):
        vod_id = str((ids or [""])[0] or "").strip()
        kind, path = self._decode_vod_id(vod_id)
        if not path:
            return {"list": []}
        html = self._fetch_html(path)
        root = self._load_html(html)
        title = self._clean_text("".join(root.xpath("//h1[1]//text()")))
        pic = self._build_url("".join(root.xpath("(//img[1]/@src)[1]")))
        if kind == "rank":
            return {
                "list": [
                    {
                        "vod_id": vod_id,
                        "vod_name": title or "排行榜",
                        "vod_pic": pic,
                        "vod_remarks": "",
                        "vod_content": "",
                        "vod_play_from": self.name,
                        "vod_play_url": "#".join(self._build_episode_rows(html)),
                    }
                ]
            }
        if kind == "song":
            singer = self._clean_text("".join(root.xpath("//*[contains(@class,'play_singer')]//a[1]//text()")))
            display = f"{singer} - {title}" if singer else title
            return {
                "list": [
                    {
                        "vod_id": vod_id,
                        "vod_name": title,
                        "vod_pic": pic,
                        "vod_remarks": "",
                        "vod_content": "",
                        "vod_actor": singer,
                        "vod_play_from": self.name,
                        "vod_play_url": display + "$" + self._encode_play_id("music", vod_id.split(":", 1)[1]),
                    }
                ]
            }
        if kind == "mv":
            return {
                "list": [
                    {
                        "vod_id": vod_id,
                        "vod_name": title,
                        "vod_pic": pic,
                        "vod_remarks": "",
                        "vod_content": "",
                        "vod_play_from": self.name,
                        "vod_play_url": title + "$" + self._encode_play_id("vplay", vod_id.split(":", 1)[1]),
                    }
                ]
            }
        if kind in ("playlist", "singer"):
            content = self._clean_text("".join(root.xpath("//*[contains(@class,'info')]//p[1]//text()")))
            return {
                "list": [
                    {
                        "vod_id": vod_id,
                        "vod_name": title,
                        "vod_pic": pic,
                        "vod_remarks": "",
                        "vod_content": content,
                        "vod_play_from": self.name,
                        "vod_play_url": "#".join(self._build_episode_rows(html)),
                    }
                ]
            }
        return {"list": []}
