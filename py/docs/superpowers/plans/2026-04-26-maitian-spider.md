# 麦田影院 Spider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增一个固定站点 `https://www.mtyy5.com` 的 Python Spider，支持固定分类、分类列表、详情分组、播放页解链，并保持无搜索行为。

**Architecture:** 采用单文件 Spider 加单测文件的实现方式，站点逻辑全部放在 `py/麦田影院.py`。分类和详情直接解析静态 HTML，播放页先解析 `player_data`，非直链时通过 `art.php?get_signed_url=1` 和 `art.php<signed_url>` 两步拿到最终 `jmurl`，失败时回退解析页。

**Tech Stack:** Python 3、`base.spider.Spider`、`unittest`、`unittest.mock`、内置 `json` / `re` / `urllib.parse`

---

### Task 1: 建立骨架与基础行为测试

**Files:**
- Create: `py/麦田影院.py`
- Create: `py/tests/test_麦田影院.py`
- Test: `py/tests/test_麦田影院.py`

- [ ] **Step 1: Write the failing test**

```python
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("maitian_spider", str(ROOT / "麦田影院.py")).load_module()
Spider = MODULE.Spider


class TestMaiTianSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_home_content_returns_expected_classes(self):
        result = self.spider.homeContent(False)
        self.assertEqual(
            result["class"],
            [
                {"type_id": "1", "type_name": "电影"},
                {"type_id": "2", "type_name": "电视剧"},
                {"type_id": "4", "type_name": "动漫"},
                {"type_id": "3", "type_name": "综艺"},
                {"type_id": "26", "type_name": "短剧"},
                {"type_id": "25", "type_name": "少儿"},
            ],
        )

    def test_home_video_content_returns_empty_list(self):
        self.assertEqual(self.spider.homeVideoContent(), {"list": []})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest py/tests/test_麦田影院.py -v`
Expected: FAIL with `FileNotFoundError` or import failure because `py/麦田影院.py` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# coding=utf-8
import sys

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "麦田影院"
        self.host = "https://www.mtyy5.com"
        self.user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/130.0.0.0 Safari/537.36"
        )
        self.headers = {
            "User-Agent": self.user_agent,
            "Referer": self.host + "/",
            "Origin": self.host,
        }
        self.classes = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "电视剧"},
            {"type_id": "4", "type_name": "动漫"},
            {"type_id": "3", "type_name": "综艺"},
            {"type_id": "26", "type_name": "短剧"},
            {"type_id": "25", "type_name": "少儿"},
        ]

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def homeContent(self, filter):
        return {"class": self.classes}

    def homeVideoContent(self):
        return {"list": []}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest py/tests/test_麦田影院.py -v`
Expected: PASS for `test_home_content_returns_expected_classes` and `test_home_video_content_returns_empty_list`.

- [ ] **Step 5: Commit**

```bash
git add py/麦田影院.py py/tests/test_麦田影院.py
git commit -m "feat: add maitian spider skeleton"
```

### Task 2: 实现分类解析与无搜索行为

**Files:**
- Modify: `py/麦田影院.py`
- Modify: `py/tests/test_麦田影院.py`
- Test: `py/tests/test_麦田影院.py`

- [ ] **Step 1: Write the failing tests**

```python
from unittest.mock import patch

    @patch.object(Spider, "_request_html")
    def test_category_content_builds_url_and_parses_cards(self, mock_request_html):
        mock_request_html.return_value = """
        <div class="public-list-box">
          <a class="public-list-exp" href="/voddetail/123.html" title="分类影片">
            <img data-src="/cover.jpg" />
          </a>
          <span class="public-list-prb">更新至10集</span>
        </div>
        """
        result = self.spider.categoryContent("2", "3", False, {})
        self.assertEqual(
            mock_request_html.call_args.args[0],
            "https://www.mtyy5.com/vodshow/2--------3---.html",
        )
        self.assertEqual(
            result["list"],
            [
                {
                    "vod_id": "/voddetail/123.html",
                    "vod_name": "分类影片",
                    "vod_pic": "https://www.mtyy5.com/cover.jpg",
                    "vod_remarks": "更新至10集",
                }
            ],
        )
        self.assertNotIn("pagecount", result)

    @patch.object(Spider, "_request_html")
    def test_search_content_returns_empty_result_without_network(self, mock_request_html):
        result = self.spider.searchContent("繁花", False, "2")
        self.assertEqual(result, {"page": 2, "limit": 0, "total": 0, "list": []})
        mock_request_html.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest py/tests/test_麦田影院.py -v`
Expected: FAIL with `AttributeError` for missing `_request_html`, `categoryContent`, or `searchContent`.

- [ ] **Step 3: Write minimal implementation**

```python
import re
from urllib.parse import urljoin

    def _stringify(self, value):
        return "" if value is None else str(value)

    def _clean_text(self, text):
        raw = self._stringify(text).replace("&nbsp;", " ").replace("\xa0", " ")
        return re.sub(r"\s+", " ", raw).strip()

    def _build_url(self, value):
        raw = self._stringify(value).strip()
        if not raw:
            return ""
        if raw.startswith(("http://", "https://")):
            return raw
        if raw.startswith("//"):
            return "https:" + raw
        return urljoin(self.host + "/", raw)

    def _request_html(self, path_or_url, referer=None):
        target = path_or_url if self._stringify(path_or_url).startswith("http") else self._build_url(path_or_url)
        headers = dict(self.headers)
        headers["Referer"] = referer or self.headers["Referer"]
        response = self.fetch(target, headers=headers, timeout=10)
        if response.status_code != 200:
            return ""
        return response.text or ""

    def _parse_cards(self, html):
        root = self.html(self._stringify(html))
        if root is None:
            return []
        items = []
        for node in root.xpath("//div[contains(@class,'public-list-box')]"):
            href = self._clean_text("".join(node.xpath(".//a[contains(@class,'public-list-exp')][1]/@href")))
            title = self._clean_text("".join(node.xpath(".//a[contains(@class,'public-list-exp')][1]/@title")))
            pic = self._clean_text(
                "".join(node.xpath(".//a[contains(@class,'public-list-exp')]//img[1]/@data-src"))
            ) or self._clean_text(
                "".join(node.xpath(".//a[contains(@class,'public-list-exp')]//img[1]/@src"))
            )
            remarks = self._clean_text("".join(node.xpath(".//*[contains(@class,'public-list-prb')][1]//text()")))
            if href and title:
                items.append(
                    {
                        "vod_id": href,
                        "vod_name": title,
                        "vod_pic": self._build_url(pic),
                        "vod_remarks": remarks,
                    }
                )
        return items

    def categoryContent(self, tid, pg, filter, extend):
        page = max(int(self._stringify(pg) or "1"), 1)
        url = self.host + f"/vodshow/{tid}--------{page}---.html"
        items = self._parse_cards(self._request_html(url))
        return {"page": page, "limit": len(items), "total": len(items), "list": items}

    def searchContent(self, key, quick, pg="1"):
        page = max(int(self._stringify(pg) or "1"), 1)
        return {"page": page, "limit": 0, "total": 0, "list": []}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest py/tests/test_麦田影院.py -v`
Expected: PASS for fixed classes, empty home video, category parsing, and no-network search behavior.

- [ ] **Step 5: Commit**

```bash
git add py/麦田影院.py py/tests/test_麦田影院.py
git commit -m "feat: add maitian list parsing"
```

### Task 3: 实现详情分组解析

**Files:**
- Modify: `py/麦田影院.py`
- Modify: `py/tests/test_麦田影院.py`
- Test: `py/tests/test_麦田影院.py`

- [ ] **Step 1: Write the failing test**

```python
    @patch.object(Spider, "_request_html")
    def test_detail_content_parses_meta_and_play_groups(self, mock_request_html):
        mock_request_html.return_value = """
        <html><body>
        <h1>示例影片</h1>
        <div class="detail-pic"><img data-src="/detail.jpg" /></div>
        <div class="vod_content">这里是简介</div>
        <a class="swiper-slide">线路1</a>
        <a class="swiper-slide">线路2</a>
        <div class="anthology-list-box">
          <ul class="anthology-list-play">
            <li><a href="/vodplay/1-1-1.html">第1集</a></li>
            <li><a href="/vodplay/1-1-2.html">第2集</a></li>
          </ul>
        </div>
        <div class="anthology-list-box">
          <ul class="anthology-list-play">
            <li><a href="/vodplay/1-2-1.html">正片</a></li>
          </ul>
        </div>
        </body></html>
        """
        result = self.spider.detailContent(["/voddetail/1.html"])
        vod = result["list"][0]
        self.assertEqual(vod["vod_id"], "/voddetail/1.html")
        self.assertEqual(vod["vod_name"], "示例影片")
        self.assertEqual(vod["vod_pic"], "https://www.mtyy5.com/detail.jpg")
        self.assertEqual(vod["vod_content"], "这里是简介")
        self.assertEqual(vod["vod_play_from"], "线路$$$线路")
        self.assertEqual(
            vod["vod_play_url"],
            "第1集$/vodplay/1-1-1.html#第2集$/vodplay/1-1-2.html$$$正片$/vodplay/1-2-1.html",
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest py/tests/test_麦田影院.py -v`
Expected: FAIL because `detailContent` does not exist yet or returns no grouped播放数据。

- [ ] **Step 3: Write minimal implementation**

```python
    def _extract_detail_pic(self, root):
        return self._clean_text(
            "".join(root.xpath("//*[contains(@class,'detail-pic') or contains(@class,'vod-img')]//img[1]/@data-src"))
        ) or self._clean_text(
            "".join(root.xpath("//*[contains(@class,'detail-pic') or contains(@class,'vod-img')]//img[1]/@src"))
        )

    def _extract_detail_content(self, root):
        candidates = [
            "//*[contains(@class,'vod_content')][1]//text()",
            "//*[contains(@class,'detail-content')][1]//text()",
            "//*[contains(@class,'switch-box')][1]//text()",
        ]
        for xpath in candidates:
            text = self._clean_text("".join(root.xpath(xpath)))
            if text:
                return text
        return ""

    def _parse_play_groups(self, root):
        names = []
        for node in root.xpath("//a[contains(@class,'swiper-slide')]"):
            label = re.sub(r"\d", "", self._clean_text("".join(node.xpath(".//text()")))).strip()
            names.append(label)
        groups = []
        for index, box in enumerate(root.xpath("//div[contains(@class,'anthology-list-box')]")):
            episodes = []
            for item in box.xpath(".//ul[contains(@class,'anthology-list-play')]/li"):
                name = self._clean_text("".join(item.xpath(".//text()")))
                href = self._clean_text("".join(item.xpath("./*[1]/@href")))
                if name and href:
                    episodes.append(f"{name}${href}")
            if episodes:
                title = names[index] if index < len(names) and names[index] else f"线路{index + 1}"
                groups.append((title, "#".join(episodes)))
        return groups

    def detailContent(self, ids):
        vod_id = self._clean_text(ids[0] if isinstance(ids, list) and ids else ids)
        if not vod_id:
            return {"list": []}
        root = self.html(self._request_html(self.host + vod_id))
        if root is None:
            return {"list": []}
        groups = self._parse_play_groups(root)
        vod = {
            "vod_id": vod_id,
            "vod_name": self._clean_text("".join(root.xpath("//h1[1]//text()"))),
            "vod_pic": self._build_url(self._extract_detail_pic(root)),
            "vod_content": self._extract_detail_content(root),
            "vod_remarks": "",
            "vod_play_from": "$$$".join(item[0] for item in groups),
            "vod_play_url": "$$$".join(item[1] for item in groups),
        }
        return {"list": [vod]}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest py/tests/test_麦田影院.py -v`
Expected: PASS including grouped detail parsing with short play IDs.

- [ ] **Step 5: Commit**

```bash
git add py/麦田影院.py py/tests/test_麦田影院.py
git commit -m "feat: add maitian detail parsing"
```

### Task 4: 实现播放页直链与 `art.php` 解签

**Files:**
- Modify: `py/麦田影院.py`
- Modify: `py/tests/test_麦田影院.py`
- Test: `py/tests/test_麦田影院.py`

- [ ] **Step 1: Write the failing tests**

```python
    @patch.object(Spider, "_request_json")
    @patch.object(Spider, "_request_html")
    def test_player_content_returns_direct_url(self, mock_request_html, mock_request_json):
        mock_request_html.return_value = """
        <script>var player_data={"url":"https://cdn.example.com/direct.m3u8"}</script>
        """
        result = self.spider.playerContent("线路", "/vodplay/1-1-1.html", {})
        self.assertEqual(result["parse"], 0)
        self.assertEqual(result["jx"], 0)
        self.assertEqual(result["url"], "https://cdn.example.com/direct.m3u8")
        mock_request_json.assert_not_called()

    @patch.object(Spider, "_request_json")
    @patch.object(Spider, "_request_html")
    def test_player_content_resolves_signed_art_url(self, mock_request_html, mock_request_json):
        mock_request_html.return_value = """
        <script>var player_data={"url":"%2Fapi.php%3Fid%3D1"}</script>
        """
        mock_request_json.side_effect = [
            {"signed_url": "?url=/signed/abc"},
            {"jmurl": "https://cdn.example.com/final.m3u8"},
        ]
        result = self.spider.playerContent("线路", "/vodplay/1-1-2.html", {})
        self.assertEqual(result["url"], "https://cdn.example.com/final.m3u8")
        self.assertEqual(
            mock_request_json.call_args_list[0].args[0],
            "https://www.mtyy5.com/static/player/art.php?get_signed_url=1&url=/api.php?id=1",
        )
        self.assertEqual(
            mock_request_json.call_args_list[1].args[0],
            "https://www.mtyy5.com/static/player/art.php?url=/signed/abc",
        )

    @patch.object(Spider, "_request_json")
    @patch.object(Spider, "_request_html")
    def test_player_content_falls_back_when_player_data_missing(self, mock_request_html, mock_request_json):
        mock_request_html.return_value = "<html><body>empty</body></html>"
        result = self.spider.playerContent("线路", "/vodplay/1-1-3.html", {})
        self.assertEqual(result["parse"], 1)
        self.assertEqual(result["jx"], 1)
        self.assertEqual(result["url"], "https://www.mtyy5.com/vodplay/1-1-3.html")
        mock_request_json.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest py/tests/test_麦田影院.py -v`
Expected: FAIL because `_request_json`, `playerContent`, or `player_data` extraction logic is missing.

- [ ] **Step 3: Write minimal implementation**

```python
import json
from urllib.parse import unquote

    def _request_json(self, url, referer=None):
        target = self._build_url(url)
        headers = dict(self.headers)
        headers["Referer"] = referer or self.headers["Referer"]
        response = self.fetch(target, headers=headers, timeout=10)
        if response.status_code != 200:
            return {}
        try:
            return json.loads(response.text or "")
        except Exception:
            return {}

    def _build_player_headers(self, referer):
        return {
            "User-Agent": self.user_agent,
            "Referer": referer,
        }

    def _extract_player_data(self, html):
        matched = re.search(r"player_data\s*=\s*(\{.*?\})\s*</script>", self._stringify(html), re.S)
        if not matched:
            return {}
        try:
            return json.loads(matched.group(1))
        except Exception:
            return {}

    def playerContent(self, flag, id, vipFlags):
        play_id = self._clean_text(id)
        play_url = self.host + play_id if play_id.startswith("/") else self._build_url(play_id)
        player_data = self._extract_player_data(self._request_html(play_url, referer=self.host + "/"))
        direct_url = self._clean_text(player_data.get("url"))
        if direct_url.startswith(("http://", "https://")):
            return {
                "parse": 0,
                "jx": 0,
                "playUrl": "",
                "url": direct_url,
                "header": self._build_player_headers(play_url),
            }

        decoded = unquote(direct_url)
        if decoded:
            signed = self._request_json(
                self.host + f"/static/player/art.php?get_signed_url=1&url={decoded}",
                referer=play_url,
            )
            signed_url = self._clean_text(signed.get("signed_url"))
            if signed_url:
                final_data = self._request_json(
                    self.host + f"/static/player/art.php{signed_url}",
                    referer=play_url,
                )
                final_url = self._clean_text(final_data.get("jmurl"))
                if final_url:
                    return {
                        "parse": 0,
                        "jx": 0,
                        "playUrl": "",
                        "url": final_url,
                        "header": self._build_player_headers(play_url),
                    }

        return {
            "parse": 1,
            "jx": 1,
            "playUrl": "",
            "url": play_url,
            "header": self._build_player_headers(play_url),
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest py/tests/test_麦田影院.py -v`
Expected: PASS for direct player URL, signed `art.php` resolution, and fallback behavior.

- [ ] **Step 5: Commit**

```bash
git add py/麦田影院.py py/tests/test_麦田影院.py
git commit -m "feat: add maitian player parsing"
```

### Task 5: 完整验证与收尾

**Files:**
- Modify: `py/麦田影院.py`
- Modify: `py/tests/test_麦田影院.py`
- Test: `py/tests/test_麦田影院.py`

- [ ] **Step 1: Run focused test suite**

Run: `uv run python -m unittest py/tests/test_麦田影院.py -v`
Expected: all tests PASS.

- [ ] **Step 2: Run syntax check**

Run: `uv run python -m py_compile py/麦田影院.py py/tests/test_麦田影院.py`
Expected: no output.

- [ ] **Step 3: Review scope**

```python
# Confirm the spider still has no search network behavior, keeps short IDs,
# and does not add pagecount to category or search payloads.
```

- [ ] **Step 4: Re-run verification**

Run: `uv run python -m unittest py/tests/test_麦田影院.py -v`
Expected: all tests still PASS.

- [ ] **Step 5: Commit**

```bash
git add py/麦田影院.py py/tests/test_麦田影院.py
git commit -m "feat: add maitian spider"
```
