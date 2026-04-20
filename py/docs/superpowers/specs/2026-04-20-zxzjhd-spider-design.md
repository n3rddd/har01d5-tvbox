# 在线之家 Python 爬虫设计

## 目标

在当前 Python 仓库中新增一个符合 `base.spider.Spider` 接口的在线之家站点爬虫，覆盖以下能力：

- 首页分类与筛选
- 分类列表
- 搜索
- 详情解析
- 播放解析

实现基于站点 HTML 页面结构，不引入 JS 服务端路由层，不修改 `base/` 公共层，并且保留详情页中的网盘分享线路。

## 范围

本次实现包含：

- 新增独立脚本，文件名为 `在线之家.py`
- 使用单一站点主域：`https://www.zxzjhd.com`
- 支持 `home/category/detail/search/player` 主链路
- 首页返回固定分类与静态筛选配置
- 详情页同时输出普通播放线路和网盘分享线路
- `playerContent` 对普通线路执行 `zxzj` 解密，对网盘线路直接透传分享链接

本次实现不包含：

- 参考 JS 中的 Fastify 路由封装
- 网盘驱动对象注入、驱动缓存映射、网盘目录展开
- 浏览器自动化或 JS 执行环境
- 多域名探活与自动切换
- 登录态、Cookie 常驻维护、反爬绕过

## 方案选择

采用仓库现有的“单站点单文件 + 单测”方案：

- 对外保持 `Spider` 接口兼容
- 对内拆分为请求封装、筛选路径拼接、列表解析、详情解析、播放解析几个 helper
- 保留参考 JS 规则里的关键业务行为，但只实现 Python Spider 实际需要的部分

不引入 JS 版 drive 处理层的原因是：

- 当前 Python 仓库没有统一的 drive 注入协议
- 现有同类蜘蛛对网盘资源的惯例是保留线路名与分享链接，让上层插件处理
- 本次重点是 HTML 解析、数据整形和 `zxzj` 播放解密，不是中间层编排

## 模块边界

新增脚本只在站点文件内部维护逻辑，不修改 `base/`。

脚本内部职责拆分如下：

- `init`
  - 初始化主域、请求头、固定分类、筛选项与筛选默认值
- `homeContent`
  - 返回固定 `class` 与 `filters`
- `homeVideoContent`
  - 返回空列表，不额外抓首页推荐
- `categoryContent`
  - 根据分类、筛选和分页拼出 URL，请求 HTML 并解析卡片
- `searchContent`
  - 根据关键词请求搜索页并解析结果
- `detailContent`
  - 请求详情页，提取影片元数据、普通播放线路和网盘线路
- `playerContent`
  - 对 `zxzj` 普通线路做播放解密，对网盘线路直接透传分享链接
- 私有辅助函数
  - 补全相对地址
  - 清理文本
  - 修复 JSON 包裹 HTML
  - 拼接筛选路径
  - 解析卡片列表
  - 提取详情字段
  - 提取标签页与剧集列表
  - 提取播放页中的网盘分享链接
  - 识别网盘类型
  - 执行 `zxzj` 解密

## Host 与请求策略

本次只实现单域：

- `https://www.zxzjhd.com`

请求统一通过 `self.fetch` 发起，固定请求头至少包含：

- `User-Agent`
- `Referer: https://www.zxzjhd.com/`

请求原则：

- HTML 请求超时固定为 10 秒
- 请求失败时返回空 HTML 或空结果，不抛出未处理异常
- 对字符串响应先尝试修复 JSON 包裹 HTML 的情况，避免站点返回 `"<!doctype html...>"` 这种包裹值时解析失败
- 不引入浏览器执行，也不依赖外部解压、解密服务

## 分类与筛选设计

首页分类固定为：

- `1 -> 电影`
- `2 -> 美剧`
- `3 -> 韩剧`
- `4 -> 日剧`
- `5 -> 泰剧`
- `6 -> 动漫`

筛选配置直接内置到脚本中，字段与参考实现保持一致：

- `class`
- `area`
- `year`
- `by`

筛选默认值保留 `cateId`，通过分类 id 决定。

筛选 URL 规则采用模板拼接：

- `{{fl.cateId}}-{{fl.area}}-{{fl.by}}-{{fl.class}}-----fypage---{{fl.year}}`

输出路径再包到：

- `/vodshow/<filter-path>.html`

规则说明：

- `cateId` 来自当前分类默认配置
- `class/area/year/by` 来自传入的 `extend`
- 缺失筛选值时保留空段，不重排位置
- 当前仓库约定不返回 `pagecount`，分类结果只返回 `list/page/limit/total`

`homeContent` 返回：

- `class`
- `filters`

不返回首页推荐列表。

## 列表与搜索设计

分类页和搜索页均解析 `stui-vodlist` 卡片结构。

卡片提取字段：

- 标题：`a[title]`
- 图片：`data-original`，缺失时回退到 `data-src` 或 `src`
- 备注：`.pic-text`
- 链接：`a[href]`

输出统一卡片结构：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_remarks`

其中 `vod_id` 保留短详情路径，而不是完整 URL，形式为：

- `voddetail/12345.html`

或等价的相对详情路径片段。

这样可以遵循仓库当前短 id 约定，避免把完整域名泄露到列表结果里。

搜索接口使用：

- `/vodsearch/<关键词>-------------.html`

搜索直接请求完整搜索页 HTML，不做 POST，也不做二次过滤。

分页策略采用保守估计：

- 分类页 `limit` 固定为 24
- 搜索结果 `limit` 使用结果数
- `total` 采用 `page * 30 + len(items)` 的仓库常见保守写法
- 不返回 `pagecount`

## 详情页设计

详情页解析以下字段：

- 标题
- 封面
- 简介
- 年份
- 地区
- 类型
- 导演
- 主演
- 更新信息或集数备注

详情输出字段至少包含：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_content`
- `vod_remarks`
- `vod_year`
- `vod_area`
- `vod_class`
- `vod_lang`
- `vod_director`
- `vod_actor`
- `vod_play_from`
- `vod_play_url`

图片地址统一补全为完整 URL，修复站点相对路径与 `//` 形式地址。

详情页播放来源分为两组：

1. 普通站内线路
   - 来源于详情页的播放标签和对应剧集列表
   - 不保留原站复杂线路名，统一归并成 `zxzj`
   - 每条剧集格式为 `名称$<play-id>`
   - 同一普通线路下多集使用 `#` 连接
2. 网盘线路
   - 来源于详情页标签中明显标记为网盘、百度、夸克、UC、阿里、迅雷的线路
   - 详情页中的剧集链接先指向站内播放页，不直接给出分享链接
   - 需要继续请求这些播放页，读取其中 `player_aaaa.url`
   - 如果 `player_aaaa.url` 是分享地址，则按网盘类型分组保留

网盘线路识别范围：

- `baidu`
- `quark`
- `uc`
- `aliyun`
- `xunlei`

网盘类型优先通过分享链接域名识别：

- `pan.baidu.com` -> `baidu`
- `pan.quark.cn` -> `quark`
- `drive.uc.cn` -> `uc`
- `alipan.com` 或 `aliyundrive.com` -> `aliyun`
- `pan.xunlei.com` -> `xunlei`

如果标签名称与域名不一致，以分享链接域名为准。

网盘线路保留策略：

- 每种网盘类型单独作为一条线路
- 每个条目格式为 `剧集名$分享链接`
- 按分享链接去重，保留第一次出现的标题
- 没有有效分享链接的网盘项直接跳过

最终线路组合规则：

- `vod_play_from` 为 `zxzj$$$quark$$$baidu` 这类拼接形式
- `vod_play_url` 与线路顺序严格对应
- 没有普通线路时，不强行保留 `zxzj`
- 没有网盘线路时，只返回普通线路

## 播放设计

`playerContent(flag, id, vipFlags)` 按来源分流。

### 普通线路 `zxzj`

输入 `id` 为相对播放路径或短播放 id 时，先补全为完整播放页 URL，再执行以下流程：

1. 请求播放页
2. 提取页面中指向 `jx.zxzj` 的中间页 URL
3. 请求中间页
4. 提取 `result_v2` JSON 中的加密串
5. 执行参考实现中的解密算法：
   - 先翻转字符串
   - 按两位十六进制转字符
   - 移除中间插入的 7 位混淆字符
6. 如果解密结果为媒体直链，则返回直链

成功返回：

- `parse = 0`
- `jx = 0`
- `url = 解密后的媒体地址`
- `header.Referer = 中间页 URL`

如果任一步失败，则回退为原播放页地址，返回：

- `parse = 1`
- `jx = 1`
- `url = 播放页 URL`

### 网盘线路

当 `flag` 为以下值之一时视为网盘线路：

- `baidu`
- `quark`
- `uc`
- `aliyun`
- `xunlei`

对网盘线路不做二次解析，直接透传分享链接：

- `parse = 0`
- `jx = 0`
- `url = 原始分享链接`
- `header = {}`

这样可以保持和仓库内现有带网盘蜘蛛的一致行为，让上层网盘插件继续接管。

## 解析与兼容性策略

为了降低页面结构波动影响，实现上采用“XPath/HTML 结构优先，正则兜底”的策略：

- 列表与搜索主走 XPath
- 详情字段主走 XPath 或相邻文本提取
- 播放页 `player_aaaa` 与中间页 `result_v2` 使用正则提取
- 网盘分享链接通过播放页内嵌 JSON 提取

文本处理原则：

- 缺失字段返回空字符串
- 标题、备注、简介统一做空白折叠
- 多值字段使用逗号连接
- 简介保留段落换行，不保留多余空白

URL 处理原则：

- 相对路径补全为完整 URL
- 列表和搜索输出短 `vod_id`
- 详情内普通剧集输出短 `play-id`
- 网盘线路保留完整分享链接

## 测试设计

新增测试文件：

- `tests/test_在线之家.py`

测试全部使用 `unittest` 和 `unittest.mock`，不访问真实网络，覆盖以下行为：

1. 首页
   - 断言分类 id 和筛选 key 正确输出
2. 分类 URL
   - 断言筛选模板拼接出的路径符合站点规则
3. 列表解析
   - 断言能提取短 `vod_id`、标题、封面和备注
4. 搜索解析
   - 断言能解析搜索页卡片
5. 详情解析
   - 断言能提取标题、封面、简介、年份、地区、类型、导演、主演
   - 断言普通线路统一输出为 `zxzj`
   - 断言网盘播放页会被继续请求并转成 `baidu/quark/uc/aliyun/xunlei` 线路
   - 断言网盘链接按分享链接去重
6. 播放解密
   - 断言 `zxzj` 解密算法能还原媒体地址
   - 断言 `playerContent` 对普通线路成功返回直链
   - 断言解密失败时回退到播放页地址
7. 网盘播放分流
   - 断言 `playerContent` 对 `baidu/quark/uc/aliyun/xunlei` 直接透传分享链接

## 风险与约束

- 站点反爬较强，真实页面可能偶发返回包裹字符串或异常结构，因此实现只保证对已知 HTML 结构稳健解析
- 网盘分享链接需要额外请求网盘播放页，详情阶段请求数会比普通站点更高
- 普通线路统一命名为 `zxzj` 是刻意收敛行为，丢弃了站点原始标签名，但换来更稳定的播放分流
- 该实现不承担网盘目录展开和鉴权，依赖上层现有网盘插件消费分享链接

## 验收标准

完成后应满足以下结果：

- 新增 `在线之家.py`，且不修改 `base/`
- `home/category/search/detail/player` 五条主链路都有单测覆盖
- 列表和搜索输出短 `vod_id`
- 详情页能同时输出普通线路和网盘线路
- 网盘线路按 `baidu/quark/uc/aliyun/xunlei` 标准名返回
- `playerContent("zxzj", ...)` 能执行解密并优先返回直链
- `playerContent(<网盘线路>, ...)` 直接返回分享链接
- 相关单测可在本仓库的 `unittest` 环境中稳定运行
