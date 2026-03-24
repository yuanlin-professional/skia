# skia_tiger8svg_desktop

> 源文件: tools/skp/page_sets/skia_tiger8svg_desktop.py

## 概述

`skia_tiger8svg_desktop.py` 是 Skia 的 SVG 性能测试页面集,专门用于测试复杂 SVG 图形的渲染性能。该页面集加载一个托管在 Google Cloud Storage 上的 Tiger SVG 文件(`tiger-8.svg`),这是一个包含大量路径和渐变的复杂矢量图形,常用作图形库的基准测试。通过捕获该页面的 SKP 文件,Skia 可以验证其 SVG 渲染器和路径光栅化性能。

## 架构位置

该文件属于 Skia 维护的专用测试页面集,关注特定的图形特性:

```
skia/tools/skp/page_sets/
  skia_tiger8svg_desktop.py         # Tiger 8 SVG 测试
  skia_tigersvg_desktop.py          # 原始 Tiger SVG 测试
  skia_ynevsvg_desktop.py           # 另一个 SVG 测试
  data/
    skia_tiger8svg_desktop.json
    skia_tiger8svg_desktop_*.wprgo
```

生成的 SKP 文件名为 `desk_tiger8svg.skp`,专门用于 SVG 性能回归测试。

## 主要类与结构体

### SkiaBuildbotDesktopPage 类

注意命名:`SkiaBuildbotDesktopPage` 而非 `SkiaDesktopPage`,表明这是 buildbot 自动化测试的一部分。

**关键配置:**
- `archive_data_file`: `'data/skia_tiger8svg_desktop.json'`
- `shared_page_state_class`: `SharedDesktopPageState` (桌面环境)

**`RunNavigateSteps(action_runner)` 方法:**
```python
action_runner.Navigate(self.url)
action_runner.Wait(5)
```

**等待时间分析:**
- **5 秒**: 比普通网页短(通常 15 秒)
- **原因**: SVG 文件是静态内容,无 JavaScript 执行,加载快
- **目的**: 确保浏览器完成 SVG 解析和首次渲染

### SkiaTiger8svgDesktopPageSet 类

**测试 URL:**
```python
urls_list = [
    ('https://storage.googleapis.com/skia-recreateskps-bot-hosted-pages/'
     'tiger-8.svg'),
]
```

**URL 解析:**
- **托管位置**: Google Cloud Storage bucket `skia-recreateskps-bot-hosted-pages`
- **文件名**: `tiger-8.svg`
- **来源注释**: `from skbug.com/40035867` - 关联到 Skia bug tracker

**Tiger-8.svg 特点:**
- 可能是 Tiger SVG 的变体版本
- "8" 可能表示特定复杂度级别或版本号
- 包含大量路径、渐变、图案等 SVG 特性

## 公共 API 函数

### Telemetry 集成

通过 Telemetry 框架集成:
- **页面集名称**: `skia_tiger8svg_desktop`
- **生成的 SKP**: `desk_tiger8svg.skp`
- **测试类型**: SVG 矢量图形性能

### 命名规则

- 输入: `skia_tiger8svg_desktop.py`
- 解析: `skia` + `tiger8svg` + `desktop`
- 输出: `desk_tiger8svg.skp`

## 内部实现细节

### Buildbot 专用页面类

使用 `SkiaBuildbotDesktopPage` 而非通用 `SkiaDesktopPage`:
- 表明这是持续集成测试的一部分
- 可能有额外的监控和报告逻辑
- 通常用于托管在 Skia 控制的服务器上的测试页面

### 静态 SVG 加载

SVG 文件的加载特点:
- **无 JavaScript**: 纯 SVG 内容,浏览器直接渲染
- **快速加载**: 只需解析 XML 和构建 DOM
- **确定性**: 没有动画或动态内容,每次渲染一致

### Google Storage 托管

使用 GCS 托管测试文件的优势:
- **高可用性**: Google 基础设施保证访问
- **版本控制**: 可以通过 URL 控制文件版本
- **Skia 控制**: 测试内容不会被外部网站更改
- **快速访问**: 低延迟,稳定的下载速度

## 依赖关系

### SVG 渲染栈

测试涉及的 Skia 组件:
- SVG 解析器(可能基于 Chromium 的 Blink SVG 实现)
- 路径光栅化器
- 渐变着色器
- 图案填充
- 抗锯齿算法

### 浏览器 SVG 支持

依赖 Chrome 的 SVG 渲染:
- Blink 渲染引擎的 SVG 模块
- SVG DOM 接口
- CSS 样式应用于 SVG 元素

### 网络和存储

- Google Cloud Storage: 托管 SVG 文件
- WPR 档案: 记录 SVG 文件的下载过程
- 本地缓存: 浏览器可能缓存 SVG 内容

## 设计模式与设计决策

### 控制测试内容

使用 Skia 自己托管的 SVG 文件而非外部网站:
- **稳定性**: 内容不会意外改变
- **可重复性**: 确保所有测试运行使用相同内容
- **性能**: 消除外部网站不可控因素
- **安全性**: 避免依赖第三方服务

### 短等待时间

SVG 页面只需 5 秒等待(vs 普通网页 15 秒):
- **静态内容**: 无需等待 JavaScript 执行
- **快速渲染**: SVG 解析和渲染通常很快
- **效率**: 减少测试总时间

### 专用测试页面集

为特定 SVG 文件创建独立页面集:
- **针对性**: 专门测试 SVG 性能
- **隔离性**: SVG 问题不干扰其他测试
- **可追踪性**: 通过 bug 链接(skbug.com/40035867)追踪问题

## 性能考量

### Tiger SVG 复杂度

Tiger SVG 是经典的 SVG 基准测试:
- **路径数量**: 数百到数千条贝塞尔曲线
- **渐变**: 多个线性和径向渐变
- **图层**: 复杂的分组和嵌套结构
- **细节**: 精细的毛发和条纹细节

### 渲染性能指标

该测试可以衡量:
- **路径光栅化速度**: 将贝塞尔曲线转换为像素
- **填充性能**: 复杂路径的填充算法
- **渐变计算**: 渐变着色器的性能
- **内存使用**: SVG DOM 和渲染缓存

### SKP 捕获效率

捕获 SVG 页面的 SKP:
- **命令密度**: SVG 生成大量路径绘制命令
- **文件大小**: 取决于 SVG 复杂度
- **重现性**: SKP 应完美重现原始 SVG 渲染

### 与其他 SVG 测试的对比

- `tiger8svg` vs `tigersvg`: 可能测试不同版本或复杂度
- `ynevsvg`: 另一个 SVG 测试,可能关注不同特性
- 多个 SVG 测试提供全面的 SVG 性能覆盖

## 相关文件

### 相关 SVG 页面集

- `skia_tigersvg_desktop.py`: 原始 Tiger SVG 测试(可能来自 Wikipedia)
- `skia_ynevsvg_desktop.py`: 另一个 SVG 性能测试
- 其他 `*svg*.py` 页面集

### 测试资源

- `https://storage.googleapis.com/skia-recreateskps-bot-hosted-pages/tiger-8.svg`: 实际的 SVG 文件
- `data/skia_tiger8svg_desktop.json`: WPR 配置
- `data/skia_tiger8svg_desktop_*.wprgo`: 网络流量档案

### 输出文件

- `desk_tiger8svg.skp`: 生成的 SKP 文件
- `desk_tiger8svg.pdf`: 可选的 PDF 输出(用于验证)

### Bug 跟踪

- `skbug.com/40035867`: 相关的 Skia bug,可能描述:
  - 该 SVG 暴露的特定问题
  - 性能回归
  - 渲染错误
  - 测试添加原因

### Skia SVG 模块

- `src/svg/`: Skia 的 SVG 实现(如果存在独立 SVG 模块)
- `modules/svg/`: Skia SVG 模块
- SVG 相关的单元测试和性能测试
