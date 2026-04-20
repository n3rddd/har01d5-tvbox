# 闪电 Python 爬虫与聚合接入设计

**日期：** 2026-04-20

## 目标

在当前 Python Spider 仓库中完成两项相关工作：

- 新增独立单站蜘蛛 `闪电.py`
- 将 `闪电` 站点接入 `玩偶聚合.py`

`闪电` 站点主域名固定为：

- `https://sd.sduc.site`

行为边界与用户提供的 JS 参考实现保持一致：

- 支持分类列表
- 支持搜索
- 支持详情页元数据解析
- 支持网盘分享链接整理
- `playerContent` 只透传网盘分享链接
- 不做站内直链播放解析

## 范围

本次实现包含：

- 新增独立蜘蛛文件 `py/闪电.py`
- 新增测试文件 `py/tests/test_闪电.py`
- 在 `py/玩偶聚合.py` 中新增 `shandian` 站点配置
- 在 `py/tests/test_玩偶聚合.py` 中新增 `闪电` 聚合测试
- 补充对应 spec 和 plan 文档

本次实现不包含：

- 抽取新的公共盘站基类
- 修改 `base/` 公共层
- 增加站内播放器解析
- 实现多备用域名 failover
- 修改现有 `至臻` 行为

## 现状

仓库中已经存在一批结构相近的盘站蜘蛛，尤其是：

- `py/至臻.py`
- `py/玩偶哥哥.py`

这些实现已经验证了同类 DOM 结构的解析方式：

- 列表容器：`#main .module-item`
- 搜索容器：`.module-search-item`
- 详情标题：`.page-title`
- 详情海报：`.mobile-play .lazyload`
- 详情字段标签：`.video-info-itemtitle`
- 网盘链接容器：`.module-row-info p`

当前 `py/玩偶聚合.py` 中已有 `site_priority` 对 `shandian` 的优先级预留，但 `self.sites` 还未真正接入 `闪电` 站点。

因此，本次工作重点是：

- 复用现有盘站解析模式落单站实现
- 以最小配置改动把 `闪电` 接入聚合层

## 方案选择

采用“单站独立文件 + 聚合配置接入”的方案。

### 方案 A：推荐

- 新增 `py/闪电.py`
- 结构对齐 `py/至臻.py`
- 在 `py/玩偶聚合.py` 中新增 `shandian` 站点配置
- 用 `unittest` 覆盖单站与聚合层行为

优点：

- 与当前仓库模式一致
- 改动边界清晰
- 便于后续单站修复与聚合调试

### 方案 B：不采用

- 抽取一个通用盘站基类，让 `至臻/闪电` 共享实现

不采用原因：

- 扩大改动范围
- 增加重构风险
- 当前任务目标明确，不需要提前抽象

## 独立单站蜘蛛设计

### 文件

- `py/闪电.py`
- `py/tests/test_闪电.py`

### Spider 对外行为

#### `homeContent`

返回固定 5 个分类：

- `1 -> 闪电电影`
- `2 -> 闪电剧集`
- `3 -> 闪电综艺`
- `4 -> 闪电动漫`
- `30 -> 闪电短剧`

不返回筛选项。

#### `homeVideoContent`

返回：

```python
{"list": []}
```

#### `categoryContent`

分类 URL：

- `/index.php/vod/show/id/{tid}/page/{page}.html`

解析字段：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_remarks`
- `vod_year`

结果结构包含：

- `page`
- `limit`
- `total`
- `list`

不返回 `pagecount`。

#### `searchContent`

搜索 URL：

- `/index.php/vod/search/page/{page}/wd/{keyword}.html`

空关键词直接返回空列表。

结果字段：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_remarks`

#### `detailContent`

详情页提取：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_year`
- `vod_director`
- `vod_actor`
- `vod_content`
- `vod_play_from`
- `vod_play_url`

只整理网盘线路，不解析站内直链播放页。

#### `playerContent`

已识别网盘分享链接时返回：

```python
{"parse": 0, "playUrl": "", "url": id}
```

非网盘链接返回：

```python
{"parse": 0, "playUrl": "", "url": ""}
```

### URL 与 ID 设计

独立单站的 `vod_id` 保持站内短路径，例如：

- `/index.php/vod/detail/id/123.html`

详情请求时再与主域名拼接。

### 解析策略

#### 列表页

容器：

- `#main .module-item`

提取：

- 链接：`.module-item-pic a[href]`
- 标题：`.module-item-pic img[alt]`
- 海报：`.module-item-pic img[data-src|src]`
- 备注：`.module-item-text`
- 年份：`.module-item-caption span:first-child`

#### 搜索页

容器：

- `.module-search-item`

提取：

- 链接：`.video-serial[href]`
- 标题：`.video-serial[title]`
- 海报：`.module-item-pic img[data-src|src]`
- 备注：`.video-serial` 文本，缺失时回退 `.module-item-text`

#### 详情页

字段来源：

- 标题：`.page-title`
- 海报：`.mobile-play .lazyload[data-src|src]`
- 标签区：`.video-info-itemtitle` 与相邻节点
- 网盘链接：`.module-row-info p`

字段映射：

- `年代` -> `vod_year`
- `导演` -> `vod_director`
- `主演` -> `vod_actor`
- `剧情` -> `vod_content`

### 网盘线路规则

支持识别：

- 百度
- 139
- 天翼
- 123
- 115
- 夸克
- 迅雷
- 阿里
- UC

优先级沿用当前仓库同类盘站：

1. 百度
2. 139
3. 天翼
4. 123
5. 115
6. 夸克
7. 迅雷
8. 阿里
9. UC

输出规则：

- `vod_play_from` 使用 `{pan_type}#闪电`
- `vod_play_url` 使用 `{标题}${分享链接}`
- 重复链接去重
- 非支持网盘链接忽略

## 聚合接入设计

### 修改文件

- `py/玩偶聚合.py`
- `py/tests/test_玩偶聚合.py`

### 新增站点配置

在 `self.sites` 中新增：

- `id`: `shandian`
- `name`: `闪电`
- `domains`: `["https://sd.sduc.site"]`
- `filter_files`: `[]`
- `list_xpath`: `//*[contains(@class,'module-item')]`
- `search_xpath`: `//*[contains(@class,'module-search-item')]`
- `detail_pan_xpath`: `//*[contains(@class,'module-row-info')]//p`
- `category_url`: `/index.php/vod/show/id/{categoryId}/page/{page}.html`
- `search_url`: `/index.php/vod/search/page/{page}/wd/{keyword}.html`
- `default_categories`: `[("1","电影"),("2","剧集"),("3","综艺"),("4","动漫"),("30","短剧")]`

这里不配置 `category_url_with_filters`，因为用户给出的参考实现只确认了基础分类分页 URL。

### 首页行为

`homeContent(False)` 中应新增：

- `type_id = site_shandian`
- `type_name = 闪电`

`filters["site_shandian"]` 的首个筛选组应为 `categoryId`，分类值映射到 5 个默认分类。

### 分类行为

`categoryContent("site_shandian", pg, ..., extend)` 应使用：

- `extend["categoryId"]` 指定分类
- 默认值为 `1`
- URL：`https://sd.sduc.site/index.php/vod/show/id/<categoryId>/page/<pg>.html`

返回结果中的 `vod_id` 应编码为：

- `site:shandian:<detail_path>`

### 搜索行为

`_fetch_site_search` 应使用：

- `/index.php/vod/search/page/{page}/wd/{keyword}.html`

结果进入现有 `_aggregate_search_results`。

站点优先级不调整，沿用当前 `site_priority` 中 `shandian` 的位置。

### 详情行为

聚合详情不改结构，只保证：

- `_get_site("shandian")` 能找到配置
- `_fetch_site_detail` 能正确请求并解析 `闪电` 详情页
- `detailContent` 合并 `闪电` 网盘线路时遵守现有去重与排序规则

## 测试策略

### 单站测试

新增 `py/tests/test_闪电.py`，至少覆盖：

- 固定分类
- 空首页
- URL 构建
- 网盘识别
- 分类列表解析
- 分类 URL 构造
- 搜索 URL 构造与解析
- 空关键词回退
- 详情元数据提取
- 网盘线路去重和排序
- `detailContent`
- `playerContent`

### 聚合测试

在 `py/tests/test_玩偶聚合.py` 中新增至少以下场景：

- 首页暴露 `site_shandian`
- `site_shandian` 分类组正确
- `闪电` 搜索 URL 构造与编码
- `闪电` 分类 URL 构造
- 聚合详情能合并 `闪电` 的网盘线路

## 风险

- `闪电` 的 URL 规则与旧 `/vodshow/...` 模板不同，若误复用旧模板会导致聚合接入无效
- `default_categories` 顺序和 ID 若写错，会让 UI 展示与真实站点不一致
- 若只补聚合配置、不补单站测试，后续修站时很难快速定位问题

## 验收标准

满足以下条件即可认为完成：

- `py/闪电.py` 实现独立 Spider
- `py/tests/test_闪电.py` 覆盖核心行为
- `py/玩偶聚合.py` 接入 `shandian`
- `py/tests/test_玩偶聚合.py` 覆盖 `闪电` 聚合行为
- `python -m unittest tests.test_闪电 tests.test_玩偶聚合 -v` 通过
