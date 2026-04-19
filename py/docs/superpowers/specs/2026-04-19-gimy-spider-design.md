# Gimy剧迷 Python 爬虫设计

## 目标

在当前 Python 仓库中新增一个符合 `base.spider.Spider` 接口的 Gimy剧迷站点爬虫，覆盖以下能力：

- 首页分类
- 首页推荐视频
- 分类列表
- 搜索
- 详情解析
- 播放解析

实现基于网页 HTML 抓取与播放页脚本解析，不依赖 Playwright，不修改 `base/` 公共层。

## 范围

本次实现包含：

- 新增独立脚本，文件名为 `剧迷.py`
- 使用单一站点主域：`https://gimyai.tw`
- 支持 `home/homeVideo/category/detail/search/player` 全链路
- 支持分类排序筛选
- 支持多线路详情播放列表
- 支持搜索结果精筛
- 支持播放页直链提取与 `parse.php` 回退解析

本次实现不包含：

- 多域名自动回退
- Cloudflare 或其他风控绕过
- 第三方繁转简依赖
- 参考 JS 中全部兼容分支的 1:1 平移
- 通用电影网站抽象层

## 方案选择

采用仓库风格的单文件拆分方案：

- 对外保持当前仓库统一的 `Spider` 接口
- 对内拆成列表解析、详情解析、搜索精筛、播放解析、文本清洗与繁转简几个独立 helper
- 优先复用当前仓库里 HTML 站点的实现风格，而不是逐行翻译参考 JS

不做逐行平移的原因是：

- 当前仓库以单站点单文件为主，便于维护和测试
- 参考 JS 中包含动态依赖探测和运行时日志逻辑，Python 版只保留真正影响解析结果的核心链路
- 本次目标是先把常见场景稳定覆盖，而不是追求所有历史兼容分支同步迁移

## 模块边界

新增脚本只在站点文件内部维护逻辑，不修改 `base/`。

脚本内部职责拆分如下：

- `init`
  - 初始化主域、请求头、分类配置、筛选配置
- `homeContent`
  - 返回固定分类与筛选定义
- `homeVideoContent`
  - 抓取首页卡片，返回首页推荐列表
- `categoryContent`
  - 构造分类页 URL 并解析卡片
- `detailContent`
  - 请求详情页并整理影片元信息与多线路剧集列表
- `searchContent`
  - 请求站内搜索页，解析原始结果并做关键词精筛
- `playerContent`
  - 解析播放页脚本，优先直取媒体地址，失败时回退到 `parse.php` 或播放页
- 私有辅助函数
  - URL 归一化
  - HTML 文本清洗
  - 精简繁转简映射
  - 列表卡片解析
  - 详情字段提取
  - 播放页脚本提取和 URL 解码
  - 搜索关键词归一化与打分

## Host 与请求策略

本次只实现单域：

- `https://gimyai.tw`

请求头固定为浏览器样式，至少包含：

- `User-Agent`
- `Accept-Language`
- `Referer`
- `Accept`

对播放页和 `parse.php` 请求，按需要补充：

- `Origin`

请求策略保持轻量：

- 所有页面请求统一走 `self.fetch`
- 默认超时取 10 秒到 20 秒之间的站点级固定值
- 非 200 响应统一回退为空 HTML 或在播放解析时进入回退流程

不做：

- host 探活切换
- 重试队列
- 代理层改造

## 分类与筛选设计

分类固定为：

- `1 -> 电影`
- `2 -> 电视剧`
- `4 -> 动漫`
- `29 -> 综艺`
- `34 -> 短剧`
- `13 -> 陆剧`

筛选只支持排序字段 `by`，候选值为：

- `time`
- `hits`
- `score`

`homeContent` 返回：

- `class`
- `filters`

其中 `filter_def` 只在站点内部用于默认值，不额外暴露到返回结构。

## 首页与列表设计

### 首页推荐

`homeVideoContent` 直接请求首页 HTML，并复用列表卡片解析逻辑。

卡片解析范围：

- 详情链接包含 `/detail/`
- 标题优先取 `title`
- 回退 `img alt`
- 再回退 `.title`、`.video-text`、标题标签文本或卡片文本
- 封面优先取 lazyload 属性，再回退 `img src` 或背景图样式
- 备注从卡片或父容器文本中抓取常见状态文案，例如：
  - `更新至第X集`
  - `全X集`
  - `HD`
  - `TC`
  - `抢先版`

首页推荐只返回前 24 条，保持与参考代码一致。

### 分类列表

分类 URL 模式：

- `/genre/<tid>.html`
- 当 `page > 1` 或排序不为 `time` 时追加 `?page=<pg>&by=<sort>`

返回分页字段：

- `page = 当前页`
- `pagecount = pg + 1`，当页命中数量达到列表页常规规模时递增
- `limit = 20`
- `total = pg * 20 + 当前条数`

这里的总数是近似值，和当前仓库其他 HTML 站点的处理方式保持一致，不承诺真实总数。

## 文本清洗与繁转简

站点内容与搜索结果里可能混有繁体字。为了保证搜索命中率和展示稳定性，脚本内部会提供两层处理：

- `normalizeText`
  - 去 HTML 标签
  - 去 `&nbsp;`
  - 压缩空白
- `convertTraditionalToSimplified`
  - 使用内置映射表做精简繁转简

不引入 `opencc` 或其他第三方库，原因是：

- 当前仓库未配置相关依赖
- 本次只需要覆盖站点常见影视字段和搜索词，不需要通用全文转换
- 减少安装和运行环境差异

映射表优先覆盖：

- 影视分类词
- 常见标题用字
- 搜索噪声词

展示用文本通过 `toDisplayText` 统一进入“清洗 + 繁转简”链路。

## 搜索设计

搜索 URL：

- `/find/-------------.html?wd=<keyword>&page=<pg>`

搜索流程分两步：

1. 解析原始卡片列表
2. 对原始列表做关键词精筛

关键词精筛策略保留参考实现的核心思路：

- 对关键词和片名统一做繁转简
- 去空格、破折号、标点和括号
- 移除常见噪声后缀，例如：
  - `线上看`
  - `全集`
  - `连续剧`
  - `电视剧`
  - `动漫`
  - `电影`
  - `综艺`
- 衍生 token：
  - 原始归一化词
  - 去噪声词后的词
  - 去掉结尾集数或纯数字后的词
- 打分规则：
  - 完全相等最高
  - 前缀匹配次之
  - 包含匹配再次之
  - 片名较短且被 token 包含作为弱命中

若打分结果为空，再回退到宽松包含匹配，避免误把合法结果全部过滤掉。

## 详情页设计

详情 URL 模式：

- `/detail/<id>.html`

`detailContent` 支持传入：

- 纯数字详情 id
- 完整详情 URL

输出字段包含：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_content`
- `vod_remarks`
- `type_name`
- `vod_year`
- `vod_area`
- `vod_actor`
- `vod_director`
- `vod_play_from`
- `vod_play_url`

字段提取策略：

- 标题优先取详情页主标题，回退页面 `<title>`
- 封面优先取 `og:image`，再回退详情图区域图片
- 剧情简介优先取详情正文区域，回退 `meta description`
- `状态`、`类别`、`年代`、`国家/地区` 通过标签名前缀匹配提取
- `主演` 与 `导演` 优先从带链接的列表区域提取并以逗号连接

### 多线路播放列表

详情页的线路和剧集采用 tab + playlist 容器结构：

- 线路名从 `#playTab a[href^='#con_playlist_']` 提取
- 每个 tab 内的剧集链接从 `/play/<id>.html` 提取
- 单集格式为 `集名$play_id`

最终按当前仓库约定输出：

- `vod_play_from = 线路A$$$线路B`
- `vod_play_url = 第1集$100-1-1#第2集$100-1-2$$$正片$100-2-1`

## 播放解析设计

播放 URL 模式：

- `/play/<play_id>.html`

`playerContent` 支持传入：

- 紧凑 `play_id`
- 完整播放页 URL

### 播放页数据提取

核心信息来自页面脚本中的 `player_data`：

- `url`
- `encrypt`
- `from`

提取方式：

- 用正则抓取 `var player_data = {...}`
- JSON 解析失败则视为无数据

### URL 解码策略

保留参考实现的解码规则：

- `encrypt = 0`
  - 原样使用
- `encrypt = 1`
  - URL decode
- `encrypt = 2`
  - base64 decode 后再尝试 URL decode

### 播放优先级

1. 若解码后的 `rawUrl` 已经是以 `m3u8/mp4/flv/m4s` 结尾的媒体地址，直接返回：
   - `parse = 0`
   - `url = rawUrl`
2. 若 `rawUrl` 非空但不是直接媒体地址，则根据线路名构造解析器地址：
   - 默认 `https://play.gimyai.tw/v/parse.php`
   - `JD4K/JD2K/JDHG/JDQM` 走 `/d/parse.php`
   - `NSYS` 走 `/n/parse.php`
3. 若 `parse.php` 返回 JSON，优先读取：
   - `url`
   - `video`
   - `playurl`
4. 若解析器没有给出直链，但 `rawUrl` 自身是 http 地址，则返回：
   - `parse = 1`
   - `jx = 1`
   - `url = rawUrl`
5. 全部失败时回退返回播放页地址，保证行为可用：
   - `parse = 1`
   - `jx = 1`
   - `url = 播放页 URL`

### 返回头策略

直链成功时按场景返回最小必要头：

- 直接媒体地址：
  - 保留浏览器 `User-Agent`
  - `Referer = 播放页`
- `parse.php` 成功：
  - `Referer = 对应解析页`
  - `Origin = 解析页 origin`

## 错误处理策略

站点脚本应尽量返回空结构或回退值，而不是把异常直接抛到上层。

原则如下：

- 列表页请求失败时返回空列表分页
- 详情页单条失败时可跳过当前 id，避免批量请求全失败
- 播放解析失败时优先回退到播放页 URL
- JSON 解析失败一律回退空字典或空字符串

不做细粒度错误分类，只做站点级稳妥回退。

## 测试设计

新增测试文件：

- `tests/test_剧迷.py`

测试只做离线单元测试，使用 `patch` mock 网络请求，不依赖真实站点。

重点覆盖以下行为：

1. `homeContent`
   - 返回固定分类和 `filters`
2. 列表卡片解析
   - 能提取 `vod_id`、`vod_name`、`vod_pic`、`vod_remarks`
3. `detailContent`
   - 能解析基础字段和多线路播放列表
4. 搜索精筛
   - 简体关键词能命中繁体标题
   - 噪声后缀不会挤掉正确结果
5. `playerContent`
   - 直接媒体地址时返回 `parse=0`
   - `parse.php` 成功时返回解析后的直链
   - `parse.php` 失败时能回退到原始 URL 或播放页
6. 解码辅助函数
   - 覆盖 `encrypt=0/1/2`

测试风格对齐：

- `tests/test_dbku.py`
- `tests/test_youknow.py`

## 非目标与风险

本次实现明确不覆盖：

- 多 host 灾备
- 强风控页面或验证码绕过
- 站点未来改版后的自适应恢复
- 通用繁转简库级别的高完整度转换

主要风险如下：

- Gimy 的 DOM 类名若调整，列表和详情解析会失效
- 播放解析依赖 `player_data` 和 `parse.php` 的现有格式，若接口切换需单独修复
- 精简繁转简映射只覆盖常见影视词，极少数片名可能仍然需要宽松匹配兜底

## 实施顺序

推荐实施顺序如下：

1. 先写 `tests/test_剧迷.py`，覆盖卡片、详情、搜索和播放关键行为
2. 运行测试确认红灯
3. 实现 `剧迷.py` 的基础结构与 helper
4. 逐步补齐搜索精筛与播放解析，直到测试转绿
5. 最后运行站点测试集合做回归确认
