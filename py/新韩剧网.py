# coding=utf-8
import base64
import re
import sys
from urllib.parse import quote, urljoin

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

from base.spider import Spider as BaseSpider

sys.path.append("..")


DEFAULT_PIC = "https://youke2.picui.cn/s1/2025/12/21/694796745c0c6.png"
PLAYER_AES_KEY = "my-to-newhan-2025" + ("\0" * 15)


class Spider(BaseSpider):
    def __init__(self):
        self.name = "新韩剧网"
        self.host = "https://www.hanju7.com"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/144.0.0.0 Safari/537.36"
            ),
            "Referer": self.host + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        self.classes = [
            {"type_id": "1", "type_name": "韩剧"},
            {"type_id": "3", "type_name": "韩国电影"},
            {"type_id": "4", "type_name": "韩国综艺"},
            {"type_id": "hot", "type_name": "排行榜"},
            {"type_id": "new", "type_name": "最新更新"},
        ]

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def homeContent(self, filter):
        return {"class": self.classes}

    def _build_url(self, value):
        raw = str(value or "").strip()
        if not raw:
            return ""
        if raw.startswith(("http://", "https://")):
            return raw
        if raw.startswith("//"):
            return "https:" + raw
        return urljoin(self.host + "/", raw)

    def _extract_detail_id(self, href):
        matched = re.search(r"/detail/([^/?#]+)\.html", self._build_url(href))
        return matched.group(1) if matched else str(href or "").strip().strip("/")

    def _request_text(self, path_or_url, headers=None, allow_redirects=True):
        target = path_or_url if str(path_or_url).startswith("http") else self._build_url(path_or_url)
        merged = dict(self.headers)
        if headers:
            merged.update(headers)
        response = self.fetch(target, headers=merged, timeout=10, allow_redirects=allow_redirects)
        if response.status_code != 200:
            return ""
        return response.text or ""

    def _request_html(self, path_or_url, headers=None):
        return self._request_text(path_or_url, headers=headers)

    def _clean_text(self, text):
        return re.sub(r"\s+", " ", str(text or "").replace("\xa0", " ")).strip()

    def _node_text_without_children(self, node):
        if node is None:
            return ""
        text = self._clean_text(node.text or "")
        if text:
            return text
        return self._clean_text("".join(node.xpath(".//text()")))

    def _build_list_item(self, anchor, remarks="", pic=""):
        href = (anchor.xpath("./@href") or [""])[0]
        vod_id = self._extract_detail_id(href)
        if not vod_id:
            return None
        name = self._clean_text(
            (anchor.xpath("./@title") or [""])[0]
            or self._node_text_without_children(anchor)
            or "".join(anchor.xpath(".//text()"))
        )
        image = self._build_url(pic or (anchor.xpath("./@data-original") or [""])[0] or (anchor.xpath("./@src") or [""])[0])
        return {
            "vod_id": vod_id,
            "vod_name": name,
            "vod_pic": image,
            "vod_remarks": self._clean_text(remarks),
        }

    def _parse_home_cards(self, html):
        root = self.html(html)
        if root is None:
            return []
        items = []
        for node in root.xpath("//div[contains(@class,'list')]//ul/li"):
            anchor = node.xpath(".//a[@href]")
            if not anchor:
                continue
            item = self._build_list_item(anchor[0], remarks="".join(node.xpath("./span[1]//text()")))
            if item and item["vod_name"]:
                items.append(item)
        return items

    def _default_category_pic(self, vod_id):
        return f"https://pics.hanju7.com/pics/{vod_id}.jpg" if vod_id else ""

    def _parse_category_cards(self, html):
        root = self.html(html)
        if root is None:
            return []
        items = []
        for node in root.xpath("//div[contains(@class,'list')]//ul/li"):
            anchor = node.xpath(".//a[contains(@class,'tu')][1]")
            if not anchor:
                continue
            anchor = anchor[0]
            vod_id = self._extract_detail_id((anchor.xpath("./@href") or [""])[0])
            item = self._build_list_item(
                anchor,
                remarks="".join(node.xpath(".//span[contains(@class,'tip')][1]//text()")),
                pic=(anchor.xpath("./@data-original") or [""])[0],
            )
            if item:
                item["vod_pic"] = item["vod_pic"] or self._default_category_pic(vod_id)
                items.append(item)
        return items

    def _parse_rank_cards(self, html):
        root = self.html(html)
        if root is None:
            return []
        items = []
        for node in root.xpath("//div[contains(@class,'txt') or contains(@class,'list_txt')]//ul/li"):
            anchor = node.xpath(".//a[@href][1]")
            if not anchor:
                continue
            anchor = anchor[0]
            item = self._build_list_item(anchor, remarks="".join(node.xpath("./span[1]//text()")))
            if item:
                item["vod_pic"] = self._default_category_pic(item["vod_id"])
                items.append(item)
        return items

    def homeVideoContent(self):
        return {"list": self._parse_home_cards(self._request_html(self.host))[:100]}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg)
        if str(tid) in ["hot", "new"]:
            items = self._parse_rank_cards(self._request_html(f"{self.host}/{tid}.html"))
            page_size = 20
            start = (page - 1) * page_size
            result = items[start : start + page_size]
            return {"page": page, "limit": page_size, "total": len(items), "list": result}

        page_suffix = "" if page <= 1 else str(page - 1)
        url = f"{self.host}/list/{tid}---{page_suffix}.html"
        items = self._parse_category_cards(self._request_html(url))
        return {"page": page, "limit": len(items), "total": page * 20 + len(items), "list": items}

    def _extract_redirect_location(self, response):
        if response is None:
            return ""
        return (
            response.headers.get("Location")
            or response.headers.get("location")
            or response.headers.get("Location".lower())
            or ""
        )

    def _native_post_search(self, keyword):
        payload = f"show=searchkey&keyboard={quote(str(keyword or ''))}"
        headers = dict(self.headers)
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        response = self.post(
            self.host + "/search/",
            data=payload,
            headers=headers,
            timeout=10,
            allow_redirects=False,
        )
        cookies = response.headers.get("Set-Cookie") or response.headers.get("set-cookie") or ""
        if isinstance(cookies, list):
            cookies = "; ".join(cookies)
        return self._extract_redirect_location(response), cookies

    def _normalize_search_redirect(self, location):
        raw = str(location or "").strip()
        if not raw:
            return ""
        if raw.startswith(("http://", "https://")):
            return raw
        if raw.startswith("/"):
            return self.host + raw
        return self.host + "/search/" + raw.lstrip("/")

    def _parse_search_cards(self, html):
        root = self.html(html)
        if root is None:
            return []
        items = []
        for node in root.xpath("//div[contains(@class,'txt')]//ul/li"):
            node_id = (node.xpath("./@id") or [""])[0]
            if node_id == "t":
                continue
            anchor = node.xpath(".//*[@id='name']//a[@href][1]")
            if not anchor:
                continue
            title = self._clean_text("".join(anchor[0].xpath(".//text()")))
            title = re.sub(r"\(\d+\)$", "", title).strip()
            items.append(
                {
                    "vod_id": self._extract_detail_id((anchor[0].xpath("./@href") or [""])[0]),
                    "vod_name": title,
                    "vod_pic": DEFAULT_PIC,
                    "vod_remarks": self._clean_text("".join(node.xpath(".//*[@id='actor']//text()"))),
                }
            )
        return items

    def searchContent(self, key, quick, pg="1"):
        page = int(pg)
        keyword = self._clean_text(key)
        if not keyword:
            return {"page": page, "total": 0, "list": []}
        location, cookie = self._native_post_search(keyword)
        url = self._normalize_search_redirect(location)
        if not url:
            return {"page": page, "total": 0, "list": []}
        headers = {"Cookie": cookie} if cookie else None
        items = self._parse_search_cards(self._request_html(url, headers=headers))
        return {"page": page, "total": len(items), "list": items}

    def _parse_play_groups(self, html):
        root = self.html(html)
        if root is None:
            return []
        source_name = self._clean_text("".join(root.xpath("//*[@id='playlist'][1]//text()"))) or "新韩剧线路"
        episodes = []
        for anchor in root.xpath("//div[contains(@class,'play')]//ul/li//a[@onclick]"):
            onclick = (anchor.xpath("./@onclick") or [""])[0]
            matched = re.search(r"'([^']+)'", onclick)
            if not matched:
                continue
            name = self._clean_text("".join(anchor.xpath(".//text()"))) or "正片"
            episodes.append(f"{name}${matched.group(1)}")
        if not episodes:
            return []
        return [(source_name, "#".join(episodes))]

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, list) else ids
        vod_id = self._extract_detail_id(raw)
        html = self._request_html(f"{self.host}/detail/{vod_id}.html")
        root = self.html(html)
        if root is None:
            return {"list": []}
        play_groups = self._parse_play_groups(html)
        info = root.xpath("//div[contains(@class,'detail')]//div[contains(@class,'info')]/dl/dd/text()")
        info = [self._clean_text(item) for item in info]
        pic = (root.xpath("//div[contains(@class,'detail')]//div[contains(@class,'pic')]//img/@data-original") or [""])[0]
        vod = {
            "vod_id": vod_id,
            "vod_name": info[0] if len(info) > 0 else "",
            "vod_pic": self._build_url(pic),
            "vod_actor": info[1] if len(info) > 1 else "",
            "vod_remarks": info[4] if len(info) > 4 else "",
            "vod_year": info[5] if len(info) > 5 else "",
            "vod_content": self._clean_text("".join(root.xpath("//div[contains(@class,'juqing')][1]//text()"))),
            "vod_play_from": "$$$".join(name for name, _ in play_groups),
            "vod_play_url": "$$$".join(urls for _, urls in play_groups),
        }
        return {"list": [vod]}

    def _decrypt_play_url(self, payload):
        raw = str(payload or "").strip()
        if not raw:
            return ""
        try:
            data = base64.b64decode(raw)
            iv = data[:16]
            ciphertext = data[16:]
            cipher = AES.new(PLAYER_AES_KEY.encode("utf-8"), AES.MODE_CBC, iv)
            return unpad(cipher.decrypt(ciphertext), AES.block_size).decode("utf-8").strip()
        except Exception:
            return ""

    def _is_media_url(self, url):
        return bool(re.search(r"\.(m3u8|mp4|flv|avi|mkv|ts)(?:[?#]|$)", str(url or ""), re.I))

    def playerContent(self, flag, id, vipFlags):
        raw_id = str(id or "").strip()
        if self._is_media_url(raw_id):
            return {"parse": 0, "jx": 0, "url": raw_id, "header": {"Referer": self.host + "/"}}

        encrypted = self._request_text(f"{self.host}/u/u1.php?ud={raw_id}")
        real_url = self._decrypt_play_url(encrypted)
        if self._is_media_url(real_url):
            return {"parse": 0, "jx": 0, "url": real_url, "header": {"Referer": self.host + "/"}}
        return {"parse": 1, "jx": 1, "url": real_url or raw_id, "header": {"Referer": self.host + "/"}}
