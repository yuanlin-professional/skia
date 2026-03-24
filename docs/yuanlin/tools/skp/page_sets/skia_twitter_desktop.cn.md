# skia_twitter_desktop

> 源文件: tools/skp/page_sets/skia_twitter_desktop.py

## 概述

`skia_twitter_desktop.py` 是 Skia 的 Telemetry 页面集定义文件,用于捕获 Twitter 桌面网站的 SKP(Skia Picture)文件。该页面集专门针对 Twitter 的名人页面(Katy Perry 的 Twitter 页面)进行性能测试和图形渲染验证。它是 Skia 性能基准测试套件的一部分,代表了中等优化水平的真实网页场景,包含复杂的 CSS、JavaScript 交互和媒体内容。

## 架构位置

该文件位于 Skia 项目的页面集定义目录,是 webpages_playback 工作流的输入:

```
skia/
  tools/
    skp/
      webpages_playback.py          # 主执行脚本
      page_sets/
        skia_twitter_desktop.py     # 本文件
        data/
          skia_twitter_desktop.json # WPR 回放配置
          skia_twitter_desktop_*.wprgo # 网络流量档案
```

该文件通过 Chromium 的 Telemetry 框架被加载和执行,用于生成名为 `desk_twitter.skp` 的 SKP 文件。

## 主要类与结构体

### SkiaDesktopPage 类

继承自 `telemetry.page.page_module.Page`,定义单个页面的行为:

**构造函数参数:**
- `url`: 要访问的 URL
- `page_set`: 所属的页面集对象

**关键属性:**
- `url`: 页面 URL(构造函数传入)
- `name`: 页面名称(与 URL 相同)
- `page_set`: 父页面集引用
- `shared_page_state_class`: 使用 `SharedDesktopPageState` 模拟桌面环境
- `archive_data_file`: WPR 档案配置文件路径 `'data/skia_twitter_desktop.json'`

**核心方法:**

**`RunNavigateSteps(action_runner)`**
定义页面导航和交互步骤:
1. `action_runner.Navigate(self.url)`: 导航到 Twitter 页面
2. `action_runner.Wait(15)`: 等待 15 秒让页面完全加载

等待时间设置为 15 秒是为了:
- 确保所有 JavaScript 执行完毕
- 加载延迟内容(图片、媒体)
- 触发动画和交互效果
- 完成所有网络请求

### SkiaTwitterDesktopPageSet 类

继承自 `telemetry.story.StorySet`,定义页面集合:

**构造函数:**
调用父类构造函数,设置 `archive_data_file='data/skia_twitter_desktop.json'`,这是 WPR 回放时使用的配置文件。

**页面列表:**
`urls_list` 包含单个 URL:
- `'https://twitter.com/katyperry'`: Katy Perry 的 Twitter 页面

选择这个页面的原因(注释 `go/skia-skps-3-2019`):
- 代表高流量的社交媒体页面
- 包含丰富的图形内容(头像、图片、视频缩略图)
- 复杂的 CSS 样式和动画效果
- 动态内容加载和无限滚动特性
- 测试文本渲染和 emoji 显示

**初始化流程:**
```python
for url in urls_list:
    self.AddStory(SkiaDesktopPage(url, self))
```
为每个 URL 创建 `SkiaDesktopPage` 实例并添加到页面集。

## 公共 API 函数

该文件不直接提供公共函数,而是通过 Telemetry 框架的类接口与外部交互:

### Telemetry 集成点

1. **页面集发现**: `webpages_playback.py` 通过文件名模式发现此文件
2. **类实例化**: Telemetry 框架实例化 `SkiaTwitterDesktopPageSet`
3. **页面遍历**: 框架遍历页面集中的所有故事(stories)
4. **导航执行**: 调用 `RunNavigateSteps` 执行页面交互
5. **SKP 捕获**: 在页面加载完成后捕获渲染命令

### 生成的 SKP 文件

根据 `webpages_playback.py` 的命名规则:
- 输入: `skia_twitter_desktop.py`
- 解析: `skia` + `twitter` + `desktop`
- 输出: `desk_twitter.skp`(desktop → desk 前缀)

## 内部实现细节

### Telemetry 导入

```python
from telemetry import story
from telemetry.page import page as page_module
from telemetry.page import shared_page_state
```

这些导入来自 Chromium 的 `third_party/catapult` 目录,需要通过 `PYTHONPATH` 环境变量注入。

### SharedDesktopPageState

使用 `SharedDesktopPageState` 提供桌面浏览器环境:
- 桌面窗口大小(通常 1920x1080)
- 桌面 User-Agent
- 桌面特定的浏览器标志
- 启用硬件加速和 GPU 渲染

### WPR 档案关联

`archive_data_file` 属性链接到两个文件:
1. **JSON 配置文件** (`skia_twitter_desktop.json`):
   - 定义 WPR 档案的元数据
   - 映射页面到对应的 `.wprgo` 文件
   - 包含认证信息引用

2. **WPR 档案文件** (`skia_twitter_desktop_*.wprgo`):
   - 二进制格式的网络流量记录
   - 包含 HTTP/HTTPS 请求和响应
   - 支持确定性回放,消除网络变化影响

### pylint 禁用注释

```python
# pylint: disable=W0401,W0614
```

- `W0401`: 禁用通配符导入警告
- `W0614`: 禁用未使用通配符导入警告

这是因为 Telemetry 框架使用约定优于配置的设计,某些导入是隐式使用的。

## 依赖关系

### Chromium Telemetry 框架

必需的外部依赖:
- `telemetry.story.StorySet`: 故事集基类
- `telemetry.page.page_module.Page`: 页面基类
- `telemetry.page.shared_page_state.SharedDesktopPageState`: 桌面状态

### 运行时依赖

1. **Chrome 浏览器**: 需要可执行的 Chrome 二进制文件
2. **WPR 档案**: 需要预录制的网络流量档案(录制模式除外)
3. **凭证文件**: 如果 Twitter 需要登录(可选)

### Skia 工具链

- `webpages_playback.py`: 调用此页面集的脚本
- `skpicture_printer` benchmark: Telemetry 基准测试,用于生成 SKP

## 设计模式与设计决策

### 模板方法模式

`Page` 类定义了页面加载的模板流程,子类通过重写 `RunNavigateSteps` 方法自定义具体行为。这允许框架控制整体流程(启动浏览器、设置环境、捕获 SKP),而页面集控制导航逻辑。

### 配置即代码

将页面集定义为 Python 代码而非静态配置文件:
- 支持编程式页面操作(等待、滚动、点击)
- 可以使用循环批量添加页面
- 类型检查和 IDE 支持
- 版本控制友好

### 最小化交互原则

该页面集使用简单的 "导航 + 等待" 策略:
- 不模拟复杂用户交互(点击、滚动)
- 捕获页面初始加载状态
- 减少不确定性,提高可重复性

这符合 SKP 基准测试的目标:测量渲染性能而非交互性能。

### 真实世界代表性

选择 Twitter 这样的真实网站而非合成测试页面:
- 包含真实的性能瓶颈(大量 DOM 元素、复杂 CSS)
- 测试 Skia 在实际使用场景下的表现
- 帮助发现真实应用中可能遇到的问题

## 性能考量

### 等待时间权衡

15 秒的等待时间是经过权衡的:
- **太短**: 可能捕获不完整的页面,遗漏延迟加载内容
- **太长**: 增加测试总时间,资源浪费
- **15 秒**: 足够大多数内容加载,同时保持合理的测试时长

### 单页面设计

只包含一个 URL 而非多个 Twitter 页面:
- 减少测试时间和存储开销
- 一个代表性页面足以测试 Twitter 的渲染特性
- 如需更多覆盖,可创建单独的页面集文件

### 网络回放

使用 WPR 档案回放网络流量:
- **消除网络延迟**: 本地回放比真实网络快得多
- **确定性**: 每次测试使用相同的内容,消除网页更新影响
- **离线测试**: 不依赖外部网络连接
- **隐私保护**: 避免向 Twitter 发送测试流量

## 相关文件

### 同目录页面集

- `skia_twitter_mobile.py`: Twitter 移动版页面集(如存在)
- `skia_yahooanswers_desktop.py`: 类似结构的其他网站页面集
- `skia_youtube_desktop.py`: 另一个社交媒体平台页面集
- `skia_wikipedia_desktop.py`: 不同类型网站的对比

### 数据文件

- `data/skia_twitter_desktop.json`: WPR 回放配置
- `data/skia_twitter_desktop_001.wprgo`: 网络流量档案(数字后缀可能变化)
- `data/credentials.json`: 共享的登录凭证文件

### 生成的输出

- `desk_twitter.skp`: 生成的 SKP 文件
- `desk_twitter.pdf`: 如果运行 `render_pdfs` 的输出

### 调用脚本

- `webpages_playback.py`: 使用此页面集生成 SKP 的主脚本
- Chromium 的 `run_benchmark` 工具: 实际执行页面加载的工具

### 依赖框架

- `<chrome_src>/third_party/catapult/telemetry/`: Telemetry 框架源码
- `<chrome_src>/tools/perf/page_sets/`: Chromium 官方页面集示例
