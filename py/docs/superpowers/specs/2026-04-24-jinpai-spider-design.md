# 金牌 Python 爬虫设计

## 目标

在当前 Python 仓库中新增一个符合 `base.spider.Spider` 接口的金牌爬虫，行为参考用户提供的 JS 版本，覆盖以下能力：

- 首页分类与筛选
- 首页推荐
- 分类浏览
- 搜索
- 详情解析
- 播放解析

实现形式遵循当前仓库的单文件 Spider 约定和离线单测约定，不引入新的公共基类。

## 范围

本次实现包含：

- 新增独立脚本 `py/金牌.py`
- 新增独立测试 `py/tests/test_金牌.py`
- 实现带签名头的匿名 API 请求
- 动态拉取分类与筛选
- 首页返回热门推荐
- 分类支持类型、剧情、地区、语言、年份、排序筛选
- 搜索支持分页与空关键词保护
- 详情组装基础元数据与单线路剧集
- 播放接口返回多清晰度直链列表

本次实现不包含：

- 修改 `base/` 公共层
- 引入新的第三方依赖
- 真实联网集成测试
- 站点探活、容灾切换或缓存
- 参考 JS 的 HTTP 路由包装层

## 方案选择

采用“单文件 Spider + helper + 单测”的直接适配方案，而不是抽象新的签名 API 基类。

原因如下：

- 当前仓库绝大多数站点都以单文件 Spider 交付，新增公共基类会放大本次范围
- 参考实现已经清晰给出了接口路径、签名算法和字段映射，直接适配风险最低
- 当前需求重点是完整还原站点能力，而不是为未知后续站点提前抽象

## 模块边界

新增 `py/金牌.py`，只在模块内部维护站点逻辑，不修改 `base/`。

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

- `_obj_to_form`
  - 将请求参数按 `k=v&...` 拼接，忽略空值
- `_signed_headers`
  - 根据请求参数、`APP_KEY` 和时间戳生成签名头
- `_fetch_json`
  - 统一发起 GET 请求、校验状态码并解析 JSON
- `_map_vod`
  - 统一列表项字段映射
- `_build_filters`
  - 请求分类接口与筛选接口并组装首页筛选结构
- `_page_result`
  - 统一分类和搜索的分页返回结构
- `_build_play_id`
  - 将主视频 ID 与分集 ID 组合成短播放 ID
- `_parse_play_id`
  - 解析 `主ID@子ID` 形式的播放 ID

## 站点配置与签名策略

固定配置来自参考实现：

- 站点名：`金牌`
- 主站：`https://m.jiabaide.cn`
- 默认 UA：移动端 Chrome UA
- `Referer`：`${host}/`
- `APP_KEY`：`cb808529bae6b6be45ecfab29a4889bc`

签名规则保持与参考实现一致：

1. 取当前毫秒时间戳作为 `t`
2. 将请求参数与 `key=APP_KEY`、`t` 合并
3. 按 `k=v&...` 形式拼接
4. 先对拼接字符串做 `MD5`
5. 再对 `MD5` 结果做 `SHA1`
6. 将 `t` 和 `sign` 放入请求头

请求策略：

- 接口请求统一使用 `GET`
- 参数通过 query string 传递
- 请求头统一带 `User-Agent`、`Referer`、`t`、`sign`
- 若响应状态码不是 `2xx`，或业务 `code` 不是成功值，则返回空结果而非抛出未处理异常

## 分类与首页设计

`homeContent` 负责同时返回分类、筛选和首页推荐。

分类来源：

- `/api/mw-movie/anonymous/get/filer/type`

筛选来源：

- `/api/mw-movie/anonymous/v1/get/filer/list`

首页推荐来源：

- `/api/mw-movie/anonymous/home/hotSearch`

筛选字段映射遵循参考实现：

- `typeList -> key=type, name=类型`
- `plotList -> key=class, name=剧情`
- `districtList -> key=area, name=地区`
- `languageList -> key=lang, name=语言`
- `yearList -> key=year, name=年份`
- `serialList -> key=by, name=排序`

排序选项固定为：

- 最近更新 -> `1`
- 添加时间 -> `2`
- 人气高低 -> `3`
- 评分高低 -> `4`

每个筛选项都默认插入“全部”。

`homeVideoContent` 保持仓库现有习惯，返回：

- `{"list": []}`

## 列表与搜索设计

分类接口使用：

- `/api/mw-movie/anonymous/video/list`

请求参数如下：

- `type1`
  - 当前分类 ID
- `pageNum`
  - 当前页码
- `pageSize`
  - 固定 `30`
- `sort`
  - 由筛选项 `by` 映射，默认 `1`
- `sortBy`
  - 固定 `1`
- `type`
  - 子类型筛选
- `v_class`
  - 剧情筛选
- `area`
  - 地区筛选
- `lang`
  - 语言筛选
- `year`
  - 年份筛选

搜索接口使用：

- `/api/mw-movie/anonymous/video/searchByWordPageable`

请求参数如下：

- `keyword`
- `pageNum`
- `pageSize`

返回结构遵循当前仓库约定：

- `page`
- `limit`
- `total`
- `list`

其中：

- `limit` 固定为 `30`
- 默认不返回 `pagecount`
- 空关键词搜索直接返回空列表

## 列表字段映射

列表页与搜索页的单项统一映射为：

- `vod_id`
  - `vodId`
- `vod_name`
  - `vodName`
- `vod_pic`
  - `vodPic`
- `vod_remarks`
  - `vodRemarks` 与 `vodDoubanScore` 以 `_` 连接，空值自动忽略
- `vod_year`
  - 优先从 `vodPubdate` 提取年份
- `type_id`
  - `typeId`
- `type_name`
  - `typeName`

这样首页推荐、分类和搜索的列表结构保持一致。

## 详情设计

详情接口使用：

- `/api/mw-movie/anonymous/video/detail`

请求参数：

- `id`

详情返回只保留当前仓库需要的核心字段：

- `vod_id`
- `vod_name`
- `vod_pic`
- `type_name`
- `vod_remarks`
- `vod_year`
- `vod_area`
- `vod_lang`
- `vod_director`
- `vod_actor`
- `vod_content`
- `vod_play_from`
- `vod_play_url`

剧集列表来自 `episodeList`，每一集的播放 ID 设计为：

- `<vodId>@<nid>`

播放线路先收敛为单条：

- `金牌线路`

这样可以兼容仓库现有以 `vod_play_from` / `vod_play_url` 为核心的详情结构，同时避免把上游清晰度层级提前展开到详情页。

## 播放设计

播放接口使用：

- `/api/mw-movie/anonymous/v2/video/episode/url`

请求参数如下：

- `clientType=3`
- `id`
  - 主视频 ID
- `nid`
  - 分集 ID

播放页逻辑：

- 从 `主ID@子ID` 解析出 `id` 和 `nid`
- 请求上游接口拿到 `list`
- 将上游返回的多清晰度地址整理为播放器可消费的结果

播放器返回结构：

- `parse: 0`
- `playUrl: ""`
- `url`
  - 优先返回首个可用地址
- `header`
  - 至少包含移动端 `User-Agent`

不额外引入 `pagecount`、`urls` 或其他参考 JS 的扩展字段，优先保持与当前 Python 仓库播放器返回习惯一致。

同时，为了兼容仓库中部分站点会保留扩展信息，模块内部仍会保留原始清晰度列表的整理逻辑；若调用方仅消费 `url`，则使用首个可用地址即可。

异常策略：

- 播放 ID 不是 `主ID@子ID` 格式时，返回空 URL
- 上游返回空列表时，返回空 URL

## 错误处理

所有公开接口都以“尽量返回空结果”作为失败策略：

- `homeContent`
  - 失败时返回空分类、空筛选、空推荐
- `categoryContent`
  - 失败时返回 `page/limit/total/list` 的空结构
- `searchContent`
  - 失败时返回空分页结果
- `detailContent`
  - 失败时返回 `{"list": []}`
- `playerContent`
  - 失败时返回空 URL

不向上抛出未处理异常，保持与现有仓库 Spider 的容错风格一致。

## 测试设计

新增 `py/tests/test_金牌.py`，全部通过 mock 网络层验证离线行为。

至少覆盖以下测试：

1. `_signed_headers` 会写入 `t` 和正确的 `sign`
2. `homeContent` 能组合分类、筛选和首页推荐
3. `categoryContent` 能把 `by/class/area/lang/year/type` 正确映射到请求参数
4. `searchContent` 对空关键词直接返回空列表，对正常结果正确映射
5. `detailContent` 能输出基础元数据、单线路名与 `主ID@子ID` 剧集串
6. `playerContent` 能拆分播放 ID、请求上游并返回首个可用播放地址
7. 公开接口在上游异常或空数据时返回约定的空结构

测试原则：

- 不依赖真实网络
- 尽量验证最小行为单元
- 对签名和请求参数做精确断言，避免只测结果不测协议

## 风险与约束

主要风险如下：

- 上游匿名接口的业务 `code` 语义可能并不完全稳定，需要测试中明确覆盖成功与失败分支
- 参考 JS 的 `play` 返回了多清晰度数组，而仓库 Python Spider 通常以单个 `url` 为主，需要在实现中做兼容收敛
- 详情中的 `vodClass`、`vodYear`、`vodArea` 等字段可能出现缺失，需要统一空值兜底

对应约束如下：

- 优先保证仓库消费兼容性，而不是 1:1 复刻 JS 返回结构
- 不额外改动公共播放器约定
- 所有行为变化都必须由离线测试先定义再实现
