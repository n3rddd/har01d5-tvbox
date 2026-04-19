# coding=utf-8
import base64
import json
import re
import sys
from urllib.parse import quote, unquote

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "Gimy剧迷"
        self.host = "https://gimyai.tw"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/146.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://gimyai.tw/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        }
        self.categories = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "电视剧"},
            {"type_id": "4", "type_name": "动漫"},
            {"type_id": "29", "type_name": "综艺"},
            {"type_id": "34", "type_name": "短剧"},
            {"type_id": "13", "type_name": "陆剧"},
        ]
        filter_value = [
            {"n": "最新", "v": "time"},
            {"n": "人气", "v": "hits"},
            {"n": "评分", "v": "score"},
        ]
        self.filters = {
            key: [{"key": "by", "name": "排序", "init": "time", "value": filter_value}]
            for key in ["1", "2", "4", "29", "34", "13"]
        }
        self.filter_def = {key: {"by": "time"} for key in self.filters}
        self.t2s_map = {
            "鬥": "斗",
            "羅": "罗",
            "陸": "陆",
            "劇": "剧",
            "藝": "艺",
            "綜": "综",
            "動": "动",
            "畫": "画",
            "機": "机",
            "戰": "战",
            "鋼": "钢",
            "彈": "弹",
            "雲": "云",
            "狀": "状",
            "態": "态",
            "類": "类",
            "國": "国",
            "導": "导",
            "簡": "简",
            "線": "线",
            "賊": "贼",
        }

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def homeContent(self, filter):
        return {"class": self.categories, "filters": self.filters}

    def _build_url(self, href):
        raw = str(href or "").strip()
        if not raw:
            return ""
        if raw.startswith(("http://", "https://")):
            return raw
        if raw.startswith("//"):
            return "https:" + raw
        return self.host + "/" + raw.lstrip("/")

    def _normalize_text(self, text):
        value = re.sub(r"<[^>]+>", " ", str(text or ""))
        return re.sub(r"\s+", " ", value.replace("&nbsp;", " ")).strip()

    def _to_display_text(self, text):
        clean = self._normalize_text(text)
        for trad, simp in self.t2s_map.items():
            clean = clean.replace(trad, simp)
        return clean

    def _extract_cards(self, html):
        root = self.html(html)
        if root is None:
            return []

        items = []
        seen = set()
        for anchor in root.xpath("//a[contains(@href,'/detail/')]"):
            href = (anchor.xpath("./@href") or [""])[0].strip()
            matched = re.search(r"/detail/(\d+)\.html", href)
            if not matched:
                continue

            vod_id = matched.group(1)
            if vod_id in seen:
                continue

            title = (
                (anchor.xpath("./@title") or [""])[0].strip()
                or (anchor.xpath(".//img/@alt") or [""])[0].strip()
                or "".join(anchor.xpath(".//text()")).strip()
            )
            pic = (
                (anchor.xpath("./@data-original") or [""])[0].strip()
                or (anchor.xpath("./@data-src") or [""])[0].strip()
                or (anchor.xpath(".//img/@src") or [""])[0].strip()
            )
            parent = anchor.getparent()
            remarks = ""
            if parent is not None:
                remarks = "".join(
                    parent.xpath(".//*[contains(@class,'note') or contains(@class,'text')]//text()")
                ).strip()

            seen.add(vod_id)
            items.append(
                {
                    "vod_id": vod_id,
                    "vod_name": self._to_display_text(title),
                    "vod_pic": self._build_url(pic),
                    "vod_remarks": self._to_display_text(remarks),
                }
            )
        return items

    def _build_category_url(self, tid, pg, extend):
        page = int(pg)
        values = dict(self.filter_def.get(str(tid), {"by": "time"}))
        if isinstance(extend, dict):
            values.update(extend)

        by = str(values.get("by", "time"))
        url = f"{self.host}/genre/{tid}.html"
        if page > 1 or by != "time":
            url += f"?page={page}&by={by}"
        return url

    def _request_html(self, path_or_url, referer=None):
        target = path_or_url if str(path_or_url).startswith("http") else self._build_url(path_or_url)
        headers = dict(self.headers)
        headers["Referer"] = referer or self.headers["Referer"]
        response = self.fetch(target, headers=headers, timeout=10)
        if response.status_code != 200:
            return ""
        return response.text or ""

    def homeVideoContent(self):
        html = self._request_html(self.host)
        return {"list": self._extract_cards(html)[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        url = self._build_category_url(str(tid), str(pg), extend if isinstance(extend, dict) else {})
        items = self._extract_cards(self._request_html(url))
        page = int(pg)
        pagecount = page + 1 if len(items) >= 20 else page
        return {
            "list": items,
            "page": page,
            "pagecount": pagecount,
            "limit": 20,
            "total": page * 20 + len(items),
        }

    def _pick_info(self, html, label):
        matched = re.search(rf"<span[^>]*>{label}[：:]</span>(.*?)</li>", str(html or ""), re.S)
        return self._to_display_text(matched.group(1) if matched else "")

    def _parse_play_sources(self, html):
        root = self.html(html)
        if root is None:
            return []

        groups = []
        tabs = []
        for tab in root.xpath("//*[@id='playTab']//a[starts-with(@href,'#con_playlist_')]"):
            tabs.append(
                {
                    "id": (tab.xpath("./@href") or [""])[0].replace("#", ""),
                    "name": self._to_display_text("".join(tab.xpath(".//text()"))),
                }
            )

        for tab in tabs:
            episodes = []
            for anchor in root.xpath(f"//*[@id='{tab['id']}']//a[contains(@href,'/play/')]"):
                href = (anchor.xpath("./@href") or [""])[0].strip()
                matched = re.search(r"/play/(\d+-\d+-\d+)\.html", href)
                if not matched:
                    continue
                title = self._to_display_text("".join(anchor.xpath(".//text()"))) or "正片"
                episodes.append(f"{title}${matched.group(1)}")
            if episodes:
                groups.append({"from": tab["name"], "urls": "#".join(episodes)})
        return groups

    def _parse_detail_page(self, html, vod_id):
        root = self.html(html)
        if root is None:
            return {"list": []}

        title = "".join(
            root.xpath("//h1[contains(@class,'text-overflow')][1]//text()") or root.xpath("//h1[1]//text()")
        ).strip()
        poster = ((root.xpath("//meta[@property='og:image']/@content") or [""])[0]).strip()
        content = "".join(
            root.xpath("//*[contains(@class,'details-content') or contains(@class,'detail-sketch')][1]//text()")
        ).strip()
        actors = [self._to_display_text(text) for text in root.xpath("//li[contains(.,'主演')]//a/text()")]
        directors = [
            self._to_display_text(text)
            for text in root.xpath("//li[contains(.,'導演') or contains(.,'导演')]//a/text()")
        ]
        play_groups = self._parse_play_sources(html)

        return {
            "list": [
                {
                    "vod_id": str(vod_id),
                    "vod_name": self._to_display_text(title),
                    "vod_pic": self._build_url(poster),
                    "vod_content": self._to_display_text(content),
                    "vod_remarks": self._pick_info(html, "狀態") or self._pick_info(html, "状态"),
                    "type_name": self._pick_info(html, "類別") or self._pick_info(html, "类别"),
                    "vod_year": self._pick_info(html, "年代") or self._pick_info(html, "年份"),
                    "vod_area": self._pick_info(html, "國家/地區") or self._pick_info(html, "国家/地区"),
                    "vod_actor": ",".join([item for item in actors if item]),
                    "vod_director": ",".join([item for item in directors if item]),
                    "vod_play_from": "$$$".join([item["from"] for item in play_groups]),
                    "vod_play_url": "$$$".join([item["urls"] for item in play_groups]),
                }
            ]
        }

    def detailContent(self, ids):
        raw = ids[0]
        url = raw if str(raw).startswith("http") else f"{self.host}/detail/{raw}.html"
        html = self._request_html(url)
        matched = re.search(r"/detail/(\d+)\.html", url)
        vod_id = matched.group(1) if matched else str(raw)
        return self._parse_detail_page(html, vod_id)

    def _normalize_search_keyword(self, text):
        value = self._to_display_text(text).lower()
        return re.sub(r"[\s\-_—–·•:：,，.。!?！？'\"“”‘’()（）\[\]【】{}]", "", value)

    def _build_search_tokens(self, keyword):
        base = self._normalize_search_keyword(keyword)
        if not base:
            return []

        tokens = [base]
        simplified = re.sub(
            r"线上看|線上看|全集|連續劇|连续剧|電視劇|电视剧|動漫|动漫|電影|电影|綜藝|综艺",
            "",
            base,
        ).strip()
        if simplified and simplified not in tokens:
            tokens.append(simplified)

        stripped = re.sub(r"第\d+[集季部篇]?$", "", simplified)
        stripped = re.sub(r"\d+$", "", stripped)
        if stripped and stripped not in tokens:
            tokens.append(stripped)

        return sorted([item for item in tokens if item], key=len, reverse=True)

    def _score_search_result(self, vod_name, keyword):
        name = self._normalize_search_keyword(vod_name)
        best = 0
        for token in self._build_search_tokens(keyword):
            if name == token:
                best = max(best, 1000 + len(token))
            elif name.startswith(token):
                best = max(best, 800 + len(token))
            elif token in name:
                best = max(best, 600 + len(token))
            elif len(name) >= 2 and name in token:
                best = max(best, 450 + len(name))
        return best

    def _refine_search_results(self, items, keyword):
        scored = []
        for item in items:
            score = self._score_search_result(item.get("vod_name", ""), keyword)
            if score > 0:
                scored.append((score, item))

        if scored:
            scored.sort(key=lambda pair: (-pair[0], pair[1].get("vod_name", "")))
            return [item for _, item in scored]

        loose_key = self._normalize_search_keyword(keyword)
        return [
            item
            for item in items
            if loose_key and loose_key in self._normalize_search_keyword(item.get("vod_name", ""))
        ]

    def searchContent(self, key, quick, pg="1"):
        url = f"{self.host}/find/-------------.html?wd={quote(str(key))}&page={pg}"
        html = self._request_html(url)
        raw_items = self._extract_cards(html)
        items = self._refine_search_results(raw_items, key)
        page = int(pg)
        pagecount = page + 1 if len(raw_items) >= 20 else page
        return {
            "list": items,
            "page": page,
            "pagecount": pagecount,
            "limit": len(items),
            "total": len(items),
        }

    def _extract_player_data(self, html):
        matched = re.search(r"var\s+player_data\s*=\s*(\{[\s\S]*?\})\s*;?\s*</script>", str(html or ""), re.S)
        if not matched:
            return {}
        try:
            return json.loads(matched.group(1))
        except Exception:
            return {}

    def _decode_play_url(self, player_data):
        raw = str(player_data.get("url", "")).strip()
        encrypt = str(player_data.get("encrypt", "0")).strip()
        if not raw:
            return ""
        if encrypt == "1":
            return unquote(raw)
        if encrypt == "2":
            try:
                decoded = base64.b64decode(raw).decode("utf-8")
                return unquote(decoded)
            except Exception:
                return ""
        return raw

    def _is_direct_media_url(self, url):
        return bool(re.match(r"^https?://.*\.(m3u8|mp4|flv|m4s)(\?.*)?$", str(url or ""), re.I))

    def _build_parse_context(self, raw_url, play_from, play_page_url):
        base = "https://play.gimyai.tw/v/"
        referer = f"https://play.gimyai.tw/v/?url={quote(raw_url)}"
        if play_from in ["JD4K", "JD2K", "JDHG", "JDQM"]:
            base = "https://play.gimyai.tw/d/"
            referer = (
                f"https://play.gimyai.tw/d/?url={quote(raw_url)}"
                f"&jctype={play_from}&next={quote(play_page_url)}"
            )
        elif play_from == "NSYS":
            base = "https://play.gimyai.tw/n/"
            referer = (
                f"https://play.gimyai.tw/n/?url={quote(raw_url)}"
                f"&jctype={play_from}&next={quote(play_page_url)}"
            )
        return {
            "parse_url": f"{base}parse.php?url={quote(raw_url)}&_t=1",
            "referer": referer,
            "origin": "https://play.gimyai.tw",
        }

    def playerContent(self, flag, id, vipFlags):
        play_id = str(id)
        play_page_url = play_id if play_id.startswith("http") else f"{self.host}/play/{play_id}.html"
        page_headers = {
            "User-Agent": self.headers["User-Agent"],
            "Referer": play_page_url,
            "Origin": self.host,
        }

        html = self._request_html(play_page_url, referer=play_page_url)
        player_data = self._extract_player_data(html)
        raw_url = self._decode_play_url(player_data)

        if self._is_direct_media_url(raw_url):
            return {
                "parse": 0,
                "jx": 0,
                "url": raw_url,
                "header": {"User-Agent": self.headers["User-Agent"], "Referer": play_page_url},
            }

        if raw_url:
            context = self._build_parse_context(raw_url, str(player_data.get("from", "")).strip(), play_page_url)
            parse_text = self._request_html(context["parse_url"], referer=context["referer"])
            try:
                parse_json = json.loads(parse_text or "{}")
            except Exception:
                parse_json = {}

            media_url = str(
                parse_json.get("url") or parse_json.get("video") or parse_json.get("playurl") or ""
            ).strip()
            if media_url:
                return {
                    "parse": 0,
                    "jx": 0,
                    "url": media_url,
                    "header": {
                        "User-Agent": self.headers["User-Agent"],
                        "Referer": context["referer"],
                        "Origin": context["origin"],
                    },
                }

            if raw_url.startswith("http"):
                return {
                    "parse": 1,
                    "jx": 1,
                    "url": raw_url,
                    "header": {
                        "User-Agent": self.headers["User-Agent"],
                        "Referer": context["referer"],
                    },
                }

        return {"parse": 1, "jx": 1, "url": play_page_url, "header": page_headers}
