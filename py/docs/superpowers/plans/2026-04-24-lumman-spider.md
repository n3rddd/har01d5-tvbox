# 路漫漫 Spider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在当前 Python 仓库中新增一个 `路漫漫` spider，支持 6 个动漫/动画电影分类、首页推荐、分类、搜索、详情和带回退能力的播放解析。

**Architecture:** 使用单文件 `Spider` 实现，内部按 URL 构造、列表卡片解析、详情线路解析、播放器 JSON 解码、AES token 解密和主解析链分层拆成 helper。测试采用 `unittest + SourceFileLoader + unittest.mock`，按红绿重构覆盖列表、详情、播放解码与回退路径，避免真实联网。

**Tech Stack:** Python 3, `re`, `json`, `base64`, `urllib.parse`, `Crypto.Cipher.AES`, `Crypto.Util.Padding`, `base.spider.Spider`, `unittest`, `unittest.mock`

---

## File Structure

- Create: `py/路漫漫.py`
  - 站点实现，负责固定分类、HTML 请求、卡片解析、详情组装、播放器解码和主解析链回退
- Create: `py/tests/test_路漫漫.py`
  - 离线测试，使用 `SourceFileLoader` 加载 spider，并 mock `_get_html` / `_post_json` / `_head_url`

### Task 1: Scaffold Spider, Fixed Classes, And List/Search Parsing

**Files:**
- Create: `py/tests/test_路漫漫.py`
- Create: `py/路漫漫.py`

- [ ] **Step 1: Write the failing test**

```python
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("lumman_spider", str(ROOT / "路漫漫.py")).load_module()
Spider = MODULE.Spider

SAMPLE_LIST_HTML = """
<html><body>
<div class="video-img-box">
  <a href="/vod/detail/1001.html">
    <img class="lazyload" data-src="/upload/1001.jpg" />
    <h6 class="title">海贼王</h6>
    <div class="label">更新至1123集</div>
  </a>
</div>
<div class="video-img-box">
  <a href="/vod/detail/1002.html">
    <img class="lazyload" src="https://img.example.com/1002.jpg" />
    <h6 class="title">你的名字</h6>
    <div class="label">全集</div>
  </a>
</div>
</body></html>
"""


class TestLuManManSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_home_content_returns_only_animation_classes(self):
        result = self.spider.homeContent(False)
        self.assertEqual(
            result["class"],
            [
                {"type_id": "6", "type_name": "日本动漫"},
                {"type_id": "7", "type_name": "国产动漫"},
                {"type_id": "8", "type_name": "欧美动漫"},
                {"type_id": "3", "type_name": "日本动画电影"},
                {"type_id": "4", "type_name": "国产动画电影"},
                {"type_id": "5", "type_name": "欧美动画电影"},
            ],
        )

    @patch.object(Spider, "_get_html")
    def test_home_video_content_parses_cards(self, mock_html):
        mock_html.return_value = SAMPLE_LIST_HTML
        result = self.spider.homeVideoContent()
        self.assertEqual(len(result["list"]), 2)
        self.assertEqual(result["list"][0]["vod_id"], "vod/detail/1001.html")
        self.assertEqual(result["list"][0]["vod_pic"], "https://www.lmm85.com/upload/1001.jpg")
        self.assertEqual(result["list"][1]["vod_pic"], "https://img.example.com/1002.jpg")

    @patch.object(Spider, "_get_html")
    def test_category_content_builds_filtered_url(self, mock_html):
        mock_html.return_value = SAMPLE_LIST_HTML
        result = self.spider.categoryContent("6", "2", False, {"年代": "/year/2024", "排序": "/by/time"})
        self.assertEqual(result["page"], 2)
        self.assertEqual(len(result["list"]), 2)
        mock_html.assert_called_with("https://www.lmm85.com/vod/show/id/6/year/2024/by/time/page/2.html")

    @patch.object(Spider, "_get_html")
    def test_search_content_uses_search_path(self, mock_html):
        mock_html.return_value = SAMPLE_LIST_HTML
        result = self.spider.searchContent("海贼", False, "3")
        self.assertEqual(result["page"], 3)
        self.assertEqual(result["list"][0]["vod_name"], "海贼王")
        mock_html.assert_called_with("https://www.lmm85.com/vod/search/page/3/wd/%E6%B5%B7%E8%B4%BC.html")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd py && python -m unittest tests.test_路漫漫.TestLuManManSpider.test_home_content_returns_only_animation_classes -v`
Expected: FAIL with `FileNotFoundError` for `py/路漫漫.py`

- [ ] **Step 3: Write minimal implementation**

```python
# coding=utf-8
import base64
import json
import re
import sys
from urllib.parse import quote, unquote, urljoin

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "路漫漫"
        self.host = "https://www.lmm85.com"
        self.mobile_ua = (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 "
            "Mobile/15E148 Safari/604.1"
        )
        self.headers = {
            "User-Agent": self.mobile_ua,
            "Referer": "http://www.lmm50.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        self.classes = [
            {"type_id": "6", "type_name": "日本动漫"},
            {"type_id": "7", "type_name": "国产动漫"},
            {"type_id": "8", "type_name": "欧美动漫"},
            {"type_id": "3", "type_name": "日本动画电影"},
            {"type_id": "4", "type_name": "国产动画电影"},
            {"type_id": "5", "type_name": "欧美动画电影"},
        ]

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def homeContent(self, filter):
        return {"class": self.classes}

    def _abs_url(self, value):
        raw = str(value or "").strip()
        if not raw:
            return ""
        return urljoin(self.host + "/", raw)

    def _encode_vod_id(self, href):
        raw = str(href or "").strip()
        matched = re.search(r"(/vod/detail/[^?#]+\.html)", raw)
        return matched.group(1).lstrip("/") if matched else raw.lstrip("/")

    def _clean_text(self, text):
        return re.sub(r"\s+", " ", str(text or "")).strip()

    def _get_html(self, url, headers=None):
        request_headers = dict(self.headers)
        if headers:
            request_headers.update(headers)
        response = self.fetch(url, headers=request_headers, timeout=15, verify=False)
        return response.text if response.status_code == 200 else ""

    def _parse_cards(self, html):
        root = self.html(html)
        if root is None:
            return []
        items = []
        seen = set()
        for box in root.xpath("//*[contains(@class,'video-img-box')]"):
            href = self._clean_text((box.xpath(".//a[1]/@href") or [""])[0])
            title = self._clean_text("".join(box.xpath(".//*[contains(@class,'title')][1]//text()")))
            pic = self._clean_text(
                (box.xpath(".//img[1]/@data-src") or box.xpath(".//img[1]/@src") or [""])[0]
            )
            remarks = self._clean_text("".join(box.xpath(".//*[contains(@class,'label')][1]//text()")))
            vod_id = self._encode_vod_id(href)
            if not vod_id or not title or vod_id in seen:
                continue
            seen.add(vod_id)
            items.append(
                {
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": self._abs_url(pic),
                    "vod_remarks": remarks,
                }
            )
        return items

    def homeVideoContent(self):
        return {"list": self._parse_cards(self._get_html(self.host + "/"))[:20]}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg)
        extend = extend or {}
        path = f"/vod/show/id/{tid}"
        path += str(extend.get("年代", "") or "")
        path += str(extend.get("排序", "") or "")
        path += f"/page/{page}.html"
        items = self._parse_cards(self._get_html(self.host + path))
        return {"page": page, "total": len(items), "list": items}

    def searchContent(self, key, quick, pg="1"):
        page = int(pg)
        keyword = self._clean_text(key)
        if not keyword:
            return {"page": page, "total": 0, "list": []}
        url = f"{self.host}/vod/search/page/{page}/wd/{quote(keyword)}.html"
        items = self._parse_cards(self._get_html(url))
        return {"page": page, "total": len(items), "list": items[:10] if quick else items}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd py && python -m unittest tests.test_路漫漫.TestLuManManSpider.test_home_content_returns_only_animation_classes tests.test_路漫漫.TestLuManManSpider.test_home_video_content_parses_cards tests.test_路漫漫.TestLuManManSpider.test_category_content_builds_filtered_url tests.test_路漫漫.TestLuManManSpider.test_search_content_uses_search_path -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add py/路漫漫.py py/tests/test_路漫漫.py
git commit -m "feat: scaffold lumman spider"
```

### Task 2: Add Detail Parsing And Multi-Line Episode Grouping

**Files:**
- Modify: `py/tests/test_路漫漫.py`
- Modify: `py/路漫漫.py`

- [ ] **Step 1: Write the failing test**

```python
SAMPLE_DETAIL_HTML = """
<html><body>
<h1 class="page-title">进击的巨人</h1>
<div class="module-item-pic"><img class="lazyload" src="/upload/jjdr.jpg" /></div>
<div class="video-info-items">状态：已完结</div>
<div class="video-info-items">地区：日本</div>
<div class="video-info-content">人类与巨人的战斗。</div>
<a class="module-tab-item tab-item" href="#line1">在线播放</a>
<a class="module-tab-item tab-item" href="#line2">云播</a>
<div id="line1" class="module-player-list">
  <a href="/vod/play/1001-1-1.html">第1集</a>
  <a href="/vod/play/1001-1-2.html">第2集</a>
</div>
<div id="line2" class="module-player-list">
  <a href="/vod/play/1001-2-1.html">HD</a>
</div>
</body></html>
"""

    @patch.object(Spider, "_get_html")
    def test_detail_content_parses_meta_and_playlists(self, mock_html):
        mock_html.return_value = SAMPLE_DETAIL_HTML
        result = self.spider.detailContent(["vod/detail/1001.html"])
        vod = result["list"][0]
        self.assertEqual(vod["vod_name"], "进击的巨人")
        self.assertEqual(vod["vod_pic"], "https://www.lmm85.com/upload/jjdr.jpg")
        self.assertEqual(vod["vod_content"], "人类与巨人的战斗。")
        self.assertEqual(vod["vod_remarks"], "状态：已完结 / 地区：日本")
        self.assertEqual(vod["vod_play_from"], "在线播放$$$云播")
        self.assertIn("第1集$vod/play/1001-1-1.html#第2集$vod/play/1001-1-2.html", vod["vod_play_url"])
        self.assertIn("HD$vod/play/1001-2-1.html", vod["vod_play_url"])

    @patch.object(Spider, "_get_html")
    def test_detail_content_falls_back_to_direct_playlist_scan(self, mock_html):
        mock_html.return_value = """
        <html><body>
        <h1 class="page-title">测试</h1>
        <div class="module-player-list">
          <a href="/vod/play/1-1-1.html">正片</a>
        </div>
        </body></html>
        """
        result = self.spider.detailContent(["vod/detail/1.html"])
        vod = result["list"][0]
        self.assertEqual(vod["vod_play_from"], "播放列表")
        self.assertEqual(vod["vod_play_url"], "正片$vod/play/1-1-1.html")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd py && python -m unittest tests.test_路漫漫.TestLuManManSpider.test_detail_content_parses_meta_and_playlists tests.test_路漫漫.TestLuManManSpider.test_detail_content_falls_back_to_direct_playlist_scan -v`
Expected: FAIL with `AttributeError: 'Spider' object has no attribute 'detailContent'`

- [ ] **Step 3: Write minimal implementation**

```python
    def _decode_vod_id(self, vod_id):
        raw = str(vod_id or "").strip().lstrip("/")
        return self._abs_url(raw)

    def _encode_play_id(self, href):
        raw = str(href or "").strip()
        matched = re.search(r"(/vod/play/[^?#]+\.html)", raw)
        return matched.group(1).lstrip("/") if matched else raw.lstrip("/")

    def _parse_play_groups(self, root):
        groups = []
        tabs = root.xpath("//*[contains(@class,'module-tab-item') and contains(@class,'tab-item')]")
        for index, tab in enumerate(tabs):
            name = self._clean_text("".join(tab.xpath(".//text()")))
            target = self._clean_text((tab.xpath("./@href") or [""])[0])
            if not name:
                continue
            if target.startswith("#"):
                playlist = root.xpath(f"//*[@id='{target[1:]}']")
            else:
                playlist = []
            if not playlist:
                playlist = root.xpath(f\"(//*[contains(@class,'module-player-list')])[{index + 1}]\")
            if not playlist:
                continue
            episodes = []
            for anchor in playlist[0].xpath(".//a[@href]"):
                ep_name = self._clean_text("".join(anchor.xpath(".//text()")))
                ep_id = self._encode_play_id((anchor.xpath("./@href") or [""])[0])
                if ep_name and ep_id:
                    episodes.append(f"{ep_name}${ep_id}")
            if episodes:
                groups.append((name, "#".join(episodes)))
        if groups:
            return groups
        episodes = []
        for anchor in root.xpath("//*[contains(@class,'module-player-list')]//a[@href]"):
            ep_name = self._clean_text("".join(anchor.xpath(".//text()")))
            ep_id = self._encode_play_id((anchor.xpath("./@href") or [""])[0])
            if ep_name and ep_id:
                episodes.append(f"{ep_name}${ep_id}")
        return [("播放列表", "#".join(episodes))] if episodes else []

    def detailContent(self, ids):
        raw_id = ids[0] if isinstance(ids, list) else ids
        html = self._get_html(self._decode_vod_id(raw_id))
        root = self.html(html)
        if root is None:
            return {"list": []}
        groups = self._parse_play_groups(root)
        remarks = [
            self._clean_text("".join(node.xpath(".//text()")))
            for node in root.xpath("//*[contains(@class,'video-info-items')]")
        ]
        pic = (
            root.xpath("//*[contains(@class,'module-item-pic')]//img[1]/@data-src")
            or root.xpath("//*[contains(@class,'module-item-pic')]//img[1]/@src")
            or [""]
        )[0]
        vod = {
            "vod_id": str(raw_id),
            "vod_name": self._clean_text("".join(root.xpath("//*[contains(@class,'page-title')][1]//text()"))),
            "vod_pic": self._abs_url(pic),
            "vod_content": self._clean_text("".join(root.xpath("//*[contains(@class,'video-info-content')][1]//text()"))),
            "vod_remarks": " / ".join([value for value in remarks if value]),
            "vod_play_from": "$$$".join(name for name, _ in groups),
            "vod_play_url": "$$$".join(urls for _, urls in groups),
        }
        return {"list": [vod]}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd py && python -m unittest tests.test_路漫漫.TestLuManManSpider.test_detail_content_parses_meta_and_playlists tests.test_路漫漫.TestLuManManSpider.test_detail_content_falls_back_to_direct_playlist_scan -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add py/路漫漫.py py/tests/test_路漫漫.py
git commit -m "feat: add lumman detail parsing"
```

### Task 3: Add Player JSON Decoding, Direct Media Return, And AES Helper

**Files:**
- Modify: `py/tests/test_路漫漫.py`
- Modify: `py/路漫漫.py`

- [ ] **Step 1: Write the failing test**

```python
from base64 import b64encode
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

    def test_decrypt_token_returns_plaintext(self):
        key = b"ejjooopppqqqrwww"
        iv = b"1348987635684651"
        cipher = AES.new(key, AES.MODE_CBC, iv)
        token = b64encode(cipher.encrypt(pad(b"plain-token", AES.block_size))).decode("utf-8")
        self.assertEqual(self.spider._decrypt_token(token), "plain-token")

    def test_decrypt_token_handles_bad_ciphertext(self):
        self.assertEqual(self.spider._decrypt_token("not-valid"), "")

    @patch.object(Spider, "_resolve_player_url")
    def test_player_content_returns_direct_media_without_parse(self, mock_resolve):
        result = self.spider.playerContent("在线播放", "https://cdn.example.com/video.m3u8", {})
        self.assertEqual(result["parse"], 0)
        self.assertEqual(result["url"], "https://cdn.example.com/video.m3u8")
        mock_resolve.assert_not_called()

    @patch.object(Spider, "_resolve_player_url")
    @patch.object(Spider, "_get_html")
    def test_player_content_decodes_encrypt_1_and_encrypt_2(self, mock_html, mock_resolve):
        encoded = b64encode("https://cdn.example.com/e2.m3u8".encode("utf-8")).decode("utf-8")
        mock_html.side_effect = [
            '<script>var player_aaaa={"url":"https%3A%2F%2Fcdn.example.com%2Fe1.m3u8","encrypt":"1","from":"line"};</script>',
            f'<script>var player_aaaa={{"url":"{encoded}","encrypt":"2","from":"line"}};</script>',
        ]
        mock_resolve.side_effect = ["https://cdn.example.com/e1.m3u8", "https://cdn.example.com/e2.m3u8"]
        first = self.spider.playerContent("在线播放", "vod/play/1001-1-1.html", {})
        second = self.spider.playerContent("在线播放", "vod/play/1001-1-2.html", {})
        self.assertEqual(first["url"], "https://cdn.example.com/e1.m3u8")
        self.assertEqual(second["url"], "https://cdn.example.com/e2.m3u8")

    @patch.object(Spider, "_resolve_player_url", return_value="")
    @patch.object(Spider, "_get_html", return_value="<html><body>missing player</body></html>")
    def test_player_content_falls_back_to_parse_when_player_missing(self, mock_html, mock_resolve):
        result = self.spider.playerContent("在线播放", "vod/play/1001-1-1.html", {})
        self.assertEqual(result["parse"], 1)
        self.assertEqual(result["url"], "https://www.lmm85.com/vod/play/1001-1-1.html")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd py && python -m unittest tests.test_路漫漫.TestLuManManSpider.test_decrypt_token_returns_plaintext tests.test_路漫漫.TestLuManManSpider.test_player_content_returns_direct_media_without_parse tests.test_路漫漫.TestLuManManSpider.test_player_content_decodes_encrypt_1_and_encrypt_2 tests.test_路漫漫.TestLuManManSpider.test_player_content_falls_back_to_parse_when_player_missing -v`
Expected: FAIL with missing `_decrypt_token`, `_resolve_player_url`, or `playerContent`

- [ ] **Step 3: Write minimal implementation**

```python
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

    def _decode_player_url(self, raw_url, encrypt):
        value = str(raw_url or "").strip()
        mode = str(encrypt or "0").strip()
        if mode == "1":
            return unquote(value)
        if mode == "2":
            try:
                return unquote(base64.b64decode(value).decode("utf-8"))
            except Exception:
                return ""
        return value

    def _extract_player_data(self, html):
        matched = re.search(r"player_[a-z0-9_]+\s*=\s*(\{[\s\S]*?\})\s*;?", str(html or ""), re.I)
        if not matched:
            return {}
        try:
            return json.loads(matched.group(1))
        except Exception:
            return {}

    def _decode_play_id(self, play_id):
        return self._abs_url(str(play_id or "").strip().lstrip("/"))

    def _decrypt_token(self, token):
        try:
            payload = base64.b64decode(str(token or ""))
            cipher = AES.new(b"ejjooopppqqqrwww", AES.MODE_CBC, b"1348987635684651")
            value = unpad(cipher.decrypt(payload), AES.block_size)
            return value.decode("utf-8")
        except Exception:
            return ""

    def _is_media_url(self, url):
        return bool(re.search(r"\.(m3u8|mp4|flv|avi|mkv|ts)(?:[?#]|$)", str(url or ""), re.I))

    def _build_player_headers(self, referer):
        return {
            "User-Agent": self.mobile_ua,
            "Referer": referer,
            "Origin": self.host,
        }

    def _resolve_player_url(self, player, play_page_url):
        media = self._decode_player_url(player.get("url", ""), player.get("encrypt", "0"))
        if self._is_media_url(media):
            return media.split("&", 1)[0]
        return ""

    def playerContent(self, flag, id, vipFlags):
        play_page_url = self._decode_play_id(id)
        if self._is_media_url(play_page_url):
            return {"parse": 0, "url": play_page_url, "header": self._build_player_headers(self.host + "/")}
        body = self._get_html(play_page_url, headers={"Referer": self.host + "/"})
        player = self._extract_player_data(body)
        real_url = self._resolve_player_url(player, play_page_url)
        if real_url:
            return {"parse": 0, "url": real_url, "header": self._build_player_headers(play_page_url)}
        return {"parse": 1, "url": play_page_url, "header": self._build_player_headers(self.host + "/")}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd py && python -m unittest tests.test_路漫漫.TestLuManManSpider.test_decrypt_token_returns_plaintext tests.test_路漫漫.TestLuManManSpider.test_decrypt_token_handles_bad_ciphertext tests.test_路漫漫.TestLuManManSpider.test_player_content_returns_direct_media_without_parse tests.test_路漫漫.TestLuManManSpider.test_player_content_decodes_encrypt_1_and_encrypt_2 tests.test_路漫漫.TestLuManManSpider.test_player_content_falls_back_to_parse_when_player_missing -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add py/路漫漫.py py/tests/test_路漫漫.py
git commit -m "feat: add lumman player decode"
```

### Task 4: Add Main Parse Chain For Player JS And POST API Resolution

**Files:**
- Modify: `py/tests/test_路漫漫.py`
- Modify: `py/路漫漫.py`

- [ ] **Step 1: Write the failing test**

```python
    @patch.object(Spider, "_post_json")
    @patch.object(Spider, "_get_html")
    def test_resolve_player_url_requests_parser_api_with_decrypted_token(self, mock_html, mock_post_json):
        player = {"url": "source-id", "encrypt": "0", "from": "lineA"}
        mock_html.side_effect = [
            'var player_xx={}; var MacPlayer={Parse:"https://parser.example.com/jx.php?url=",PlayUrl:""}; document.querySelector("iframe").src = MacPlayer.Parse + MacPlayer.PlayUrl + "&type=m3u8";',
            '<script>var vid="vid-1";var t="123";var token="YxF6M7yw8U7OQcW9t6Qx4w==";var act="play";var play="1";post("/api.php",{});</script>',
        ]
        mock_post_json.return_value = {"url": "https://cdn.example.com/final.m3u8"}
        with patch.object(self.spider, "_decrypt_token", return_value="decoded-token") as mock_decrypt:
            result = self.spider._resolve_player_url(player, "https://www.lmm85.com/vod/play/1001-1-1.html")
        self.assertEqual(result, "https://cdn.example.com/final.m3u8")
        mock_decrypt.assert_called_once_with("YxF6M7yw8U7OQcW9t6Qx4w==")
        mock_post_json.assert_called_once_with(
            "https://parser.example.com/api.php",
            {"vid": "vid-1", "t": "123", "token": "decoded-token", "act": "play", "play": "1"},
            referer="https://www.lmm85.com",
        )

    @patch.object(Spider, "_post_json", return_value={})
    @patch.object(Spider, "_get_html", return_value='document.querySelector("iframe").src = "";')
    def test_resolve_player_url_returns_empty_when_chain_cannot_be_built(self, mock_html, mock_post_json):
        result = self.spider._resolve_player_url({"url": "vid", "encrypt": "0", "from": "lineA"}, "https://www.lmm85.com/vod/play/1.html")
        self.assertEqual(result, "")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd py && python -m unittest tests.test_路漫漫.TestLuManManSpider.test_resolve_player_url_requests_parser_api_with_decrypted_token tests.test_路漫漫.TestLuManManSpider.test_resolve_player_url_returns_empty_when_chain_cannot_be_built -v`
Expected: FAIL because `_resolve_player_url` only handles direct media

- [ ] **Step 3: Write minimal implementation**

```python
    def _post_json(self, url, data, referer=None):
        headers = {"Referer": referer or self.host, "Origin": self.host, "User-Agent": self.mobile_ua}
        response = self.post(url, data=data, headers=headers, timeout=10, verify=False)
        if response.status_code != 200:
            return {}
        try:
            return json.loads(response.text or "{}")
        except Exception:
            return {}

    def _extract_js_src(self, js_text, video_url, play_page_url):
        matched = re.search(r"\.src\s*=\s*(.*?);", str(js_text or ""))
        if not matched:
            return ""
        raw = re.sub(r"[\+\s']", "", matched.group(1))
        raw = raw.replace("MacPlayer.Parse", "")
        raw = raw.replace("MacPlayer.PlayUrl", video_url)
        raw = raw.replace("window.location.href", play_page_url)
        return raw

    def _resolve_player_url(self, player, play_page_url):
        media = self._decode_player_url(player.get("url", ""), player.get("encrypt", "0"))
        if self._is_media_url(media):
            return media.split("&", 1)[0]
        source = self._clean_text(player.get("from", ""))
        if not media or not source:
            return ""
        js_url = f"{self.host}/static/player/{source}.js"
        js_text = self._get_html(js_url, headers={"Referer": play_page_url})
        iframe_url = self._extract_js_src(js_text, media, play_page_url)
        if not iframe_url or "type=" not in iframe_url:
            return ""
        iframe_html = self._get_html(iframe_url, headers={"Referer": self.host})
        if not re.search(r'vid\s*=\s*".+?"', iframe_html):
            return ""
        api_root = self.regStr(r"^(.*?//.*?/)", iframe_url)
        api_path = self.regStr(r'post\("(.*?)"', iframe_html)
        if not api_root or not api_path:
            return ""
        post_url = urljoin(api_root, api_path.lstrip("/"))
        token = self.regStr(r'token\s*=\s*"(.*?)"', iframe_html)
        payload = {
            "vid": self.regStr(r'vid\s*=\s*"(.*?)"', iframe_html),
            "t": self.regStr(r'var\s+t\s*=\s*"(.*?)"', iframe_html),
            "token": self._decrypt_token(token),
            "act": self.regStr(r'act\s*=\s*"(.*?)"', iframe_html),
            "play": self.regStr(r'play\s*=\s*"(.*?)"', iframe_html),
        }
        data = self._post_json(post_url, payload, referer=self.host)
        return str(data.get("url", "")).strip()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd py && python -m unittest tests.test_路漫漫.TestLuManManSpider.test_resolve_player_url_requests_parser_api_with_decrypted_token tests.test_路漫漫.TestLuManManSpider.test_resolve_player_url_returns_empty_when_chain_cannot_be_built -v`
Expected: PASS

- [ ] **Step 5: Run the full module tests**

Run: `cd py && python -m unittest tests.test_路漫漫 -v`
Expected: PASS with all `路漫漫` tests green

- [ ] **Step 6: Commit**

```bash
git add py/路漫漫.py py/tests/test_路漫漫.py
git commit -m "feat: complete lumman spider"
```

## Self-Review

- Spec coverage: 固定 6 分类、首页、分类、搜索、详情、多线路、播放直链/解码/主解析链/回退都对应到 Task 1-4，没有遗漏站点目标。
- Placeholder scan: 计划中没有 `TODO/TBD/implement later` 之类占位内容，测试命令和文件路径都给了精确值。
- Type consistency: 方法名统一使用 `_abs_url`、`_encode_vod_id`、`_decode_vod_id`、`_encode_play_id`、`_decode_play_id`、`_parse_cards`、`_parse_play_groups`、`_extract_player_data`、`_decrypt_token`、`_resolve_player_url`、`playerContent`。
