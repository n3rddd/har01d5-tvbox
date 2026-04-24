# 路漫漫 Python 爬虫设计

## 目标

在当前 Python 仓库中新增一个符合 `base.spider.Spider` 接口的 `路漫漫` 爬虫，参考用户提供的 JS 站点逻辑，实现首页、分类、搜索、详情和播放能力，并将站点能力收口为动漫与动画电影分类。

## 范围

本次实现包含：

- 新增 `py/路漫漫.py`
- 新增 `py/tests/test_路漫漫.py`
- 固定 6 个动漫/动画电影分类
- 首页推荐、分类、搜索卡片解析
- 详情元数据与多线路播放列表解析
- 播放页的基础解码、主解析链与失败回退

本次实现不包含：

- 动态扩展站点其他分类
- 修改 `py/base/` 公共层
- 真实联网测试
- 为未知播放器分支补齐所有站外解析逻辑

## 分类范围

固定返回以下分类，与参考脚本一致：

- `6` 日本动漫
- `7` 国产动漫
- `8` 欧美动漫
- `3` 日本动画电影
- `4` 国产动画电影
- `5` 欧美动画电影

## 方案

采用“单 Spider 文件 + 站点内解析 helper + 离线 fixture 测试”的方案，而不是直接移植 Node.js 服务端入口。

原因：

- 仓库交付格式是 Python 单文件蜘蛛
- 当前测试体系要求 `unittest + mock`
- 列表、详情与播放页逻辑可以映射到 Spider 接口
- 参考脚本的播放解析链较长，Python 版本需要保留核心能力并允许安全回退

## 接口映射

- `homeContent`
  - 返回固定 6 个分类
- `homeVideoContent`
  - 请求首页
  - 解析 `.video-img-box` 卡片
  - 去重后返回前若干推荐
- `categoryContent`
  - 构造 `/vod/show/id/<tid>/page/<pg>.html`
  - 预留 `extend` 的 `年代`、`排序` 片段拼接能力
  - 解析卡片列表
- `searchContent`
  - 构造 `/vod/search/page/<pg>/wd/<keyword>.html`
  - 解析搜索卡片
- `detailContent`
  - 请求详情页
  - 解析标题、封面、简介、附加信息
  - 解析 tab 与播放列表，输出 `vod_play_from` / `vod_play_url`
- `playerContent`
  - 先识别直接媒体链接
  - 再解析播放页中的 `player_*` 数据
  - 支持 `encrypt=1/2` 解码
  - 命中主解析链时继续请求播放器 JS 与中间页换取直链
  - 失败时回退 `parse=1`

## ID 策略

- 详情 `vod_id` 保留站内短路径，例如 `vod/detail/123.html` 或站点原始相对路径的紧凑形式
- 播放条目中的 episode id 保留站内短路径或站内播放页相对路径
- Spider 内部统一提供 helper，将短路径恢复为绝对 URL

约束：

- 不把完整绝对 URL 作为列表页默认 `vod_id`
- 仅在播放器解析流程内部使用绝对 URL

## 解析细节

### 列表与搜索

- 复用 `.video-img-box` 卡片结构
- 提取标题、图片、备注、链接
- 图片统一补全为绝对 URL
- 过滤空标题和空链接项目

### 详情页

- 标题取 `.page-title`
- 简介取 `.video-info-content`
- 封面优先取 `.module-item-pic` 下懒加载图片
- 备注整合 `.video-info-items`
- 线路优先按 tab 顺序与对应播放列表容器配对
- 如果缺少 tab，则直接扫描 `.module-player-list`
- 如果仍无播放数据，则允许返回空播放线路，不强行伪造可播集

### 播放页

分三层处理：

1. 直接链接
   - URL 已经是 `m3u8/mp4/flv` 等媒体地址时直接返回 `parse=0`
2. 站内主解析链
   - 提取 `player_* = {...}`
   - 读取 `url/from/encrypt`
   - 处理 URL 编码和 base64 编码
   - 如果结果已经是媒体直链则直接返回
   - 否则继续拉取 `/static/player/<from>.js`
   - 根据脚本中的 `src` 规则请求中间页
   - 若命中带 `vid/t/token/act/play` 的 POST 流程，则按参考脚本执行 AES 解密 token 后换取真实 URL
   - 若命中另一种 POST body 结构，则按页面中拼接出的参数请求接口
3. 失败回退
   - 无法提取 `player_*`
   - 中间页结构不符合预期
   - 接口返回空 URL
   - 以上场景统一回退 `parse=1`

## AES 解密策略

参考脚本中的固定 key/iv：

- key: `ejjooopppqqqrwww`
- iv: `1348987635684651`

Python 版本使用本仓库可用的加密依赖实现 AES-CBC-PKCS7 解密；如果运行环境缺少该依赖，则实现应当保证安全失败并回退解析，而不是抛出未处理异常。

## 错误处理

- 任一网络请求失败时返回空 HTML 或解析回退，不向上抛出站点异常
- 详情页解析失败时返回空列表
- 播放解析失败时返回 `{"parse": 1, "url": 原始播放页}`，并带最小必要请求头
- 所有 helper 对缺失字段、无效 JSON、空 XPath 结果保持容错

## 测试策略

使用 `unittest` 和内嵌 fixture，不走真网。

至少覆盖：

- 固定 6 分类输出
- 首页推荐卡片解析与去重
- 分类 URL 拼接与卡片解析
- 搜索 URL 拼接与结果解析
- 详情页基础元数据解析
- 详情页多线路播放列表组装
- 播放页 `encrypt=1` URL 解码
- 播放页 `encrypt=2` base64 解码
- 直接媒体链接返回 `parse=0`
- 缺失播放器数据时回退 `parse=1`
- AES token 解密 helper 的成功与失败分支

## 验收标准

- `homeContent` 仅返回 6 个动漫相关分类
- 列表、搜索、详情在离线 HTML 夹具下稳定输出预期字段
- `playerContent` 至少覆盖“直链返回、`player_*` 解码、主解析链成功、失败回退”四条路径
- 新增模块测试可独立运行通过
