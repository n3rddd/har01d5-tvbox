# coding=utf-8
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from urllib.parse import quote, urlencode, urljoin

from lxml import html as lxml_html

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "两个BT"
        self.host = "https://www.bttwoo.com"
        self._wasm_asset_cache = {}
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
        url = self.host + f"/search?q={quote(keyword)}"
        if page > 1:
            url += f"&page={page}"
        items = self._extract_cards(self._request_html(url), keyword=keyword)
        return {"page": page, "limit": len(items), "total": len(items), "list": items}

    def detailContent(self, ids):
        vod_id = self._normalize_vod_id(ids[0] if isinstance(ids, list) and ids else ids)
        if not vod_id:
            return {"list": []}
        html = self._request_html(self._build_detail_url(vod_id))
        detail = self._parse_detail(html, vod_id)
        return {"list": [detail]} if detail else {"list": []}

    def playerContent(self, flag, id, vipFlags):
        play_id = str(id or "").strip()
        if self._is_media_url(play_id):
            return self._build_player_result(play_id, self.host + "/")

        meta = self._decode_play_id(play_id)
        pid = meta.get("pid") or play_id
        play_path = self._extract_play_path(pid)
        if str(pid or "").startswith(("http://", "https://")):
            play_page_url = str(pid)
        elif play_path:
            play_page_url = self._abs_url(play_path)
        else:
            play_page_url = self.host + f"/v_play/{pid}.html"
        html = self._request_html(play_page_url, referer=self.host + "/")
        media_url = self._extract_media_url(html)
        if media_url:
            return self._build_player_result(media_url, play_page_url)

        iframe_url = self._extract_iframe_url(html)
        if iframe_url:
            iframe_html = self._request_html(iframe_url, referer=play_page_url)
            iframe_media_url = self._extract_media_url(iframe_html)
            if iframe_media_url:
                return self._build_player_result(iframe_media_url, iframe_url)

        if play_path:
            self._cache_wasm_assets(html)
            dataid = self._extract_play_dataid(html, play_page_url)
            secret_key = play_path.rsplit("/", 1)[-1]
            userlink = self._extract_userlink(html) or "0"
            api_url = self._build_wasm_play_api_url(dataid, secret_key, "1080", userlink)
            api_data = self._request_json(api_url, referer=play_page_url)
            media_url = self._extract_media_from_play_api(api_data)
            if media_url:
                return self._build_player_result(media_url, play_page_url)

        return self._build_parse_result(play_page_url, play_page_url)

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
        filters = {
            "zgjun": {"classify": "2", "tvclasses": "20"},
            "meiju": {"classify": "2", "tvclasses": "21"},
            "jpsrtv": {"classify": "2", "tvclasses": "22"},
            "movie_bt_tags/xiju": {"classify": "1", "types": "5"},
            "movie_bt_tags/aiqing": {"classify": "1", "types": "6"},
            "movie_bt_tags/adt": {"classify": "1", "types": "18"},
            "movie_bt_tags/at": {"classify": "1", "types": "10"},
            "movie_bt_tags/donghua": {"classify": "1", "types": "11"},
            "movie_bt_tags/qihuan": {"classify": "1", "types": "12"},
            "movie_bt_tags/xuanni": {"classify": "1", "types": "2"},
            "movie_bt_tags/kehuan": {"classify": "1", "types": "14"},
            "movie_bt_tags/juqing": {"classify": "1", "types": "1"},
            "movie_bt_tags/kongbu": {"classify": "1", "types": "3"},
            "gf": {"classify": "1", "sort_by": "score", "order": "desc"},
        }.get(path)
        if filters:
            params = dict(filters)
            if page > 1:
                params["page"] = str(page)
            return self.host + "/filter?" + urlencode(params)
        url = self.host + "/" + path
        if page > 1:
            url += f"?page={page}"
        return url

    def _extract_cards(self, html, keyword=None):
        root = self._parse_html(html)
        if root is None:
            return []
        results = []
        seen = set()
        nodes = root.xpath(
            "//*[contains(concat(' ', normalize-space(@class), ' '), ' movie-card ')]"
            "|//li[.//a[contains(@href,'/movie/')]]"
        )
        for node in nodes:
            href = (
                self._first_attr(node, ".//a[contains(@href,'/play/')][1]", "href")
                or self._first_attr(node, ".//a[contains(@href,'/movie/')][1]", "href")
            )
            vod_id = self._extract_card_id(href)
            title = (
                self._first_text(node, ".//h3//a[1]")
                or self._first_text(node, ".//h3[1]")
                or self._clean_text(self._first_attr(node, ".//a[@title][1]", "title"))
                or self._clean_text(self._first_attr(node, ".//img[@alt][1]", "alt"))
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
                or self._first_text(node, ".//span[contains(text(),'集')][1]")
                or self._first_text(node, ".//span[contains(text(),'HD')][1]")
                or self._first_text(node, ".//span[contains(text(),'4k')][1]")
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

    def _extract_play_path(self, href):
        raw = str(href or "").strip()
        if "/play/" not in raw:
            return ""
        path = raw[raw.find("/play/") :]
        return path.split("?", 1)[0].split("#", 1)[0]

    def _extract_card_id(self, href):
        return self._extract_play_path(href) or self._extract_vod_id(href)

    def _extract_play_pid(self, href):
        matched = re.search(r"/v_play/([^.]+)\.html", str(href or "").strip())
        return matched.group(1) if matched else ""

    def _normalize_vod_id(self, value):
        raw = str(value or "").strip()
        return self._extract_play_path(raw) or raw

    def _build_detail_url(self, vod_id):
        raw = str(vod_id or "").strip()
        if not raw:
            return ""
        if raw.startswith(("http://", "https://")):
            return raw
        play_path = self._extract_play_path(raw)
        if play_path:
            return self._abs_url(play_path)
        if raw.startswith("/movie/"):
            return self._abs_url(raw)
        return self.host + f"/movie/{raw}.html"

    def _parse_detail(self, html, vod_id):
        root = self._parse_html(html)
        if root is None:
            return None

        vod_name = (
            self._first_text(root, "//*[contains(@class,'movie-poster')]//h1[1]")
            or self._first_text(root, "//h1[1]")
            or self._first_text(root, "//h2[1]")
            or self._extract_title_text(html)
        )
        vod_pic = (
            self._first_attr(root, "//meta[@property='og:image'][1]", "content")
            or self._first_attr(root, "//*[contains(@class,'movie-poster')]//img[1]", "src")
            or self._first_attr(root, "//img[contains(@class,'poster')][1]", "src")
            or self._first_attr(root, "//*[contains(@class,'poster')]//img[1]", "src")
            or self._first_attr(root, "//img[1]", "src")
        )
        vod_content = (
            self._first_attr(root, "//meta[@name='description'][1]", "content")
            or self._first_text(root, "//*[contains(text(),'剧情简介')]/following::p[1]")
            or self._first_text(root, "//*[contains(@class,'intro')][1]")
            or self._first_text(root, "//*[contains(@class,'description')][1]")
            or self._first_text(root, "//*[contains(@class,'desc')][1]")
        )
        vod_actor = self._extract_labeled_value(root, "主演") or self._extract_meta_text(root, "主演")
        vod_director = self._extract_labeled_value(root, "导演") or self._extract_meta_text(root, "导演")

        episodes = []
        seen = set()
        episode_nodes = root.xpath(
            "//*[@x-data[contains(.,'episodeManager')]]//a[contains(@href,'/play/')]"
            "|//*[contains(@class,'episode-link') and contains(@href,'/play/')]"
            "|//a[contains(@href,'/v_play/')]"
        )
        for index, node in enumerate(episode_nodes):
            href = str(node.get("href") or "").strip()
            pid = self._extract_play_path(href) or self._extract_play_pid(href)
            name = self._clean_text(node.text_content()) or self._clean_text(node.get("data-episode")) or f"第{index + 1}集"
            if not pid or pid in seen:
                continue
            seen.add(pid)
            episodes.append(f"{name}${self._encode_play_id(pid, vod_id, name)}")

        if not episodes:
            return None

        return {
            "vod_id": vod_id,
            "vod_name": vod_name or "未知标题",
            "vod_pic": self._abs_url(vod_pic),
            "vod_content": vod_content,
            "vod_actor": vod_actor,
            "vod_director": vod_director,
            "vod_play_from": "两个BT",
            "vod_play_url": "#".join(episodes),
        }

    def _encode_play_id(self, pid, sid, name):
        raw = json.dumps(
            {"pid": str(pid or ""), "sid": str(sid or ""), "name": str(name or "")},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return base64.b64encode(raw.encode("utf-8")).decode("utf-8")

    def _decode_play_id(self, value):
        try:
            raw = base64.b64decode(str(value or "").encode("utf-8")).decode("utf-8")
            data = json.loads(raw)
        except Exception:
            return {"pid": "", "sid": "", "name": ""}
        return {
            "pid": str(data.get("pid") or ""),
            "sid": str(data.get("sid") or ""),
            "name": str(data.get("name") or ""),
        }

    def _extract_title_text(self, html):
        matched = re.search(r"<title>(.*?)</title>", str(html or ""), re.I | re.S)
        return self._clean_text(matched.group(1)) if matched else ""

    def _extract_meta_text(self, root, label):
        text = self._first_text(root, f"//*[contains(text(),'{label}')][1]")
        return re.sub(rf"^{label}[:：]?", "", text).strip()

    def _extract_labeled_value(self, root, label):
        if root is None:
            return ""
        for node in root.xpath(
            f"//*[normalize-space(text())='{label}' or contains(text(),'{label}：') or contains(text(),'{label}:')]"
        ):
            text = self._clean_text(node.text_content())
            inline = re.sub(rf"^{label}[:：]?", "", text).strip()
            if inline and inline != text:
                return inline
            sibling = node.getnext()
            if sibling is not None:
                sibling_text = self._clean_text(sibling.text_content())
                if sibling_text:
                    return sibling_text
        return ""

    def _extract_userlink(self, html):
        matched = re.search(r"userlink:'([^']+)'", str(html or ""))
        return str(matched.group(1) or "").strip() if matched else ""

    def _extract_play_dataid(self, html, play_page_url):
        root = self._parse_html(html)
        if root is None:
            return ""
        play_path = self._extract_play_path(play_page_url)
        if play_path:
            for node in root.xpath(f"//a[@dataid and contains(@href,'{play_path}')]"):
                dataid = str(node.get("dataid") or "").strip()
                if dataid:
                    return dataid
        return self._first_attr(root, "//a[@dataid][1]", "dataid")

    def _cache_wasm_assets(self, html):
        js_rel = self._first_attr(self._parse_html(html), "//*[@id='wasm-cfg'][1]", "data-js")
        wasm_rel = self._first_attr(self._parse_html(html), "//*[@id='wasm-cfg'][1]", "data-bg")
        if not js_rel or not wasm_rel:
            return
        cache_key = f"{js_rel}|{wasm_rel}"
        cached = self._wasm_asset_cache.get(cache_key)
        if cached and os.path.exists(cached.get("js", "")) and os.path.exists(cached.get("wasm", "")):
            self._wasm_asset_cache["active"] = cached
            return
        tmp_dir = tempfile.gettempdir()
        js_path = os.path.join(tmp_dir, f"lianggebt_{hashlib.md5(js_rel.encode('utf-8')).hexdigest()}.mjs")
        wasm_path = os.path.join(tmp_dir, f"lianggebt_{hashlib.md5(wasm_rel.encode('utf-8')).hexdigest()}.wasm")
        if not os.path.exists(js_path):
            response = self.fetch(self._abs_url(js_rel), headers=self.headers, timeout=15, verify=False)
            if response.status_code == 200:
                with open(js_path, "w", encoding="utf-8") as handle:
                    handle.write(response.text or "")
        if not os.path.exists(wasm_path):
            response = self.fetch(self._abs_url(wasm_rel), headers=self.headers, timeout=15, verify=False)
            if response.status_code == 200:
                with open(wasm_path, "wb") as handle:
                    handle.write(response.content or b"")
        active = {"js": js_path, "wasm": wasm_path}
        self._wasm_asset_cache[cache_key] = active
        self._wasm_asset_cache["active"] = active

    def _build_wasm_play_api_url(self, dataid, secret_key, quality, userlink):
        active = self._wasm_asset_cache.get("active") or {}
        js_path = active.get("js", "")
        wasm_path = active.get("wasm", "")
        if not dataid or not secret_key or not js_path or not wasm_path:
            return ""
        if not os.path.exists(js_path) or not os.path.exists(wasm_path):
            return ""
        script = (
            "import { pathToFileURL } from 'node:url';"
            "const mod = await import(pathToFileURL(process.argv[1]).href);"
            "await mod.default({module_or_path: await (await import('node:fs/promises')).readFile(process.argv[2])});"
            "console.log(mod.build_play_url(process.argv[3], process.argv[4], process.argv[5], process.argv[6]));"
        )
        try:
            result = subprocess.run(
                [
                    "node",
                    "--input-type=module",
                    "-e",
                    script,
                    js_path,
                    wasm_path,
                    str(dataid),
                    str(secret_key),
                    str(quality or "1080"),
                    str(userlink or "0"),
                ],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
        except Exception:
            return ""
        if result.returncode != 0:
            return ""
        return self._abs_url((result.stdout or "").strip())

    def _request_json(self, url, referer=None):
        target = str(url or "").strip()
        if not target:
            return {}
        headers = dict(self.headers)
        headers["Referer"] = referer or self.headers["Referer"]
        headers["Accept"] = "application/json,text/plain,*/*"
        try:
            response = self.fetch(target, headers=headers, timeout=15, verify=False)
        except Exception:
            return {}
        if response.status_code != 200:
            return {}
        try:
            return json.loads(response.text or "{}")
        except Exception:
            return {}

    def _extract_media_from_play_api(self, data):
        payload = ((data or {}).get("data") or {}) if isinstance(data, dict) else {}
        quality_urls = payload.get("quality_urls") or []
        current_quality = self._to_int(payload.get("current_quality"), 0)
        ordered = []
        if 0 <= current_quality < len(quality_urls):
            ordered.append(quality_urls[current_quality])
        ordered.extend([item for index, item in enumerate(quality_urls) if index != current_quality])
        for item in ordered:
            url = str((item or {}).get("url") or "").strip()
            if url and url != "1":
                return self._abs_url(url)
        return ""

    def _extract_media_url(self, html):
        body = str(html or "")
        patterns = [
            r'(https?://[^"\'\s<>]+\.(?:m3u8|mp4|flv|avi|mkv|ts)(?:\?[^"\'\s<>]*)?)',
            r'"url"\s*:\s*"([^"]+\.(?:m3u8|mp4|flv|avi|mkv|ts)[^"]*)"',
            r"'url'\s*:\s*'([^']+\.(?:m3u8|mp4|flv|avi|mkv|ts)[^']*)'",
        ]
        for pattern in patterns:
            matched = re.search(pattern, body, re.I)
            if matched:
                value = matched.group(1) if matched.groups() else matched.group(0)
                return self._abs_url(value)
        return ""

    def _is_media_url(self, value):
        return bool(re.search(r"\.(?:m3u8|mp4|flv|avi|mkv|ts)(?:\?|#|$)", str(value or ""), re.I))

    def _build_player_result(self, url, referer):
        return {
            "parse": 0,
            "jx": 0,
            "playUrl": "",
            "url": str(url or ""),
            "header": {
                "User-Agent": self.headers["User-Agent"],
                "Referer": str(referer or self.host + "/"),
                "Origin": self.host,
            },
        }

    def _build_parse_result(self, url, referer):
        return {
            "parse": 1,
            "jx": 1,
            "playUrl": "",
            "url": str(url or ""),
            "header": {
                "User-Agent": self.headers["User-Agent"],
                "Referer": str(referer or self.host + "/"),
                "Origin": self.host,
            },
        }

    def _extract_iframe_url(self, html):
        matched = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', str(html or ""), re.I)
        return self._abs_url(matched.group(1)) if matched else ""

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
