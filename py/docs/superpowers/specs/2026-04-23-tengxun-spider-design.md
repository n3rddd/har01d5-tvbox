# 腾讯视频 Python 蜘蛛设计

## 目标

在当前 Python 仓库中新增一个符合 `base.spider.Spider` 接口的腾讯视频蜘蛛，覆盖以下能力：

- 首页分类与推荐
- 分类列表
- 搜索
- 详情解析
- 播放透传

实现以用户提供的 Node/JS 版本为行为参考，但落地形式遵循当前仓库的单文件 Spider 约定。

## 范围

本次实现包含：

- 新增独立脚本，文件名为 `腾讯视频.py`
- 首页使用腾讯频道页 HTML 抓取推荐卡片
- 分类页使用腾讯频道页 HTML 抓取卡片并支持常见筛选参数
- 详情页调用 `float_vinfo2` 与批量详情接口，组装单条播放线路
- 搜索调用 `MultiTerminalSearch`
- 播放阶段只做原始链接透传
- 为新增行为补齐 `unittest`

本次实现不包含：

- 参考代码中的 HTTP 路由导出层
- 任何 parse 相关逻辑
- 解析器线路生成
- 花絮/预告拆分为独立线路
- 公共 helper 抽象

## 方案选择

候选方案有三种：

1. 单文件直译版
2. 单文件加 `lxml` 解析列表页
3. 站点文件加多个私有 helper 重构

选用方案 1，并保留少量私有 helper。

原因：

- 与用户提供的参考实现最接近
- 列表页测试夹具最容易构造
- 不额外扩大实现范围

## 模块边界

新增脚本只在站点文件内部维护逻辑，不修改 `base/`。

Spider 对外方法：

- `init`
- `getName`
- `homeContent`
- `homeVideoContent`
- `categoryContent`
- `detailContent`
- `searchContent`
- `playerContent`

站点内部私有 helper：

- `_headers`
  - 统一请求头
- `_parse_list_items`
  - 从频道页 HTML 中提取卡片
- `_get_batch_video_info`
  - 批量请求分集信息
- `_safe_json`
  - 解析 JSON 和 JSONP 载荷

## 请求与 ID 设计

固定主域：

- `https://v.qq.com`

固定请求头：

- `User-Agent: PC_UA`

`vod_id` 设计：

- 首页直接使用卡片里的 `data-float`
- 分类页使用 `频道$sourceId`
- 搜索结果直接使用 `doc.id`

详情阶段：

- 如果传入的是 `频道$sourceId`，取 `$` 后面的值作为 `cid`
- 如果没有 `$`，直接把原值作为 `cid`

## 首页与分类设计

### 首页

首页请求：

- `/x/bu/pagesheet/list?_all=1&append=1&channel=cartoon&listpage=1&offset=0&pagesize=21&iarea=-1&sort=18`

解析规则：

- 用正则提取 `list_item`
- 取 `img alt` 作为 `vod_name`
- 取 `img src` 作为 `vod_pic`
- 取第一个链接文本作为 `vod_remarks`
- 取 `a[data-float]` 作为 `vod_id`

首页只返回：

- `class`
- `list`

不返回 `filters`。

### 分类

分类请求基础路径：

- `/x/bu/pagesheet/list`

固定参数：

- `_all=1`
- `append=1`
- `channel=<id>`
- `listpage=1`
- `offset=(page-1)*21`
- `pagesize=21`
- `iarea=-1`

可选筛选参数：

- `sort`
- `iyear`
- `year`
- `itype`
- `ifeature`
- `iarea`
- `itrailer`
- `gender`

分类页返回结构遵循当前参考实现：

- `list`
- `page`
- `pagecount`
- `limit`
- `total`

## 详情设计

详情请求：

- `https://node.video.qq.com/x/api/float_vinfo2?cid=<targetCid>`

详情字段映射：

- `vod_name <- json.c.title`
- `type_name <- json.typ`
- `vod_actor <- json.nam`
- `vod_year <- json.c.year`
- `vod_content <- json.c.description`
- `vod_remarks <- json.rec`
- `vod_pic <- json.c.pic`

播放列表生成：

1. 读取 `json.c.video_ids`
2. 调用批量接口：
   - `https://union.video.qq.com/fcgi-bin/data?...&idlist=<vid1,vid2,...>`
3. 按原始 `video_ids` 顺序回填标题
4. 正片与花絮/预告不拆线路，统一合并为一条 `腾讯视频`
5. 每个播放项格式为：
   - `标题$https://v.qq.com/x/cover/<cid>/<vid>.html`

最终详情仅保留一条线路：

- `vod_play_from = "腾讯视频"`

## 搜索设计

搜索请求：

- `https://pbaccess.video.qq.com/trpc.videosearch.mobile_search.MultiTerminalSearch/MbSearch?vplatform=2`

请求头：

- 桌面浏览器 UA
- `Content-Type: application/json`
- `Origin: https://v.qq.com`
- `Referer: https://v.qq.com/`

请求体字段沿用参考实现：

- `version`
- `clientType`
- `query`
- `pagenum`
- `pagesize`
- `extraInfo`

结果提取：

- 同时遍历 `data.normalList.itemList`
- 同时遍历 `data.areaBoxList[].itemList`
- 只保留 `doc.id` 存在且长度大于 11 的结果
- 标题去掉 `<em>` 标签

分页结构保持参考行为：

- `list`
- `page`
- `pagecount`
- `limit`
- `total`

## 播放设计

用户明确要求：

- 不要 parse 相关内容
- 不保留任何解析器线路

因此 `playerContent` 只做原始链接透传，固定返回：

- `parse = 1`
- `jx = 1`
- `url = id`
- `header = {"User-Agent": "PC_UA"}`

不做任何站内解析或解析器回退。

## 容错策略

- 首页和分类页 HTML 抓取失败时返回空列表
- 批量详情接口单次失败时忽略该批次，保留已成功条目
- 详情接口失败时跳过当前 `id`
- 搜索接口异常时返回空分页结构
- 播放阶段不抛异常，直接透传原始 `id`

## 测试设计

新增 `tests/test_腾讯视频.py`，使用 `unittest` 与 `unittest.mock`，不访问真实网络。

首轮测试覆盖：

1. 首页 HTML 提取推荐卡片
2. 首页返回固定分类
3. 分类页正确拼接筛选参数
4. 分类页返回 `频道$sourceId` 形式的 `vod_id`
5. `_get_batch_video_info` 解析 `QZOutputJson=` 响应
6. 详情页把正片和花絮/预告合并为单条 `腾讯视频` 线路
7. 搜索同时处理 `normalList` 与 `areaBoxList`
8. 播放透传返回 `parse=1/jx=1`

## 风险与边界

- 列表页 HTML 结构若改动，正则提取会失效，但这与参考实现保持一致
- 腾讯搜索返回结构可能包含多种卡片形态，首轮只覆盖参考代码已处理的两种容器
- `PC_UA` 是否需要替换成真实 UA 可在实现阶段决定，但行为上保持统一 header 即可
