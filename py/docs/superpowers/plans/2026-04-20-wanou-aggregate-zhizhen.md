# 玩偶聚合接入至臻 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 `玩偶聚合` 蜘蛛中正式接入 `至臻` 站点，使其参与首页展示、分类访问、搜索聚合和详情网盘线路合并。

**Architecture:** 继续沿用 `py/玩偶聚合.py` 的配置驱动结构，不新增共享基类，只补 `zhizhen` 站点配置并扩充测试覆盖。实现顺序遵循 TDD：先写失败测试锁定首页、搜索 URL 和详情合并行为，再做最小配置改动直至 `tests.test_玩偶聚合` 转绿。

**Tech Stack:** Python 3, `unittest`, `unittest.mock`, `base.spider.Spider`, `re`, `json`, `base64`

---

## File Structure

- Modify: `py/玩偶聚合.py`
  - 在 `self.sites` 中新增 `zhizhen` 站点配置
  - 复用现有聚合逻辑，不改编码格式和公共 helper 接口
- Modify: `py/tests/test_玩偶聚合.py`
  - 新增 `site_zhizhen` 首页暴露测试
  - 新增 `zhizhen` 搜索 URL 与结果编码测试
  - 新增聚合详情合并 `至臻` 网盘线路测试

### Task 1: Lock HomeContent And Search Expectations For 至臻

**Files:**
- Modify: `py/tests/test_玩偶聚合.py`
- Modify: `py/玩偶聚合.py`

- [ ] **Step 1: Write the failing test**

```python
    def test_home_content_exposes_zhizhen_site_and_categories(self):
        content = self.spider.homeContent(False)
        type_ids = [item["type_id"] for item in content["class"]]
        self.assertIn("site_zhizhen", type_ids)
        self.assertEqual(
            content["filters"]["site_zhizhen"][0]["value"][1:],
            [
                {"n": "电影", "v": "1"},
                {"n": "剧集", "v": "2"},
                {"n": "动漫", "v": "3"},
                {"n": "综艺", "v": "4"},
                {"n": "短剧", "v": "5"},
                {"n": "老剧", "v": "24"},
                {"n": "严选", "v": "26"},
            ],
        )

    @patch.object(Spider, "_request_with_failover")
    def test_fetch_site_search_builds_zhizhen_search_url_and_parses_results(self, mock_request_with_failover):
        mock_request_with_failover.return_value = """
        <div class="module-search-item">
          <a class="video-serial" href="/index.php/vod/detail/id/789.html" title="至臻影片">抢先版</a>
          <div class="module-item-pic"><img data-src="/search.jpg" alt="至臻影片" /></div>
        </div>
        """
        site = self.spider._get_site("zhizhen")
        results = self.spider._fetch_site_search(site, "繁花", 1)
        self.assertEqual(
            mock_request_with_failover.call_args.args[1],
            "/index.php/vod/search/page/1/wd/%E7%B9%81%E8%8A%B1.html",
        )
        self.assertEqual(
            results[0],
            {
                "vod_id": "site:zhizhen:/index.php/vod/detail/id/789.html",
                "vod_name": "至臻影片",
                "vod_pic": "http://www.miqk.cc/search.jpg",
                "vod_remarks": "",
                "vod_year": "",
                "_site": "zhizhen",
                "_detail_path": "/index.php/vod/detail/id/789.html",
            },
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run from `py/`: `python -m unittest tests.test_玩偶聚合.TestWanouAggregateSpider.test_home_content_exposes_zhizhen_site_and_categories tests.test_玩偶聚合.TestWanouAggregateSpider.test_fetch_site_search_builds_zhizhen_search_url_and_parses_results -v`
Expected: FAIL because `site_zhizhen` is absent and `_get_site("zhizhen")` returns `None`.

- [ ] **Step 3: Write minimal implementation**

```python
            {
                "id": "zhizhen",
                "name": "至臻",
                "domains": ["http://www.miqk.cc"],
                "filter_files": [],
                "list_xpath": "//*[contains(@class,'module-item')]",
                "search_xpath": "//*[contains(@class,'module-search-item')]",
                "detail_pan_xpath": "//*[contains(@class,'module-row-info')]//p",
                "category_url": "/index.php/vod/show/id/{categoryId}/page/{page}.html",
                "search_url": "/index.php/vod/search/page/{page}/wd/{keyword}.html",
                "default_categories": [
                    ("1", "电影"),
                    ("2", "剧集"),
                    ("3", "动漫"),
                    ("4", "综艺"),
                    ("5", "短剧"),
                    ("24", "老剧"),
                    ("26", "严选"),
                ],
            },
```

- [ ] **Step 4: Run test to verify it passes**

Run from `py/`: `python -m unittest tests.test_玩偶聚合.TestWanouAggregateSpider.test_home_content_exposes_zhizhen_site_and_categories tests.test_玩偶聚合.TestWanouAggregateSpider.test_fetch_site_search_builds_zhizhen_search_url_and_parses_results -v`
Expected: PASS with `site_zhizhen` visible and search URL/path matching the `miqk` rule.

- [ ] **Step 5: Commit**

```bash
git add py/玩偶聚合.py py/tests/test_玩偶聚合.py
git commit -m "feat: add zhizhen aggregate site config"
```

### Task 2: Lock Detail Merge Behavior For 至臻 Lines

**Files:**
- Modify: `py/tests/test_玩偶聚合.py`
- Modify: `py/玩偶聚合.py`

- [ ] **Step 1: Write the failing test**

```python
    @patch.object(Spider, "_fetch_site_detail")
    def test_detail_content_for_aggregate_id_merges_zhizhen_pan_lines(self, mock_fetch_site_detail):
        mock_fetch_site_detail.side_effect = [
            {
                "vod_name": "繁花",
                "vod_pic": "https://img.example/w.jpg",
                "vod_year": "2024",
                "vod_director": "导演甲",
                "vod_actor": "演员甲",
                "vod_content": "玩偶简介",
                "pan_urls": ["https://pan.baidu.com/s/b1"],
                "_site_name": "玩偶",
            },
            {
                "vod_name": "繁花",
                "vod_pic": "http://www.miqk.cc/poster.jpg",
                "vod_year": "2024",
                "vod_director": "导演乙",
                "vod_actor": "演员乙",
                "vod_content": "至臻简介",
                "pan_urls": ["https://pan.quark.cn/s/z1", "https://pan.baidu.com/s/b1"],
                "_site_name": "至臻",
            },
        ]
        payload = [
            {"site": "wanou", "path": "/voddetail/1.html", "name": "繁花", "year": "2024"},
            {"site": "zhizhen", "path": "/index.php/vod/detail/id/2.html", "name": "繁花", "year": "2024"},
        ]
        result = self.spider.detailContent([self.spider._encode_aggregate_vod_id(payload)])
        vod = result["list"][0]
        self.assertEqual(vod["vod_name"], "繁花")
        self.assertEqual(vod["vod_play_from"], "baidu#玩偶$$$quark#至臻")
        self.assertEqual(
            vod["vod_play_url"],
            "百度资源$https://pan.baidu.com/s/b1$$$夸克资源$https://pan.quark.cn/s/z1",
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run from `py/`: `python -m unittest tests.test_玩偶聚合.TestWanouAggregateSpider.test_detail_content_for_aggregate_id_merges_zhizhen_pan_lines -v`
Expected: FAIL before Task 1 is implemented because `zhizhen` site lookup is missing or detail merge path cannot resolve it.

- [ ] **Step 3: Write minimal implementation**

```python
        self.sites = [
            # existing wanou / muou / labi configs...
            {
                "id": "zhizhen",
                "name": "至臻",
                "domains": ["http://www.miqk.cc"],
                "filter_files": [],
                "list_xpath": "//*[contains(@class,'module-item')]",
                "search_xpath": "//*[contains(@class,'module-search-item')]",
                "detail_pan_xpath": "//*[contains(@class,'module-row-info')]//p",
                "category_url": "/index.php/vod/show/id/{categoryId}/page/{page}.html",
                "search_url": "/index.php/vod/search/page/{page}/wd/{keyword}.html",
                "default_categories": [
                    ("1", "电影"),
                    ("2", "剧集"),
                    ("3", "动漫"),
                    ("4", "综艺"),
                    ("5", "短剧"),
                    ("24", "老剧"),
                    ("26", "严选"),
                ],
            },
        ]
```

这一步不需要再改 `detailContent` 逻辑，只要确保 `zhizhen` 站点能被 `_get_site` 和 `_fetch_site_detail` 走通即可。

- [ ] **Step 4: Run test to verify it passes**

Run from `py/`: `python -m unittest tests.test_玩偶聚合.TestWanouAggregateSpider.test_detail_content_for_aggregate_id_merges_zhizhen_pan_lines -v`
Expected: PASS and duplicate百度链接被去重，只保留 `至臻` 的夸克线路增量。

- [ ] **Step 5: Commit**

```bash
git add py/玩偶聚合.py py/tests/test_玩偶聚合.py
git commit -m "test: cover zhizhen aggregate detail merge"
```

### Task 3: Run Full 玩偶聚合 Verification

**Files:**
- Modify: `py/tests/test_玩偶聚合.py`
- Modify: `py/玩偶聚合.py`

- [ ] **Step 1: Write the failing test**

```python
    @patch.object(Spider, "_request_with_failover")
    def test_category_content_builds_zhizhen_category_url(self, mock_request_with_failover):
        mock_request_with_failover.return_value = """
        <div class="module-item">
          <div class="module-item-pic">
            <a href="/index.php/vod/detail/id/456.html"></a>
            <img data-src="/cate.jpg" alt="至臻分类片" />
          </div>
          <div class="module-item-text">HD</div>
        </div>
        """
        result = self.spider.categoryContent("site_zhizhen", "2", False, {"categoryId": "24"})
        self.assertEqual(
            mock_request_with_failover.call_args.args[1],
            "http://www.miqk.cc/index.php/vod/show/id/24/page/2.html",
        )
        self.assertEqual(result["list"][0]["vod_id"], "site:zhizhen:/index.php/vod/detail/id/456.html")
```

- [ ] **Step 2: Run test to verify it fails**

Run from `py/`: `python -m unittest tests.test_玩偶聚合.TestWanouAggregateSpider.test_category_content_builds_zhizhen_category_url -v`
Expected: FAIL before the new config is in place because `site_zhizhen` cannot resolve.

- [ ] **Step 3: Write minimal implementation**

```python
            {
                "id": "zhizhen",
                "name": "至臻",
                "domains": ["http://www.miqk.cc"],
                "filter_files": [],
                "list_xpath": "//*[contains(@class,'module-item')]",
                "search_xpath": "//*[contains(@class,'module-search-item')]",
                "detail_pan_xpath": "//*[contains(@class,'module-row-info')]//p",
                "category_url": "/index.php/vod/show/id/{categoryId}/page/{page}.html",
                "search_url": "/index.php/vod/search/page/{page}/wd/{keyword}.html",
                "default_categories": [
                    ("1", "电影"),
                    ("2", "剧集"),
                    ("3", "动漫"),
                    ("4", "综艺"),
                    ("5", "短剧"),
                    ("24", "老剧"),
                    ("26", "严选"),
                ],
            },
```

这一步依旧是复用 Task 1 的配置，目标是用完整模块测试证明没有遗漏分类 URL 规则。

- [ ] **Step 4: Run test to verify it passes**

Run from `py/`: `python -m unittest tests.test_玩偶聚合.TestWanouAggregateSpider.test_category_content_builds_zhizhen_category_url -v`
Expected: PASS and category URL 使用 `/index.php/vod/show/id/<id>/page/<page>.html`。

- [ ] **Step 5: Commit**

```bash
git add py/玩偶聚合.py py/tests/test_玩偶聚合.py
git commit -m "test: verify zhizhen aggregate category url"
```

## Self-Review

- Spec coverage: 首页暴露、搜索 URL、分类 URL、详情合并都对应了独立任务，没有遗漏 `至臻` 在聚合层的关键入口。
- Placeholder scan: 已给出精确文件路径、测试名、命令、站点配置代码和期望输出，没有保留 TBD 或泛化描述。
- Type consistency: 全程使用 `site_zhizhen`、`site:zhizhen:<path>`、`zhizhen` 站点 ID 和 `http://www.miqk.cc` 域名，命名保持一致。
