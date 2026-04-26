# 飞快TV Spider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增一个固定站点 `https://feikuai.tv` 的 Python Spider，支持分类、搜索、详情、站内播放和网盘分组。

**Architecture:** 采用单文件 Spider 实现，所有站点逻辑放在 `py/飞快TV.py`。列表和搜索直接解析静态 HTML，详情页同时提取站内播放分组和网盘分组，播放页只覆盖 `player_aaaa` 的 `encrypt=1/2` 两条解链路径，失败时回退解析页。

**Tech Stack:** Python 3、`base.spider.Spider`、`unittest`、`unittest.mock`、内置 `json` / `re` / `base64` / `urllib.parse`

---

### Task 1: 搭建 Spider 骨架与基础测试

**Files:**
- Create: `py/飞快TV.py`
- Create: `py/tests/test_飞快TV.py`
- Test: `py/tests/test_飞快TV.py`

- [ ] **Step 1: Write the failing tests**

```python
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("feikuai_spider", str(ROOT / "飞快TV.py")).load_module()
Spider = MODULE.Spider


class TestFeikuaiSpider(unittest.TestCase):
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
                {"type_id": "2", "type_name": "剧集"},
                {"type_id": "3", "type_name": "综艺"},
                {"type_id": "4", "type_name": "动漫"},
            ],
        )

    def test_home_video_content_returns_empty_list(self):
        self.assertEqual(self.spider.homeVideoContent(), {"list": []})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest py/tests/test_飞快TV.py -v`
Expected: FAIL with `FileNotFoundError` or import failure because `py/飞快TV.py` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# coding=utf-8
import sys

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "飞快TV"
        self.host = "https://feikuai.tv"
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
            {"type_id": "2", "type_name": "剧集"},
            {"type_id": "3", "type_name": "综艺"},
            {"type_id": "4", "type_name": "动漫"},
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

Run: `uv run python -m unittest py/tests/test_飞快TV.py -v`
Expected: PASS for `test_home_content_returns_expected_classes` and `test_home_video_content_returns_empty_list`.

- [ ] **Step 5: Commit**

```bash
git add py/飞快TV.py py/tests/test_飞快TV.py
git commit -m "feat: add feikuai spider skeleton"
```

### Task 2: 实现分类与搜索解析

**Files:**
- Modify: `py/飞快TV.py`
- Modify: `py/tests/test_飞快TV.py`
- Test: `py/tests/test_飞快TV.py`

- [ ] **Step 1: Write the failing tests**

```python
from unittest.mock import patch

    @patch.object(Spider, "_request_html")
    def test_category_content_parses_short_vod_id(self, mock_request_html):
        mock_request_html.return_value = """
        <a class="module-poster-item" href="/voddetail/12345.html" title="分类影片">
          <img class="lazy" data-original="/cover.jpg" />
          <div class="module-item-note">更新至10集</div>
        </a>
        """
        result = self.spider.categoryContent("2", "3", False, {})
        self.assertEqual(
            mock_request_html.call_args.args[0],
            "https://feikuai.tv/vodshow/2--------3---.html",
        )
        self.assertEqual(
            result["list"],
            [
                {
                    "vod_id": "/voddetail/12345.html",
                    "vod_name": "分类影片",
                    "vod_pic": "https://feikuai.tv/cover.jpg",
                    "vod_remarks": "更新至10集",
                }
            ],
        )
        self.assertNotIn("pagecount", result)

    @patch.object(Spider, "_request_html")
    def test_search_content_parses_cards_and_blank_keyword(self, mock_request_html):
        blank = self.spider.searchContent("", False, "1")
        self.assertEqual(blank, {"page": 1, "limit": 0, "total": 0, "list": []})
        mock_request_html.assert_not_called()

        mock_request_html.return_value = """
        <div class="module-card-item module-item">
          <a class="module-card-item-poster" href="/voddetail/67890.html"></a>
          <div class="module-item-pic"><img data-original="/search.jpg" /></div>
          <div class="module-card-item-title"><strong>搜索命中</strong></div>
          <div class="module-item-note">HD</div>
        </div>
        """
        result = self.spider.searchContent("繁花", False, "2")
        self.assertEqual(
            mock_request_html.call_args.args[0],
            "https://feikuai.tv/label/search_ajax.html?wd=%E7%B9%81%E8%8A%B1&by=time&order=desc&page=2",
        )
        self.assertEqual(result["list"][0]["vod_id"], "/voddetail/67890.html")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest py/tests/test_飞快TV.py -v`
Expected: FAIL with `AttributeError` for missing `_request_html`, `categoryContent`, or `searchContent`.

- [ ] **Step 3: Write minimal implementation**

```python
import re
from urllib.parse import quote, urljoin

    def _build_url(self, value):
        raw = str(value or "").strip()
        if not raw:
            return ""
        if raw.startswith(("http://", "https://")):
            return raw
        if raw.startswith("//"):
            return "https:" + raw
        return urljoin(self.host + "/", raw)

    def _clean_text(self, text):
        return re.sub(r"\s+", " ", str(text or "").replace("\xa0", " ")).strip()

    def _request_html(self, path_or_url):
        target = path_or_url if str(path_or_url).startswith("http") else self._build_url(path_or_url)
        response = self.fetch(target, headers=self.headers, timeout=10)
        if response.status_code != 200:
            return ""
        return str(response.text or "")

    def _parse_category_cards(self, html):
        root = self.html(html or "")
        if root is None:
            return []
        items = []
        for node in root.xpath("//a[contains(@class,'module-poster-item')]"):
            vod_id = self._clean_text("".join(node.xpath("./@href")))
            vod_name = self._clean_text("".join(node.xpath("./@title"))) or self._clean_text(
                "".join(node.xpath(".//*[contains(@class,'module-poster-item-title')][1]//text()"))
            )
            vod_pic = self._clean_text("".join(node.xpath(".//img[contains(@class,'lazy')][1]/@data-original")))
            vod_remarks = self._clean_text("".join(node.xpath(".//*[contains(@class,'module-item-note')][1]//text()")))
            if vod_id and vod_name:
                items.append(
                    {
                        "vod_id": vod_id,
                        "vod_name": vod_name,
                        "vod_pic": self._build_url(vod_pic),
                        "vod_remarks": vod_remarks,
                    }
                )
        return items

    def _parse_search_cards(self, html):
        root = self.html(html or "")
        if root is None:
            return []
        items = []
        for node in root.xpath("//*[contains(@class,'module-card-item') and contains(@class,'module-item')]"):
            vod_id = self._clean_text("".join(node.xpath(".//a[contains(@class,'module-card-item-poster')][1]/@href")))
            vod_name = self._clean_text("".join(node.xpath(".//*[contains(@class,'module-card-item-title')][1]//strong/text()")))
            vod_pic = self._clean_text("".join(node.xpath(".//*[contains(@class,'module-item-pic')]//img[1]/@data-original")))
            vod_remarks = self._clean_text("".join(node.xpath(".//*[contains(@class,'module-item-note')][1]//text()")))
            if vod_id and vod_name:
                items.append(
                    {
                        "vod_id": vod_id,
                        "vod_name": vod_name,
                        "vod_pic": self._build_url(vod_pic),
                        "vod_remarks": vod_remarks,
                    }
                )
        return items

    def categoryContent(self, tid, pg, filter, extend):
        page = max(1, int(pg))
        url = self.host + f"/vodshow/{tid}--------{page}---.html"
        items = self._parse_category_cards(self._request_html(url))
        return {"page": page, "limit": len(items), "total": len(items), "list": items}

    def searchContent(self, key, quick, pg="1"):
        page = max(1, int(pg))
        keyword = self._clean_text(key)
        if not keyword:
            return {"page": page, "limit": 0, "total": 0, "list": []}
        url = self.host + "/label/search_ajax.html?wd=" + quote(keyword) + f"&by=time&order=desc&page={page}"
        items = self._parse_search_cards(self._request_html(url))
        return {"page": page, "limit": len(items), "total": len(items), "list": items}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest py/tests/test_飞快TV.py -v`
Expected: PASS for home, category, and search tests.

- [ ] **Step 5: Commit**

```bash
git add py/飞快TV.py py/tests/test_飞快TV.py
git commit -m "feat: add feikuai category and search parsing"
```

### Task 3: 实现详情页在线播放与网盘分组

**Files:**
- Modify: `py/飞快TV.py`
- Modify: `py/tests/test_飞快TV.py`
- Test: `py/tests/test_飞快TV.py`

- [ ] **Step 1: Write the failing test**

```python
    @patch.object(Spider, "_request_html")
    def test_detail_content_merges_online_and_pan_groups(self, mock_request_html):
        mock_request_html.return_value = """
        <h1>示例影片</h1>
        <div class="module-item-pic"><img data-original="/detail.jpg" /></div>
        <div class="module-info-introduction-content">这里是简介</div>
        <div class="module-tab-items-box">
          <div class="module-tab-item"><span>线路A</span></div>
          <div class="module-tab-item"><span>线路B</span></div>
        </div>
        <div class="module-list tab-list">
          <a class="module-play-list-link" href="/vodplay/1-1-1.html">第1集</a>
          <a class="module-play-list-link" href="/vodplay/1-1-2.html">第2集</a>
        </div>
        <div class="module-list tab-list">
          <a class="module-play-list-link" href="/vodplay/1-2-1.html">第1集</a>
        </div>
        <div class="module-list">
          <div class="tab-content">
            <h4>夸克资源@分享一</h4>
            <p>https://pan.quark.cn/s/demo1</p>
          </div>
          <div class="tab-content">
            <h4>百度合集@分享二</h4>
            <p>https://pan.baidu.com/s/demo2</p>
          </div>
        </div>
        """
        result = self.spider.detailContent(["/voddetail/1.html"])
        vod = result["list"][0]
        self.assertEqual(vod["vod_id"], "/voddetail/1.html")
        self.assertEqual(vod["vod_name"], "示例影片")
        self.assertEqual(vod["vod_pic"], "https://feikuai.tv/detail.jpg")
        self.assertEqual(vod["vod_content"], "这里是简介")
        self.assertEqual(vod["vod_play_from"], "线路A$$$线路B$$$quark$$$baidu")
        self.assertEqual(
            vod["vod_play_url"],
            "第1集$/vodplay/1-1-1.html#第2集$/vodplay/1-1-2.html$$$第1集$/vodplay/1-2-1.html$$$夸克资源$https://pan.quark.cn/s/demo1$$$百度合集$https://pan.baidu.com/s/demo2",
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest py/tests/test_飞快TV.py -v`
Expected: FAIL with missing `detailContent` or empty result assertions.

- [ ] **Step 3: Write minimal implementation**

```python
    def _detect_pan_type(self, url):
        value = str(url or "").strip()
        if "pan.quark.cn" in value:
            return "quark"
        if "drive.uc.cn" in value:
            return "uc"
        if "alipan.com" in value or "aliyundrive.com" in value:
            return "aliyun"
        if "pan.baidu.com" in value:
            return "baidu"
        return "pan"

    def _join_group_urls(self, groups):
        return "$$$".join("#".join(group) for group in groups if group)

    def detailContent(self, ids):
        vod_id = str(ids[0] if isinstance(ids, list) and ids else ids or "").strip()
        if not vod_id:
            return {"list": []}
        html = self._request_html(self.host + vod_id)
        root = self.html(html or "")
        if root is None:
            return {"list": []}

        title = self._clean_text("".join(root.xpath("//h1[1]//text()")))
        pic = self._clean_text(
            "".join(root.xpath("//*[contains(@class,'module-item-pic')]//img[1]/@data-original"))
        )
        content = self._clean_text(
            "".join(
                root.xpath(
                    "//*[contains(@class,'module-info-introduction-content')][1]//text()"
                )
            )
        )

        play_from = []
        play_urls = []
        online_names = [
            self._clean_text("".join(node.xpath(".//text()")))
            for node in root.xpath(
                "//div[contains(@class,'module-tab-items-box')]/*[contains(@class,'module-tab-item')][not(@onclick)]"
            )
        ]
        online_lists = root.xpath(
            "//div[contains(@class,'module-list') and contains(@class,'tab-list')][not(contains(@class,'module-downlist'))]"
        )
        for index, node in enumerate(online_lists):
            episodes = []
            for item in node.xpath(".//a[contains(@class,'module-play-list-link')]"):
                name = self._clean_text("".join(item.xpath(".//text()")))
                href = self._clean_text("".join(item.xpath("./@href")))
                if name and href:
                    episodes.append(f\"{name}${href}\")
            if episodes:
                play_from.append(online_names[index] if index < len(online_names) and online_names[index] else f\"线路{index + 1}\")
                play_urls.append(episodes)

        pan_groups = {}
        for node in root.xpath("//div[contains(@class,'module-list')]/*[contains(@class,'tab-content')]"):
            raw_name = self._clean_text("".join(node.xpath(".//h4[1]//text()")))
            pan_name = raw_name.split("@", 1)[0].strip() if raw_name else "网盘资源"
            pan_url = self._clean_text("".join(node.xpath(".//p[1]//text()")))
            if not pan_url.startswith("http"):
                continue
            pan_type = self._detect_pan_type(pan_url)
            pan_groups.setdefault(pan_type, []).append(f\"{pan_name}${pan_url}\")

        for key, values in pan_groups.items():
            play_from.append(key)
            play_urls.append(values)

        vod = {
            "vod_id": vod_id,
            "vod_name": title,
            "vod_pic": self._build_url(pic),
            "vod_content": content,
            "vod_remarks": "",
            "vod_play_from": "$$$".join(play_from),
            "vod_play_url": self._join_group_urls(play_urls),
        }
        return {"list": [vod]}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest py/tests/test_飞快TV.py -v`
Expected: PASS for detail merge test and previous tests.

- [ ] **Step 5: Commit**

```bash
git add py/飞快TV.py py/tests/test_飞快TV.py
git commit -m "feat: add feikuai detail and pan groups"
```

### Task 4: 实现播放页直链解析与回退

**Files:**
- Modify: `py/飞快TV.py`
- Modify: `py/tests/test_飞快TV.py`
- Test: `py/tests/test_飞快TV.py`

- [ ] **Step 1: Write the failing tests**

```python
    def test_base64decode_decodes_fixture(self):
        self.assertEqual(self.spider._base64decode("aHR0cHM6Ly9jZG4uZXhhbXBsZS5jb20vdjIubTN1OA=="), "https://cdn.example.com/v2.m3u8")

    @patch.object(Spider, "_request_html")
    def test_player_content_supports_encrypt_1_and_encrypt_2(self, mock_request_html):
        mock_request_html.side_effect = [
            '<script>player_aaaa={"url":"https%3A//cdn.example.com/v1.m3u8","encrypt":"1"}</script>',
            '<script>player_aaaa={"url":"aHR0cHM6Ly9jZG4uZXhhbXBsZS5jb20vdjIubTN1OA==","encrypt":"2"}</script>',
        ]
        direct = self.spider.playerContent("feikuai", "/vodplay/1-1-1.html", {})
        encoded = self.spider.playerContent("feikuai", "/vodplay/1-1-2.html", {})
        self.assertEqual(direct["parse"], 0)
        self.assertEqual(direct["url"], "https://cdn.example.com/v1.m3u8")
        self.assertEqual(encoded["parse"], 0)
        self.assertEqual(encoded["url"], "https://cdn.example.com/v2.m3u8")

    @patch.object(Spider, "_request_html")
    def test_player_content_falls_back_when_script_missing(self, mock_request_html):
        mock_request_html.return_value = "<html><body>empty</body></html>"
        result = self.spider.playerContent("feikuai", "/vodplay/1-1-3.html", {})
        self.assertEqual(result["parse"], 1)
        self.assertEqual(result["jx"], 1)
        self.assertEqual(result["url"], "https://feikuai.tv/vodplay/1-1-3.html")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest py/tests/test_飞快TV.py -v`
Expected: FAIL with missing `_base64decode` / `playerContent` or incorrect assertions.

- [ ] **Step 3: Write minimal implementation**

```python
import base64
from urllib.parse import unquote

    def _base64decode(self, value):
        try:
            return base64.b64decode(str(value or "")).decode("utf-8")
        except Exception:
            return ""

    def _extract_player_data(self, html):
        matched = re.search(r"player_aaaa\s*=\s*(\{[\s\S]*?\})\s*</script>", str(html or ""))
        if not matched:
            return {}
        try:
            return json.loads(matched.group(1))
        except Exception:
            return {}

    def playerContent(self, flag, id, vipFlags):
        target = self.host + str(id or "")
        if str(id or "").startswith(("http://", "https://")) and any(
            str(id).lower().split("?")[0].endswith(ext) for ext in [".m3u8", ".mp4", ".flv"]
        ):
            return {"parse": 0, "jx": 0, "url": id}

        data = self._extract_player_data(self._request_html(target))
        raw_url = str(data.get("url") or "")
        encrypt = str(data.get("encrypt") or "")
        media_url = ""
        if encrypt == "1":
            media_url = unquote(raw_url)
        elif encrypt == "2":
            media_url = unquote(self._base64decode(raw_url))
        elif raw_url:
            media_url = raw_url

        if media_url.startswith("http"):
            return {"parse": 0, "jx": 0, "url": media_url}
        return {"parse": 1, "jx": 1, "url": target}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest py/tests/test_飞快TV.py -v`
Expected: PASS for all tests in `py/tests/test_飞快TV.py`.

- [ ] **Step 5: Commit**

```bash
git add py/飞快TV.py py/tests/test_飞快TV.py
git commit -m "feat: add feikuai player parsing"
```

### Task 5: 验证与收尾

**Files:**
- Modify: `py/飞快TV.py`
- Modify: `py/tests/test_飞快TV.py`
- Test: `py/tests/test_飞快TV.py`

- [ ] **Step 1: Run the focused module test suite**

Run: `uv run python -m unittest py/tests/test_飞快TV.py -v`
Expected: PASS with all新增测试通过，无网络访问。

- [ ] **Step 2: Refine code only if test output exposes duplication or brittle parsing**

```python
# 只允许整理已通过测试覆盖的辅助方法，例如：
def _parse_text(self, node, xpath):
    return self._clean_text("".join(node.xpath(xpath)))
```

- [ ] **Step 3: Re-run the focused module test suite**

Run: `uv run python -m unittest py/tests/test_飞快TV.py -v`
Expected: PASS again after any small refactor.

- [ ] **Step 4: Commit final cleanup if Step 2 changed code**

```bash
git add py/飞快TV.py py/tests/test_飞快TV.py
git commit -m "refactor: tidy feikuai spider helpers"
```

## Self-Review

- Spec coverage:
  - 固定站点、四个分类、空首页视频由 Task 1 覆盖。
  - 分类页和搜索页短路径解析由 Task 2 覆盖。
  - 详情页站内播放与网盘分组由 Task 3 覆盖。
  - `player_aaaa` 的 `encrypt=1/2` 与回退路径由 Task 4 覆盖。
- Placeholder scan:
  - 计划中没有 `TODO`、`TBD`、`implement later` 之类占位词。
  - 所有测试步骤都给出具体命令与预期结果。
- Type consistency:
  - Spider 方法名统一使用 `homeContent`、`homeVideoContent`、`categoryContent`、`searchContent`、`detailContent`、`playerContent`。
  - 测试里的 `vod_id`、`vod_play_from`、`vod_play_url` 与实现步骤保持一致。
