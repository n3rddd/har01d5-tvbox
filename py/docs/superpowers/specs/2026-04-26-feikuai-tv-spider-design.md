# 飞快TV Python 爬虫设计

## 目标

在当前 Python 仓库中新增一个符合 `base.spider.Spider` 接口的飞快TV爬虫，行为参考用户提供的 JS 版本，但实现形式遵循仓库现有的单文件 Spider 与 `unittest` 测试约定。

本次实现范围：

- 首页分类
- 分类浏览
- 搜索
- 详情解析
- 站内在线播放分组
- 网盘分组
- 播放页 `player_aaaa` 直链解析

本次不实现：

- 首页推荐抓取
- 复杂筛选项
- 额外加密算法扩展
- 浏览器回退或动态渲染

## 方案选择

采用“固定站点 + DOM 直解析 + 播放页脚本解链 + 网盘直出”的方案，而不是为该站额外设计通用抽象或复杂 `play_id` 编码。

原因如下：

- 用户给出的参考实现本身就是固定站点 `https://feikuai.tv`
- 当前仓库对同类站点优先使用站内短路径作为 `vod_id` 与播放 ID
- 该站的在线播放和网盘在详情页上是两类不同数据，分开组装最清晰
- 播放页只需要覆盖 `player_aaaa` 的 `encrypt=1/2` 分支，过度抽象没有收益

## 模块边界

新增 `py/飞快TV.py`，不修改 `py/base/`。

模块对外实现：

- `init`
- `getName`
- `homeContent`
- `homeVideoContent`
- `categoryContent`
- `searchContent`
- `detailContent`
- `playerContent`

模块内部 helper 负责：

- 统一请求头
- URL 归一化与短路径提取
- 列表卡片解析
- 详情元信息解析
- 在线播放分组解析
- 网盘分组解析
- 播放页脚本解析
- Base64 解码与结果归一化

## 站点策略

固定站点参数：

- host：`https://feikuai.tv`
- 固定桌面端 `User-Agent`
- 默认请求头包含 `Referer` 与 `Origin`

请求策略：

- 分类、搜索、详情、播放页都使用 GET
- 不引入可配置 `site`
- 请求失败时返回空结果或解析回退，不抛额外异常

## 分类与首页

`homeContent` 返回固定分类：

- `1` 电影
- `2` 剧集
- `3` 综艺
- `4` 动漫

`homeVideoContent` 固定返回 `{"list": []}`。

分类 URL 固定为：

- `/vodshow/{type_id}--------{page}---.html`

分类页解析规则：

- 遍历 `a.module-poster-item`
- 提取详情短路径、标题、封面、备注
- `vod_id` 保留站内短路径，例如 `/voddetail/12345.html`
- `vod_pic` 统一补全为绝对 URL

返回结构遵循仓库当前约定：

- `page`
- `limit`
- `total`
- `list`

不返回 `pagecount`。

## 搜索

搜索 URL 固定为：

- `/label/search_ajax.html?wd=<urlencoded keyword>&by=time&order=desc&page=<page>`

搜索页解析规则：

- 遍历 `div.module-card-item.module-item`
- 提取详情短路径、标题、封面、备注
- 去重后返回
- 关键字为空时直接返回空列表

搜索返回：

- `page`
- `limit`
- `total`
- `list`

不返回 `pagecount`。

## 详情解析

详情页 URL 为：

- `https://feikuai.tv` + `vod_id`

详情页需要同时解析基础信息、在线播放分组和网盘分组。

基础元信息：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_content`
- `vod_remarks`

在线播放分组规则：

- 线路名来自 `div.module-tab-items-box > .module-tab-item`
- 排除带 `onclick` 的节点
- 播放列表来自 `div.module-list.tab-list`
- 排除 `.module-downlist`
- 每条剧集提取显示名与播放短路径，例如 `/vodplay/123-1-1.html`
- `vod_play_from` 中站内分组名保留页面线路名
- 站内各线路之间用 `$$$` 拼接，线路内各剧集用 `#` 拼接

网盘分组规则：

- 读取 `div.module-list > .tab-content`
- 每个网盘条目优先取 `h4` 文本的 `@` 前缀作为剧集名
- 分享链接取条目内 `p` 文本
- 根据分享链接域名识别线路名：
  - `pan.quark.cn` -> `quark`
  - `drive.uc.cn` -> `uc`
  - `alipan.com`、`aliyundrive.com` -> `aliyun`
  - `pan.baidu.com` -> `baidu`
  - 其他回退 `pan`
- 按识别后的线路名归并，追加到 `vod_play_from` / `vod_play_url`
- 网盘链接直接写入 `vod_play_url`，不经过 `playerContent`

如果站内播放和网盘都缺失，则返回空播放字段。

## 播放解析

`playerContent` 只处理站内在线播放短路径。

播放页 URL 为：

- `https://feikuai.tv` + `id`

解析规则：

- 从页面脚本中提取 `player_aaaa=...`
- 解析 JSON 后读取 `url` 与 `encrypt`
- `encrypt == "1"` 时对 `url` 执行 `unescape`
- `encrypt == "2"` 时先 Base64 解码，再执行 `unescape`
- 解出媒体地址后返回 `parse=0`、`jx=0`

回退规则：

- 如果脚本缺失、JSON 解析失败或未得到可用媒体地址，则返回 `parse=1`、`jx=1`
- 回退 URL 使用完整播放页地址，由上层决定是否继续解析

## 数据约束

ID 设计保持仓库现有风格：

- `vod_id` 使用详情短路径
- 站内播放项 ID 使用播放短路径
- 不把完整详情 URL 或播放 URL 直接写入站内 ID 字段

字段约束：

- 列表与搜索结果不返回 `pagecount`
- `vod_pic` 必须尽量输出绝对地址
- 网盘链接作为最终分享链接直出
- 站内播放链接只在 `playerContent` 中转换为媒体直链

## 测试策略

采用 TDD，实现前先写 `py/tests/test_飞快TV.py`。

测试覆盖最小闭环：

- `homeContent` 返回固定分类
- `homeVideoContent` 返回空列表
- `categoryContent` 解析分类卡片并输出短 `vod_id`
- `searchContent` 解析搜索结果并处理空关键字
- `detailContent` 同时组装站内分组与网盘分组
- `playerContent` 覆盖 `encrypt=1` 明文分支
- `playerContent` 覆盖 `encrypt=2` Base64 分支
- `playerContent` 在脚本缺失或无可用地址时回退解析页

测试方法：

- 使用 `unittest`
- 使用 `unittest.mock.patch` 隔离网络请求
- 测试 HTML 与脚本夹具直接内嵌在测试文件中
- 先跑单个新增测试模块，再决定是否补跑相关模块
