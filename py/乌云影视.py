# coding=utf-8
import json
import sys

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "乌云影视"
        self.host = "https://wooyun.tv"
        self.page_size = 24
        self.home_limit = 12
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Origin": self.host,
            "Referer": self.host + "/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        }
        self.sort_options = [
            {"n": "默认", "v": "default"},
            {"n": "最新", "v": "latest"},
            {"n": "最热", "v": "hot"},
            {"n": "评分", "v": "score"},
        ]

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def _stringify(self, value):
        return "" if value is None else str(value)

    def _ensure_list(self, value):
        return value if isinstance(value, list) else []

    def _normalize_ext(self, extend):
        if isinstance(extend, dict):
            return extend
        if not extend:
            return {}
        try:
            return json.loads(str(extend))
        except Exception:
            return {}

    def _request_json(self, path, method="GET", data=None, headers=None):
        url = path if str(path).startswith("http") else self.host + path
        merged_headers = dict(self.headers)
        if headers:
            merged_headers.update(headers)

        if method == "POST":
            response = self.post(url, json=data, headers=merged_headers, timeout=15)
        else:
            response = self.fetch(url, headers=merged_headers, timeout=15)

        if response.status_code < 200 or response.status_code >= 300:
            raise ValueError(f"{method} {path} => HTTP {response.status_code}")

        payload = response.json()
        if payload.get("code") not in (None, 200) and payload.get("isSuccess") is False:
            raise ValueError(payload.get("resultMsg") or str(payload.get("code")))
        return payload.get("data")

    def _build_classes(self, menu):
        classes = []
        for code, fallback in [
            ("movie", "电影"),
            ("tv_series", "电视剧"),
            ("animation", "动画"),
            ("variety", "综艺"),
            ("short_drama", "短剧"),
        ]:
            found = next((item for item in self._ensure_list(menu) if item.get("code") == code), None)
            classes.append(
                {"type_id": code, "type_name": self._stringify((found or {}).get("name") or fallback)}
            )

        year_group = next((item for item in self._ensure_list(menu) if item.get("nameEn") == "year"), {})
        year_children = self._ensure_list(year_group.get("children"))
        this_year = next((item for item in year_children if item.get("code") == "THIS_YEAR"), {})
        last_year = next((item for item in year_children if item.get("code") == "LAST_YEAR"), {})
        classes.append({"type_id": "THIS_YEAR", "type_name": self._stringify(this_year.get("name") or "今年")})
        classes.append({"type_id": "LAST_YEAR", "type_name": self._stringify(last_year.get("name") or "去年")})
        return classes

    def _build_filters(self, menu, classes):
        option_map = {"genre": [], "region": [], "year": [], "language": []}
        for group in self._ensure_list(menu):
            values = []
            for item in self._ensure_list(group.get("children")):
                code = self._stringify(item.get("code"))
                name = self._stringify(item.get("name") or item.get("nameEn") or code)
                if code and name and code not in ("THIS_YEAR", "LAST_YEAR"):
                    values.append({"n": name, "v": code})
            if group.get("nameEn") in option_map:
                option_map[group.get("nameEn")] = values

        filters = {}
        for cls in classes:
            items = []
            if option_map["year"]:
                items.append(
                    {
                        "key": "year",
                        "name": "年份",
                        "init": "",
                        "value": [{"n": "全部", "v": ""}] + option_map["year"],
                    }
                )
            if option_map["region"]:
                items.append(
                    {
                        "key": "region",
                        "name": "地区",
                        "init": "",
                        "value": [{"n": "全部", "v": ""}] + option_map["region"],
                    }
                )
            if option_map["genre"] and cls["type_id"] in (
                "movie",
                "tv_series",
                "animation",
                "variety",
                "short_drama",
            ):
                items.append(
                    {
                        "key": "genre",
                        "name": "类型",
                        "init": "",
                        "value": [{"n": "全部", "v": ""}] + option_map["genre"],
                    }
                )
            if option_map["language"]:
                items.append(
                    {
                        "key": "lang",
                        "name": "语言",
                        "init": "",
                        "value": [{"n": "全部", "v": ""}] + option_map["language"],
                    }
                )
            items.append({"key": "sort", "name": "排序", "init": "default", "value": self.sort_options})
            filters[cls["type_id"]] = items
        return filters

    def _map_top_code(self, category_id):
        mapping = {
            "movie": "movie",
            "tv_series": "tv_series",
            "animation": "animation",
            "variety": "variety",
            "short_drama": "short_drama",
            "THIS_YEAR": "movie",
            "LAST_YEAR": "movie",
        }
        return mapping.get(category_id, "movie")

    def _build_category_body(self, category_id, page, extend):
        filters = self._normalize_ext(extend)
        menu_code_list = []
        if category_id not in ("movie", "tv_series", "animation", "variety", "short_drama"):
            menu_code_list.append(category_id)
        for key in ("genre", "region", "year", "lang", "other"):
            value = self._stringify(filters.get(key))
            if value and value not in menu_code_list:
                menu_code_list.append(value)
        return {
            "menuCodeList": menu_code_list,
            "pageIndex": self._stringify(page or 1),
            "pageSize": self.page_size,
            "searchKey": "",
            "sortCode": "" if filters.get("sort") in (None, "", "default") else self._stringify(filters.get("sort")),
            "topCode": self._map_top_code(category_id),
        }

    def homeContent(self, filter):
        menu = self._request_json("/movie/category/menu")
        classes = self._build_classes(menu)
        return {"class": classes, "filters": self._build_filters(menu, classes)}
