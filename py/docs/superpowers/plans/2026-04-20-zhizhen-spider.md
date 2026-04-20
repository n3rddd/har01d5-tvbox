# 至臻 Spider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在当前 Python 仓库中新增一个独立单站 `至臻` 蜘蛛，支持固定分类、分类列表、搜索、详情页网盘线路整理和网盘分享链接透传。

**Architecture:** 采用单文件站点脚本 `py/至臻.py` 承担全部站点逻辑，内部拆分为 URL 组装、文本清洗、请求封装、卡片解析、详情字段提取、网盘类型识别和线路拼接几个 helper。测试沿用现有 `unittest + SourceFileLoader + mock` 风格，先写失败测试锁定分类、解析和透传行为，再实现最小代码直到模块测试转绿。

**Tech Stack:** Python 3, `unittest`, `unittest.mock`, `re`, `sys`, `urllib.parse`, `base.spider.Spider`

---

## File Structure

- Create: `py/至臻.py`
  - 实现 `Spider` 类和站点全部逻辑
  - 暴露 `init`、`getName`、`homeContent`、`homeVideoContent`、`categoryContent`、`searchContent`、`detailContent`、`playerContent`
  - 私有方法负责 URL 拼装、文本清洗、请求、卡片解析、详情字段提取、网盘识别和线路组装
- Create: `py/tests/test_至臻.py`
  - 使用 `SourceFileLoader` 加载 `py/至臻.py`
  - 通过内联 HTML 与 `mock` 覆盖分类、搜索、详情、线路排序和透传

### Task 1: Scaffold Spider And Pan Detection

**Files:**
- Create: `py/tests/test_至臻.py`
- Create: `py/至臻.py`

- [ ] **Step 1: Write the failing test**

```python
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("zhizhen_spider", str(ROOT / "至臻.py")).load_module()
Spider = MODULE.Spider


class TestZhiZhenSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_home_content_exposes_all_categories(self):
        content = self.spider.homeContent(False)
        self.assertEqual(
            [(item["type_id"], item["type_name"]) for item in content["class"]],
            [
                ("1", "至臻电影"),
                ("2", "至臻剧集"),
                ("3", "至臻动漫"),
                ("4", "至臻综艺"),
                ("5", "至臻短剧"),
                ("24", "至臻老剧"),
                ("26", "至臻严选"),
            ],
        )

    def test_home_video_content_returns_empty_list(self):
        self.assertEqual(self.spider.homeVideoContent(), {"list": []})

    def test_build_url_and_detect_pan_type(self):
        self.assertEqual(
            self.spider._build_url("/index.php/vod/detail/id/1.html"),
            "http://www.miqk.cc/index.php/vod/detail/id/1.html",
        )
        self.assertEqual(
            self.spider._detect_pan_type("https://pan.baidu.com/s/demo"),
            ("baidu", "百度资源"),
        )
        self.assertEqual(
            self.spider._detect_pan_type("https://example.com/video"),
            ("", ""),
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run from `py/`: `python -m unittest tests.test_至臻.TestZhiZhenSpider -v`
Expected: FAIL with `FileNotFoundError` for `至臻.py` or missing `Spider` attributes.

- [ ] **Step 3: Write minimal implementation**

```python
# coding=utf-8
import re
import sys
from urllib.parse import urljoin

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "至臻"
        self.host = "http://www.miqk.cc"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/136.0.0.0 Safari/537.36"
            ),
            "Referer": self.host + "/",
        }
        self.categories = [
            {"type_id": "1", "type_name": "至臻电影"},
            {"type_id": "2", "type_name": "至臻剧集"},
            {"type_id": "3", "type_name": "至臻动漫"},
            {"type_id": "4", "type_name": "至臻综艺"},
            {"type_id": "5", "type_name": "至臻短剧"},
            {"type_id": "24", "type_name": "至臻老剧"},
            {"type_id": "26", "type_name": "至臻严选"},
        ]
        self.pan_patterns = [
            ("baidu", "百度资源", r"pan\.baidu\.com|yun\.baidu\.com"),
            ("a139", "139资源", r"yun\.139\.com"),
            ("a189", "天翼资源", r"cloud\.189\.cn"),
            ("a123", "123资源", r"123684\.com|123865\.com|123912\.com|123pan\.com"),
            ("a115", "115资源", r"115\.com"),
            ("quark", "夸克资源", r"pan\.quark\.cn"),
            ("xunlei", "迅雷资源", r"pan\.xunlei\.com"),
            ("aliyun", "阿里资源", r"aliyundrive\.com|alipan\.com"),
            ("uc", "UC资源", r"drive\.uc\.cn"),
        ]

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def homeContent(self, filter):
        return {"class": self.categories}

    def homeVideoContent(self):
        return {"list": []}

    def _build_url(self, path):
        return urljoin(self.host + "/", str(path or "").strip())

    def _detect_pan_type(self, url):
        raw = str(url or "").strip()
        for pan_type, title, pattern in self.pan_patterns:
            if re.search(pattern, raw, re.I):
                return pan_type, title
        return "", ""
```

- [ ] **Step 4: Run test to verify it passes**

Run from `py/`: `python -m unittest tests.test_至臻.TestZhiZhenSpider -v`
Expected: PASS for the scaffold tests.

- [ ] **Step 5: Commit**

```bash
git add py/tests/test_至臻.py py/至臻.py
git commit -m "feat: scaffold zhizhen spider"
```

### Task 2: Add Category And Search Parsing

**Files:**
- Modify: `py/tests/test_至臻.py`
- Modify: `py/至臻.py`

- [ ] **Step 1: Write the failing test**

```python
from unittest.mock import patch


class TestZhiZhenSpider(unittest.TestCase):
    def test_parse_cards_extracts_short_path_ids(self):
        html = """
        <div id="main">
          <div class="module-item">
            <div class="module-item-pic">
              <a href="/index.php/vod/detail/id/123.html"></a>
              <img data-src="/poster.jpg" alt="示例影片" />
            </div>
            <div class="module-item-text">HD</div>
            <div class="module-item-caption"><span>2025</span></div>
          </div>
        </div>
        """
        self.assertEqual(
            self.spider._parse_cards(html),
            [
                {
                    "vod_id": "/index.php/vod/detail/id/123.html",
                    "vod_name": "示例影片",
                    "vod_pic": "http://www.miqk.cc/poster.jpg",
                    "vod_remarks": "HD",
                    "vod_year": "2025",
                }
            ],
        )

    @patch.object(Spider, "_request_html")
    def test_category_content_builds_reference_url_and_returns_page_payload(self, mock_request_html):
        mock_request_html.return_value = """
        <div id="main">
          <div class="module-item">
            <div class="module-item-pic">
              <a href="/index.php/vod/detail/id/456.html"></a>
              <img data-src="/cate.jpg" alt="分类影片" />
            </div>
            <div class="module-item-text">更新至10集</div>
            <div class="module-item-caption"><span>2024</span></div>
          </div>
        </div>
        """
        result = self.spider.categoryContent("2", "3", False, {})
        self.assertEqual(
            mock_request_html.call_args.args[0],
            "http://www.miqk.cc/index.php/vod/show/id/2/page/3.html",
        )
        self.assertEqual(result["page"], 3)
        self.assertEqual(result["limit"], 1)
        self.assertEqual(result["list"][0]["vod_name"], "分类影片")
        self.assertNotIn("pagecount", result)

    @patch.object(Spider, "_request_html")
    def test_search_content_builds_reference_search_url_and_parses_results(self, mock_request_html):
        mock_request_html.return_value = """
        <div class="module-search-item">
          <a class="video-serial" href="/index.php/vod/detail/id/789.html" title="搜索影片">抢先版</a>
          <div class="module-item-pic">
            <img data-src="/search.jpg" alt="搜索影片" />
          </div>
        </div>
        """
        result = self.spider.searchContent("繁花", False, "2")
        self.assertEqual(
            mock_request_html.call_args.args[0],
            "http://www.miqk.cc/index.php/vod/search/page/2/wd/%E7%B9%81%E8%8A%B1.html",
        )
        self.assertEqual(
            result["list"][0],
            {
                "vod_id": "/index.php/vod/detail/id/789.html",
                "vod_name": "搜索影片",
                "vod_pic": "http://www.miqk.cc/search.jpg",
                "vod_remarks": "抢先版",
            },
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run from `py/`: `python -m unittest tests.test_至臻.TestZhiZhenSpider -v`
Expected: FAIL with missing `_parse_cards` or `categoryContent`/`searchContent`.

- [ ] **Step 3: Write minimal implementation**

```python
from urllib.parse import quote


    def _clean_text(self, text):
        return re.sub(r"\s+", " ", str(text or "").replace("\xa0", " ")).strip()

    def _request_html(self, path_or_url):
        target = path_or_url if str(path_or_url).startswith("http") else self._build_url(path_or_url)
        response = self.fetch(target, headers=dict(self.headers), timeout=10)
        if response.status_code != 200:
            return ""
        return response.text or ""

    def _page_result(self, items, pg):
        page = int(pg)
        return {"page": page, "limit": len(items), "total": page * 20 + len(items), "list": items}

    def _parse_cards(self, html):
        root = self.html(html)
        if root is None:
            return []
        items = []
        for node in root.xpath("//*[@id='main']//*[contains(@class,'module-item')]"):
            href = "".join(node.xpath(".//*[contains(@class,'module-item-pic')]//a[1]/@href")).strip()
            title = "".join(node.xpath(".//*[contains(@class,'module-item-pic')]//img[1]/@alt")).strip()
            pic = (
                "".join(node.xpath(".//*[contains(@class,'module-item-pic')]//img[1]/@data-src")).strip()
                or "".join(node.xpath(".//*[contains(@class,'module-item-pic')]//img[1]/@src")).strip()
            )
            remarks = self._clean_text("".join(node.xpath(".//*[contains(@class,'module-item-text')][1]//text()")))
            year = self._clean_text("".join(node.xpath(".//*[contains(@class,'module-item-caption')][1]//span[1]//text()")))
            if not href or not title:
                continue
            items.append(
                {
                    "vod_id": href,
                    "vod_name": title,
                    "vod_pic": self._build_url(pic),
                    "vod_remarks": remarks,
                    "vod_year": year,
                }
            )
        return items

    def categoryContent(self, tid, pg, filter, extend):
        url = self._build_url(f"/index.php/vod/show/id/{tid}/page/{int(pg)}.html")
        return self._page_result(self._parse_cards(self._request_html(url)), pg)

    def searchContent(self, key, quick, pg="1"):
        keyword = self._clean_text(key)
        page = int(pg)
        if not keyword:
            return {"page": page, "total": 0, "list": []}
        url = self._build_url(f"/index.php/vod/search/page/{page}/wd/{quote(keyword)}.html")
        root = self.html(self._request_html(url))
        if root is None:
            return {"page": page, "total": 0, "list": []}
        items = []
        for node in root.xpath("//*[contains(@class,'module-search-item')]"):
            href = "".join(node.xpath(".//*[contains(@class,'video-serial')][1]/@href")).strip()
            title = "".join(node.xpath(".//*[contains(@class,'video-serial')][1]/@title")).strip()
            pic = (
                "".join(node.xpath(".//*[contains(@class,'module-item-pic')]//img[1]/@data-src")).strip()
                or "".join(node.xpath(".//*[contains(@class,'module-item-pic')]//img[1]/@src")).strip()
            )
            remarks = self._clean_text(
                "".join(node.xpath(".//*[contains(@class,'video-serial')][1]//text()"))
                or "".join(node.xpath(".//*[contains(@class,'module-item-text')][1]//text()"))
            )
            if not href or not title:
                continue
            items.append(
                {
                    "vod_id": href,
                    "vod_name": title,
                    "vod_pic": self._build_url(pic),
                    "vod_remarks": remarks,
                }
            )
        return {"page": page, "total": len(items), "list": items}
```

- [ ] **Step 4: Run test to verify it passes**

Run from `py/`: `python -m unittest tests.test_至臻.TestZhiZhenSpider -v`
Expected: PASS for the list and search tests.

- [ ] **Step 5: Commit**

```bash
git add py/tests/test_至臻.py py/至臻.py
git commit -m "feat: add zhizhen list and search parsing"
```

### Task 3: Add Detail Parsing, Pan Line Building, And Player Passthrough

**Files:**
- Modify: `py/tests/test_至臻.py`
- Modify: `py/至臻.py`

- [ ] **Step 1: Write the failing test**

```python
class TestZhiZhenSpider(unittest.TestCase):
    def test_build_pan_lines_deduplicates_and_sorts_supported_links(self):
        detail = {
            "pan_urls": [
                "https://pan.quark.cn/s/q1",
                "https://pan.baidu.com/s/b1",
                "https://pan.baidu.com/s/b1",
                "https://example.com/ignored",
            ]
        }
        self.assertEqual(
            self.spider._build_pan_lines(detail),
            [
                ("baidu#至臻", "百度资源$https://pan.baidu.com/s/b1"),
                ("quark#至臻", "夸克资源$https://pan.quark.cn/s/q1"),
            ],
        )

    def test_parse_detail_page_extracts_meta_content_and_pan_urls(self):
        html = """
        <div class="page-title">示例剧</div>
        <div class="mobile-play"><img class="lazyload" data-src="/poster.jpg" /></div>
        <div class="video-info-itemtitle">年代</div><div><a>2024</a></div>
        <div class="video-info-itemtitle">导演</div><div><a>导演甲</a></div>
        <div class="video-info-itemtitle">主演</div><div><a>演员甲</a><a>演员乙</a></div>
        <div class="video-info-itemtitle">剧情</div><div><p>一段剧情简介</p></div>
        <div class="module-row-info">
          <p>https://pan.quark.cn/s/q1</p>
          <p>https://pan.baidu.com/s/b1</p>
        </div>
        """
        detail = self.spider._parse_detail_page("/index.php/vod/detail/id/123.html", html)
        self.assertEqual(detail["vod_name"], "示例剧")
        self.assertEqual(detail["vod_pic"], "http://www.miqk.cc/poster.jpg")
        self.assertEqual(detail["vod_year"], "2024")
        self.assertEqual(detail["vod_director"], "导演甲")
        self.assertEqual(detail["vod_actor"], "演员甲,演员乙")
        self.assertEqual(detail["vod_content"], "一段剧情简介")
        self.assertEqual(detail["pan_urls"], ["https://pan.quark.cn/s/q1", "https://pan.baidu.com/s/b1"])

    @patch.object(Spider, "_request_html")
    def test_detail_content_builds_pan_play_fields(self, mock_request_html):
        mock_request_html.return_value = """
        <div class="page-title">示例剧</div>
        <div class="mobile-play"><img class="lazyload" data-src="/poster.jpg" /></div>
        <div class="video-info-itemtitle">年代</div><div><a>2024</a></div>
        <div class="video-info-itemtitle">导演</div><div><a>导演甲</a></div>
        <div class="video-info-itemtitle">主演</div><div><a>演员甲</a></div>
        <div class="video-info-itemtitle">剧情</div><div><p>一段剧情简介</p></div>
        <div class="module-row-info">
          <p>https://pan.quark.cn/s/q1</p>
          <p>https://pan.baidu.com/s/b1</p>
        </div>
        """
        result = self.spider.detailContent(["/index.php/vod/detail/id/123.html"])
        vod = result["list"][0]
        self.assertEqual(vod["vod_name"], "示例剧")
        self.assertEqual(vod["vod_play_from"], "baidu#至臻$$$quark#至臻")
        self.assertEqual(
            vod["vod_play_url"],
            "百度资源$https://pan.baidu.com/s/b1$$$夸克资源$https://pan.quark.cn/s/q1",
        )

    def test_player_content_passthroughs_supported_pan_urls(self):
        self.assertEqual(
            self.spider.playerContent("baidu#至臻", "https://pan.baidu.com/s/demo", {}),
            {"parse": 0, "playUrl": "", "url": "https://pan.baidu.com/s/demo"},
        )

    def test_player_content_rejects_non_pan_url(self):
        self.assertEqual(
            self.spider.playerContent("site", "/index.php/vod/play/id/1.html", {}),
            {"parse": 0, "playUrl": "", "url": ""},
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run from `py/`: `python -m unittest tests.test_至臻.TestZhiZhenSpider -v`
Expected: FAIL with missing detail parser, line builder, or player logic.

- [ ] **Step 3: Write minimal implementation**

```python
        self.pan_priority = {
            "baidu": 1,
            "a139": 2,
            "a189": 3,
            "a123": 4,
            "a115": 5,
            "quark": 6,
            "xunlei": 7,
            "aliyun": 8,
            "uc": 9,
        }

    def _parse_detail_page(self, vod_id, html):
        root = self.html(html)
        if root is None:
            return {
                "vod_id": vod_id,
                "vod_name": "",
                "vod_pic": "",
                "vod_year": "",
                "vod_director": "",
                "vod_actor": "",
                "vod_content": "",
                "pan_urls": [],
            }
        detail = {
            "vod_id": vod_id,
            "vod_name": self._clean_text("".join(root.xpath("//*[contains(@class,'page-title')][1]//text()"))),
            "vod_pic": self._build_url(
                "".join(
                    root.xpath(
                        "//*[contains(@class,'mobile-play')]//*[contains(@class,'lazyload')][1]/@data-src | "
                        "//*[contains(@class,'mobile-play')]//*[contains(@class,'lazyload')][1]/@src"
                    )
                ).strip()
            ),
            "vod_year": "",
            "vod_director": "",
            "vod_actor": "",
            "vod_content": "",
            "pan_urls": [],
        }
        for label_node in root.xpath("//*[contains(@class,'video-info-itemtitle')]"):
            key = self._clean_text("".join(label_node.xpath(".//text()")))
            sibling = label_node.getnext()
            if sibling is None:
                continue
            values = [self._clean_text(text) for text in sibling.xpath(".//a//text()")]
            joined = ",".join([value for value in values if value])
            text_value = self._clean_text("".join(sibling.xpath(".//text()")))
            if "年代" in key:
                detail["vod_year"] = joined or text_value
            elif "导演" in key:
                detail["vod_director"] = joined or text_value
            elif "主演" in key:
                detail["vod_actor"] = joined or text_value
            elif "剧情" in key:
                detail["vod_content"] = text_value
        for node in root.xpath("//*[contains(@class,'module-row-info')]//p"):
            text = self._clean_text("".join(node.xpath(".//text()")))
            if text:
                detail["pan_urls"].append(text)
        return detail

    def _build_pan_lines(self, detail):
        lines = []
        seen = set()
        for url in detail.get("pan_urls", []):
            pan_type, title = self._detect_pan_type(url)
            if not pan_type or url in seen:
                continue
            seen.add(url)
            lines.append((self.pan_priority.get(pan_type, 999), f"{pan_type}#至臻", f"{title}${url}"))
        lines.sort(key=lambda item: item[0])
        return [(item[1], item[2]) for item in lines]

    def detailContent(self, ids):
        result = {"list": []}
        for raw_id in ids:
            vod_id = str(raw_id or "").strip()
            detail = self._parse_detail_page(vod_id, self._request_html(self._build_url(vod_id)))
            lines = self._build_pan_lines(detail)
            result["list"].append(
                {
                    "vod_id": vod_id,
                    "vod_name": detail["vod_name"],
                    "vod_pic": detail["vod_pic"],
                    "vod_year": detail["vod_year"],
                    "vod_director": detail["vod_director"],
                    "vod_actor": detail["vod_actor"],
                    "vod_content": detail["vod_content"],
                    "vod_play_from": "$$$".join([item[0] for item in lines]),
                    "vod_play_url": "$$$".join([item[1] for item in lines]),
                }
            )
        return result

    def playerContent(self, flag, id, vipFlags):
        pan_type, _ = self._detect_pan_type(id)
        if pan_type:
            return {"parse": 0, "playUrl": "", "url": id}
        return {"parse": 0, "playUrl": "", "url": ""}
```

- [ ] **Step 4: Run test to verify it passes**

Run from `py/`: `python -m unittest tests.test_至臻.TestZhiZhenSpider -v`
Expected: PASS for the detail and player tests.

- [ ] **Step 5: Commit**

```bash
git add py/tests/test_至臻.py py/至臻.py
git commit -m "feat: add zhizhen detail and player support"
```

## Self-Review

- Spec coverage: 覆盖了固定分类、列表、搜索、详情、网盘线路和播放透传，没有遗漏公共层改动。
- Placeholder scan: 计划中的文件路径、测试名、命令和关键代码均已具体化，没有保留 TBD 或“类似前一项”。
- Type consistency: `vod_id` 使用短路径，`vod_play_from` / `vod_play_url`、`_detect_pan_type`、`_build_pan_lines` 的命名在各任务中保持一致。
