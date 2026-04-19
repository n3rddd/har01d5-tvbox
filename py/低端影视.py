# coding=utf-8
import base64
import json
import re
import sys
from urllib.parse import quote

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "低端影视"
        self.host = "https://ddys.io"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/145.0.0.0 Safari/537.36"
            ),
            "Referer": self.host + "/",
        }
        self.classes = [
            {"type_id": "series", "type_name": "剧集"},
            {"type_id": "movie", "type_name": "电影"},
            {"type_id": "variety", "type_name": "综艺"},
            {"type_id": "anime", "type_name": "动漫"},
        ]
        self.filter_def = {
            "movie": {"cateId": "movie"},
            "series": {"cateId": "series"},
            "variety": {"cateId": "variety"},
            "anime": {"cateId": "anime"},
        }
        self.filters = {
            key: [
                {"key": "class", "name": "剧情", "init": "", "value": [{"n": "全部", "v": ""}]},
                {"key": "area", "name": "地区", "init": "", "value": [{"n": "全部", "v": ""}]},
                {"key": "year", "name": "年份", "init": "", "value": [{"n": "全部", "v": ""}]},
                {
                    "key": "by",
                    "name": "排序",
                    "init": "",
                    "value": [
                        {"n": "时间", "v": ""},
                        {"n": "评分", "v": "rating/"},
                        {"n": "热门", "v": "popular/"},
                    ],
                },
            ]
            for key in ["movie", "series", "variety", "anime"]
        }

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def homeContent(self, filter):
        return {"class": self.classes, "filters": self.filters}

    def homeVideoContent(self):
        return {"list": []}

    def _stringify(self, value):
        return "" if value is None else str(value)

    def _normalize_ext(self, extend):
        if isinstance(extend, dict):
            return extend
        if not extend:
            return {}
        try:
            return json.loads(str(extend))
        except Exception:
            return {}

    def _build_url(self, path):
        raw = self._stringify(path).strip()
        if not raw:
            return ""
        if raw.startswith(("http://", "https://")):
            return raw
        if raw.startswith("//"):
            return "https:" + raw
        if raw.startswith("/"):
            return self.host + raw
        return self.host + "/" + raw

    def _build_category_url(self, tid, pg, extend):
        values = dict(self.filter_def.get(str(tid), {"cateId": str(tid)}))
        values.update(self._normalize_ext(extend))
        path = (
            f"{values.get('by', '')}"
            f"{values.get('cateId', tid)}"
            f"{values.get('class', '')}"
            f"{values.get('area', '')}"
            f"{values.get('year', '')}"
            f"/page/{int(pg)}"
        )
        return self._build_url(path)

    def _request_html(self, path_or_url, method="GET", data=None, headers=None, referer=None):
        target = path_or_url if str(path_or_url).startswith("http") else self._build_url(path_or_url)
        merged_headers = dict(self.headers)
        if headers:
            merged_headers.update(headers)
        merged_headers["Referer"] = referer or self.headers["Referer"]
        if method == "POST":
            response = self.post(target, data=data, headers=merged_headers, timeout=10)
        else:
            response = self.fetch(target, headers=merged_headers, timeout=10)
        if response.status_code != 200:
            return ""
        return response.text or ""

    def _clean_text(self, text):
        return re.sub(r"\s+", " ", str(text or "").replace("\xa0", " ")).strip()

    def _parse_movie_cards(self, html, root_xpath="//*[contains(@class,'movie-card')]"):
        root = self.html(html)
        if root is None:
            return []
        items = []
        seen = set()
        for node in root.xpath(root_xpath):
            href = ((node.xpath(".//a[@href][1]/@href") or [""])[0]).strip()
            title = self._clean_text("".join(node.xpath(".//h3[1]//text()")))
            pic = (
                ((node.xpath(".//img[1]/@src") or [""])[0]).strip()
                or ((node.xpath(".//img[1]/@data-src") or [""])[0]).strip()
            )
            remarks = self._clean_text("".join(node.xpath(".//*[contains(@class,'poster-badge')][1]//text()")))
            vod_id = self._build_url(href)
            if not vod_id or not title or vod_id in seen:
                continue
            seen.add(vod_id)
            items.append(
                {
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": self._build_url(pic),
                    "vod_remarks": remarks,
                }
            )
        return items

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg)
        items = self._parse_movie_cards(self._request_html(self._build_category_url(tid, pg, extend)))
        return {
            "list": items,
            "page": page,
            "pagecount": page + 1 if items else page,
            "limit": 24,
            "total": page * 24 + len(items),
        }

    def searchContent(self, key, quick, pg="1"):
        page = int(pg)
        keyword = self._stringify(key).strip()
        if not keyword:
            return {"page": page, "pagecount": 0, "total": 0, "list": []}
        html = self._request_html(
            self.host + "/search",
            method="POST",
            data=f"q={quote(keyword)}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        items = self._parse_movie_cards(
            html,
            root_xpath="(//*[contains(@class,'mb-12')])[1]//*[contains(@class,'movie-card')]",
        )
        if not items:
            items = self._parse_movie_cards(html)
        return {"page": page, "pagecount": page + 1 if items else page, "total": len(items), "list": items}

    def _extract_switch_sources(self, html):
        root = self.html(html)
        if root is None:
            return []
        groups = []
        for button in root.xpath("//button[contains(@onclick,'switchSource')]"):
            onclick = (button.xpath("./@onclick") or [""])[0]
            matched = re.search(r"switchSource\(\d+,\s*'([^']*)',\s*'[^']*'\)", onclick, re.S)
            if not matched:
                continue
            name = self._clean_text("".join(button.xpath(".//text()"))) or self.name
            payload = self._clean_text(matched.group(1))
            if not payload:
                continue
            if "$" not in payload:
                payload = f"全集${payload}"
            groups.append({"from": name, "urls": payload})
        return groups

    def _extract_pan_sources(self, html):
        root = self.html(html)
        if root is None:
            return []
        groups = []
        for panel in root.xpath("//*[contains(@class,'download-type-content')]"):
            panel_id = ((panel.xpath("./@id") or [""])[0]).replace("download-type-", "").strip()
            if panel_id not in ("quark", "xunlei", "baidu"):
                continue
            entries = []
            for button in panel.xpath(".//button[@onclick]"):
                onclick = (button.xpath("./@onclick") or [""])[0]
                matched = re.search(r"atob\('([^']+)'\)", onclick)
                if not matched:
                    continue
                try:
                    link = base64.b64decode(matched.group(1)).decode("utf-8").strip()
                except Exception:
                    continue
                title = self._clean_text("".join(button.xpath(".//text()"))) or panel_id
                if link:
                    entries.append(f"{title}${link}")
            if entries:
                groups.append({"from": panel_id, "urls": "#".join(dict.fromkeys(entries))})
        return groups

    def _parse_detail_page(self, html, vod_id):
        root = self.html(html)
        if root is None:
            return {"vod_id": vod_id, "vod_name": "", "vod_play_from": "", "vod_play_url": ""}
        title = self._clean_text("".join(root.xpath("//h1[1]/text()")))
        pic = ((root.xpath("//img[@alt][1]/@src") or [""])[0]).strip()
        meta = self._clean_text("".join(root.xpath("(//*[contains(@class,'text-gray-600')])[1]//text()")))
        parts = [self._clean_text(item) for item in meta.split("·")] if meta else []
        director = ""
        actor = ""
        for text in root.xpath("//*[contains(@class,'text-gray-700')]"):
            joined = self._clean_text("".join(text.xpath(".//text()")))
            if joined.startswith("导演："):
                director = joined.split("：", 1)[-1].strip()
            if joined.startswith("主演："):
                actor = joined.split("：", 1)[-1].strip()
        content = "\n".join(
            [self._clean_text("".join(node.xpath(".//text()"))) for node in root.xpath("//*[contains(@class,'prose')]//p")]
        ).strip()
        play_groups = self._extract_switch_sources(html) + self._extract_pan_sources(html)
        return {
            "vod_id": vod_id,
            "vod_name": title,
            "vod_pic": self._build_url(pic),
            "vod_content": content,
            "vod_remarks": " · ".join([item for item in parts if item]),
            "vod_year": parts[0] if len(parts) > 0 else "",
            "vod_area": parts[1] if len(parts) > 1 else "",
            "vod_class": parts[2] if len(parts) > 2 else "",
            "vod_director": director,
            "vod_actor": actor,
            "vod_play_from": "$$$".join([item["from"] for item in play_groups]),
            "vod_play_url": "$$$".join([item["urls"] for item in play_groups]),
        }

    def detailContent(self, ids):
        result = {"list": []}
        for raw_id in ids:
            vod_id = self._stringify(raw_id).strip()
            if not vod_id:
                continue
            vod = self._parse_detail_page(self._request_html(vod_id), vod_id)
            result["list"].append(vod)
        return result

    def _is_pan_flag(self, flag):
        lowered = self._stringify(flag).lower()
        return any(token in lowered for token in ["quark", "baidu", "xunlei"])

    def playerContent(self, flag, id, vipFlags):
        target = self._stringify(id).strip()
        if self._is_pan_flag(flag):
            return {"parse": 0, "jx": 0, "url": target, "header": {}}
        return {
            "parse": 0,
            "jx": 0,
            "url": self._build_url(target),
            "header": dict(self.headers),
        }
