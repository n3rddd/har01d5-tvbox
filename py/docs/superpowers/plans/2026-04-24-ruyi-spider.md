# 如意资源 Spider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在当前 Python 仓库中新增一个 `如意资源` spider，支持硬编码分类筛选、首页推荐、分类列表、搜索、详情和基础播放解析。

**Architecture:** 使用单文件 `Spider` 实现，内部按采集 API fallback、图片 URL 补全、列表字段映射、分类类型推导、详情播放组装和基础播放分支拆成 helper。测试使用 `unittest + SourceFileLoader + unittest.mock`，严格按红绿重构覆盖 fallback、参数拼接、详情字段解析和播放输出，不做真实联网。

**Tech Stack:** Python 3, `json`, `re`, `sys`, `base.spider.Spider`, `unittest`, `unittest.mock`

---

## File Structure

- Create: `py/如意资源.py`
  - 站点实现，负责硬编码分类、API 请求 fallback、列表映射、详情组装和播放结果输出
- Create: `py/tests/test_如意资源.py`
  - 离线测试，使用 `SourceFileLoader` 加载 spider，并 mock `fetch` 或 `_request_json`

### Task 1: Scaffold Spider, API Fallback, Home, Category, And Search

**Files:**
- Create: `py/tests/test_如意资源.py`
- Create: `py/如意资源.py`

- [ ] **Step 1: Write the failing test**

```python
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("ruyi_spider", str(ROOT / "如意资源.py")).load_module()
Spider = MODULE.Spider


class FakeResponse:
    def __init__(self, status_code=200, text="{}"):
        self.status_code = status_code
        self.text = text
        self.encoding = "utf-8"


class TestRuYiSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_home_content_returns_hardcoded_classes_and_filters(self):
        result = self.spider.homeContent(False)
        class_ids = [item["type_id"] for item in result["class"]]
        self.assertEqual(class_ids, ["1", "2", "3", "4", "35", "36"])
        self.assertEqual(result["filters"]["1"][0]["key"], "type")
        self.assertEqual(result["filters"]["1"][0]["value"][0], {"n": "动作片", "v": "7"})
        self.assertEqual(result["filters"]["2"][0]["value"][0], {"n": "国产剧", "v": "13"})
        self.assertEqual(result["filters"]["35"], [])
        self.assertEqual(result["list"], [])

    def test_get_pic_url_handles_empty_absolute_and_relative_values(self):
        self.assertEqual(self.spider._get_pic_url(""), "")
        self.assertEqual(self.spider._get_pic_url("<nil>"), "")
        self.assertEqual(self.spider._get_pic_url("https://img.example.com/poster.jpg"), "https://img.example.com/poster.jpg")
        self.assertEqual(self.spider._get_pic_url("/upload/poster.jpg"), "https://ps.ryzypics.com/upload/poster.jpg")

    @patch.object(Spider, "fetch")
    def test_request_json_falls_back_to_second_api_after_failure(self, mock_fetch):
        mock_fetch.side_effect = [
            FakeResponse(status_code=500, text=""),
            FakeResponse(text='{"list":[{"vod_id":"9","vod_name":"后备命中","vod_pic":"/poster.jpg","vod_remarks":"HD","vod_year":"2026","type_id":"7"}]}'),
        ]
        result = self.spider._request_json({"ac": "list", "pg": "1", "pagesize": "20"})
        self.assertEqual(result["list"][0]["vod_name"], "后备命中")
        self.assertEqual(mock_fetch.call_count, 2)
        first_url = mock_fetch.call_args_list[0].args[0]
        second_url = mock_fetch.call_args_list[1].args[0]
        self.assertIn("https://cj.rycjapi.com/api.php/provide/vod", first_url)
        self.assertIn("https://cj.rytvapi.com/api.php/provide/vod", second_url)

    @patch.object(Spider, "_request_json")
    def test_home_video_content_maps_recommend_list(self, mock_request_json):
        mock_request_json.return_value = {
            "list": [
                {
                    "vod_id": "101",
                    "vod_name": "推荐影片",
                    "vod_pic": "/cover.jpg",
                    "vod_remarks": "更新至1集",
                    "vod_year": "2025",
                    "type_id": "7",
                }
            ]
        }
        result = self.spider.homeVideoContent()
        self.assertEqual(
            result,
            {
                "list": [
                    {
                        "vod_id": "101",
                        "vod_name": "推荐影片",
                        "vod_pic": "https://ps.ryzypics.com/cover.jpg",
                        "vod_remarks": "更新至1集",
                        "vod_year": "2025",
                        "type_id": "7",
                    }
                ]
            },
        )
        self.assertEqual(mock_request_json.call_args.args[0], {"ac": "list", "pg": "1", "pagesize": "20"})

    @patch.object(Spider, "_request_json")
    def test_category_content_uses_default_sub_type_for_main_class(self, mock_request_json):
        mock_request_json.return_value = {
            "list": [
                {"vod_id": "202", "vod_name": "动作电影", "vod_pic": "", "vod_remarks": "HD", "vod_year": "2024", "type_id": "7"}
            ]
        }
        result = self.spider.categoryContent("1", "2", False, {})
        self.assertEqual(mock_request_json.call_args.args[0], {"ac": "list", "t": "7", "pg": "2", "pagesize": "20"})
        self.assertEqual(result["page"], 2)
        self.assertEqual(result["limit"], 20)
        self.assertEqual(result["list"][0]["vod_id"], "202")
        self.assertNotIn("pagecount", result)

    @patch.object(Spider, "_request_json")
    def test_category_content_prefers_extend_type(self, mock_request_json):
        mock_request_json.return_value = {"list": []}
        self.spider.categoryContent("1", "1", False, {"type": "10"})
        self.assertEqual(mock_request_json.call_args.args[0]["t"], "10")

    def test_search_content_returns_empty_for_blank_keyword(self):
        self.assertEqual(self.spider.searchContent("", False, "1"), {"page": 1, "limit": 30, "total": 0, "list": []})

    @patch.object(Spider, "_request_json")
    def test_search_content_filters_titles_by_keyword(self, mock_request_json):
        mock_request_json.return_value = {
            "list": [
                {"vod_id": "301", "vod_name": "繁花", "vod_pic": "/a.jpg", "vod_remarks": "完结", "vod_year": "2024", "type_id": "13"},
                {"vod_id": "302", "vod_name": "狂飙", "vod_pic": "/b.jpg", "vod_remarks": "完结", "vod_year": "2023", "type_id": "13"},
            ]
        }
        result = self.spider.searchContent("繁花", False, "3")
        self.assertEqual(mock_request_json.call_args.args[0], {"ac": "list", "wd": "繁花", "pg": "3", "pagesize": "30"})
        self.assertEqual(result["page"], 3)
        self.assertEqual(result["list"], [
            {
                "vod_id": "301",
                "vod_name": "繁花",
                "vod_pic": "https://ps.ryzypics.com/a.jpg",
                "vod_remarks": "完结",
                "vod_year": "2024",
                "type_id": "13",
            }
        ])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd py && python -m unittest tests.test_如意资源.TestRuYiSpider -v`
Expected: FAIL with `FileNotFoundError` for `py/如意资源.py`

- [ ] **Step 3: Write minimal implementation**

```python
# coding=utf-8
import json
import sys

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "如意资源"
        self.api_urls = [
            "https://cj.rycjapi.com/api.php/provide/vod",
            "https://cj.rytvapi.com/api.php/provide/vod",
            "https://bycj.rytvapi.com/api.php/provide/vod",
        ]
        self.img_hosts = [
            "https://ps.ryzypics.com",
            "https://ry-pic.com",
            "https://img.lzzyimg.com",
        ]
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": "https://cj.rycjapi.com/",
        }
        self.classes = [
            {"type_id": "1", "type_name": "电影片"},
            {"type_id": "2", "type_name": "连续剧"},
            {"type_id": "3", "type_name": "综艺片"},
            {"type_id": "4", "type_name": "动漫片"},
            {"type_id": "35", "type_name": "电影解说"},
            {"type_id": "36", "type_name": "体育"},
        ]
        self.sub_class_map = {
            "1": ["7", "6", "8", "9", "10", "11", "12", "20", "34", "45", "47"],
            "2": ["13", "14", "15", "16", "21", "22", "23", "24", "46"],
            "3": ["25", "26", "27", "28"],
            "4": ["29", "30", "31", "32", "33"],
            "35": [],
            "36": ["37", "38", "39", "40"],
        }
        self.type_options = {
            "1": [{"n": "动作片", "v": "7"}, {"n": "喜剧片", "v": "8"}, {"n": "爱情片", "v": "9"}, {"n": "科幻片", "v": "10"}, {"n": "恐怖片", "v": "11"}, {"n": "剧情片", "v": "12"}, {"n": "战争片", "v": "6"}, {"n": "记录片", "v": "20"}, {"n": "伦理片", "v": "34"}, {"n": "预告片", "v": "45"}, {"n": "动画电影", "v": "47"}],
            "2": [{"n": "国产剧", "v": "13"}, {"n": "香港剧", "v": "14"}, {"n": "韩国剧", "v": "15"}, {"n": "欧美剧", "v": "16"}, {"n": "台湾剧", "v": "21"}, {"n": "日本剧", "v": "22"}, {"n": "海外剧", "v": "23"}, {"n": "泰国剧", "v": "24"}, {"n": "短剧", "v": "46"}],
            "3": [{"n": "大陆综艺", "v": "25"}, {"n": "港台综艺", "v": "26"}, {"n": "日韩综艺", "v": "27"}, {"n": "欧美综艺", "v": "28"}],
            "4": [{"n": "国产动漫", "v": "29"}, {"n": "日韩动漫", "v": "30"}, {"n": "欧美动漫", "v": "31"}, {"n": "港台动漫", "v": "32"}, {"n": "海外动漫", "v": "33"}],
            "35": [],
            "36": [{"n": "足球", "v": "37"}, {"n": "篮球", "v": "38"}, {"n": "网球", "v": "39"}, {"n": "斯诺克", "v": "40"}],
        }

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def _build_query(self, params=None):
        parts = []
        for key, value in (params or {}).items():
            if value in ("", None):
                continue
            parts.append(f"{key}={value}")
        return "&".join(parts)

    def _request_json(self, params=None, url=""):
        if url:
            targets = [url]
        else:
            query = self._build_query(params)
            targets = [f"{base}?{query}" if query else base for base in self.api_urls]
        for target in targets:
            response = self.fetch(target, headers=self.headers, timeout=10)
            if response.status_code != 200:
                continue
            try:
                return json.loads(response.text or "{}")
            except Exception:
                continue
        return {}

    def _get_pic_url(self, value):
        raw = str(value or "").strip()
        if raw in ("", "<nil>", "nil", "null"):
            return ""
        if raw.startswith("http://") or raw.startswith("https://"):
            return raw
        if raw.startswith("/"):
            return self.img_hosts[0] + raw
        return raw

    def _format_vod_list(self, items):
        result = []
        for item in items or []:
            vod_id = str((item or {}).get("vod_id", "")).strip()
            if not vod_id or vod_id == "0":
                continue
            vod_year = str((item or {}).get("vod_year", "")).strip()
            vod_remarks = str((item or {}).get("vod_remarks", "")).strip() or vod_year
            result.append(
                {
                    "vod_id": vod_id,
                    "vod_name": str((item or {}).get("vod_name", "")).strip() or "未知标题",
                    "vod_pic": self._get_pic_url((item or {}).get("vod_pic", "")),
                    "vod_remarks": vod_remarks,
                    "vod_year": vod_year,
                    "type_id": str((item or {}).get("type_id", "")).strip(),
                }
            )
        return result

    def _build_filters(self):
        filters = {}
        for cls in self.classes:
            tid = cls["type_id"]
            filters[tid] = []
            values = self.type_options.get(tid, [])
            if values:
                filters[tid].append({"key": "type", "name": "类型", "value": values})
        return filters

    def _resolve_type_id(self, tid, extend=None):
        current = dict(extend or {})
        if current.get("type"):
            return str(current["type"])
        values = self.sub_class_map.get(str(tid), [])
        if values:
            return values[0]
        return str(tid)

    def _page_result(self, items, pg, limit):
        page = max(int(str(pg or 1)), 1)
        return {"page": page, "limit": limit, "total": page * limit + len(items), "list": items}

    def homeContent(self, filter):
        return {"class": self.classes, "filters": self._build_filters(), "list": []}

    def homeVideoContent(self):
        data = self._request_json({"ac": "list", "pg": "1", "pagesize": "20"})
        return {"list": self._format_vod_list(data.get("list", []))}

    def categoryContent(self, tid, pg, filter, extend):
        params = {"ac": "list", "t": self._resolve_type_id(tid, extend), "pg": str(pg), "pagesize": "20"}
        data = self._request_json(params)
        return self._page_result(self._format_vod_list(data.get("list", [])), pg, 20)

    def searchContent(self, key, quick, pg="1"):
        keyword = str(key or "").strip()
        page = max(int(str(pg or 1)), 1)
        if not keyword:
            return {"page": page, "limit": 30, "total": 0, "list": []}
        data = self._request_json({"ac": "list", "wd": keyword, "pg": str(page), "pagesize": "30"})
        items = [item for item in self._format_vod_list(data.get("list", [])) if keyword.lower() in item["vod_name"].lower()]
        return self._page_result(items, page, 30)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd py && python -m unittest tests.test_如意资源.TestRuYiSpider.test_home_content_returns_hardcoded_classes_and_filters tests.test_如意资源.TestRuYiSpider.test_get_pic_url_handles_empty_absolute_and_relative_values tests.test_如意资源.TestRuYiSpider.test_request_json_falls_back_to_second_api_after_failure tests.test_如意资源.TestRuYiSpider.test_home_video_content_maps_recommend_list tests.test_如意资源.TestRuYiSpider.test_category_content_uses_default_sub_type_for_main_class tests.test_如意资源.TestRuYiSpider.test_category_content_prefers_extend_type tests.test_如意资源.TestRuYiSpider.test_search_content_returns_empty_for_blank_keyword tests.test_如意资源.TestRuYiSpider.test_search_content_filters_titles_by_keyword -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add py/如意资源.py py/tests/test_如意资源.py
git commit -m "feat: scaffold ruyi spider"
```

### Task 2: Add Detail Parsing And Base Player Branches

**Files:**
- Modify: `py/tests/test_如意资源.py`
- Modify: `py/如意资源.py`

- [ ] **Step 1: Write the failing test**

```python
    @patch.object(Spider, "_request_json")
    def test_detail_content_maps_metadata_and_play_groups(self, mock_request_json):
        mock_request_json.return_value = {
            "list": [
                {
                    "vod_id": "888",
                    "vod_name": "示例剧",
                    "vod_pic": "/detail.jpg",
                    "type_name": "国产剧",
                    "vod_year": "2026",
                    "vod_area": "大陆",
                    "vod_remarks": "更新至2集",
                    "vod_actor": "张三,李四",
                    "vod_director": "导演甲",
                    "vod_content": "一段简介",
                    "vod_play_from": "如意线路,备用线路",
                    "vod_play_url": "第1集$https://cdn.example.com/1.m3u8#第2集$https://parser.example.com/play/2",
                }
            ]
        }
        result = self.spider.detailContent(["888"])
        vod = result["list"][0]
        self.assertEqual(mock_request_json.call_args.args[0], {"ac": "videolist", "ids": "888"})
        self.assertEqual(vod["vod_id"], "888")
        self.assertEqual(vod["vod_pic"], "https://ps.ryzypics.com/detail.jpg")
        self.assertEqual(vod["type_name"], "国产剧")
        self.assertEqual(vod["vod_play_from"], "如意线路$$$备用线路")
        self.assertEqual(
            vod["vod_play_url"],
            "第1集$https://cdn.example.com/1.m3u8#第2集$https://parser.example.com/play/2$$$第1集$https://cdn.example.com/1.m3u8#第2集$https://parser.example.com/play/2",
        )

    def test_detail_content_returns_empty_for_blank_id(self):
        self.assertEqual(self.spider.detailContent([""]), {"list": []})

    def test_parse_play_groups_skips_invalid_entries_and_fills_missing_names(self):
        play_from, play_url = self.spider._parse_play_groups("主线", "$https://cdn.example.com/a.m3u8#预告$#https://cdn.example.com/b.mp4")
        self.assertEqual(play_from, "主线")
        self.assertEqual(play_url, "第1集$https://cdn.example.com/a.m3u8#第3集$https://cdn.example.com/b.mp4")

    def test_player_content_returns_direct_media_url(self):
        result = self.spider.playerContent("如意线路", "https://cdn.example.com/1.m3u8", {})
        self.assertEqual(result, {"parse": 0, "playUrl": "", "url": "https://cdn.example.com/1.m3u8", "header": {}})

    def test_player_content_returns_parser_url_for_non_media_link(self):
        result = self.spider.playerContent("如意线路", "https://parser.example.com/play/2", {})
        self.assertEqual(result, {"parse": 1, "playUrl": "", "url": "https://parser.example.com/play/2", "header": {}})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd py && python -m unittest tests.test_如意资源.TestRuYiSpider.test_detail_content_maps_metadata_and_play_groups tests.test_如意资源.TestRuYiSpider.test_detail_content_returns_empty_for_blank_id tests.test_如意资源.TestRuYiSpider.test_parse_play_groups_skips_invalid_entries_and_fills_missing_names tests.test_如意资源.TestRuYiSpider.test_player_content_returns_direct_media_url tests.test_如意资源.TestRuYiSpider.test_player_content_returns_parser_url_for_non_media_link -v`
Expected: FAIL with `AttributeError` for missing `detailContent`, `_parse_play_groups`, or `playerContent`

- [ ] **Step 3: Write minimal implementation**

```python
    def _parse_play_groups(self, play_from, play_url):
        groups = []
        episodes = []
        for index, item in enumerate(str(play_url or "").split("#"), start=1):
            raw = str(item or "").strip()
            if not raw:
                continue
            if "$" in raw:
                name, url = raw.split("$", 1)
            else:
                name, url = "", raw
            name = str(name or "").strip() or f"第{index}集"
            url = str(url or "").strip()
            if not url:
                continue
            episodes.append(f"{name}${url}")
        line_names = [value.strip() for value in str(play_from or "").split(",") if value.strip()]
        if not line_names:
            line_names = ["如意资源"]
        for line_name in line_names:
            groups.append({"from": line_name, "urls": "#".join(episodes)})
        return "$$$".join(group["from"] for group in groups), "$$$".join(group["urls"] for group in groups)

    def detailContent(self, ids):
        vod_id = str(ids[0] if isinstance(ids, list) and ids else ids or "").strip()
        if not vod_id:
            return {"list": []}
        data = self._request_json({"ac": "videolist", "ids": vod_id})
        items = data.get("list", [])
        if not items:
            return {"list": []}
        item = items[0] or {}
        play_from, play_url = self._parse_play_groups(item.get("vod_play_from", ""), item.get("vod_play_url", ""))
        return {
            "list": [
                {
                    "vod_id": str(item.get("vod_id", vod_id)),
                    "vod_name": str(item.get("vod_name", "")),
                    "vod_pic": self._get_pic_url(item.get("vod_pic", "")),
                    "type_name": str(item.get("type_name", "")),
                    "vod_year": str(item.get("vod_year", "")),
                    "vod_area": str(item.get("vod_area", "")),
                    "vod_remarks": str(item.get("vod_remarks", "")),
                    "vod_actor": str(item.get("vod_actor", "")),
                    "vod_director": str(item.get("vod_director", "")),
                    "vod_content": str(item.get("vod_content", "")).strip(),
                    "vod_play_from": play_from,
                    "vod_play_url": play_url,
                }
            ]
        }

    def _is_direct_media_url(self, value):
        raw = str(value or "").lower()
        for suffix in (".m3u8", ".mp4", ".flv", ".avi", ".mkv", ".ts"):
            if suffix in raw:
                return True
        return False

    def playerContent(self, flag, id, vipFlags):
        play_id = str(id or "").strip()
        if not play_id:
            return {"parse": 0, "playUrl": "", "url": "", "header": {}}
        if self._is_direct_media_url(play_id):
            return {"parse": 0, "playUrl": "", "url": play_id, "header": {}}
        return {"parse": 1, "playUrl": "", "url": play_id, "header": {}}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd py && python -m unittest tests.test_如意资源.TestRuYiSpider.test_detail_content_maps_metadata_and_play_groups tests.test_如意资源.TestRuYiSpider.test_detail_content_returns_empty_for_blank_id tests.test_如意资源.TestRuYiSpider.test_parse_play_groups_skips_invalid_entries_and_fills_missing_names tests.test_如意资源.TestRuYiSpider.test_player_content_returns_direct_media_url tests.test_如意资源.TestRuYiSpider.test_player_content_returns_parser_url_for_non_media_link -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add py/如意资源.py py/tests/test_如意资源.py
git commit -m "feat: add ruyi detail and player parsing"
```

### Task 3: Harden Empty Paths, Invalid JSON, And Final Verification

**Files:**
- Modify: `py/tests/test_如意资源.py`
- Modify: `py/如意资源.py`

- [ ] **Step 1: Write the failing test**

```python
    @patch.object(Spider, "fetch")
    def test_request_json_returns_empty_dict_when_all_apis_fail(self, mock_fetch):
        mock_fetch.side_effect = [
            FakeResponse(status_code=500, text=""),
            FakeResponse(status_code=200, text="{bad json"),
            FakeResponse(status_code=404, text=""),
        ]
        self.assertEqual(self.spider._request_json({"ac": "list"}), {})

    @patch.object(Spider, "_request_json")
    def test_home_video_content_filters_invalid_vod_rows(self, mock_request_json):
        mock_request_json.return_value = {
            "list": [
                {"vod_id": "0", "vod_name": "无效", "vod_pic": "", "vod_remarks": "", "vod_year": "", "type_id": ""},
                {"vod_id": "", "vod_name": "空ID", "vod_pic": "", "vod_remarks": "", "vod_year": "", "type_id": ""},
                {"vod_id": "501", "vod_name": "", "vod_pic": "null", "vod_remarks": "", "vod_year": "2022", "type_id": "7"},
            ]
        }
        result = self.spider.homeVideoContent()
        self.assertEqual(result["list"], [
            {
                "vod_id": "501",
                "vod_name": "未知标题",
                "vod_pic": "",
                "vod_remarks": "2022",
                "vod_year": "2022",
                "type_id": "7",
            }
        ])

    def test_player_content_returns_empty_payload_for_blank_id(self):
        self.assertEqual(
            self.spider.playerContent("如意线路", "", {}),
            {"parse": 0, "playUrl": "", "url": "", "header": {}},
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd py && python -m unittest tests.test_如意资源.TestRuYiSpider.test_request_json_returns_empty_dict_when_all_apis_fail tests.test_如意资源.TestRuYiSpider.test_home_video_content_filters_invalid_vod_rows tests.test_如意资源.TestRuYiSpider.test_player_content_returns_empty_payload_for_blank_id -v`
Expected: FAIL if `_request_json` leaks exceptions or `_format_vod_list` keeps invalid rows

- [ ] **Step 3: Write minimal implementation**

```python
    def _request_json(self, params=None, url=""):
        if url:
            targets = [url]
        else:
            query = self._build_query(params)
            targets = [f"{base}?{query}" if query else base for base in self.api_urls]
        for target in targets:
            try:
                response = self.fetch(target, headers=self.headers, timeout=10)
            except Exception:
                continue
            if response.status_code != 200:
                continue
            try:
                return json.loads(response.text or "{}")
            except Exception:
                continue
        return {}

    def _format_vod_list(self, items):
        result = []
        for item in items or []:
            current = item or {}
            vod_id = str(current.get("vod_id", "")).strip()
            if not vod_id or vod_id == "0":
                continue
            vod_year = str(current.get("vod_year", "")).strip()
            result.append(
                {
                    "vod_id": vod_id,
                    "vod_name": str(current.get("vod_name", "")).strip() or "未知标题",
                    "vod_pic": self._get_pic_url(current.get("vod_pic", "")),
                    "vod_remarks": str(current.get("vod_remarks", "")).strip() or vod_year,
                    "vod_year": vod_year,
                    "type_id": str(current.get("type_id", "")).strip(),
                }
            )
        return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd py && python -m unittest tests.test_如意资源.TestRuYiSpider.test_request_json_returns_empty_dict_when_all_apis_fail tests.test_如意资源.TestRuYiSpider.test_home_video_content_filters_invalid_vod_rows tests.test_如意资源.TestRuYiSpider.test_player_content_returns_empty_payload_for_blank_id -v`
Expected: PASS

- [ ] **Step 5: Run full module test suite**

Run: `cd py && python -m unittest tests.test_如意资源 -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add py/如意资源.py py/tests/test_如意资源.py
git commit -m "feat: finalize ruyi spider"
```
