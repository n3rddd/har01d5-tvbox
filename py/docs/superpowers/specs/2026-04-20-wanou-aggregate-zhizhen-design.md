# 玩偶聚合接入至臻设计

**日期：** 2026-04-20

## 目标

在现有聚合蜘蛛 [玩偶聚合.py](/home/harold/workspace/tvbox-resources/py/玩偶聚合.py) 中正式接入 `至臻` 站点，使其参与：

- 首页站点列表展示
- 站点分类页抓取
- 聚合搜索
- 聚合详情页网盘线路合并

主域名固定为：

- `http://www.miqk.cc`

本次接入沿用已经确认的单站 `至臻` 解析边界：

- 只抓列表、搜索、详情元数据和网盘链接
- `playerContent` 只透传网盘分享链接
- 不做站内直链播放解析

## 范围

本次改动包含：

- 在 [玩偶聚合.py](/home/harold/workspace/tvbox-resources/py/玩偶聚合.py) 的 `self.sites` 中增加 `zhizhen` 配置
- 让 `homeContent` 暴露 `site_zhizhen`
- 让 `categoryContent` 使用 `至臻` 的分类和 URL 模板
- 让 `searchContent` 将 `至臻` 结果纳入聚合
- 让 `detailContent` 能合并 `至臻` 的网盘链接
- 在 [test_玩偶聚合.py](/home/harold/workspace/tvbox-resources/py/tests/test_玩偶聚合.py) 中补充对应测试

本次不包含：

- 修改聚合 ID 编码格式
- 抽取新的共享基类
- 为 `至臻` 增加备用域名
- 修改单站 [至臻.py](/home/harold/workspace/tvbox-resources/py/至臻.py) 的行为

## 现状

当前聚合蜘蛛已有：

- `site_priority` 中的 `zhizhen` 优先级占位
- 通用的列表、搜索、详情和网盘线路组装逻辑
- 站点配置驱动的 URL 构建和 XPath 解析

当前缺口是：

- `self.sites` 里还没有真正的 `zhizhen` 配置
- 测试中也没有覆盖 `至臻` 在聚合层的展示、搜索和详情合并

这意味着聚合层逻辑本身基本够用，本次重点是补站点定义并用测试锁定行为。

## 方案选择

采用“最小配置接入 + 现有聚合逻辑复用”的方案。

具体做法：

- 新增一条 `zhizhen` 站点配置
- 复用现有 `module-item`、`module-search-item`、`module-row-info` 解析流程
- 复用现有 `_fetch_site_search`、`_parse_detail_page`、`_build_pan_lines`、`detailContent` 合并逻辑

不采用“让聚合层调用单站 `至臻.py`”的方案，原因是：

- 当前聚合蜘蛛的结构是配置驱动，不是子 Spider 组合
- 强行调用单站 Spider 会把接口耦合变复杂
- 本次站点结构与现有聚合模板兼容，没有必要新增调度层

## 站点配置设计

新增站点项字段：

- `id`: `zhizhen`
- `name`: `至臻`
- `domains`: `["http://www.miqk.cc"]`
- `filter_files`: `[]`
- `list_xpath`: `//*[contains(@class,'module-item')]`
- `search_xpath`: `//*[contains(@class,'module-search-item')]`
- `detail_pan_xpath`: `//*[contains(@class,'module-row-info')]//p`
- `category_url`: `/index.php/vod/show/id/{categoryId}/page/{page}.html`
- `search_url`: `/index.php/vod/search/page/{page}/wd/{keyword}.html`
- `default_categories`: `[("1","电影"),("2","剧集"),("3","动漫"),("4","综艺"),("5","短剧"),("24","老剧"),("26","严选")]`

这里不配置 `category_url_with_filters`，因为用户给出的 `至臻` 参考实现只确认了基础分类翻页 URL，没有额外筛选规则。

## 行为设计

### 首页

`homeContent` 应新增一项：

- `type_id = site_zhizhen`
- `type_name = 至臻`

`filters["site_zhizhen"]` 中的第一个筛选组应为 `categoryId`，值列表映射到 `至臻` 的 7 个默认分类。

### 分类页

`categoryContent("site_zhizhen", pg, ..., extend)` 应：

- 从 `extend["categoryId"]` 读取分类
- 若未提供，则默认使用 `1`
- 构建 `http://www.miqk.cc/index.php/vod/show/id/<categoryId>/page/<pg>.html`
- 按现有通用列表解析逻辑输出站内条目

返回结构保持与现有聚合站一致：

- `vod_id` 使用 `site:zhizhen:<detail_path>`
- 保留 `_site` 和 `_detail_path`
- 不返回 `pagecount`

### 搜索

`searchContent` 不改接口，只需要确保：

- `_fetch_site_search` 能对 `zhizhen` 使用其 `search_url`
- 结果进入 `_aggregate_search_results`
- 若同名同年命中多个站点，仍按 `site_priority` 决定主信息来源

因为 `site_priority` 中 `zhizhen` 已排在 `labi` 后、`erxiao` 前，本次不调整站点优先级。

### 详情

聚合详情和单站详情都不改数据模型，只要 `zhizhen` 配置加入后能被现有流程消费。

重点保证：

- `_fetch_site_detail` 能按 `site["domains"][0] + path` 请求 `至臻` 详情页
- `_parse_detail_page` 可用通用 `.page-title` / `.mobile-play` / `.video-info-itemtitle` / `detail_pan_xpath` 提取字段
- `detailContent` 合并 `至臻` 的网盘线路时遵守现有去重和排序规则

## 测试设计

本次至少新增以下测试：

1. 首页暴露 `site_zhizhen`
   - 校验 `homeContent(False)["class"]` 中包含 `site_zhizhen`
   - 校验 `filters["site_zhizhen"]` 的分类项包含 `1/2/3/4/5/24/26`

2. `至臻` 搜索 URL 构造与解析
   - 构造一个 `zhizhen` 站点配置
   - mock `_request_with_failover`
   - 断言 `_fetch_site_search` 请求 `http://www.miqk.cc/index.php/vod/search/page/1/wd/<keyword>.html`
   - 断言结果被编码为 `site:zhizhen:<path>`

3. 聚合详情合并 `至臻` 网盘线路
   - mock `_fetch_site_detail`，让一个聚合 payload 同时包含例如 `wanou` 和 `zhizhen`
   - 断言 `vod_play_from` / `vod_play_url` 中含 `#至臻` 的线路
   - 断言重复链接仍会按现有规则去重

必要时再补一个分类页测试，锁定 `site_zhizhen` 的分类 URL 模板。

## 风险

- `至臻` 的分类 URL 与现有 `/vodshow/...` 模板不同，若直接沿用旧模板会导致站点在聚合层无法访问分类页
- `default_categories` 若错误复用其他站的 `29` 或 `21` 等 ID，会让筛选项和真实站点不一致
- 若测试只验证首页展示、不验证搜索和详情，则很容易出现“站点名显示了，但实际不可用”的假集成

## 验收标准

满足以下条件即可认为完成：

- [玩偶聚合.py](/home/harold/workspace/tvbox-resources/py/玩偶聚合.py) 的 `self.sites` 中新增 `zhizhen` 配置
- [test_玩偶聚合.py](/home/harold/workspace/tvbox-resources/py/tests/test_玩偶聚合.py) 覆盖 `至臻` 的首页、搜索或详情至少三类行为
- `python -m unittest tests.test_玩偶聚合 -v` 通过
- 聚合层返回结构不引入新的字段格式变化
