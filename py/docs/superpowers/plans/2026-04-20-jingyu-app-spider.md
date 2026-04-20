# 鲸鱼APP Spider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the 鲸鱼APP JS TVBox T4 plugin to a Python spider following existing repo patterns.

**Architecture:** Single-file spider (`鲸鱼APP.py`) inheriting `base.spider.Spider`. Uses AES-CBC encryption for API communication. Dynamic host fetched from COS URL at init time. Categories/filters pulled from init API. Play parsing supports 4 modes (direct, prefix, fetch, vodParse).

**Tech Stack:** Python 3.14, pycryptodome (AES-CBC), requests, unittest+mock for tests

---

## File Structure

- **Create:** `py/鲸鱼APP.py` — spider implementation (single file, ~350 lines)
- **Create:** `py/tests/test_鲸鱼APP.py` — unit tests

---

### Task 1: AES encrypt/decrypt helpers

**Files:**
- Create: `py/鲸鱼APP.py`
- Test: `py/tests/test_鲸鱼APP.py`

- [ ] **Step 1: Write failing test for AES round-trip**

```python
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("jingyu_spider", str(ROOT / "鲸鱼APP.py")).load_module()
Spider = MODULE.Spider


class TestJingyuSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()

    def test_aes_encrypt_decrypt_roundtrip(self):
        plaintext = '{"key":"value"}'
        encrypted = self.spider._aes_encrypt(plaintext)
        decrypted = self.spider._aes_decrypt(encrypted)
        self.assertEqual(decrypted, plaintext)

    def test_aes_encrypt_produces_base64(self):
        import re
        encrypted = self.spider._aes_encrypt("hello")
        self.assertTrue(re.match(r'^[A-Za-z0-9+/=]+$', encrypted))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/harold/workspace/tvbox-resources/py && python -m unittest tests.test_鲸鱼APP -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write spider skeleton with AES helpers**

Create `py/鲸鱼APP.py`:

```python
# coding=utf-8
import base64
import json
import re
import sys
import time

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from base.spider import Spider as BaseSpider

sys.path.append("..")

AES_KEY = "AAdgrdghjfgsABC1"
AES_IV = "AAdgrdghjfgsABC1"


class Spider(BaseSpider):
    def __init__(self):
        self.name = "鲸鱼APP"
        self.host = ""
        self.ua = "okhttp/3.10.0"
        self.api_path = "/api.php/qijiappapi.index"
        self.init_endpoint = "initV122"
        self.search_endpoint = "searchList"
        self.search_verify = False
        self.init_data = None

    def getName(self):
        return self.name

    def init(self, extend=""):
        pass

    def _aes_encrypt(self, plaintext):
        key = AES_KEY.encode("utf-8")
        iv = AES_IV.encode("utf-8")
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded = pad(plaintext.encode("utf-8"), AES.block_size)
        encrypted = cipher.encrypt(padded)
        return base64.b64encode(encrypted).decode("utf-8")

    def _aes_decrypt(self, ciphertext):
        key = AES_KEY.encode("utf-8")
        iv = AES_IV.encode("utf-8")
        raw = base64.b64decode(ciphertext)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(raw), AES.block_size)
        return decrypted.decode("utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/harold/workspace/tvbox-resources/py && python -m unittest tests.test_鲸鱼APP -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add py/鲸鱼APP.py py/tests/test_鲸鱼APP.py
git commit -m "feat: add 鲸鱼APP spider skeleton with AES helpers"
```

---

### Task 2: API request helper (`_api_post`)

**Files:**
- Modify: `py/鲸鱼APP.py`
- Test: `py/tests/test_鲸鱼APP.py`

- [ ] **Step 1: Write failing test for `_api_post`**

Append to `py/tests/test_鲸鱼APP.py`:

```python
    def test_api_post_decrypts_response(self):
        # Encrypt a known JSON payload
        payload = {"result": "ok"}
        encrypted = self.spider._aes_encrypt(json.dumps(payload))

        class FakeResponse:
            status_code = 200
            encoding = "utf-8"
            def json(self):
                return {"data": encrypted}

        def fake_post(url, **kwargs):
            return FakeResponse()

        self.spider.post = fake_post
        self.spider.host = "http://test.com"
        result = self.spider._api_post("someEndpoint")
        self.assertEqual(result, payload)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/harold/workspace/tvbox-resources/py && python -m unittest tests.test_鲸鱼APP.TestJingyuSpider.test_api_post_decrypts_response -v`
Expected: FAIL — AttributeError

- [ ] **Step 3: Implement `_api_post`**

Append to `py/鲸鱼APP.py` inside the `Spider` class, after `_aes_decrypt`:

```python
    def _api_post(self, endpoint, payload=None):
        if payload is None:
            payload = {}
        ep = f"/{endpoint}" if not endpoint.startswith("/") else endpoint
        url = f"{self.host}{self.api_path}{ep}"
        headers = {
            "User-Agent": self.ua,
            "Accept-Encoding": "gzip",
        }
        rsp = self.post(url, json=payload, headers=headers, timeout=15, verify=False)
        data = rsp.json().get("data")
        if not data:
            return None
        try:
            return json.loads(self._aes_decrypt(data))
        except Exception as e:
            self.log(f"JSON解析失败: {e}")
            return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/harold/workspace/tvbox-resources/py && python -m unittest tests.test_鲸鱼APP -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add py/鲸鱼APP.py py/tests/test_鲸鱼APP.py
git commit -m "feat: add _api_post with encrypted API communication"
```

---

### Task 3: Init and host resolution

**Files:**
- Modify: `py/鲸鱼APP.py`
- Test: `py/tests/test_鲸鱼APP.py`

- [ ] **Step 1: Write failing test for init**

Append to test file:

```python
    def test_init_fetches_host_from_site_url(self):
        init_encrypted = self.spider._aes_encrypt(json.dumps({"type_list": []}))

        class FakeInitResponse:
            status_code = 200
            encoding = "utf-8"
            text = "http://example.com"
            def json(self):
                return {"data": init_encrypted}

        call_count = {"n": 0}

        def fake_fetch(url, **kwargs):
            return FakeInitResponse()

        def fake_post(url, **kwargs):
            call_count["n"] += 1
            return FakeInitResponse()

        self.spider.fetch = fake_fetch
        self.spider.post = fake_post
        self.spider.init()
        self.assertEqual(self.spider.host, "http://example.com")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/harold/workspace/tvbox-resources/py && python -m unittest tests.test_鲸鱼APP.TestJingyuSpider.test_init_fetches_host_from_site_url -v`
Expected: FAIL

- [ ] **Step 3: Implement `init` method**

Replace the existing `init` method in `py/鲸鱼APP.py`:

```python
    SITE_URL = "https://jingyu4k-1312635929.cos.ap-nanjing.myqcloud.com/juyu3.json"

    def init(self, extend=""):
        if self.host:
            return
        headers = {"User-Agent": self.ua}
        try:
            rsp = self.fetch(self.SITE_URL, headers=headers, timeout=10, verify=False)
            host = rsp.text.strip().rstrip("/")
            if not host.startswith("http"):
                host = "http://" + host
            self.host = host
        except Exception as e:
            self.log(f"获取host失败: {e}")
            raise
        try:
            data = self._api_post(self.init_endpoint)
            if data and data.get("config", {}).get("system_search_verify_status"):
                self.search_verify = True
            self.init_data = data
        except Exception as e:
            self.log(f"初始化数据失败: {e}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/harold/workspace/tvbox-resources/py && python -m unittest tests.test_鲸鱼APP -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add py/鲸鱼APP.py py/tests/test_鲸鱼APP.py
git commit -m "feat: add init with host resolution and search verify check"
```

---

### Task 4: Category management and homeContent

**Files:**
- Modify: `py/鲸鱼APP.py`
- Test: `py/tests/test_鲸鱼APP.py`

- [ ] **Step 1: Write failing tests for category processing**

Append to test file:

```python
    def test_process_classes_blocks_and_sorts(self):
        type_list = [
            {"type_id": "0", "type_name": "全部"},
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "3", "type_name": "综艺"},
            {"type_id": "2", "type_name": "电视剧"},
            {"type_id": "4", "type_name": "动漫"},
        ]
        classes = self.spider._process_classes(type_list)
        names = [c["type_name"] for c in classes]
        self.assertNotIn("全部", names)
        self.assertEqual(names, ["电影", "电视剧", "综艺", "动漫"])

    def test_process_area_filter_merges_mainland_areas(self):
        areas = ["全部", "中国大陆", "大陆", "内地", "美国", "日本"]
        result = self.spider._process_area_filter(areas)
        self.assertIn("大陆", result)
        self.assertNotIn("中国大陆", result)
        self.assertNotIn("内地", result)
        self.assertIn("美国", result)

    def test_convert_filters_adds_current_year(self):
        import datetime
        type_list = [{
            "type_id": "1",
            "filter_type_list": [
                {"name": "year", "list": ["全部", "2024"]},
                {"name": "area", "list": ["全部", "中国大陆"]},
            ]
        }]
        current = str(datetime.datetime.now().year)
        filters = self.spider._convert_filters(type_list)
        year_values = [v["v"] for v in filters["1"][0]["value"]]
        self.assertIn(current, year_values)
        area_values = [v["v"] for v in filters["1"][1]["value"]]
        self.assertIn("大陆", area_values)
        self.assertNotIn("中国大陆", area_values)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/harold/workspace/tvbox-resources/py && python -m unittest tests.test_鲸鱼APP -v`
Expected: FAIL — missing methods

- [ ] **Step 3: Implement category helpers and homeContent**

Append to `py/鲸鱼APP.py` inside the class, after `init`:

```python
    CATEGORY_BLOCKED = ["全部"]
    CATEGORY_FORCE_ORDER = ["电影", "电视剧", "综艺", "动漫", "短剧"]
    AREA_MERGE_DISPLAY = "大陆"
    AREA_MERGE_LIST = ["中国大陆", "大陆", "内地"]

    def _process_classes(self, type_list):
        order_map = {n: i for i, n in enumerate(self.CATEGORY_FORCE_ORDER)}
        classes = [
            {"type_id": t["type_id"], "type_name": t["type_name"]}
            for t in type_list
            if t["type_name"] not in self.CATEGORY_BLOCKED
        ]
        classes.sort(key=lambda c: order_map.get(c["type_name"], 999))
        return classes

    def _process_area_filter(self, area_list):
        if not area_list:
            return area_list
        merge_set = set(self.AREA_MERGE_LIST)
        filtered = [a for a in area_list if a not in merge_set]
        has_merge = any(a in merge_set for a in area_list)
        if has_merge:
            try:
                idx = filtered.index("全部")
                filtered.insert(idx + 1, self.AREA_MERGE_DISPLAY)
            except ValueError:
                filtered.insert(0, self.AREA_MERGE_DISPLAY)
        return filtered

    def _convert_filters(self, type_list):
        name_map = {"class": "类型", "area": "地区", "lang": "语言", "year": "年份", "sort": "排序"}
        current_year = str(time.localtime().tm_year)
        filters = {}
        for t in type_list:
            arr = []
            for f in t.get("filter_type_list", []):
                key = "by" if f["name"] == "sort" else f["name"]
                values = list(f.get("list", []))
                if f["name"] == "area":
                    values = self._process_area_filter(values)
                if f["name"] == "year" and current_year not in values:
                    try:
                        idx = values.index("全部")
                        values.insert(idx + 1, current_year)
                    except ValueError:
                        values.insert(0, current_year)
                arr.append({
                    "key": key,
                    "name": name_map.get(f["name"], f["name"]),
                    "value": [{"n": v, "v": v} for v in values],
                })
            filters[t["type_id"]] = arr
        return filters

    def homeContent(self, filter):
        self.init()
        data = self.init_data
        if not data:
            return {"class": [], "filters": {}}
        classes = self._process_classes(data.get("type_list", []))
        filters = self._convert_filters(data.get("type_list", []))
        return {"class": classes, "filters": filters}

    def homeVideoContent(self):
        self.init()
        if not self.init_data:
            return {"list": []}
        videos = []
        for t in self.init_data.get("type_list", []):
            for item in t.get("recommend_list", []):
                videos.append({
                    "vod_id": str(item.get("vod_id", "")),
                    "vod_name": item.get("vod_name", ""),
                    "vod_pic": item.get("vod_pic", ""),
                    "vod_remarks": item.get("vod_remarks", ""),
                })
        return {"list": videos}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/harold/workspace/tvbox-resources/py && python -m unittest tests.test_鲸鱼APP -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add py/鲸鱼APP.py py/tests/test_鲸鱼APP.py
git commit -m "feat: add category management, area merge, and homeContent"
```

---

### Task 5: categoryContent with area merge

**Files:**
- Modify: `py/鲸鱼APP.py`
- Test: `py/tests/test_鲸鱼APP.py`

- [ ] **Step 1: Write failing test for categoryContent**

Append to test file:

```python
    def test_category_content_posts_filter_payload(self):
        encrypted_empty = self.spider._aes_encrypt(json.dumps({"recommend_list": []}))

        class FakeRsp:
            status_code = 200
            encoding = "utf-8"
            def json(self):
                return {"data": encrypted_empty}

        calls = {}

        def fake_post(url, **kwargs):
            calls.update(kwargs)
            return FakeRsp()

        self.spider.post = fake_post
        self.spider.host = "http://test.com"
        result = self.spider.categoryContent("1", "2", False, {"area": "美国", "year": "2025"})
        self.assertEqual(result["page"], 2)
        self.assertNotIn("pagecount", result)
        self.assertEqual(result["list"], [])

    def test_category_content_merges_area_when_mainland_selected(self):
        items_a = [{"vod_id": "1", "vod_name": "A", "vod_pic": "", "vod_remarks": ""}]
        items_b = [{"vod_id": "2", "vod_name": "B", "vod_pic": "", "vod_remarks": ""},
                    {"vod_id": "1", "vod_name": "A", "vod_pic": "", "vod_remarks": ""}]

        call_idx = {"n": 0}

        def fake_api_post(endpoint, payload=None):
            call_idx["n"] += 1
            if call_idx["n"] == 1:
                return {"recommend_list": items_a}
            return {"recommend_list": items_b}

        self.spider._api_post = fake_api_post
        self.spider.host = "http://test.com"
        result = self.spider.categoryContent("1", "1", False, {"area": "大陆"})
        ids = [v["vod_id"] for v in result["list"]]
        self.assertEqual(len(ids), 2)
        self.assertIn("1", ids)
        self.assertIn("2", ids)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/harold/workspace/tvbox-resources/py && python -m unittest tests.test_鲸鱼APP.TestJingyuSpider.test_category_content_posts_filter_payload -v`
Expected: FAIL

- [ ] **Step 3: Implement categoryContent**

Append to `py/鲸鱼APP.py` inside the class:

```python
    def _merge_area_search(self, type_id, page, base_filters):
        all_results = []
        seen = set()
        for area_val in self.AREA_MERGE_LIST:
            try:
                payload = {"type_id": type_id, "page": page, "area": area_val}
                payload.update(base_filters)
                res = self._api_post("typeFilterVodList", payload)
                for item in (res or {}).get("recommend_list", []):
                    vid = str(item.get("vod_id", ""))
                    if vid not in seen:
                        seen.add(vid)
                        all_results.append({
                            "vod_id": vid,
                            "vod_name": item.get("vod_name", ""),
                            "vod_pic": item.get("vod_pic", ""),
                            "vod_remarks": item.get("vod_remarks", ""),
                        })
            except Exception as e:
                self.log(f"聚合搜索地区[{area_val}]失败: {e}")
        return all_results

    def categoryContent(self, tid, pg, filter, extend):
        self.init()
        page = int(pg)
        ext = extend or {}

        if ext.get("area") == self.AREA_MERGE_DISPLAY:
            base = {k: v for k, v in ext.items() if k != "area"}
            base.setdefault("year", "全部")
            base.setdefault("sort", "最新")
            base.setdefault("lang", "全部")
            base.setdefault("class", "全部")
            merged = self._merge_area_search(tid, page, base)
            return {"list": merged, "page": page, "limit": 90, "total": 999999}

        payload = {
            "type_id": tid,
            "page": page,
            "area": ext.get("area", "全部"),
            "year": ext.get("year", "全部"),
            "sort": ext.get("by", ext.get("sort", "最新")),
            "lang": ext.get("lang", "全部"),
            "class": ext.get("class", "全部"),
        }
        res = self._api_post("typeFilterVodList", payload)
        items = []
        for item in (res or {}).get("recommend_list", []):
            items.append({
                "vod_id": str(item.get("vod_id", "")),
                "vod_name": item.get("vod_name", ""),
                "vod_pic": item.get("vod_pic", ""),
                "vod_remarks": item.get("vod_remarks", ""),
            })
        return {"list": items, "page": page, "limit": 90, "total": 999999}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/harold/workspace/tvbox-resources/py && python -m unittest tests.test_鲸鱼APP -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add py/鲸鱼APP.py py/tests/test_鲸鱼APP.py
git commit -m "feat: add categoryContent with area merge support"
```

---

### Task 6: detailContent with line management

**Files:**
- Modify: `py/鲸鱼APP.py`
- Test: `py/tests/test_鲸鱼APP.py`

- [ ] **Step 1: Write failing test for detailContent**

Append to test file:

```python
    def test_detail_content_builds_play_lines(self):
        detail_data = {
            "vod": {
                "vod_name": "测试影片",
                "vod_pic": "http://pic.jpg",
                "vod_remarks": "HD",
                "vod_content": "简介",
                "vod_actor": "演员张三",
                "vod_director": "导演李四",
                "vod_year": "2025",
                "vod_area": "大陆",
            },
            "vod_play_list": [
                {
                    "player_info": {
                        "show": "线路一",
                        "parse": "http://parse.com/",
                        "player_parse_type": "1",
                        "parse_type": "1",
                    },
                    "urls": [
                        {"name": "第1集", "url": "http://play/1", "token": "tok1"},
                        {"name": "第2集", "url": "http://play/2", "token": "tok2"},
                    ],
                },
            ],
        }

        self.spider._api_post = lambda ep, payload=None: detail_data if "vodDetail" in ep else None
        self.spider.host = "http://test.com"
        result = self.spider.detailContent(["123"])
        vod = result["list"][0]
        self.assertEqual(vod["vod_name"], "测试影片")
        self.assertEqual(vod["vod_year"], "2025年")
        self.assertIn("线路一", vod["vod_play_from"])
        self.assertIn("第1集$", vod["vod_play_url"])
        self.assertIn("第2集$", vod["vod_play_url"])

    def test_detail_content_filters_junk_lines(self):
        detail_data = {
            "vod": {"vod_name": "X", "vod_pic": "", "vod_remarks": "", "vod_content": "",
                    "vod_actor": "", "vod_director": "", "vod_year": "", "vod_area": ""},
            "vod_play_list": [
                {
                    "player_info": {"show": "防走丢群", "parse": "", "player_parse_type": "0", "parse_type": "0"},
                    "urls": [{"name": "链接", "url": "http://x", "token": ""}],
                },
                {
                    "player_info": {"show": "正式线路", "parse": "", "player_parse_type": "0", "parse_type": "0"},
                    "urls": [{"name": "第1集", "url": "http://y", "token": ""}],
                },
            ],
        }

        self.spider._api_post = lambda ep, payload=None: detail_data
        self.spider.host = "http://test.com"
        result = self.spider.detailContent(["1"])
        vod = result["list"][0]
        # 防走丢 line renamed to "1线"
        self.assertIn("1线", vod["vod_play_from"])
        self.assertIn("正式线路", vod["vod_play_from"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/harold/workspace/tvbox-resources/py && python -m unittest tests.test_鲸鱼APP.TestJingyuSpider.test_detail_content_builds_play_lines -v`
Expected: FAIL

- [ ] **Step 3: Implement detailContent**

Append to `py/鲸鱼APP.py` inside the class:

```python
    JUNK_KEYWORDS = ["防走丢", "群", "防失群", "官网"]

    def detailContent(self, ids):
        self.init()
        vod_id = ids[0]
        data = None
        for endpoint in ["vodDetail", "vodDetail2"]:
            try:
                data = self._api_post(endpoint, {"vod_id": vod_id})
                if data:
                    break
            except Exception:
                continue
        if not data:
            return {"list": []}

        vod = data.get("vod", {})
        lines = []
        name_count = {}
        line_id = 1

        for line in data.get("vod_play_list", []):
            info = line.get("player_info", {})
            name = info.get("show", "")

            if any(kw in name for kw in self.JUNK_KEYWORDS):
                name = f"{line_id}线"
                info["show"] = name

            count = name_count.get(name, 0) + 1
            name_count[name] = count
            if count > 1:
                name = f"{name}{count}"
                info["show"] = name

            urls = line.get("urls", [])
            if not urls:
                line_id += 1
                continue

            play_items = []
            for vod in urls:
                payload = ",".join([
                    info.get("parse", ""),
                    vod.get("url", ""),
                    "token+" + vod.get("token", ""),
                    str(info.get("player_parse_type", "")),
                    str(info.get("parse_type", "")),
                ])
                play_items.append(f"{vod.get('name', '')}${name}@@direct@@{payload}")

            if play_items:
                lines.append({
                    "display": name,
                    "urls": "#".join(play_items),
                })
            line_id += 1

        return {
            "list": [{
                "vod_id": vod_id,
                "vod_name": vod.get("vod_name", ""),
                "vod_pic": vod.get("vod_pic", ""),
                "vod_remarks": vod.get("vod_remarks", ""),
                "vod_content": vod.get("vod_content", ""),
                "vod_actor": (vod.get("vod_actor") or "").replace("演员", ""),
                "vod_director": (vod.get("vod_director") or "").replace("导演", ""),
                "vod_year": (vod.get("vod_year") or "") + "年" if vod.get("vod_year") else "",
                "vod_area": vod.get("vod_area", ""),
                "vod_play_from": "$$$".join(l["display"] for l in lines),
                "vod_play_url": "$$$".join(l["urls"] for l in lines),
            }]
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/harold/workspace/tvbox-resources/py && python -m unittest tests.test_鲸鱼APP -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add py/鲸鱼APP.py py/tests/test_鲸鱼APP.py
git commit -m "feat: add detailContent with line management"
```

---

### Task 7: searchContent

**Files:**
- Modify: `py/鲸鱼APP.py`
- Test: `py/tests/test_鲸鱼APP.py`

- [ ] **Step 1: Write failing test for searchContent**

Append to test file:

```python
    def test_search_content_filters_and_maps_results(self):
        search_data = {
            "search_list": [
                {"vod_id": "1", "vod_name": "繁花", "vod_pic": "http://p1.jpg",
                 "vod_remarks": "更新中", "vod_class": "都市", "vod_year": "2024"},
                {"vod_id": "2", "vod_name": "花繁", "vod_pic": "http://p2.jpg",
                 "vod_remarks": "", "vod_class": "屏蔽预留", "vod_year": ""},
            ]
        }

        self.spider._api_post = lambda ep, payload=None: search_data
        self.spider.host = "http://test.com"
        result = self.spider.searchContent("繁花", False, "1")
        self.assertEqual(len(result["list"]), 1)
        self.assertEqual(result["list"][0]["vod_name"], "繁花")
        self.assertNotIn("pagecount", result)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/harold/workspace/tvbox-resources/py && python -m unittest tests.test_鲸鱼APP.TestJingyuSpider.test_search_content_filters_and_maps_results -v`
Expected: FAIL

- [ ] **Step 3: Implement searchContent**

Append to `py/鲸鱼APP.py` inside the class:

```python
    def _get_verify_code(self):
        import uuid
        try:
            uid = str(uuid.uuid4())
            verify_url = f"{self.host}{self.api_path}/verify/create?key={uid}"
            rsp = self.fetch(verify_url, headers={"User-Agent": self.ua},
                             timeout=10, verify=False)
            b64_img = base64.b64encode(rsp.content).decode("utf-8")
            ocr_url = "http://154.222.22.188:9898/ocr/b64/text"
            ocr_rsp = self.post(ocr_url, data=b64_img,
                                headers={"User-Agent": self.ua, "Content-Type": "text/plain"},
                                timeout=10, verify=False)
            code = (ocr_rsp.text or "").strip()
            if not code:
                return None
            replacements = {
                "y": "9", "口": "0", "q": "0", "u": "0", "o": "0",
                ">": "1", "d": "0", "b": "8", "已": "2", "D": "0", "五": "5",
            }
            code = "".join(replacements.get(c, c) for c in code)
            if not re.match(r"^\d{4}$", code):
                return None
            return {"uuid": uid, "code": code}
        except Exception as e:
            self.log(f"验证码获取失败: {e}")
            return None

    def searchContent(self, key, quick, pg="1"):
        self.init()
        payload = {"keywords": key, "type_id": "0", "page": str(pg)}
        if self.search_verify:
            verify = self._get_verify_code()
            if verify:
                payload["code"] = verify["code"]
                payload["key"] = verify["uuid"]
        res = self._api_post(self.search_endpoint, payload)
        if not res:
            return {"list": [], "page": int(pg), "limit": 90, "total": 999999}
        raw = res.get("search_list", [])
        filtered = [i for i in raw if "屏蔽预留" not in (i.get("vod_class") or "").lower()]
        kw = (key or "").strip().lower()
        if kw:
            filtered = [
                i for i in filtered
                if kw in " ".join([
                    i.get("vod_name", ""),
                    i.get("vod_remarks", ""),
                    i.get("vod_class", ""),
                ]).lower()
            ]
        items = [{
            "vod_id": str(i.get("vod_id", "")),
            "vod_name": i.get("vod_name", ""),
            "vod_pic": i.get("vod_pic", ""),
            "vod_remarks": f"{i.get('vod_year', '')} {i.get('vod_class', '')}".strip(),
        } for i in filtered]
        return {"list": items, "page": int(pg), "limit": 90, "total": 999999}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/harold/workspace/tvbox-resources/py && python -m unittest tests.test_鲸鱼APP -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add py/鲸鱼APP.py py/tests/test_鲸鱼APP.py
git commit -m "feat: add searchContent with OCR verification and filtering"
```

---

### Task 8: playerContent with multi-mode parsing

**Files:**
- Modify: `py/鲸鱼APP.py`
- Test: `py/tests/test_鲸鱼APP.py`

- [ ] **Step 1: Write failing tests for playerContent parse modes**

Append to test file:

```python
    def test_player_direct_parse_type_0(self):
        play_id = "线路一@@direct@@http://parse.com,http://video.m3u8,token+t1,1,0"
        result = self.spider.playerContent("线路一", play_id, {})
        self.assertEqual(result["parse"], 0)
        self.assertEqual(result["url"], "http://video.m3u8")

    def test_player_prefix_parse_type_2(self):
        play_id = "线路二@@direct@@http://parse.com,http://video.m3u8,token+t1,1,2"
        result = self.spider.playerContent("线路二", play_id, {})
        self.assertEqual(result["parse"], 1)
        self.assertEqual(result["url"], "http://parse.comhttp://video.m3u8")

    def test_player_vod_parse_default(self):
        play_id = "线路三@@direct@@http://parse.com,http://video.m3u8,token+t1,1,1"
        inner = json.dumps({"url": "http://decrypted.m3u8"})
        encrypted_inner = self.spider._aes_encrypt(json.dumps({"json": inner}))

        class FakeRsp:
            status_code = 200
            encoding = "utf-8"
            def json(self):
                return {"data": encrypted_inner}

        self.spider.post = lambda url, **kwargs: FakeRsp()
        self.spider.host = "http://test.com"
        result = self.spider.playerContent("线路三", play_id, {})
        self.assertEqual(result["parse"], 0)
        self.assertEqual(result["url"], "http://decrypted.m3u8")

    def test_player_fetch_parse_player_parse_type_2(self):
        play_id = "线路四@@direct@@,http://video.m3u8,token+t1,2,1"
        self.spider.fetch = lambda url, **kwargs: type("R", (), {
            "json": lambda s: {"url": "http://fetched.m3u8"}
        })()
        self.spider.host = "http://test.com"
        result = self.spider.playerContent("线路四", play_id, {})
        self.assertEqual(result["parse"], 0)
        self.assertEqual(result["url"], "http://fetched.m3u8")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/harold/workspace/tvbox-resources/py && python -m unittest tests.test_鲸鱼APP.TestJingyuSpider.test_player_direct_parse_type_0 -v`
Expected: FAIL

- [ ] **Step 3: Implement playerContent**

Append to `py/鲸鱼APP.py` inside the class:

```python
    def playerContent(self, flag, id, vipFlags):
        try:
            parts = id.split("@@")
            if len(parts) < 3:
                return {"parse": 0, "jx": 0, "url": ""}
            line_name = parts[0]
            mode = parts[1]
            payload = parts[2]

            arr = payload.split(",")
            if len(arr) < 5:
                return {"parse": 0, "jx": 0, "url": ""}

            parse_api = arr[0]
            kurl = arr[1]
            token = arr[2].replace("token+", "") if arr[2].startswith("token+") else arr[2]
            player_parse_type = arr[3]
            parse_type = arr[4]

            try:
                kurl = __import__("urllib.parse", fromlist=["unquote"]).unquote(kurl)
            except Exception:
                pass

            header = {"User-Agent": "Dalvik/2.1.0 (Linux; Android 14)"}

            # parse_type == '0': direct URL
            if parse_type == "0":
                return {"parse": 0, "jx": 0, "url": kurl, "header": header}

            # parse_type == '2': prefix URL
            if parse_type == "2":
                return {"parse": 1, "jx": 1, "url": parse_api + kurl, "header": header}

            # player_parse_type == '2': fetch parse_api+url
            if player_parse_type == "2":
                try:
                    rsp = self.fetch(parse_api + kurl, headers={"User-Agent": self.ua}, timeout=10, verify=False)
                    fetched = rsp.json()
                    if fetched.get("url"):
                        return {"parse": 0, "jx": 0, "url": fetched["url"]}
                except Exception:
                    pass

            # default: AES encrypt + vodParse
            encrypted_url = self._aes_encrypt(kurl)
            res = self._api_post("vodParse", {
                "parse_api": parse_api,
                "url": encrypted_url,
                "player_parse_type": player_parse_type,
                "token": token,
            })
            if not res or not res.get("json"):
                return {"parse": 0, "jx": 0, "url": ""}
            inner = json.loads(res["json"])
            return {"parse": 0, "jx": 0, "url": inner.get("url", "")}
        except Exception as e:
            self.log(f"播放解析失败: {e}")
            return {"parse": 0, "jx": 0, "url": ""}
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `cd /home/harold/workspace/tvbox-resources/py && python -m unittest tests.test_鲸鱼APP -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add py/鲸鱼APP.py py/tests/test_鲸鱼APP.py
git commit -m "feat: add playerContent with multi-mode play parsing"
```

---

### Task 9: Run full test suite and final verification

**Files:**
- Verify: `py/鲸鱼APP.py`
- Verify: `py/tests/test_鲸鱼APP.py`

- [ ] **Step 1: Run full project test suite to check for regressions**

Run: `cd /home/harold/workspace/tvbox-resources/py && python -m unittest discover -v -s tests`
Expected: ALL PASS, no regressions in other spider tests

- [ ] **Step 2: Run only 鲸鱼APP tests**

Run: `cd /home/harold/workspace/tvbox-resources/py && python -m unittest tests.test_鲸鱼APP -v`
Expected: ALL PASS

- [ ] **Step 3: Final commit if any fixes needed**

```bash
git add -A
git commit -m "feat: finalize 鲸鱼APP spider"
```
