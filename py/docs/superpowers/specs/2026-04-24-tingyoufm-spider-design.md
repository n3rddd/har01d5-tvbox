# 听友FM Python 爬虫设计

## 目标

在当前 Python 仓库中新增一个符合 `base.spider.Spider` 接口的听友 FM 站点爬虫，行为参考用户提供的 JS 版本，但交付物遵循当前仓库的单文件 Spider 结构和测试约定。

本次设计覆盖以下能力：

- 首页分类
- 首页推荐
- 分类列表
- 搜索
- 专辑详情
- 章节播放

## 范围

本次实现包含：

- 新增独立脚本 `py/听友FM.py`
- 新增独立测试 `py/tests/test_听友FM.py`
- 首页与分类优先解析页面结构和 `__NUXT_DATA__`
- 搜索优先解析搜索页中的 Nuxt 数据，失败时回退 DOM
- 详情页解析专辑元信息和章节列表
- 播放优先请求 `/api/play_token` 获取直链
- `/api/play_token` 支持参考实现中的加密响应解包逻辑
- 播放失败时回退到 `/audios/{albumId}/{chapterIdx}` 页面
- 为新增行为补齐离线 `unittest`

本次实现不包含：

- 修改 `base/` 公共层
- 引入新的第三方依赖
- 真实联网集成测试
- 浏览器嗅探执行能力
- 长期可用的硬编码匿名凭证管理

## 方案选择

采用“页面解析为主，播放接口为主链”的方案，而不是把所有能力都绑定到加密 API。

原因如下：

- 用户已明确要求分类和详情优先走页面结构与 Nuxt 数据
- 当前仓库的 Python Spider 更适合做 HTML 与 JSON 的离线可测解析
- 听友 FM 的播放加密链路只对 `playerContent` 是刚需，列表和详情没必要强耦合
- 当鉴权或解密链路波动时，首页、分类、搜索和详情仍可独立工作

## 模块边界

新增模块 `py/听友FM.py` 只负责站点逻辑，不修改 `base/`。

模块对外实现以下接口：

- `init`
- `getName`
- `homeContent`
- `homeVideoContent`
- `categoryContent`
- `detailContent`
- `searchContent`
- `playerContent`

模块内部拆分以下 helper：

- `_get_headers`
  - 统一请求头和可选鉴权头
- `_get_html`
  - 发起页面请求并返回文本
- `_api_post`
  - 统一请求 `/api/*` 接口
- `_encrypt_payload`
  - 发送 API 请求前按站点规则加密请求体
- `_decrypt_payload`
  - 解包接口返回的十六进制 payload
- `_decode_nuxt_value`
  - 还原 `__NUXT_DATA__` 中的引用表
- `_parse_home_cards`
  - 首页推荐卡片解析
- `_parse_category_nuxt`
  - 分类页专辑数据解析
- `_parse_detail_page`
  - 专辑详情和章节列表解析
- `_parse_search_nuxt`
  - 搜索结果解析
- `_extract_play_url`
  - 从 `play_token` 解包结果中抽取音频直链

## 站点配置

固定站点配置如下：

- 站点名：`听友FM`
- 站点根地址：`https://tingyou.fm`
- 请求头包含桌面浏览器 `User-Agent`
- 页面请求默认带 `Referer` 与 `Origin`
- 分类使用固定映射：
  - `46 -> 有声小说`
  - `11 -> 武侠小说`
  - `19 -> 言情通俗`
  - `21 -> 相声小品`
  - `14 -> 恐怖惊悚`
  - `17 -> 官场商战`
  - `15 -> 历史军事`
  - `9 -> 百家讲坛`

请求体加密配置沿用参考实现中的固定值：

- `PAYLOAD_KEY_HEX`
- `PAYLOAD_VERSION = 1`

这些值只在模块内部使用，不外露到公共层。

## 首页、分类与搜索设计

`homeContent` 返回：

- `class`
- `list`

首页解析策略：

- 先抓取站点首页 HTML
- 从页面上的 `/categories/{id}` 链接提取分类
- 若页面未给出足够分类，则回退到固定分类映射
- 从首页中的 `/albums/{id}` 卡片提取推荐内容
- 推荐卡片按 `vod_id` 去重

列表项统一映射为：

- `vod_id`
  - 来自专辑 ID
- `vod_name`
  - 来自标题、图片 alt 或卡片文本
- `vod_pic`
  - 来自卡片封面
- `vod_remarks`
  - 组合期数、连载状态、播音或作者

`categoryContent` 解析策略：

- 请求 `/categories/{categoryId}?sort=comprehensive&page={pg}`
- 优先解析 `__NUXT_DATA__` 中的 `categoryAlbums-{categoryId}`
- 若 Nuxt 数据不存在，则回退页面卡片 DOM
- 返回 `page/limit/total/list`
- `limit` 固定为当前页实际条数或使用站点默认分页大小
- 不返回 `pagecount`

`searchContent` 解析策略：

- 请求 `/search?q={keyword}`
- 先从 `__NUXT_DATA__` 中定位搜索结果数据块
- 若 Nuxt 结果缺失，则回退 DOM 中的专辑卡片
- 结果按 `vod_id` 去重
- 再按标题、备注和简介做一次本地关键词过滤
- 返回 `page/limit/total/list`

空关键字直接返回空结果：

- `{"page": 1, "limit": 0, "total": 0, "list": []}`

## 详情设计

`detailContent` 根据专辑页 `/albums/{id}` 解析单个专辑对象。

详情字段至少包含：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_content`
- `type_name`
- `vod_play_from`
- `vod_play_url`

详情页解析策略：

- 专辑名称优先取面板内标题，回退 `og:title`
- 封面优先取正文图片，回退 `og:image`
- 简介优先取 `description` 或正文简介
- 分类从信息区的 `分类:` 字段提取
- 章节列表从 `ul.chapter-list > li.chapter-item` 提取
- 每个章节的播放 ID 格式为 `{albumId}|{chapterIdx}`

播放线路固定为单线路：

- `vod_play_from = 听友FM`
- `vod_play_url = 章节名$albumId|chapterIdx#...`

## 播放与解密设计

`playerContent` 的主链路为 `/api/play_token`。

播放流程如下：

1. 解析 `id` 为 `{albumId}|{chapterIdx}`
2. 组装请求体 `{"album_id": int(albumId), "chapter_idx": int(chapterIdx)}`
3. 调用 `/api/play_token`
4. 解包接口返回内容
5. 遍历解包后的对象，抽取可能的音频直链
6. 若获取成功，返回 `parse=0` 的直链结果
7. 若失败，回退到 `/audios/{albumId}/{chapterIdx}` 页面并返回 `parse=1`

解密规则沿用用户提供说明：

- 发送请求体前使用 AES-GCM 加密为十六进制字符串
- 响应若为十六进制 payload，需要按首字节识别版本
- `version === 1`
  - 按 `version + iv(12) + cipher` 的结构做 AES-GCM 解密
- `version === 2`
  - `nonce = bytes[1..24]`
  - `cipher = bytes[25..]`
  - 解密前先对 `cipher` 做 `reverse`
  - 再按 XChaCha20-Poly1305 规则解密

Python 版本不引入外部加密库，因此实现策略如下：

- 先覆盖 AES-GCM 的 v1 收发逻辑
- 对 v2 解密提供明确的 helper 边界和测试桩
- 若本地环境缺少可用的 XChaCha20-Poly1305 实现，则保留为可注入 helper，并在测试中验证“倒序 + 调用解密器”的行为
- 生产代码中优先走可用解密器；不可用时直接回退播放页，而不是抛未处理异常

这样可以兼顾仓库的无新增依赖要求与播放链路的可维护性。

## 错误处理设计

错误处理原则为“尽量返回空结果或可回退结果，不中断主链路”：

- 页面请求失败
  - 首页、分类、搜索返回空列表
- Nuxt 数据解析失败
  - 回退 DOM 解析
- 详情页无章节
  - 返回正常元信息，播放字段置空
- `play_token` 请求失败
  - 回退到播放页 URL
- `play_token` 解密失败
  - 回退到播放页 URL
- 播放结果中未找到直链
  - 回退到播放页 URL

## 测试设计

新增 `py/tests/test_听友FM.py`，使用 `unittest` 和 `unittest.mock` 做离线测试。

测试覆盖以下行为：

- 首页从 DOM 提取分类与推荐卡片
- 分类页优先解析 `__NUXT_DATA__`
- 分类页在 Nuxt 缺失时回退 DOM
- 搜索页优先 Nuxt、失败回退 DOM
- 搜索空关键字返回空结果
- 详情页生成正确的 `vod_play_from` 和 `vod_play_url`
- AES-GCM 请求加密与 v1 响应解密
- v2 解密路径会先反转密文再调用解密器
- `playerContent` 成功返回直链
- `playerContent` 在 API 失败或无直链时回退播放页

测试不做真实联网，不依赖站点在线状态。
