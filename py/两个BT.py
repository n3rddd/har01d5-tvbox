# coding=utf-8
import re
import sys
from urllib.parse import quote, urljoin

from lxml import html as lxml_html

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "两个BT"
        self.host = "https://www.bttwoo.com"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": self.host + "/",
        }
        self.classes = [
            {"type_id": "zgjun", "type_name": "国产剧"},
            {"type_id": "meiju", "type_name": "美剧"},
            {"type_id": "jpsrtv", "type_name": "日韩剧"},
            {"type_id": "movie_bt_tags/xiju", "type_name": "喜剧"},
            {"type_id": "movie_bt_tags/aiqing", "type_name": "爱情"},
            {"type_id": "movie_bt_tags/adt", "type_name": "冒险"},
            {"type_id": "movie_bt_tags/at", "type_name": "动作"},
            {"type_id": "movie_bt_tags/donghua", "type_name": "动画"},
            {"type_id": "movie_bt_tags/qihuan", "type_name": "奇幻"},
            {"type_id": "movie_bt_tags/xuanni", "type_name": "悬疑"},
            {"type_id": "movie_bt_tags/kehuan", "type_name": "科幻"},
            {"type_id": "movie_bt_tags/juqing", "type_name": "剧情"},
            {"type_id": "movie_bt_tags/kongbu", "type_name": "恐怖"},
            {"type_id": "gf", "type_name": "高分电影"},
        ]

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def homeContent(self, filter):
        return {"class": self.classes}

    def homeVideoContent(self):
        return {"list": self._extract_cards(self._request_html(self.host))}

    def categoryContent(self, tid, pg, filter, extend):
        page = max(1, self._to_int(pg, 1))
        items = self._extract_cards(self._request_html(self._build_category_url(tid, page)))
        return {"page": page, "limit": len(items), "total": len(items), "list": items}

    def searchContent(self, key, quick, pg="1"):
        page = max(1, self._to_int(pg, 1))
        keyword = self._clean_text(key)
        if not keyword:
            return {"page": page, "limit": 0, "total": 0, "list": []}
        url = self.host + f"/xssssearch?q={quote(keyword)}"
        if page > 1:
            url += f"&p={page}"
        items = self._extract_cards(self._request_html(url), keyword=keyword)
        return {"page": page, "limit": len(items), "total": len(items), "list": items}

    def detailContent(self, ids):
        return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        return {"parse": 1, "jx": 1, "playUrl": "", "url": "", "header": {}}

    def _request_html(self, url, referer=None):
        headers = dict(self.headers)
        headers["Referer"] = referer or self.headers["Referer"]
        try:
            response = self.fetch(url, headers=headers, timeout=10, verify=False)
        except Exception:
            return ""
        if response.status_code != 200:
            return ""
        return str(response.text or "")

    def _build_category_url(self, tid, page):
        path = str(tid or "").strip().lstrip("/")
        url = self.host + "/" + path
        if page > 1:
            url += f"?paged={page}"
        return url

    def _extract_cards(self, html, keyword=None):
        root = self._parse_html(html)
        if root is None:
            return []
        results = []
        seen = set()
        for node in root.xpath("//li[.//a[contains(@href,'/movie/')]]"):
            href = self._first_attr(node, ".//a[contains(@href,'/movie/')][1]", "href")
            vod_id = self._extract_vod_id(href)
            title = (
                self._first_text(node, ".//h3//a[1]")
                or self._first_text(node, ".//h3[1]")
                or self._clean_text(self._first_attr(node, ".//a[@title][1]", "title"))
                or self._first_text(node, ".//*[contains(@class,'title')][1]")
                or self._first_text(node, ".//*[contains(@class,'name')][1]")
            )
            if not vod_id or not title or vod_id in seen:
                continue
            if keyword and not self._is_relevant_search_result(title, keyword):
                continue
            pic = (
                self._first_attr(node, ".//img[@data-original][1]", "data-original")
                or self._first_attr(node, ".//img[@data-src][1]", "data-src")
                or self._first_attr(node, ".//img[@src][1]", "src")
            )
            remarks = (
                self._first_text(node, ".//*[contains(@class,'rating')][1]")
                or self._first_text(node, ".//*[contains(@class,'status')][1]")
            )
            seen.add(vod_id)
            results.append(
                {
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": self._abs_url(pic),
                    "vod_remarks": remarks,
                }
            )
        return results

    def _is_relevant_search_result(self, title, keyword):
        title_text = self._clean_text(title).lower()
        keyword_text = self._clean_text(keyword).lower()
        if not title_text or not keyword_text:
            return False
        if keyword_text in title_text:
            return True
        if len(keyword_text) <= 2:
            return False
        key_chars = set(keyword_text.replace(" ", ""))
        title_chars = set(title_text.replace(" ", ""))
        if not key_chars:
            return False
        return len(key_chars & title_chars) / float(len(key_chars)) >= 0.6

    def _extract_vod_id(self, href):
        matched = re.search(r"/movie/(\d+)\.html", str(href or "").strip())
        return matched.group(1) if matched else ""

    def _abs_url(self, value):
        raw = str(value or "").strip()
        if not raw:
            return ""
        if raw.startswith(("http://", "https://")):
            return raw
        if raw.startswith("//"):
            return "https:" + raw
        return urljoin(self.host + "/", raw.lstrip("/"))

    def _parse_html(self, text):
        body = str(text or "").strip()
        if not body:
            return None
        try:
            return lxml_html.fromstring(body)
        except Exception:
            return None

    def _clean_text(self, text):
        return re.sub(r"\s+", " ", str(text or "").replace("\xa0", " ")).strip()

    def _first_attr(self, node, xpath, attr):
        if node is None:
            return ""
        for item in node.xpath(xpath):
            value = str(item.get(attr) or "").strip()
            if value:
                return value
        return ""

    def _first_text(self, node, xpath):
        if node is None:
            return ""
        for item in node.xpath(xpath):
            text = self._clean_text(item.text_content())
            if text:
                return text
        return ""

    def _to_int(self, value, default=0):
        try:
            return int(str(value))
        except Exception:
            return default
