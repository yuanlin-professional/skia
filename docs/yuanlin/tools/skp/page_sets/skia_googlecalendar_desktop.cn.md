# skia_googlecalendar_desktop.py

> 源文件: tools/skp/page_sets/skia_googlecalendar_desktop.py

## 概述

`skia_googlecalendar_desktop.py` 是一个基于 Telemetry 框架的页面集定义文件,用于测试 Skia 图形库在渲染 Google Calendar 桌面版应用时的性能表现。该文件是 Skia 2019 年第三季度 SKP 更新计划(go/skia-skps-3-2019)的一部分,配置了针对 Google Calendar 主页面的自动化测试场景,包含了 Google 账号认证流程。

Google Calendar 是 Google 的核心生产力应用之一,是一个复杂的单页应用(SPA),包含日历网格视图、事件卡片、时间轴、拖放操作和实时同步等功能。该测试页面集能够全面评估 Skia 在处理复杂日历界面、大量 UI 元素和密集文本渲染时的综合能力,代表了企业级 Web 应用的渲染需求。

## 架构位置

该文件位于 Skia 项目的测试工具目录结构中:

```
skia/
└── tools/                          # 工具目录
    └── skp/                        # SKP (Skia Picture) 相关工具
        └── page_sets/              # 页面集定义目录
            └── skia_googlecalendar_desktop.py
            └── data/               # 页面归档数据
                ├── skia_googlecalendar_desktop.json
                └── credentials.json
            └── login_helpers/      # 登录辅助模块
                └── google_login.py
```

该文件是 Skia Google Workspace 测试套件的核心部分,与 Gmail、Google Docs、Google Sheets 等测试共同确保 Skia 在 Google 生产力应用中的稳定性和性能。这些测试对于验证 Skia 作为现代 Web 应用渲染引擎的能力至关重要。

## 主要类与结构体

### SkiaDesktopPage

```python
class SkiaDesktopPage(page_module.Page)
```

这是继承自 Telemetry 框架 `Page` 类的自定义页面类,代表 Google Calendar 页面的测试实例。使用 `SkiaDesktopPage` 命名,符合 2019 年更新的命名规范。

**主要属性:**
- `url`: 要测试的网页 URL,指向 Google Calendar 主页面
- `name`: 页面名称(通常与 URL 相同)
- `page_set`: 所属的页面集对象
- `shared_page_state_class`: 共享的页面状态类,使用 `SharedDesktopPageState` 表示桌面环境
- `archive_data_file`: 归档数据文件路径,指向 `data/skia_googlecalendar_desktop.json`
- `wpr_mode`: Web Page Replay 模式,用于判断是否在回放模式

**主要方法:**

- `__init__(self, url, page_set)`: 构造函数,初始化页面对象,设置桌面页面状态和归档文件路径

- `RunNavigateSteps(self, action_runner)`: 执行导航步骤,包括 Google 账号登录(非回放模式)和导航到 Calendar 主页面,等待 15 秒确保应用完全加载

### SkiaGooglecalendarDesktopPageSet

```python
class SkiaGooglecalendarDesktopPageSet(story.StorySet)
```

这是继承自 Telemetry 框架 `StorySet` 类的页面集合类,用于组织和管理 Google Calendar 测试页面。

**主要属性:**
- `archive_data_file`: 页面集的归档数据文件路径
- `urls_list`: 包含 Google Calendar URL 的列表

**主要方法:**

- `__init__(self)`: 构造函数,初始化页面集,设置归档文件,创建 URL 列表,并为每个 URL 创建页面实例添加到故事集中

## 公共 API 函数

该文件主要提供了两个公共类供 Telemetry 框架使用:

1. **SkiaDesktopPage**: 可以被实例化以创建 Google Calendar 页面的测试对象,支持认证流程
2. **SkiaGooglecalendarDesktopPageSet**: 可以被实例化以创建完整的页面集,供测试框架加载和执行

这些类通过 Telemetry 框架的标准接口进行交互,由测试运行器自动发现和加载,并根据运行模式决定是否执行登录流程。

## 内部实现细节

### URL 结构

测试使用的 URL 非常简洁:
```python
'https://www.google.com/calendar/'
```

这是 Google Calendar 的主入口,加载后会:
- 检查用户认证状态
- 如果已登录,显示用户的日历
- 如果未登录,重定向到登录页面或显示营销页面

### SKP 更新计划

代码注释中的 `go/skia-skps-3-2019` 表明:
- 这是 2019 年第三季度的 SKP 更新计划
- Google Calendar 被选为代表性的生产力应用
- 反映 2019 年 Calendar 的界面设计和功能

### 认证流程

`RunNavigateSteps` 方法实现了条件性的登录逻辑:

```python
if self.wpr_mode != wpr_modes.WPR_REPLAY:
    credentials_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'data/credentials.json')
    google_login.BaseLoginGoogle(action_runner, 'google', credentials_path)
    action_runner.Wait(15)
```

**认证机制:**
- 检查是否在 Web Page Replay 回放模式
- 非回放模式时执行真实 Google 登录
- 从 `data/credentials.json` 读取测试账号凭证
- 调用 `google_login.BaseLoginGoogle` 执行登录流程
- 登录后等待 15 秒确保登录完成并重定向

**回放模式:**
- 跳过登录流程(归档数据已包含认证状态)
- 直接导航到 Calendar 页面

### 导航和等待策略

导航流程分为两个阶段:
1. **登录阶段**(非回放模式):
   - 执行 Google 登录
   - 等待 15 秒(登录和重定向)

2. **导航阶段**:
   - 导航到 Calendar URL
   - 再等待 15 秒(应用加载)

总等待时间可达 30 秒(登录 15 秒 + 加载 15 秒),这对于 Google Calendar 是必要的:
- 登录涉及多次重定向和 OAuth 流程
- Calendar 是大型 JavaScript 应用,需要时间初始化
- 日历数据需要从服务器异步加载
- 复杂的 UI 需要时间渲染

### Google Calendar 的视觉特性

Google Calendar 桌面版包含:

**顶部导航栏:**
- Google 标志和应用切换器
- 搜索栏
- 设置按钮
- 用户头像

**侧边栏:**
- 创建事件按钮
- 迷你月历视图
- 日历列表(多个日历的复选框)
- 任务和提醒列表

**主视图:**
- 日历网格(月视图、周视图、日视图等)
- 时间槽和小时标记
- 事件卡片(彩色块显示事件)
- 全天事件区域
- 当前时间线(红线)

**事件卡片:**
- 彩色背景(不同日历不同颜色)
- 事件标题
- 时间信息
- 可能的图标(视频会议、位置等)

**交互元素:**
- 拖放事件改变时间
- 调整事件长度
- 悬停显示详情
- 点击编辑事件

### 归档数据和凭证

测试依赖两个数据文件:
1. **skia_googlecalendar_desktop.json**: 页面归档数据
   - HTTP 请求和响应
   - Calendar 应用的 HTML/CSS/JS
   - 日历数据(事件列表)
   - API 调用的响应

2. **credentials.json**: Google 账号凭证
   - 测试账号的用户名和密码
   - 仅在非回放模式使用
   - 应保密,不提交到公开仓库

## 依赖关系

### 外部依赖

- **telemetry**: Google Chromium 项目的性能测试框架
  - `telemetry.story`: 故事集管理模块
  - `telemetry.page.page`: 页面基类定义
  - `telemetry.page.shared_page_state`: 共享页面状态管理
  - `telemetry.util.wpr_modes`: Web Page Replay 模式定义

- **page_sets.login_helpers.google_login**: Google 账号登录辅助模块
  - `BaseLoginGoogle`: 执行 Google 账号登录的函数

- **os**: Python 标准库,用于文件路径操作

### Skia 模块依赖

- **文本渲染**: SkTextBlob, SkFont, SkTypeface (事件标题、时间、日期)
- **图形绘制**: SkCanvas, SkPaint (日历网格、时间线)
- **矩形和圆角矩形**: SkRRect (事件卡片的圆角)
- **颜色和着色器**: SkColor, SkShader (事件卡片的彩色背景)
- **路径绘制**: SkPath (可能的图标)
- **GPU 加速**: GrContext (加速 UI 渲染)

### 系统依赖

- 网络栈(用于真实登录或 WPR 回放)
- 字体系统(渲染日历文本)
- JavaScript 引擎(V8,执行 Calendar 应用)
- Cookie 和会话管理(保持登录状态)

### 测试目标

该页面集主要用于测试:
- 复杂日历界面的渲染性能
- 网格布局的渲染
- 大量小型 UI 元素(事件卡片)
- 彩色矩形的绘制和合成
- 密集文本渲染
- 动态内容加载和更新
- 认证流程的兼容性
- 交互元素的视觉反馈

## 设计模式与设计决策

### 条件性认证

使用 WPR 模式判断来决定是否登录:
- **回放模式**: 使用归档的认证状态,快速稳定
- **真实模式**: 执行实际登录,测试完整流程
- 平衡测试速度和真实性

### 双阶段等待策略

登录和导航各等待 15 秒:
- 确保每个阶段完全完成
- 给予 Calendar 应用充分的加载时间
- 避免测试不稳定和时序问题

### 简洁的 URL

使用根 URL 而非特定日期或视图:
- 默认加载用户的主视图
- 简化测试配置
- 归档数据会包含特定的状态

### 代表性应用选择

选择 Google Calendar 的原因:
- 核心生产力应用
- 复杂的 UI 和交互
- 大量视觉元素
- 代表企业级 Web 应用

## 性能考量

### Google Calendar 的渲染挑战

Calendar 应用的复杂性:
- **日历网格**: 复杂的表格布局,多行多列
- **大量元素**: 一个月视图可能有数百个小格子和数十个事件
- **动态布局**: 事件的位置和大小需要动态计算
- **重叠处理**: 同一时间段的多个事件需要巧妙排列
- **彩色渲染**: 每个日历和事件有不同的颜色
- **文本密度**: 大量小号字体的文本

### 网格渲染性能

日历网格的渲染:
- 多条水平和垂直线
- 单元格的背景色(周末可能不同)
- 当前日期的高亮
- 高效的线条和矩形绘制
- 可能的 GPU 加速

### 事件卡片渲染

事件卡片的特点:
- 圆角矩形背景
- 半透明或渐变效果
- 文本裁剪(长标题需要截断)
- 多行文本布局
- 小图标的渲染

大量事件卡片的渲染是性能挑战。

### 文本渲染优化

Calendar 的文本渲染需求:
- 多种字体大小(日期数字、事件标题、时间标签)
- 文本对齐和裁剪
- 可能的文本阴影或效果
- 国际化支持(不同语言的日期格式)

Skia 的文本缓存对 Calendar 特别重要。

### 动态更新性能

Calendar 可能的动态更新:
- 实时事件提醒
- 其他日历的同步
- 事件的拖放(需要快速重绘)
- 视图切换(月/周/日视图)

这些操作需要高效的增量渲染。

### 认证的性能影响

登录流程增加测试时间:
- 登录涉及多次网络请求和重定向
- 但对于测试真实的 Calendar 数据和权限是必要的
- 回放模式可以绕过登录,加快测试

### 归档回放优势

使用归档数据:
- 消除网络延迟
- 固定日历数据(不受真实日历变化影响)
- 保护测试账号隐私
- 加快测试执行
- 确保测试一致性

## 相关文件

### 同目录下的相关 Google Workspace 测试

- `skia_gmail_desktop.py` - Gmail 桌面版测试
- `skia_googledocs_desktop.py` - Google Docs 桌面版测试
- `skia_googlespreadsheet_desktop.py` - Google Sheets 桌面版测试
- `skia_googlesearch_desktop.py` - Google 搜索测试
- `skia_googleimagesearch_desktop.py` - Google 图片搜索测试

这些测试共同覆盖了 Google 生态系统。

### 登录辅助模块

- `page_sets/login_helpers/google_login.py` - Google 账号登录实现
- `page_sets/login_helpers/__init__.py` - 登录模块初始化

### 数据文件

- `data/skia_googlecalendar_desktop.json` - Calendar 页面归档数据
- `data/credentials.json` - Google 测试账号凭证(需保密)

### Skia 核心模块

- `src/core/SkCanvas.h` - 画布 API
- `src/core/SkPaint.h` - 画笔对象(线条、填充)
- `src/core/SkTextBlob.h` - 文本渲染
- `src/core/SkRRect.h` - 圆角矩形
- `src/core/SkColor.h` - 颜色定义
- `src/gpu/` - GPU 加速渲染

### Chromium 集成

- Blink 渲染引擎
- V8 JavaScript 引擎
- 网络栈和 Cookie 管理
- DOM 和 CSS 实现

### Telemetry 框架

- `telemetry/page/shared_page_state.py` - 桌面页面状态
- `telemetry/story.py` - 故事集框架
- `telemetry/util/wpr_modes.py` - WPR 模式定义
- `telemetry/page/page.py` - 页面基类

### Web Page Replay 工具

- WPR 服务器和代理
- 归档数据格式
- 请求匹配和响应重放

该文件是确保 Skia 能够高效渲染复杂生产力应用的关键测试,验证了日历网格渲染、大量小型 UI 元素、彩色矩形和密集文本渲染的性能,对于支持 Google Calendar 等企业级 Web 应用至关重要。
