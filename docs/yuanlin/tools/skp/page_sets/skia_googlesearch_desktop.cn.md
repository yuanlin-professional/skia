# skia_googlesearch_desktop.py

> 源文件: tools/skp/page_sets/skia_googlesearch_desktop.py

## 概述

`skia_googlesearch_desktop.py` 是一个基于 Telemetry 框架的页面集定义文件,用于测试 Skia 图形库在渲染 Google 搜索页面时的性能表现。该文件配置了针对 Google 搜索结果页面("barack obama"查询)的桌面端测试场景,是 Skia 2019 年第三季度 SKP 更新计划(go/skia-skps-3-2019)的一部分。

Google 搜索页面作为全球访问量最大的网站之一,包含了复杂的 DOM 结构、动态内容、大量文本渲染和交互元素,是测试渲染引擎综合性能的理想样本。该测试页面集代表了中等优化水平的网页,而非高度优化的极端情况,能够真实反映 Skia 在实际使用场景中的表现。

## 架构位置

该文件位于 Skia 项目的测试工具目录结构中:

```
skia/
└── tools/                          # 工具目录
    └── skp/                        # SKP (Skia Picture) 相关工具
        └── page_sets/              # 页面集定义目录
            └── skia_googlesearch_desktop.py
            └── data/               # 页面归档数据
                └── skia_googlesearch_desktop.json
```

该文件是 Skia 性能测试基础设施的核心组成部分,与其他 Google 服务测试文件(如 Gmail、Google Calendar、Google Docs)共同构成了对 Google 生态系统的完整测试覆盖。这些测试用例确保 Skia 在主流 Web 应用上的稳定性和性能。

## 主要类与结构体

### SkiaDesktopPage

```python
class SkiaDesktopPage(page_module.Page)
```

这是继承自 Telemetry 框架 `Page` 类的自定义页面类,代表 Google 搜索页面的测试实例。与其他页面集中的 `SkiaBuildbotDesktopPage` 命名不同,这里使用了更通用的 `SkiaDesktopPage` 命名。

**主要属性:**
- `url`: 要测试的网页 URL,指向 Google 搜索 "barack obama" 的结果页
- `name`: 页面名称(通常与 URL 相同)
- `page_set`: 所属的页面集对象
- `shared_page_state_class`: 共享的页面状态类,使用 `SharedDesktopPageState` 表示桌面环境
- `archive_data_file`: 归档数据文件路径,指向 `data/skia_googlesearch_desktop.json`

**主要方法:**

- `__init__(self, url, page_set)`: 构造函数,初始化页面对象,设置桌面页面状态和归档文件路径

- `RunNavigateSteps(self, action_runner)`: 执行导航步骤,包括导航到 Google 搜索结果页并等待 15 秒确保页面及所有动态内容完全加载

### SkiaGooglesearchDesktopPageSet

```python
class SkiaGooglesearchDesktopPageSet(story.StorySet)
```

这是继承自 Telemetry 框架 `StorySet` 类的页面集合类,用于组织和管理 Google 搜索相关的测试页面。

**主要属性:**
- `archive_data_file`: 页面集的归档数据文件路径
- `urls_list`: 包含要测试的 Google 搜索 URL 列表

**主要方法:**

- `__init__(self)`: 构造函数,初始化页面集,设置归档文件,创建 URL 列表,并为每个 URL 创建页面实例添加到故事集中

## 公共 API 函数

该文件主要提供了两个公共类供 Telemetry 框架使用:

1. **SkiaDesktopPage**: 可以被实例化以创建 Google 搜索页面的测试对象
2. **SkiaGooglesearchDesktopPageSet**: 可以被实例化以创建完整的页面集,供测试框架加载和执行

这些类通过 Telemetry 框架的标准接口进行交互,由测试运行器自动发现和加载。测试框架会调用 `RunNavigateSteps` 方法来执行页面加载和导航操作。

## 内部实现细节

### URL 特殊格式

测试使用的 URL 格式值得注意:
```python
'https://www.google.com/#hl=en&q=barack+obama'
```

这个 URL 包含:
- `#hl=en`: 设置语言为英语,确保测试一致性
- `q=barack+obama`: 搜索查询参数,使用加号连接多个词

使用 URL 片段标识符(#)而非查询字符串(?)是 Google 搜索早期 AJAX 架构的特征,虽然现代 Google 搜索已经改变,但归档数据仍保留了这种格式。

### 等待时间配置

15 秒的等待时间对于 Google 搜索页面特别重要:
- Google 搜索结果页包含大量异步加载的内容
- 搜索结果可能包括知识图谱、相关搜索、新闻结果等多个模块
- JavaScript 需要时间执行以渲染动态元素
- 图片和其他媒体资源需要加载

这个等待时间确保测试捕获的是完全渲染后的页面状态。

### 搜索查询选择

选择 "barack obama" 作为测试查询有几个原因:
1. **稳定性**: 这是一个不会随时间变化的历史人物查询
2. **复杂性**: 搜索结果通常包含知识面板、图片、相关搜索等丰富元素
3. **可重现性**: 归档数据可以保存特定时间点的搜索结果
4. **国际化**: 包含拉丁字符,测试基本文本渲染

### SKP 更新计划

代码注释中提到 `go/skia-skps-3-2019`,这是 Skia 团队内部的 SKP 更新计划:
- 定期更新测试页面集以反映现代 Web 的变化
- 2019 年第三季度的更新可能包括新的网站或更新现有网站的归档
- 确保测试用例与实际 Web 开发趋势保持一致

### 归档数据机制

归档文件 `data/skia_googlesearch_desktop.json` 包含:
- 完整的 HTML 响应
- 所有 JavaScript 文件(Google 搜索使用大量 JS)
- CSS 样式表
- 图片和其他资源
- API 请求和响应(如果有)

这使得即使 Google 搜索界面更新,测试仍然使用一致的归档版本。

## 依赖关系

### 外部依赖

- **telemetry**: Google Chromium 项目的性能测试框架
  - `telemetry.story`: 故事集管理模块
  - `telemetry.page.page`: 页面基类定义
  - `telemetry.page.shared_page_state`: 共享页面状态管理

### 内部依赖

- 归档数据文件: `data/skia_googlesearch_desktop.json`
- Skia 的文本渲染引擎(处理搜索结果文本)
- Skia 的图像解码器(处理搜索结果中的图片)
- Skia 的 GPU 后端(如果启用硬件加速)

### 测试目标

该页面集主要用于测试:
- 复杂 Web 应用的渲染性能
- 大量文本内容的布局和渲染
- 动态内容加载和渲染
- 混合内容(文本、图片、UI 元素)的合成性能
- CSS 样式的复杂应用

## 设计模式与设计决策

### 类命名规范化

与旧的 `SkiaBuildbotDesktopPage` 命名不同,这里使用 `SkiaDesktopPage`,表明:
- 更新的代码使用更简洁的命名
- 去除了 "Buildbot" 特定的名称,使类更通用
- 可能是 2019 年代码重构的一部分

### 单一职责原则

`RunNavigateSteps` 方法只负责页面导航和等待:
```python
def RunNavigateSteps(self, action_runner):
    action_runner.Navigate(self.url)
    action_runner.Wait(15)
```

这种简洁的实现:
- 专注于基本的导航任务
- 不包含复杂的交互逻辑
- 便于维护和理解

### 代表性测试策略

注释明确说明 "Pages designed to represent the median, not highly optimized web":
- Google 搜索虽然是高流量网站,但其复杂性代表了中等水平
- 避免测试过于简单或过于复杂的极端情况
- 平衡测试覆盖和维护成本

### 配置即代码

所有配置(URL、等待时间、归档文件)都在代码中明确定义:
- 易于版本控制
- 易于代码审查
- 减少外部配置文件的复杂性

## 性能考量

### Google 搜索页面的渲染挑战

Google 搜索页面包含:
- **动态 DOM 操作**: JavaScript 大量修改 DOM 结构
- **异步资源加载**: 图片、API 数据等异步加载
- **复杂 CSS**: 使用现代 CSS 特性(Grid、Flexbox、动画)
- **大量文本**: 搜索结果包含标题、摘要、URL 等多种文本元素
- **交互元素**: 按钮、链接、下拉菜单等

这些特性使其成为全面测试 Skia 性能的理想用例。

### Skia 渲染路径

对于 Google 搜索页面,Skia 需要处理:
- **文本渲染**: 使用 SkTextBlob 和字形缓存
- **图像解码**: 解码搜索结果中的 JPEG/PNG 图片
- **图层合成**: 合成多个渲染层
- **硬件加速**: 如果可用,使用 GPU 渲染

### 等待时间与测试精度

15 秒的等待时间是经过权衡的:
- **太短**: 可能捕获未完全加载的页面,导致测试不稳定
- **太长**: 增加测试时间,降低 CI/CD 效率
- **15 秒**: 对于 Google 搜索页面是合理的中间值

### 归档回放的性能优势

使用 Web Page Replay:
- 消除网络延迟的变化
- 确保每次测试使用相同的内容和资源
- 提高测试执行速度(从本地读取而非网络下载)
- 提高测试可重现性

### 桌面环境的性能特征

桌面环境通常意味着:
- 更高的 CPU/GPU 性能
- 更大的屏幕分辨率(需要渲染更多像素)
- 可能启用更多的渲染优化
- 鼠标交互而非触摸交互

## 相关文件

### 同目录下的相关 Google 服务测试

- `skia_gmail_desktop.py` - Gmail 应用测试
- `skia_googlecalendar_desktop.py` - Google Calendar 测试
- `skia_googledocs_desktop.py` - Google Docs 测试
- `skia_googlespreadsheet_desktop.py` - Google Sheets 测试
- `skia_googleimagesearch_desktop.py` - Google 图片搜索测试
- `skia_googlenews_mobile.py` - Google 新闻移动版测试
- `skia_googlesearch_mobile.py` - Google 搜索移动版测试

### 数据文件

- `data/skia_googlesearch_desktop.json` - 页面归档数据
- `data/credentials.json` - 可能的 Google 账号认证信息(用于其他 Google 服务测试)

### Skia 核心模块

- `src/core/SkCanvas.h` - 画布 API,所有渲染的基础
- `src/core/SkTextBlob.h` - 文本渲染数据结构
- `src/gpu/` - GPU 加速渲染后端
- `modules/skottie/` - 动画支持(如果页面包含动画)

### Telemetry 框架

- `telemetry/page/shared_page_state.py` - 桌面页面状态实现
- `telemetry/story.py` - 故事集框架
- `telemetry/page/page.py` - 页面基类

### SKP 工具链

- `tools/skp/*.py` - SKP 文件生成和处理工具
- Skia 的 SKP 录制和回放功能
- Skia 的性能分析工具

该文件是 Skia 性能测试套件的重要组成部分,通过测试 Google 搜索这样的复杂 Web 应用,确保 Skia 在真实场景下的稳定性和高性能表现。
