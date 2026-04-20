# 至臻 Python 爬虫设计

**日期：** 2026-04-20

## 目标

在当前 Python Spider 仓库中新增一个独立单站蜘蛛 `至臻.py`，参考用户提供的 JS 版本行为，实现符合 `base.spider.Spider` 接口的网盘资源站适配。

本次实现需要覆盖：

- 固定 7 个分类
- 分类列表
- 搜索
- 详情页元数据解析
- 网盘链接整理
- 播放透传
- 对应 `unittest`

## 范围

本次实现包含：

- 新增独立蜘蛛文件 `py/至臻.py`
- 新增测试文件 `py/tests/test_至臻.py`
- 单域名站点适配：`http://www.miqk.cc`
- 固定 7 个分类，分类 ID 与参考 JS 保持一致
- 分类页和搜索页卡片解析
- 详情页元数据与网盘链接提取
- 按网盘类型输出 `vod_play_from` 和 `vod_play_url`
- `playerContent` 对已识别网盘分享链接直接透传

本次实现不包含：

- 聚合多站
- 站内直链播放解析
- 本地筛选配置文件
- 验证码、浏览器执行或复杂反爬绕过
- 修改 `base/` 公共层

## 方案选择

采用“单站单文件 + 少量 helper + 单测”的仓库现有模式，而不是直接保存用户提供的 JS 代码。

原因：

- 用户已确认以独立单站爬虫交付
- 当前仓库已存在多个相同结构的单文件 Spider
- 私有 helper 能把 URL 组装、文本清洗、卡片解析、详情提取和网盘识别拆开，便于后续修站
- 解析逻辑可以通过静态 HTML 单测稳定覆盖，不依赖真实网络

不采用“提前抽公共盘站基类”的方案，因为本次目标是尽快落一个站点，过早抽象会扩大改动面。

## 接口设计

### `homeContent`

返回固定 7 个分类：

- `1 -> 至臻电影`
- `2 -> 至臻剧集`
- `3 -> 至臻动漫`
- `4 -> 至臻综艺`
- `5 -> 至臻短剧`
- `24 -> 至臻老剧`
- `26 -> 至臻严选`

不返回筛选项。

### `homeVideoContent`

返回空列表：

- `{"list": []}`

### `categoryContent`

分类页 URL 规则：

- `/index.php/vod/show/id/{tid}/page/{page}.html`

解析 `#main .module-item` 卡片并输出：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_remarks`
- `vod_year`

分页返回字段：

- `page`
- `limit`
- `total`
- `list`

不返回 `pagecount`。

### `searchContent`

搜索 URL 规则：

- `/index.php/vod/search/page/{page}/wd/{keyword}.html`

空关键词直接返回空列表。

搜索结果结构与分类列表保持一致，但 `vod_remarks` 优先取 `.video-serial` 文本。

### `detailContent`

通过详情页提取：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_year`
- `vod_director`
- `vod_actor`
- `vod_content`
- `vod_play_from`
- `vod_play_url`

详情页只整理网盘分享链接，不解析站内播放器。

### `playerContent`

若 `id` 是支持的网盘分享链接，则返回透传结果：

```python
{"parse": 0, "playUrl": "", "url": id}
```

若不是已识别网盘链接，则返回空 URL：

```python
{"parse": 0, "playUrl": "", "url": ""}
```

## 模块边界

新蜘蛛内部拆分为以下职责：

- 站点配置与固定分类
- URL 组装
- 文本清洗
- HTML 请求封装
- 列表卡片解析
- 搜索结果解析
- 详情页字段提取
- 网盘类型识别
- 网盘线路拼接

不新增公共基类，不抽共享模块。

## URL 与 ID 设计

详情页 `vod_id` 使用站内短路径，而不是完整 URL。

编码方式：

- 详情链接 `/index.php/vod/detail/id/123.html` 对外直接保存为 `/index.php/vod/detail/id/123.html`

原因：

- 与用户给出的 JS 行为一致
- 当前仓库已有多个蜘蛛直接使用站内短路径作为 `vod_id`
- 单站实现不需要额外编码层

详情请求时再基于主域拼成完整地址。

## 请求策略

主域固定为：

- `http://www.miqk.cc`

请求头包含固定 `User-Agent` 和首页 `Referer`。

异常处理策略：

- 页面请求失败时返回空列表或空字段结果
- 不向上抛出未处理异常
- 不实现多域名切换
- 不实现重试

## 列表与搜索解析

分类列表解析容器：

- `#main .module-item`

提取策略：

- 链接：`.module-item-pic a[href]`
- 标题：`.module-item-pic img[alt]`
- 封面：`.module-item-pic img[data-src|src]`
- 备注：`.module-item-text`
- 年份：`.module-item-caption span:first-child`

搜索结果解析容器：

- `.module-search-item`

提取策略：

- 链接和标题优先来自 `.video-serial`
- 封面来自 `.module-item-pic img[data-src|src]`
- 备注优先取 `.video-serial` 文本，缺失时回退 `.module-item-text`

列表和搜索都应忽略空标题或空链接项。

## 详情解析

详情页字段来源按用户提供的 JS 保持一致：

- 标题：`.page-title`
- 封面：`.mobile-play .lazyload[data-src|src]`
- 标注区：`.video-info-itemtitle` 与其相邻节点
- 网盘链接：`.module-row-info p`

字段映射规则：

- `年代` -> `vod_year`
- `导演` -> `vod_director`
- `主演` -> `vod_actor`
- `剧情` -> `vod_content`

其中导演、主演优先拼接相邻区域中的链接文本；剧情提取文本内容并做空白清洗。

## 网盘线路整理

支持识别以下网盘：

- 百度
- 139
- 天翼
- 123
- 115
- 夸克
- 迅雷
- 阿里
- UC

排序优先级：

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

- `vod_play_from` 使用 `{pan_type}#至臻` 线路名拼接
- `vod_play_url` 使用 `{标题}${分享链接}` 拼接
- 不支持的链接忽略
- 重复链接去重

## 测试策略

采用 `unittest` 和 `unittest.mock`，不依赖真实网络。

至少覆盖：

- 固定分类和空首页
- URL 构建与网盘识别
- 分类卡片解析
- 分类接口 URL 拼装
- 搜索接口 URL 拼装和结果解析
- 详情元数据提取
- 网盘线路去重和排序
- `detailContent` 最终输出
- `playerContent` 对网盘链接透传和非网盘拒绝

## 风险与约束

- 站点 DOM 如果与用户提供的 JS 片段不一致，测试需要以当前仓库约定的静态夹具为准
- 搜索关键词直接拼接到路径中，需做 URL 编码
- 详情页相邻节点结构若出现空白文本节点，解析时需要回退到 XPath 文本合并，避免取值为空

## 验收标准

满足以下条件即可认为完成：

- `py/至臻.py` 实现 `Spider` 所需接口
- `py/tests/test_至臻.py` 覆盖核心行为
- 针对 `至臻` 模块的单测全部通过
- 返回结构与当前仓库同类盘站蜘蛛保持一致
