# 步步影视 Python 爬虫设计

## 目标

在当前 Python 仓库中新增一个符合 `base.spider.Spider` 接口的步步影视站点爬虫，覆盖以下能力：

- 首页分类与筛选
- 首页推荐视频
- 分类列表
- 搜索
- 详情解析
- 播放解析

实现基于站点现有 JSON API，不依赖浏览器自动化，不修改 `base/` 公共层。

## 范围

本次实现包含：

- 新增独立脚本，文件名为 `步步影视.py`
- 使用单一站点主域：`https://bbys.app`
- 支持 `home/homeVideo/category/detail/search/player` 全链路
- 支持类型、地区、年份、排序筛选
- 支持首页接口失败时回退到主分类聚合
- 支持播放线路解码

本次实现不包含：

- 多域名自动探活与切换
- 调试日志文件、路由注册和 Node 中间层封装
- 浏览器执行、验证码处理或复杂反爬绕过
- 登录态、会员内容和本地缓存持久化
- 通用 JSON 影视站抽象层

## 方案选择

采用仓库现有的“单站点单文件 + 单测”方案：

- 对外保持 `Spider` 接口兼容
- 对内拆分为签名头生成、请求封装、列表映射、详情重组和播放解码几个 helper
- 保留参考 JS 的核心行为，但去掉 Fastify 路由层、调试日志和无关包装

不直接照搬参考 JS 路由层的原因是：

- 当前仓库只消费 Spider 接口，不消费站内 HTTP API 路由
- Python 版单文件 Spider 更符合现有项目结构
- 测试重点应放在请求参数与返回映射，而不是路由分发

## 模块边界

新增脚本只在站点文件内部维护逻辑，不修改 `base/`。

脚本内部职责拆分如下：

- `init`
  - 初始化主域、固定头字段、分类、筛选定义和签名常量
- `homeContent`
  - 返回固定 `class` 与 `filters`
- `homeVideoContent`
  - 请求首页接口并映射首页卡片，失败时回退到主分类聚合
- `categoryContent`
  - 请求分类接口并返回分页结果
- `detailContent`
  - 请求详情接口并整理影片元数据与播放列表
- `searchContent`
  - 请求搜索接口并映射结果列表
- `playerContent`
  - 解析压缩后的播放载荷，必要时调用解码接口
- 私有辅助函数
  - 签名生成
  - `app/web` 请求头构造
  - 文本与数组归一化
  - 视频卡片映射
  - 首页数据映射
  - 播放线路重组
  - 播放地址解码与兜底

## Host 与请求策略

本次只实现单域：

- `https://bbys.app`

请求分两类：

- `app` 接口：`/api.php/app/...`
- `web` 接口：`/api.php/web/...`

固定签名参数来自参考实现：

- `pkg = com.sunshine.tv`
- `ver = 4`
- `finger = SF-C3B2B41F6EFFFF9869176CF68F6790E8F07506FC88632C94B4F5F0430D5498CA`
- `sk = SK-thanks`
- `webSign = f65f3a83d6d9ad6f`
- `xClient = 8f3d2a1c7b6e5d4c9a0b1f2e3d4c5b6a`

请求头策略：

- `app` 请求带 `x-aid/x-time/x-sign/x-nonc/x-ave`
- `web` 请求在此基础上额外带 `web-sign/X-Client`
- 默认 `User-Agent` 维持参考实现的移动端接口风格

失败策略：

- 单次请求失败返回空数据，不向上抛出未处理异常
- 首页接口为空时回退到主分类聚合
- 分类未知或为空时回退到主分类热门列表

不做：

- 自动重试
- 动态 host 探活
- 写入本地日志文件

## 分类与筛选设计

首页分类固定为：

- `1 -> 电影`
- `2 -> 剧集`
- `3 -> 动漫`
- `4 -> 综艺`

筛选配置直接内置到脚本中，字段沿用参考实现：

- `class`
- `area`
- `year`
- `by`

年份值按当前年份动态生成：

- 电影从当年递减到 2016，并补充区间项
- 剧集从当年递减到 2021，并补充区间项
- 动漫、综艺从当年递减到 2011，并补充“更早”

`homeContent` 返回：

- `class`
- `filters`

`homeVideoContent` 不在 `homeContent` 内联返回，保持与仓库现有模式一致。

## 首页与列表设计

首页接口：

- `GET /api.php/web/index/home`

首页数据从 `data.categories` 提取：

- 分类列表映射为 `type_id/type_name`
- 各分类下 `videos` 聚合后映射为统一卡片结构

卡片字段至少包含：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_remarks`
- `type_name`
- `vod_year`
- `vod_area`

若首页接口为空或异常：

- 依次请求“电影/剧集/综艺/动漫”四个主分类的热门列表
- 聚合结果作为首页推荐

分类接口：

- `GET /api.php/web/filter/vod`

请求参数包括：

- `type_name`
- `page`
- `sort`
- `class`
- `area`
- `year`

分类返回字段：

- `page`
- `limit`
- `total`
- `list`

为了符合仓库约定，分类与搜索结果不返回 `pagecount`。

`limit/total` 采用保守策略：

- 有结果时 `limit = len(list)`
- `total` 至少为当前页已知数量
- 不承诺站点真实总页数

当外部传入未知分类值时：

- 不直接报空
- 自动回退到四个主分类热门列表聚合，减少壳子兼容性问题

## 搜索设计

搜索接口：

- `GET /api.php/app/search/index`

请求参数包括：

- `wd`
- `page`
- `limit=15`

返回结果统一映射为卡片结构：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_remarks`
- `type_name`
- `vod_year`
- `vod_area`

空关键字直接返回空结果，不发起请求。

## 详情页设计

详情接口：

- `GET /api.php/web/vod/get_detail?vod_id=<id>`

接口可能返回对象或数组，设计上统一兼容：

- 若为数组则取首项
- 若为空则返回空 `list`

详情输出字段至少包含：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_remarks`
- `vod_year`
- `vod_area`
- `vod_actor`
- `vod_director`
- `vod_content`
- `type_name`
- `vod_play_from`
- `vod_play_url`

说明：

- `vod_content` 需移除 HTML 标签并把段落、换行转为纯文本
- `type_name` 优先取站点详情中的分类字段

### 播放线路重组

站点详情返回的原始播放字段：

- `vod_play_from`
- `vod_play_url`

两者都可能以 `$$$` 分组，以 `#` 分集，以 `$` 分割标题和地址。

实现时将其重组为仓库侧可用格式：

- 每个线路名显示为 `线路名(集数)`
- 每个分集地址编码为 `标题$线路名@1@原始地址`

规则：

- 空线路组跳过
- 分集无标题时兜底为“播放”
- 没有线路名时兜底为 `lineN`

## 播放设计

播放阶段优先消费详情中编码后的 `线路名@1@原始地址`。

### 输入解析

支持三类输入：

- `线路名@1@原始地址`
- 直接 `http/https` 地址
- 未带前缀的原始地址

解析规则：

- `@1@` 表示需要调用解码接口
- 已经是绝对地址时直接透传
- 未带协议且未带前缀时视为需要解码

### 解码接口

- `GET /api.php/app/decode/url/?url=<raw>&vodFrom=<from>`

返回结构可能是：

- `data` 为字符串
- `data.url`
- `url`

实现时依次兼容提取。

### 输出规则

播放器结果字段：

- `parse = 0`
- `playUrl = ""`
- `url = 最终地址`

当最终地址属于以下站点时，额外标记需要嗅探：

- `iqiyi.com`
- `v.qq.com`
- `youku.com`
- `mgtv.com`
- `bilibili.com`

兼容策略：

- 仓库现有 Spider 接口不统一消费 `jx`
- 本次实现仍保留 `jx` 字段，便于上层兼容支持

解码失败时：

- 回退返回原始输入地址
- 不抛出异常

## 测试设计

新增 `tests/test_步步影视.py`，使用 `unittest` 和 `unittest.mock`，不访问真实网络。

首批测试覆盖：

- 签名头包含必要字段，`web` 头附带 `web-sign/X-Client`
- `homeContent` 返回固定分类与筛选
- `homeVideoContent` 可从首页接口提取分类和视频，并在失败时走主分类聚合
- `categoryContent` 正确拼接查询参数并映射列表
- 未知分类触发主分类聚合回退
- `searchContent` 对空关键字不发请求，对有效关键字正确构造参数
- `detailContent` 兼容对象和数组详情，能完成 HTML 简介清洗
- 播放线路重组能处理多线路、多分集和空标题兜底
- `playerContent` 能解析编码播放 ID，并在需要时调用解码接口
- 解码结果兼容 `data/data.url/url` 三种结构

验证顺序：

- 先跑 `tests/test_步步影视.py`
- 通过后再视情况补跑更大范围测试

## 风险与取舍

主要风险：

- 站点接口签名字段未来可能变更
- 首页与分类接口的真实响应结构可能出现字段漂移
- 解码接口返回格式不稳定

本次取舍：

- 优先保证接口兼容和测试可维护性
- 不为未知响应结构做过度抽象
- 不引入真实联网测试，避免把站点波动带进单测
