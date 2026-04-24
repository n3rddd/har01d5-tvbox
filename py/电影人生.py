# coding=utf-8
import json
import re
import sys
from urllib.parse import quote, urlencode, urljoin

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "电影人生"
        self.host = "https://dyrsok.com"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/146.0.0.0 Safari/537.36"
            ),
            "Referer": self.host + "/",
        }
        self.classes = [
            {"type_id": "dianying", "type_name": "电影"},
            {"type_id": "dianshiju", "type_name": "电视剧"},
            {"type_id": "dongman", "type_name": "动漫"},
            {"type_id": "zongyi", "type_name": "综艺"},
        ]
        common_movie_tv = [
            {
                "key": "class",
                "name": "类型",
                "init": "",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "剧情", "v": "剧情"},
                    {"n": "喜剧", "v": "喜剧"},
                    {"n": "动作", "v": "动作"},
                ],
            },
            {
                "key": "sort_field",
                "name": "排序",
                "init": "",
                "value": [
                    {"n": "默认", "v": ""},
                    {"n": "热度", "v": "play_hot"},
                    {"n": "更新时间", "v": "update_time"},
                ],
            },
        ]
        common_dm = [
            {
                "key": "class",
                "name": "类型",
                "init": "",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "冒险", "v": "冒险"},
                    {"n": "热血", "v": "热血"},
                    {"n": "搞笑", "v": "搞笑"},
                ],
            },
            {
                "key": "sort_field",
                "name": "排序",
                "init": "",
                "value": [
                    {"n": "默认", "v": ""},
                    {"n": "热度", "v": "play_hot"},
                    {"n": "更新时间", "v": "update_time"},
                ],
            },
        ]
        common_zy = [
            {
                "key": "class",
                "name": "类型",
                "init": "",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "真人秀", "v": "真人秀"},
                    {"n": "脱口秀", "v": "脱口秀"},
                    {"n": "音乐", "v": "音乐"},
                ],
            },
            {
                "key": "sort_field",
                "name": "排序",
                "init": "",
                "value": [
                    {"n": "默认", "v": ""},
                    {"n": "热度", "v": "play_hot"},
                    {"n": "更新时间", "v": "update_time"},
                ],
            },
        ]
        self.filters = {
            "dianying": common_movie_tv,
            "dianshiju": common_movie_tv,
            "dongman": common_dm,
            "zongyi": common_zy,
        }

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def homeContent(self, filter):
        return {"class": self.classes, "filters": self.filters}

    def homeVideoContent(self):
        return {"list": self._parse_vod_cards(self._request_html(self.host + "/"))[:24]}

    def _abs_url(self, value):
        raw = str(value or "").strip()
        if not raw:
            return ""
        return urljoin(self.host + "/", raw)

    def _clean_text(self, text):
        return re.sub(r"\s+", " ", str(text or "").replace("\xa0", " ")).strip()

    def _request_html(self, url, headers=None):
        request_headers = dict(self.headers)
        if headers:
            request_headers.update(headers)
        response = self.fetch(url, headers=request_headers, timeout=10, verify=False)
        return response.text if response.status_code == 200 else ""

    def _request_response(self, url, headers=None, allow_redirects=False):
        request_headers = dict(self.headers)
        if headers:
            request_headers.update(headers)
        return self.fetch(
            url,
            headers=request_headers,
            timeout=10,
            verify=False,
            allow_redirects=allow_redirects,
        )

    def _parse_vod_cards(self, html):
        root = self.html(html)
        if root is None:
            return []
        cards = []
        seen = set()
        for node in root.xpath("//a[@data-url and @title]"):
            href = ((node.xpath("./@href") or [""])[0]).strip()
            title = ((node.xpath("./@title") or [""])[0]).strip()
            if not href or not title or "/dyrscom-" not in href:
                continue
            vod_id = href.lstrip("/")
            if vod_id in seen:
                continue
            seen.add(vod_id)
            parent = node.getparent()
            year = ""
            type_name = ""
            if parent is not None:
                year = self._clean_text(
                    "".join(parent.xpath(".//*[contains(@class,'items-center')][1]/span[1]//text()"))
                )
                type_name = self._clean_text(
                    "".join(parent.xpath(".//*[contains(@class,'items-center')][1]/span[last()]//text()"))
                )
            remarks = self._clean_text("".join(node.xpath(".//*[contains(@class,'text-[10px]')][1]//text()")))
            pic = ((node.xpath(".//img[1]/@data-src") or node.xpath(".//img[1]/@src") or [""])[0]).strip()
            cards.append(
                {
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": self._abs_url(pic),
                    "vod_url": self._abs_url(href),
                    "vod_year": year,
                    "type_name": type_name,
                    "vod_remarks": remarks,
                }
            )
        return cards

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg)
        values = extend if isinstance(extend, dict) else {}
        query = {}
        if values.get("class"):
            query["class"] = values["class"]
        if values.get("sort_field"):
            query["sort_field"] = values["sort_field"]
        if page > 1:
            query["page"] = page
        url = self.host + f"/{tid}.html"
        if query:
            url += "?" + urlencode(query)
        return {
            "page": page,
            "total": 0,
            "list": self._parse_vod_cards(self._request_html(url)),
        }

    def _pick_meta_value(self, html, label):
        patterns = [
            rf"{label}\s*</span>\s*<span[^>]*>([^<]+)</span>",
            rf">{label}\s*<[^>]*>\s*<span[^>]*>([^<]+)</span>",
            rf"<span[^>]*>{label}</span>\s*<span[^>]*>([^<]+)</span>",
        ]
        for pattern in patterns:
            matched = re.search(pattern, html)
            if matched:
                return self._clean_text(matched.group(1))
        root = self.html(html)
        if root is None:
            return ""
        nodes = root.xpath(f"//span[normalize-space(text())='{label}']/following-sibling::span[1]")
        if nodes:
            return self._clean_text("".join(nodes[0].xpath(".//text()")))
        return ""

    def _extract_link_texts(self, html, title):
        root = self.html(html)
        if root is None:
            return []
        values = []
        for node in root.xpath(f"//h3[contains(normalize-space(.), '{title}')]/following-sibling::*[1]//a//span"):
            text = self._clean_text("".join(node.xpath(".//text()"))).replace("#", "")
            if text:
                values.append(text)
        return values

    def detailContent(self, ids):
        vod_id = str(ids[0] if isinstance(ids, list) and ids else ids).strip()
        if not vod_id:
            return {"list": []}
        url = self._abs_url(vod_id)
        html = self._request_html(url)
        root = self.html(html)
        if root is None:
            return {"list": []}

        vod_name = self._clean_text("".join(root.xpath("(//h1|//h2)[1]//text()")))
        vod_pic = self._abs_url(((root.xpath("//meta[@property='og:image']/@content") or [""])[0]).strip())
        vod_content = self._clean_text(
            "".join(
                root.xpath(
                    "//h3[contains(normalize-space(.), '剧情简介')]/following-sibling::*[1]"
                    "//*[contains(@class,'text-sm')][1]//text()"
                )
            )
        ) or self._clean_text(((root.xpath("//meta[@name='description']/@content") or [""])[0]))
        vod_year = self._pick_meta_value(html, "年份")
        vod_area = self._pick_meta_value(html, "地区")
        vod_lang = self._pick_meta_value(html, "语言")
        vod_director = ",".join(self._extract_link_texts(html, "导演"))
        vod_actor = ",".join(self._extract_link_texts(html, "主演"))
        tags = self._extract_link_texts(html, "标签")

        from_list = []
        url_list = []
        for line_node in root.xpath("//*[@id='originTabs']//a[@href]"):
            href = ((line_node.xpath("./@href") or [""])[0]).strip()
            name = self._clean_text(
                ((line_node.xpath(".//button[@data-origin]/@data-origin") or [""])[0])
                or "".join(line_node.xpath(".//text()"))
            )
            line_url = self._abs_url(href)
            line_html = html if line_url == url else self._request_html(line_url)
            line_root = self.html(line_html)
            episodes = []
            if line_root is not None:
                for episode in line_root.xpath("//*[contains(@class,'seqlist')]//a[@href]"):
                    ep_href = ((episode.xpath("./@href") or [""])[0]).strip()
                    ep_title = self._clean_text(
                        ((episode.xpath("./@data-title") or [""])[0]) or "".join(episode.xpath(".//text()"))
                    ) or "播放"
                    payload = json.dumps(
                        {
                            "title": ep_title,
                            "origin": name,
                            "page": self._abs_url(ep_href),
                            "vodName": vod_name,
                            "pic": vod_pic,
                        },
                        ensure_ascii=False,
                    )
                    episodes.append(f"{ep_title}${payload}")
            if episodes:
                from_list.append(name)
                url_list.append("#".join(episodes))

        return {
            "list": [
                {
                    "vod_id": vod_id,
                    "vod_name": vod_name,
                    "vod_pic": vod_pic,
                    "vod_content": vod_content,
                    "vod_year": vod_year,
                    "vod_area": vod_area,
                    "vod_lang": vod_lang,
                    "vod_director": vod_director,
                    "vod_actor": vod_actor,
                    "type_name": " / ".join(tags),
                    "vod_play_from": "$$$".join(from_list),
                    "vod_play_url": "$$$".join(url_list),
                }
            ]
        }

    def _normalize_keyword(self, value):
        return re.sub(r"[\s\-_—–·•:：,，.。!?！？'\"“”‘’()（）\[\]【】{}]", "", str(value or "")).lower()

    def _search_score(self, vod_name, keyword):
        name = self._normalize_keyword(vod_name)
        key = self._normalize_keyword(keyword)
        if not name or not key:
            return 0
        if name == key:
            return 1000
        if name.startswith(key):
            return 800
        if key in name:
            return 600
        return 0

    def _refine_search_results(self, items, keyword):
        scored = [(self._search_score(item.get("vod_name"), keyword), item) for item in items]
        matched = [
            item
            for score, item in sorted(scored, key=lambda pair: (-pair[0], pair[1].get("vod_name", "")))
            if score > 0
        ]
        return matched or items

    def searchContent(self, key, quick, pg="1"):
        page = int(pg)
        keyword = self._clean_text(key)
        if not keyword:
            return {"page": page, "total": 0, "list": []}
        url = self.host + "/s.html?name=" + quote(keyword)
        if page > 1:
            url += "&page=" + str(page - 1)
        items = self._parse_vod_cards(self._request_html(url))
        return {"page": page, "total": len(items), "list": self._refine_search_results(items, keyword)}

    def playerContent(self, flag, id, vipFlags):
        raw = str(id or "").strip()
        if not raw:
            return {"parse": 1, "playUrl": "", "url": "", "header": {}, "jx": 1}
        try:
            meta = json.loads(raw)
        except Exception:
            meta = {"page": raw}
        page_url = self._abs_url(meta.get("page", ""))
        headers = {
            "User-Agent": self.headers["User-Agent"],
            "Referer": page_url or self.host + "/",
            "Origin": self.host,
        }
        html = self._request_html(page_url, headers={"Referer": self.host + "/"}) if page_url else ""
        matched = re.search(r"/api/m3u8\?origin=([^\"'\\\s&]+|[^\"'\\\s]+?)(&amp;|&)url=([a-zA-Z0-9]+)", html)
        if not matched:
            return {"parse": 1, "playUrl": "", "url": page_url, "header": headers, "jx": 1}

        api_url = self.host + "/api/m3u8?origin=" + matched.group(1) + "&url=" + matched.group(3)
        probe = self._request_response(api_url, headers=headers, allow_redirects=False)
        final_url = api_url
        location = ""
        if hasattr(probe, "headers"):
            location = probe.headers.get("Location") or probe.headers.get("location") or ""
        if location:
            final_url = self._abs_url(location)
            playlist = self._request_html(final_url, headers={"Referer": self.host + "/"})
            raw_line = next(
                (line.strip() for line in playlist.splitlines() if "/api/m3u8?id=" in line and "raw=1" in line),
                "",
            )
            if raw_line:
                final_url = urljoin(final_url, raw_line)
        return {"parse": 0, "playUrl": "", "url": final_url, "header": headers, "jx": 0}
