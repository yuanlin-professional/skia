# skia_baidu_mobile.py - 百度移动端页面集定义

> 源文件: [tools/skp/page_sets/skia_baidu_mobile.py](../../../tools/skp/page_sets/skia_baidu_mobile.py)

## 概述

此文件定义了一个 Chromium Telemetry 页面集，用于以移动端用户代理从百度搜索结果页面录制 Skia Picture（SKP）文件。百度是中国最大的搜索引擎，页面 URL 包含 "barack+obama" 的搜索查询。百度搜索结果页包含中文搜索结果、图片预览、百度百科摘要和特有的搜索建议 UI。作为中文网页的代表，此页面集对测试 Skia 的 CJK（中日韩）文本渲染能力至关重要。

## 架构位置

该文件属于 Skia SKP 页面集合（`tools/skp/page_sets/`），是移动端搜索引擎类网站的代表。在 Skia 的国际化测试覆盖中，百度是唯一的中文搜索引擎页面集，确保 Skia 的渲染测试不仅限于拉丁文字网站。

该页面集的特殊价值在于：
- **CJK 字符渲染**：中文字符使用完全不同的字体和字形处理路径
- **复杂文本整形**：中文文本的换行、字间距和排版规则与西文不同
- **大字符集**：中文字体包含数万个字形，对字形缓存是压力测试

## 主要类与结构体

### `SkiaMobilePage(page_module.Page)`
移动端页面定义类。

**属性**：
- `shared_page_state_class`：`SharedMobilePageState`
- `archive_data_file`：`'data/skia_baidu_mobile.json'`

**方法**：
- `RunNavigateSteps(action_runner)`：导航到百度搜索结果并等待 15 秒

### `SkiaBaiduMobilePageSet(story.StorySet)`
页面集合定义。

**URL**：百度搜索结果页，含多个搜索参数（`wd=barack+obama` 及建议相关参数）
**来源**：`go/skia-skps-3-2019`

## 公共 API 函数

| 方法 | 所属类 | 参数 | 描述 |
|------|--------|------|------|
| `__init__(url, page_set)` | SkiaMobilePage | URL 和父页面集 | 初始化移动端页面 |
| `RunNavigateSteps(action_runner)` | SkiaMobilePage | Telemetry action_runner | 导航并等待 15 秒 |
| `__init__()` | SkiaBaiduMobilePageSet | 无 | 初始化页面集 |

## 内部实现细节

1. **复杂 URL**：URL 包含多个百度内部参数：
   - `wd`：搜索词（"barack+obama"）
   - `rsv_bp`、`rsv_spt`、`rsv_sug*`：百度搜索建议和排序参数
   - `inputT=4920`：可能记录搜索输入时间（毫秒）
2. **字符串连接**：因 URL 较长，使用括号内隐式连接。
3. **HTTP 协议**：使用 HTTP 协议访问。
4. **标准移动端模式**：使用 `SharedMobilePageState` 模拟移动浏览器。

## 依赖关系

- **Telemetry 框架**：
  - `telemetry.story.StorySet`
  - `telemetry.page.page.Page`
  - `telemetry.page.shared_page_state.SharedMobilePageState`
- **存档数据**：`data/skia_baidu_mobile.json`

## 设计模式与设计决策

- **国际化覆盖**：百度是页面集中唯一的中文搜索引擎，确保 CJK 字符渲染路径得到测试。这对 Skia 作为全球化渲染引擎的质量保证至关重要。
- **搜索结果页**：选择搜索结果页而非首页，因为搜索结果包含更多混合内容（中英文混排、图片、链接）。
- **固定搜索词**：使用固定的英文搜索词确保结果可重复，同时搜索结果中仍包含大量中文内容。
- **遵循移动端标准模式**：与其他移动端页面集保持一致的代码结构。

## 性能考量

- **字形缓存压力**：中文字体包含数万个字形，首次渲染时的字形缓存填充可能导致性能下降。
- **文本整形开销**：CJK 文本的整形（text shaping）比拉丁文更复杂，涉及更多 Unicode 处理逻辑。
- **字体文件大小**：中文字体文件通常远大于西文字体（10MB+ vs 几百KB），加载时间更长。
- **15 秒标准等待**：对搜索结果页通常足够。

## 相关文件

- `tools/skp/page_sets/data/skia_baidu_mobile.json`：WPR 存档数据
- `tools/skp/page_sets/skia_googlenews_mobile.py`：另一个移动端搜索/新闻页面集
- `tools/skp/page_sets/skia_amazon_mobile.py`：移动端电商页面集
- Skia 的 CJK 字体渲染和文本整形相关代码
