# coding=utf-8
import base64
import json
import os
import re
import sys
from urllib.parse import quote

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "玩偶聚合"
        self.filter_root = os.path.join(os.path.dirname(__file__), "../筛选")
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/136.0.0.0 Safari/537.36"
            )
        }
        self.site_priority = [
            "wanou",
            "muou",
            "labi",
            "zhizhen",
            "erxiao",
            "huban",
            "kuaiying",
            "shandian",
            "ouge",
        ]
        self.sites = [
            {
                "id": "wanou",
                "name": "玩偶",
                "domains": ["https://www.wogg.net"],
                "filter_files": ["wogg.json"],
                "list_xpath": "//*[contains(@class,'module-item')]",
                "category_url": "/vodshow/{categoryId}--------{page}---.html",
                "category_url_with_filters": "/vodshow/{categoryId}-{area}-{by}-{class}-----{page}---{year}.html",
                "default_categories": [("1", "电影"), ("2", "电视剧"), ("3", "动漫"), ("4", "综艺")],
            },
            {
                "id": "muou",
                "name": "木偶",
                "domains": ["https://www.muou.site"],
                "filter_files": ["mogg.json"],
                "list_xpath": "//*[contains(@class,'module-item')]",
                "category_url": "/vodshow/{categoryId}--------{page}---.html",
                "default_categories": [("1", "电影"), ("2", "电视剧"), ("3", "动漫"), ("29", "综艺")],
            },
            {
                "id": "labi",
                "name": "蜡笔",
                "domains": ["http://xiaocge.fun"],
                "filter_files": ["labi.json"],
                "list_xpath": "//*[contains(@class,'module-item')]",
                "category_url": "/vodshow/{categoryId}--------{page}---.html",
                "default_categories": [("1", "电影"), ("2", "电视剧"), ("3", "动漫"), ("4", "综艺")],
            },
        ]

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def homeVideoContent(self):
        return {"list": []}

    def _load_local_filter_groups(self, site):
        return []

    def _build_site_filters(self, site):
        groups = [
            {
                "key": "categoryId",
                "name": "分类",
                "init": site["default_categories"][0][0],
                "value": [{"n": "全部", "v": ""}]
                + [{"n": name, "v": cid} for cid, name in site["default_categories"]],
            }
        ]
        groups.extend(self._load_local_filter_groups(site))
        return groups

    def homeContent(self, filter):
        classes = [{"type_id": f"site_{site['id']}", "type_name": site["name"]} for site in self.sites]
        filters = {f"site_{site['id']}": self._build_site_filters(site) for site in self.sites}
        return {"class": classes, "filters": filters}

    def _encode_site_vod_id(self, site_id, path):
        return f"site:{site_id}:{path}"

    def _decode_site_vod_id(self, value):
        prefix, site_id, path = str(value).split(":", 2)
        if prefix != "site":
            raise ValueError("not site vod id")
        return {"site": site_id, "path": path}

    def _encode_aggregate_vod_id(self, payload):
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return "agg:" + base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")

    def _decode_aggregate_vod_id(self, value):
        encoded = str(value)[4:]
        padded = encoded + "=" * (-len(encoded) % 4)
        return json.loads(base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8"))

    def _normalize_title(self, value):
        text = str(value or "").lower()
        text = re.sub(r"(4k|hdr|2160p|1080p|720p|玩偶|木偶|蜡笔)", "", text, flags=re.I)
        text = re.sub(r"[\s\-_.·,，。!！?:：()（）\[\]]+", "", text)
        return text

    def _is_same_title(self, left, right):
        left_year = str(left.get("vod_year") or "").strip()
        right_year = str(right.get("vod_year") or "").strip()
        if left_year and right_year and left_year != right_year:
            return False
        return self._normalize_title(left.get("vod_name")) == self._normalize_title(right.get("vod_name"))

    def _get_site(self, site_id):
        for site in self.sites:
            if site["id"] == site_id:
                return site
        return None

    def _build_absolute_url(self, base, path):
        raw = str(path or "").strip()
        if not raw:
            return ""
        if raw.startswith(("http://", "https://")):
            return raw
        if raw.startswith("//"):
            return "https:" + raw
        return str(base).rstrip("/") + "/" + raw.lstrip("/")

    def _build_category_url(self, site, category_id, pg, extend):
        values = dict(extend or {})
        values.setdefault("categoryId", category_id)
        values.setdefault("area", "")
        values.setdefault("by", values.get("sort", ""))
        values.setdefault("class", "")
        values.setdefault("year", "")
        if site.get("category_url_with_filters") and any(values.get(key) for key in ("area", "by", "class", "year")):
            path = site["category_url_with_filters"].format(
                **{
                    "categoryId": values["categoryId"],
                    "area": quote(str(values["area"])),
                    "by": quote(str(values["by"])),
                    "class": quote(str(values["class"])),
                    "page": int(pg),
                    "year": quote(str(values["year"])),
                }
            )
        else:
            path = site["category_url"].format(categoryId=values["categoryId"], page=int(pg))
        return self._build_absolute_url(site["domains"][0], path)

    def _request_with_failover(self, site, path_or_url, referer=None):
        last_error = None
        for index, domain in enumerate(list(site["domains"])):
            target = path_or_url if str(path_or_url).startswith("http") else self._build_absolute_url(domain, path_or_url)
            try:
                headers = dict(self.headers)
                headers["Referer"] = referer or self._build_absolute_url(domain, "/")
                response = self.fetch(target, headers=headers, timeout=10)
                if response.status_code == 200 and response.text:
                    if index > 0:
                        site["domains"].insert(0, site["domains"].pop(index))
                    return response.text
            except Exception as exc:
                last_error = exc
        raise RuntimeError(str(last_error or "all domains failed"))

    def _parse_cards(self, site, html):
        root = self.html(html)
        if root is None:
            return []

        items = []
        seen = set()
        for card in root.xpath(site["list_xpath"]):
            href = ((card.xpath(".//a[@href][1]/@href") or [""])[0]).strip()
            title = (
                ((card.xpath(".//img[@alt][1]/@alt") or [""])[0]).strip()
                or ((card.xpath(".//a[@title][1]/@title") or [""])[0]).strip()
            )
            pic = (
                ((card.xpath(".//img[@data-src][1]/@data-src") or [""])[0]).strip()
                or ((card.xpath(".//img[@src][1]/@src") or [""])[0]).strip()
            )
            remarks = "".join(card.xpath(".//*[contains(@class,'module-item-text')][1]//text()")).strip()
            if not href or not title or href in seen:
                continue
            seen.add(href)
            items.append(
                {
                    "vod_id": self._encode_site_vod_id(site["id"], href),
                    "vod_name": title,
                    "vod_pic": self._build_absolute_url(site["domains"][0], pic),
                    "vod_remarks": remarks,
                    "vod_year": "",
                    "_site": site["id"],
                    "_detail_path": href,
                }
            )
        return items

    def categoryContent(self, tid, pg, filter, extend):
        site_id = str(tid).replace("site_", "", 1)
        site = self._get_site(site_id)
        values = extend if isinstance(extend, dict) else {}
        category_id = values.get("categoryId") or site["default_categories"][0][0]
        html = self._request_with_failover(site, self._build_category_url(site, category_id, pg, values))
        items = self._parse_cards(site, html)
        return {"list": items, "page": int(pg), "limit": len(items), "total": int(pg) * 20 + len(items)}
