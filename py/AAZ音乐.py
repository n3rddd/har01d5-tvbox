# coding=utf-8
import re
import sys
from urllib.parse import quote, urljoin

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "AAZ音乐"
        self.host = "https://www.aaz.cx"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": self.host + "/",
        }
        self.classes = [
            {"type_id": "new", "type_name": "新歌榜"},
            {"type_id": "top", "type_name": "TOP榜单"},
            {"type_id": "singer", "type_name": "歌手"},
            {"type_id": "playtype", "type_name": "歌单"},
            {"type_id": "album", "type_name": "专辑"},
            {"type_id": "mv", "type_name": "高清MV"},
        ]
        self.category_paths = {
            "new": "/list/new.html",
            "top": "/list/top.html",
            "singer": "/singerlist/index/index/index/index.html",
            "playtype": "/playtype/index.html",
            "album": "/albumlist/index.html",
            "mv": "/mvlist/index.html",
        }

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

    def _empty_result(self, page=1):
        return {"page": int(page), "limit": 0, "total": 0, "list": []}

    def _extract_song_id(self, href):
        matched = re.search(r"/m/([^.?#/]+)\.html", str(href or "").strip())
        return matched.group(1) if matched else ""

    def _extract_folder_id(self, href, prefix):
        matched = re.search(r"/%s/([^/?#]+)" % re.escape(prefix), str(href or "").strip())
        return matched.group(1) if matched else ""

    def _encode_vod_id(self, href):
        raw = str(href or "").strip()
        song_id = self._extract_song_id(raw)
        if song_id:
            return "song:" + song_id
        for prefix, label in [("s", "singer"), ("p", "playlist"), ("a", "album"), ("v", "mv")]:
            folder_id = self._extract_folder_id(raw, prefix)
            if folder_id:
                return label + ":" + folder_id
        return ""

    def _parse_song_cards(self, html):
        root = self._load_html(html)
        items = []
        seen = set()
        for node in root.xpath("//li"):
            href = "".join(node.xpath(".//div[contains(@class,'name')]//a[1]/@href")).strip()
            vod_id = self._encode_vod_id(href)
            if not vod_id.startswith("song:") or vod_id in seen:
                continue
            seen.add(vod_id)
            has_mv = bool(node.xpath(".//div[contains(@class,'mv')]//a"))
            items.append(
                {
                    "vod_id": vod_id,
                    "vod_name": self._clean_text("".join(node.xpath(".//div[contains(@class,'name')]//a[1]/@title"))),
                    "vod_pic": "",
                    "vod_remarks": "高清MV" if has_mv else "",
                }
            )
        return items

    def _parse_folder_cards(self, html, expected_prefix):
        root = self._load_html(html)
        items = []
        seen = set()
        for node in root.xpath("//li"):
            href = "".join(node.xpath(".//div[contains(@class,'name')]//a[1]/@href")).strip()
            vod_id = self._encode_vod_id(href)
            if not vod_id.startswith(expected_prefix + ":") or vod_id in seen:
                continue
            seen.add(vod_id)
            items.append(
                {
                    "vod_id": vod_id,
                    "vod_name": self._clean_text("".join(node.xpath(".//div[contains(@class,'name')]//a[1]/@title"))),
                    "vod_pic": self._build_url("".join(node.xpath(".//img[1]/@src"))),
                    "vod_remarks": "",
                }
            )
        return items

    def _parse_search_cards(self, html):
        root = self._load_html(html)
        items = []
        seen = set()
        for node in root.xpath("//li"):
            href = "".join(node.xpath(".//div[contains(@class,'name')]//a[1]/@href")).strip()
            vod_id = self._encode_vod_id(href)
            if not vod_id or vod_id in seen:
                continue
            seen.add(vod_id)
            items.append(
                {
                    "vod_id": vod_id,
                    "vod_name": self._clean_text("".join(node.xpath(".//div[contains(@class,'name')]//a[1]/@title"))),
                    "vod_pic": self._build_url("".join(node.xpath(".//img[1]/@src"))),
                    "vod_remarks": "",
                }
            )
        return items

    def _decode_vod_id(self, vod_id):
        raw = str(vod_id or "").strip()
        if ":" not in raw:
            return "", ""
        prefix, value = raw.split(":", 1)
        if prefix == "song":
            return prefix, "/m/%s.html" % value
        if prefix == "singer":
            return prefix, "/s/%s" % value
        if prefix == "playlist":
            return prefix, "/p/%s" % value
        if prefix == "album":
            return prefix, "/a/%s" % value
        if prefix == "mv":
            return prefix, "/v/%s" % value
        return "", ""

    def _parse_song_detail(self, html, song_id):
        title_match = re.search(
            r'<div class="djname"><h1>(.*?)<a href="javascript:location\.reload\(\)"',
            str(html or ""),
            re.S,
        )
        title = self._clean_text(re.sub(r"<[^>]+>", " ", title_match.group(1))) if title_match else song_id
        singer_match = re.search(r'<div class="name"><a href="/s/[^"]+"[^>]*>([^<]+)</a></div>', str(html or ""))
        album_match = re.search(r'所属专辑：<a href="/a/[^"]+"[^>]*>([^<]+)</a>', str(html or ""))
        cover_match = re.search(r'<img class="rotate" id="mcover" src="([^"]+)"', str(html or ""))
        duration_match = re.search(r"歌曲时长：([^<]+)</div>", str(html or ""))
        content_match = re.search(r'<meta name="description" content="([^"]+)"', str(html or ""))
        return {
            "song_name": title,
            "singer": self._clean_text(singer_match.group(1)) if singer_match else "",
            "album": self._clean_text(album_match.group(1)) if album_match else "",
            "cover": self._build_url(cover_match.group(1)) if cover_match else "",
            "duration": self._clean_text(duration_match.group(1)) if duration_match else "",
            "content": self._clean_text(content_match.group(1)) if content_match else "",
        }

    def _parse_folder_tracks(self, html):
        root = self._load_html(html)
        rows = []
        seen = set()
        for node in root.xpath("//li"):
            href = "".join(node.xpath(".//div[contains(@class,'name')]//a[1]/@href")).strip()
            song_id = self._extract_song_id(href)
            if not song_id or song_id in seen:
                continue
            seen.add(song_id)
            rows.append(
                self._clean_text("".join(node.xpath(".//div[contains(@class,'name')]//a[1]/@title")))
                + "$song:"
                + song_id
            )
        return rows

    def homeContent(self, filter):
        items = self._parse_song_cards(self._fetch_html(self.category_paths["new"]))
        return {"class": list(self.classes), "list": items}

    def homeVideoContent(self):
        return {"list": self.homeContent(False).get("list", [])}

    def categoryContent(self, tid, pg, filter, extend):
        if tid not in self.category_paths:
            return self._empty_result(pg)
        html = self._fetch_html(self.category_paths[tid])
        if tid in ("new", "top"):
            items = self._parse_song_cards(html)
        elif tid == "singer":
            items = self._parse_folder_cards(html, "singer")
        elif tid == "playtype":
            items = self._parse_folder_cards(html, "playlist")
        elif tid == "album":
            items = self._parse_folder_cards(html, "album")
        else:
            items = self._parse_folder_cards(html, "mv")
        return {"page": int(pg), "limit": len(items), "total": len(items), "list": items}

    def searchContent(self, key, quick, pg="1"):
        keyword = self._clean_text(key)
        if not keyword:
            return self._empty_result(1)
        html = self._fetch_html("/so/%s.html" % quote(keyword))
        items = self._parse_search_cards(html)
        return {"page": int(pg), "limit": len(items), "total": len(items), "list": items}

    def detailContent(self, array):
        vod_id = str((array or [""])[0] or "").strip()
        kind, path = self._decode_vod_id(vod_id)
        if not kind:
            return {"list": []}
        html = self._fetch_html(path)
        if kind == "song":
            info = self._parse_song_detail(html, vod_id.split(":", 1)[1])
            remarks = " | ".join([item for item in [info["singer"], info["album"], info["duration"]] if item])
            return {
                "list": [
                    {
                        "vod_id": vod_id,
                        "vod_name": info["song_name"],
                        "vod_pic": info["cover"],
                        "vod_remarks": remarks,
                        "vod_content": info["content"],
                        "vod_play_from": "AAZ音乐",
                        "vod_play_url": "播放$" + vod_id,
                    }
                ]
            }
        root = self._load_html(html)
        tracks = self._parse_folder_tracks(html)
        return {
            "list": [
                {
                    "vod_id": vod_id,
                    "vod_name": self._clean_text("".join(root.xpath("//div[contains(@class,'title')]//h1[1]//text()"))),
                    "vod_pic": self._build_url("".join(root.xpath("//div[contains(@class,'pic')]//img[1]/@src"))),
                    "vod_remarks": "",
                    "vod_content": self._clean_text("".join(root.xpath("//div[contains(@class,'info')][1]//text()"))),
                    "vod_play_from": "AAZ音乐",
                    "vod_play_url": "#".join(tracks),
                }
            ]
        }
