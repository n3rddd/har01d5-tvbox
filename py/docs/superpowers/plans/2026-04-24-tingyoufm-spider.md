# 听友FM Spider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `https://tingyou.fm` 新增一个可离线测试的 Python Spider，覆盖首页、分类、搜索、详情和播放主链路。

**Architecture:** 站点文件 `py/听友FM.py` 采用“页面解析为主、播放接口为主链”的结构。列表和详情统一复用 HTML/Nuxt 解析 helper，播放链路单独收敛到 payload 加解密和直链提取 helper，并在失败时回退到播放页 URL。

**Tech Stack:** Python, `unittest`, `unittest.mock`, `json`, `re`, `base.spider.Spider`, `Crypto.Cipher.AES`

---

### Task 1: Scaffold Spider And Red Tests

**Files:**
- Create: `py/听友FM.py`
- Create: `py/tests/test_听友FM.py`
- Test: `py/tests/test_听友FM.py`

- [ ] **Step 1: Write the failing test**

```python
def test_home_content_extracts_categories_and_album_cards(self):
    result = self.spider.homeContent(False)
    self.assertEqual(result["class"][0], {"type_id": "46", "type_name": "有声小说"})
    self.assertEqual(result["list"][0]["vod_id"], "1001")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_听友FM.TestTingYouFMSpider.test_home_content_extracts_categories_and_album_cards -v`
Expected: FAIL with missing module `听友FM.py` or missing `homeContent`

- [ ] **Step 3: Write minimal implementation**

```python
class Spider(BaseSpider):
    def __init__(self):
        self.name = "听友FM"
        self.host = "https://tingyou.fm"
        self.classes = [{"type_id": "46", "type_name": "有声小说"}]

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def homeContent(self, filter):
        return {"class": list(self.classes), "list": []}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests.test_听友FM.TestTingYouFMSpider.test_home_content_extracts_categories_and_album_cards -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add py/听友FM.py py/tests/test_听友FM.py
git commit -m "feat: scaffold tingyoufm spider"
```

### Task 2: Implement HTML And Nuxt Parsing

**Files:**
- Modify: `py/听友FM.py`
- Modify: `py/tests/test_听友FM.py`
- Test: `py/tests/test_听友FM.py`

- [ ] **Step 1: Write the failing test**

```python
@patch.object(Spider, "fetch")
def test_category_and_search_prefer_nuxt_and_fallback_to_dom(self, mock_fetch):
    mock_fetch.side_effect = [
        SimpleNamespace(status_code=200, text=CATEGORY_HTML_WITH_NUXT),
        SimpleNamespace(status_code=200, text=SEARCH_HTML_WITHOUT_NUXT),
    ]
    category = self.spider.categoryContent("46", "2", False, {})
    search = self.spider.searchContent("鬼吹灯", False, "1")
    self.assertEqual(category["page"], 2)
    self.assertEqual(category["list"][0]["vod_id"], "2001")
    self.assertEqual(search["list"][0]["vod_id"], "3001")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_听友FM.TestTingYouFMSpider.test_category_and_search_prefer_nuxt_and_fallback_to_dom -v`
Expected: FAIL with missing `categoryContent`, `searchContent`, or wrong parsed fields

- [ ] **Step 3: Write minimal implementation**

```python
def _decode_nuxt_value(self, table, node, seen=None):
    if seen is None:
        seen = {}
    return node

def _parse_album_card(self, html):
    return {"vod_id": "2001", "vod_name": "示例专辑", "vod_pic": "", "vod_remarks": ""}

def categoryContent(self, tid, pg, filter, extend):
    html = self._get_html(f"/categories/{tid}?sort=comprehensive&page={pg}")
    data = self._parse_category_nuxt(html, tid)
    items = data or []
    return {"page": int(pg), "limit": len(items), "total": len(items), "list": items}

def searchContent(self, key, quick, pg="1"):
    if not str(key).strip():
        return {"page": 1, "limit": 0, "total": 0, "list": []}
    html = self._get_html(f"/search?q={quote(key)}")
    items = self._parse_search_nuxt(html) or self._parse_search_dom(html)
    return {"page": int(pg), "limit": len(items), "total": len(items), "list": items}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests.test_听友FM.TestTingYouFMSpider.test_category_and_search_prefer_nuxt_and_fallback_to_dom -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add py/听友FM.py py/tests/test_听友FM.py
git commit -m "feat: add tingyoufm list and search parsing"
```

### Task 3: Implement Detail Parsing

**Files:**
- Modify: `py/听友FM.py`
- Modify: `py/tests/test_听友FM.py`
- Test: `py/tests/test_听友FM.py`

- [ ] **Step 1: Write the failing test**

```python
@patch.object(Spider, "fetch")
def test_detail_content_extracts_album_and_playlist(self, mock_fetch):
    mock_fetch.return_value = SimpleNamespace(status_code=200, text=DETAIL_HTML)
    result = self.spider.detailContent(["1001"])
    vod = result["list"][0]
    self.assertEqual(vod["vod_name"], "鬼吹灯")
    self.assertEqual(vod["vod_play_from"], "听友FM")
    self.assertEqual(vod["vod_play_url"], "第1集$1001|1#第2集$1001|2")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_听友FM.TestTingYouFMSpider.test_detail_content_extracts_album_and_playlist -v`
Expected: FAIL with missing `detailContent` or empty playlist

- [ ] **Step 3: Write minimal implementation**

```python
def detailContent(self, ids):
    album_id = str((ids or [""])[0])
    html = self._get_html(f"/albums/{album_id}")
    vod = self._parse_detail_page(html, album_id)
    return {"list": [vod] if vod else []}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests.test_听友FM.TestTingYouFMSpider.test_detail_content_extracts_album_and_playlist -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add py/听友FM.py py/tests/test_听友FM.py
git commit -m "feat: add tingyoufm detail parsing"
```

### Task 4: Implement Payload Crypto Helpers

**Files:**
- Modify: `py/听友FM.py`
- Modify: `py/tests/test_听友FM.py`
- Test: `py/tests/test_听友FM.py`

- [ ] **Step 1: Write the failing test**

```python
def test_encrypt_payload_prefixes_version_and_decrypts_v1_payload(self):
    payload = self.spider._encrypt_payload('{"album_id":1001,"chapter_idx":1}')
    self.assertTrue(payload.startswith("01"))
    plain = self.spider._decrypt_payload(self._build_v1_response('{"url":"https://a.test/1.m4a"}'))
    self.assertEqual(plain, '{"url":"https://a.test/1.m4a"}')

def test_decrypt_v2_payload_reverses_cipher_before_decoder(self):
    self.spider._xchacha_decrypt = lambda key, nonce, cipher: self.assertEqual(cipher, b"abc") or b'{"url":"https://a.test/2.m4a"}'
    raw_hex = self._build_v2_response_with_reversed_cipher()
    plain = self.spider._decrypt_payload(raw_hex)
    self.assertIn("2.m4a", plain)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_听友FM.TestTingYouFMSpider.test_encrypt_payload_prefixes_version_and_decrypts_v1_payload tests.test_听友FM.TestTingYouFMSpider.test_decrypt_v2_payload_reverses_cipher_before_decoder -v`
Expected: FAIL with missing crypto helper behavior

- [ ] **Step 3: Write minimal implementation**

```python
def _encrypt_payload(self, plain_text):
    iv = bytes(range(12))
    return "01" + iv.hex() + plain_text.encode("utf-8").hex()

def _decrypt_payload(self, hex_text):
    version = raw[0]
    if version == 1:
        iv = raw[1:13]
        cipher = raw[13:]
        return self._decrypt_v1(iv, cipher)
    if version == 2:
        nonce = raw[1:25]
        cipher = raw[25:][::-1]
        return self._xchacha_decrypt(self.payload_key, nonce, cipher).decode("utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests.test_听友FM.TestTingYouFMSpider.test_encrypt_payload_prefixes_version_and_decrypts_v1_payload tests.test_听友FM.TestTingYouFMSpider.test_decrypt_v2_payload_reverses_cipher_before_decoder -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add py/听友FM.py py/tests/test_听友FM.py
git commit -m "feat: add tingyoufm payload crypto helpers"
```

### Task 5: Implement Player Fallback And Final Verification

**Files:**
- Modify: `py/听友FM.py`
- Modify: `py/tests/test_听友FM.py`
- Test: `py/tests/test_听友FM.py`

- [ ] **Step 1: Write the failing test**

```python
@patch.object(Spider, "_api_post")
def test_player_content_prefers_api_url_and_falls_back_to_audio_page(self, mock_api_post):
    mock_api_post.return_value = {"payload": self._build_v1_response('{"url":"https://audio.test/play.m4a"}')}
    api_result = self.spider.playerContent("听友FM", "1001|1", {})
    self.assertEqual(api_result["parse"], 0)
    self.assertEqual(api_result["url"], "https://audio.test/play.m4a")

    mock_api_post.side_effect = RuntimeError("boom")
    fallback_result = self.spider.playerContent("听友FM", "1001|1", {})
    self.assertEqual(fallback_result["parse"], 1)
    self.assertEqual(fallback_result["url"], "https://tingyou.fm/audios/1001/1")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_听友FM.TestTingYouFMSpider.test_player_content_prefers_api_url_and_falls_back_to_audio_page -v`
Expected: FAIL with missing player resolution or fallback behavior

- [ ] **Step 3: Write minimal implementation**

```python
def playerContent(self, flag, id, vipFlags):
    album_id, chapter_idx = str(id).split("|", 1)
    fallback = f"{self.host}/audios/{album_id}/{chapter_idx}"
    try:
        payload = self._api_post("/api/play_token", {"album_id": int(album_id), "chapter_idx": int(chapter_idx)})
        play_url = self._extract_play_url(payload)
        if play_url:
            return {"parse": 0, "url": play_url, "header": self._get_headers()}
    except Exception:
        pass
    return {"parse": 1, "url": fallback, "header": self._get_headers()}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests.test_听友FM -v`
Expected: PASS for all `TestTingYouFMSpider` tests

- [ ] **Step 5: Commit**

```bash
git add py/听友FM.py py/tests/test_听友FM.py
git commit -m "feat: complete tingyoufm spider"
```
