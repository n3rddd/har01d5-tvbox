# 如意资源 Python 爬虫设计

## 目标

在当前 Python 仓库中新增一个符合 `base.spider.Spider` 接口的如意资源爬虫，行为参考用户提供的 JS 版本，但范围只保留基础采集能力：

- 首页分类与筛选
- 首页推荐
- 分类浏览
- 搜索
- 详情解析
- 播放解析

实现形式遵循当前仓库的单文件 Spider 约定和离线单测约定，不引入 OmniBox 专有能力，也不修改公共基类。

## 范围

本次实现包含：

- 新增独立脚本 `py/如意资源.py`
- 新增独立测试 `py/tests/test_如意资源.py`
- 顺序尝试多个采集 API，直到拿到可用 JSON
- 使用硬编码主分类、子分类和筛选项
- 首页返回分类、筛选和推荐列表
- 分类支持类型筛选和分页
- 搜索支持分页与空关键词保护
- 详情组装基础元数据与多线路播放列表
- 播放接口区分直链与待解析链接

本次实现不包含：

- 参考 JS 中的刮削重命名
- 弹幕匹配
- 嗅探能力
- 播放页探测与二次解析页面构造
- 修改 `base/` 公共层
- 真实联网集成测试

## 方案选择

采用“仓库风格重写”的方案，而不是直接把 JS 逻辑逐行搬到 Python。

原因如下：

- 当前仓库是 Python 单文件 Spider 模式，直接适配更一致
- 用户已明确只要基础采集，没必要保留 OmniBox 的包装层和状态管理
- 仓库测试习惯更适合覆盖字段映射、fallback 和播放分支，而不是复制 JS 中的运行时行为

## 模块边界

新增 `py/如意资源.py`，只在模块内部维护站点逻辑，不修改 `base/`。

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

- `_request_json`
  - 统一对多个 API 执行 GET 请求和 fallback
- `_build_query`
  - 拼接 query string，忽略空值
- `_get_pic_url`
  - 统一补全图片 URL
- `_format_vod_list`
  - 将列表接口数据映射为仓库统一字段
- `_page_result`
  - 统一列表/搜索分页返回结构
- `_resolve_type_id`
  - 根据主类和筛选结果推导最终请求的类型 ID
- `_parse_play_groups`
  - 把详情接口返回的播放来源和剧集字符串组装成 `vod_play_from` / `vod_play_url`
- `_is_direct_media_url`
  - 判断播放链接是否为明显的直链媒体地址

## 站点配置

固定配置来自参考实现：

- 站点名：`如意资源`
- API 列表：
  - `https://cj.rycjapi.com/api.php/provide/vod`
  - `https://cj.rytvapi.com/api.php/provide/vod`
  - `https://bycj.rytvapi.com/api.php/provide/vod`
- 图片主机回退：
  - `https://ps.ryzypics.com`
  - `https://ry-pic.com`
  - `https://img.lzzyimg.com`
- 默认请求头：
  - `User-Agent`
  - `Accept: application/json`
  - `Accept-Language: zh-CN,zh;q=0.9`
  - `Referer: https://cj.rycjapi.com/`
- 请求超时：
  - `10` 秒

请求策略：

- 所有采集接口统一使用 `GET`
- 若显式传入完整 URL，则直接请求该 URL
- 否则按 API 列表顺序发起请求
- 单个 API 非 `200`、JSON 解析失败或业务字段异常时，继续尝试下一个 API
- 所有 API 均失败时返回空结果而不是抛出未处理异常

## 分类与筛选设计

分类和筛选直接采用硬编码配置，避免依赖站点分类接口的不稳定性。

主分类固定为：

- `1` 电影片
- `2` 连续剧
- `3` 综艺片
- `4` 动漫片
- `35` 电影解说
- `36` 体育

子分类映射沿用参考实现，例如：

- 电影片默认落到 `7`
- 连续剧默认落到 `13`
- 综艺片默认落到 `25`
- 动漫片默认落到 `29`
- 体育默认落到 `37`

`homeContent` 返回：

- `class`
- `filters`

同时补充首页推荐列表，便于与仓库中支持推荐的蜘蛛保持一致。

筛选结构遵循当前仓库常见格式：

- 每个主分类下只暴露一个 `key=type`
- `name=类型`
- `value` 为该主分类可选的硬编码子分类

无子分类的主类不返回筛选项。

`homeVideoContent` 保持仓库现有习惯，返回：

- `{"list": []}`

## 首页、分类与搜索设计

首页推荐接口使用：

- `ac=list`
- `pg=1`
- `pagesize=20`

分类接口使用：

- `ac=list`
- `t=<最终类型ID>`
- `pg=<页码>`
- `pagesize=20`

最终类型 ID 的推导规则：

1. 若 `extend.type` 存在且非空，则直接使用该值
2. 否则若主分类存在子分类映射，则使用该主类的第一个子分类
3. 否则使用主分类 ID 本身

搜索接口使用：

- `ac=list`
- `wd=<关键词>`
- `pg=<页码>`
- `pagesize=30`

搜索结果保留接口返回的列表映射，但会额外按标题包含关键词做一次本地过滤，尽量贴近参考实现。

返回结构遵循当前仓库约定：

- `page`
- `limit`
- `total`
- `list`

其中：

- 首页推荐只返回 `list`
- 分类的 `limit` 固定为 `20`
- 搜索的 `limit` 固定为 `30`
- 默认不返回 `pagecount`

## 列表字段映射

首页推荐、分类和搜索统一映射为：

- `vod_id`
  - `vod_id`
- `vod_name`
  - `vod_name`
- `vod_pic`
  - 优先使用 `vod_pic`，必要时补全为完整 URL
- `vod_remarks`
  - 优先使用 `vod_remarks`，否则退回年份
- `vod_year`
  - `vod_year`
- `type_id`
  - `type_id`

数据清洗规则：

- 过滤空对象、空 `vod_id` 和 `vod_id=0`
- `vod_name` 为空时回退为“未知标题”
- 图片字段为 `<nil>`、`nil`、`null` 或空值时返回空字符串
- 图片字段为相对路径时，拼接第一个图片主机

## 详情设计

详情接口使用：

- `ac=videolist`
- `ids=<vod_id>`

详情返回只保留当前仓库需要的核心字段：

- `vod_id`
- `vod_name`
- `vod_pic`
- `type_name`
- `vod_year`
- `vod_area`
- `vod_remarks`
- `vod_actor`
- `vod_director`
- `vod_content`
- `vod_play_from`
- `vod_play_url`

播放列表解析规则：

- 从 `vod_play_from` 读取线路名，逗号分隔
- 从 `vod_play_url` 读取分集，`#` 分隔
- 每个分集项按 `标题$地址` 解析
- 若分集缺少标题，则回退为 `第N集`
- 若缺少地址，则跳过

为了兼容仓库现有数据结构，详情输出不保留 JS 版的嵌套 `vod_play_sources`，而是直接组装为：

- `vod_play_from`: 用 `$$$` 连接的线路名
- `vod_play_url`: 与线路一一对应、用 `$$$` 分组、每组内部用 `#` 连接的剧集串

若参考站点只返回一组剧集但含多个线路名，则默认把同一组剧集复制到每个线路名下，以保持与参考实现的可播放行为一致。

## 播放设计

播放阶段只做基础采集，不做嗅探和刮削增强。

输入为详情里拼出的剧集地址。处理规则如下：

1. 若地址为空，返回空播放结果
2. 若地址是明显的媒体直链，返回：
   - `parse=0`
   - `playUrl=""`
   - `url=<直链>`
3. 若地址是普通 `http/https` 链接但不是明显媒体直链，返回：
   - `parse=1`
   - `playUrl=""`
   - `url=<原始链接>`
4. 若地址不是 URL，仍按待解析地址返回，交给上游处理

明显媒体直链的判定后缀包括：

- `.m3u8`
- `.mp4`
- `.flv`
- `.avi`
- `.mkv`
- `.ts`

本次实现不为播放结果附加自定义 header，除非测试或站点字段证明有明确必需值。

## 错误处理

错误处理原则是“接口尽量返回空结果，不向外抛异常”。

具体策略：

- 请求失败时继续 fallback
- 分类、首页、搜索失败时返回空列表
- 详情失败时返回 `{"list": []}`
- 播放失败时返回 `{"parse": 0, "playUrl": "", "url": "", "header": {}}`
- 局部字段缺失只影响对应字段，不使整条记录失效

## 测试设计

测试文件新增为 `py/tests/test_如意资源.py`，全部使用 `unittest` 和 `mock`，不依赖真实网络。

首轮测试覆盖：

- `homeContent` 暴露硬编码分类和筛选
- `_get_pic_url` 处理绝对路径、相对路径和空值
- `_request_json` 在首个 API 失败时会 fallback 到下一个 API
- `homeContent` 或首页推荐正确映射列表字段
- `categoryContent` 能从主类推导默认子类，也能接受 `extend.type`
- `searchContent` 对空关键词直接返回空结果
- `searchContent` 正确传递搜索参数并做标题过滤
- `detailContent` 正确映射基础字段并拼出 `vod_play_from` / `vod_play_url`
- `playerContent` 对直链返回 `parse=0`
- `playerContent` 对非直链 URL 返回 `parse=1`

测试遵循 TDD：

1. 先写失败测试
2. 确认失败原因正确
3. 再补最小实现
4. 最后跑目标模块测试

## 验收标准

完成后应满足以下标准：

- 新蜘蛛文件和对应测试文件均已存在
- 所有新增测试离线可运行
- 分类、推荐、分类列表、搜索、详情、播放六类基础能力可用
- 返回结构符合当前仓库 Spider 约定
- 不引入刮削、弹幕、嗅探等额外行为
