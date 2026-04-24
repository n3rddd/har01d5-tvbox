# 耐视点播 Python 爬虫设计

## 目标

在当前 Python 仓库中新增一个符合 `base.spider.Spider` 接口的耐视点播爬虫，行为参考用户提供的 JS 版本，覆盖以下能力：

- 首页分类
- 首页推荐
- 分类浏览
- 搜索
- 详情解析
- 播放解析

实现形式遵循当前仓库的单文件 Spider 约定和离线单测约定，不引入新的公共基类或第三方依赖。

## 范围

本次实现包含：

- 新增独立脚本 `py/耐视点播.py`
- 新增独立测试 `py/tests/test_耐视点播.py`
- 固定输出参考脚本中的分类 `1/2/3/4/37/40`
- 解析首页与分类页的视频卡片
- 搜索页关键词检索
- 详情页基础元数据与多线路剧集组装
- 播放页 `player_aaaa`、直链 `m3u8` 与播放页回退

本次实现不包含：

- 修改 `base/` 公共层
- 引入新的站点模板基类
- 真实联网集成测试
- Cloudflare、验证码或 JS 执行型反爬
- 对参考 JS 运行时接口的直接兼容层

## 方案选择

采用“单文件 Spider + HTML helper + 单测”的直接适配方案，而不是先抽象一个通用 MacCMS 基类。

原因如下：

- 当前仓库同类 HTML 站点多为单文件实现，直接适配更符合现有形态
- 参考脚本已经给出稳定页面路径和字段来源，没有必要扩大到通用抽象
- 当前任务的主要风险在页面结构解析，不在复用层设计

## 模块边界

新增 `py/耐视点播.py`，只在模块内部维护站点逻辑，不修改 `base/`。

对外实现以下接口：

- `init`
- `getName`
- `homeContent`
- `homeVideoContent`
- `categoryContent`
- `searchContent`
- `detailContent`
- `playerContent`

模块内部拆分以下 helper：

- `_stringify`
  - 统一空值转字符串
- `_clean_text`
  - 清理空白、`&nbsp;` 与残余 HTML 文本
- `_build_url`
  - 将相对路径转换为完整 URL
- `_extract_vod_id`
  - 从详情地址中抽取短 `vod_id`
- `_build_detail_url`
  - 将短 `vod_id` 还原为详情页 URL
- `_request_html`
  - 统一发起站点请求、合并请求头、校验状态码
- `_parse_cards`
  - 解析首页/分类页卡片列表
- `_extract_section_cards`
  - 在首页 HTML 中按“最新电影/最新连续剧”等区块回退提取分类结果
- `_parse_search_cards`
  - 解析搜索结果
- `_parse_play_groups`
  - 解析详情页线路 tab 与对应剧集链接
- `_parse_detail_page`
  - 解析详情基础字段并组装 `vod_play_from` / `vod_play_url`
- `_extract_player_data`
  - 提取 `player_aaaa` JSON
- `_pick_direct_media_url`
  - 提取页面中的直链媒体地址

## 站点配置

固定配置来自参考实现：

- 站点名：`耐视点播`
- 主站：`https://nsvod.me`
- 默认 UA：桌面 Chrome UA
- 默认 `Referer`：`https://nsvod.me/`

分类固定为：

- `1` 电影
- `2` 连续剧
- `3` 综艺
- `4` 动漫
- `37` Netflix
- `40` 纪录片

## 首页与分类设计

`homeContent` 仅返回固定分类：

- `{"class": [...]}`

`homeVideoContent` 请求首页 `/`，解析通用卡片列表并返回：

- `{"list": [...]}` 

卡片字段统一映射为：

- `vod_id`
  - 从 `/index.php/vod/detail/id/<id>.html` 中提取 `<id>`
- `vod_name`
  - 卡片标题或图片 `alt/title`
- `vod_pic`
  - `data-src` 优先，缺失时退回 `src`
- `vod_remarks`
  - 卡片角标、更新信息或副标题

`categoryContent` 优先请求：

- `/index.php/vod/show/id/<tid>.html?page=<pg>`

如果分类页未解析出结果，则回退请求首页并根据以下区块标题抓取：

- `1 -> 最新电影`
- `2 -> 最新连续剧`
- `3 -> 最新综艺`
- `4 -> 最新动漫`
- `37 -> 最新Netflix`
- `40 -> 最新纪录片`

返回结构遵循当前仓库约定：

- `page`
- `limit`
- `total`
- `list`

其中：

- 不返回 `pagecount`
- `limit` 为当前页结果数
- `total` 使用 `page * 20 + len(list)` 这一仓库内常见保守估算

## 搜索设计

搜索接口使用：

- `/index.php/vod/search.html?wd=<keyword>`

搜索结果优先解析 `module-search-item` 或详情链接卡片。

搜索返回结构为：

- `page`
- `total`
- `list`

空关键词直接返回空列表，不发请求。

## 详情设计

详情页 URL 使用：

- `/index.php/vod/detail/id/<vod_id>.html`

详情解析保留当前仓库需要的核心字段：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_year`
- `vod_area`
- `vod_director`
- `vod_actor`
- `vod_content`
- `vod_play_from`
- `vod_play_url`

字段来源与解析策略：

- `vod_name`
  - 优先从标题或详情主标题提取
- `vod_pic`
  - 从详情海报图提取 `data-src/src`
- `vod_year`
  - 从“年份”字段或文本中的四位年份提取
- `vod_area`
  - 从“地区”字段提取
- `vod_director`
  - 从“导演”字段提取，值为“未知”时置空
- `vod_actor`
  - 从“主演”字段提取，值为“未知”时置空
- `vod_content`
  - 从简介容器提取纯文本，缺失时返回 `暂无简介`

播放线路解析策略：

- 先读取 `.anthology-tab .swiper-slide` 作为线路名
- 再读取 `.anthology-list .anthology-list-box` 内的播放链接
- 每条线路的剧集列表按页面顺序保留
- 若多线路容器不存在，则退化为扫描整个页面中的播放链接并生成单线路
- 线路名缺失时默认 `线路1`、`线路2`

`vod_play_from` 使用 `$$$` 连接线路名。

`vod_play_url` 中每条剧集按 `剧集名$播放ID` 编码，线路间使用 `$$$` 连接，线路内使用 `#` 连接。

其中 `播放ID` 保持站内相对路径短格式：

- `/index.php/vod/play/id/...`

## 播放设计

`playerContent` 接收站内播放路径或完整 URL。

解析顺序如下：

1. 请求播放页 HTML
2. 提取 `var player_aaaa = {...}` JSON
3. 若 JSON 中存在 `url`，直接返回该地址
4. 若页面中存在直链 `.m3u8`，直接返回该地址
5. 若以上都失败，则回退返回原播放页地址，并设置 `jx=1`

返回结构对齐当前仓库习惯：

- 直链命中：
  - `{"parse": 0, "jx": 0, "playUrl": "", "url": "<real-url>", "header": {...}}`
- 回退播放页：
  - `{"parse": 0, "jx": 1, "playUrl": "", "url": "<play-page-url>", "header": {...}}`

请求头策略：

- 直链解析成功时返回 `User-Agent`，并将 `Referer` 设为当前播放页 URL
- 回退播放页时返回基础请求头，其中 `Referer` 为站点首页

## 错误处理

所有公开接口在异常或空响应场景下返回当前仓库接受的最小空结构：

- `homeVideoContent -> {"list": []}`
- `categoryContent -> {"page": <pg>, "limit": 0, "total": 0, "list": []}`
- `searchContent -> {"page": <pg>, "total": 0, "list": []}`
- `detailContent -> {"list": []}`
- `playerContent -> {"parse": 0, "jx": 0, "playUrl": "", "url": "", "header": {}}`

这样可以避免未处理异常穿透到调用侧。

## 测试设计

新增 `py/tests/test_耐视点播.py`，覆盖以下行为：

- `homeContent` 返回固定分类
- `_build_url` 与 `_extract_vod_id` 正确处理相对路径和短 ID
- `_parse_cards` 解析首页/分类卡片
- `homeVideoContent` 调用首页并返回列表
- `categoryContent` 优先走分类页，空结果时回退首页分区
- `searchContent` 空关键词短路，非空关键词正确组装 URL 并解析结果
- `_parse_detail_page` 提取元数据与多线路剧集
- `detailContent` 读取详情页并返回单条详情
- `playerContent` 覆盖 `player_aaaa`、页面直链、失败回退三条路径

测试全部使用内联 HTML 与 `unittest.mock` 隔离网络请求，不依赖站点在线状态。

## 风险与约束

已知风险如下：

- 站点卡片和搜索页 DOM 可能存在轻微变体，需要在 XPath 上做适度容错
- `player_aaaa.url` 可能是编码值或中间地址；当前实现仅按参考脚本优先直接透传
- 分类页使用 `?page=` 参数而不是路径分页，测试需要锁定该约定，避免误写为 `/page/`

本次实现优先保证：

- 行为与参考脚本核心能力一致
- 接口输出符合当前仓库既有约定
- 测试可离线稳定运行
