# skia_tigersvg_desktop

> 源文件: tools/skp/page_sets/skia_tigersvg_desktop.py

## 概述

`skia_tigersvg_desktop.py` 是 Skia 的经典 SVG 性能测试页面集,加载托管在 Wikimedia 上的著名 Ghostscript Tiger SVG 文件。这个 SVG 图形自 1990 年代起就被用作 PostScript 和 SVG 渲染器的标准基准测试,包含复杂的路径、渐变和图案,是测试矢量图形渲染性能的理想选择。该页面集生成 `desk_tigersvg.skp` 文件,用于验证 Skia 的 SVG 渲染能力和性能回归测试。

## 架构位置

该文件是 Skia SVG 测试套件的核心部分,与其他 SVG 测试页面集并列:

```
skia/tools/skp/page_sets/
  skia_tigersvg_desktop.py          # 本文件 - Wikimedia Tiger
  skia_tiger8svg_desktop.py         # 变体版本
  skia_ynevsvg_desktop.py           # 其他 SVG 测试
  data/
    skia_tigersvg_desktop.json
    skia_tigersvg_desktop_*.wprgo
```

与 `tiger8svg` 的区别在于,本文件使用 Wikipedia/Wikimedia 托管的官方版本,而 `tiger8svg` 使用 Skia 自己托管的变体。

## 主要类与结构体

### SkiaBuildbotDesktopPage 类

buildbot 自动化测试专用页面类,配置简单但稳定:

**核心配置:**
- `archive_data_file`: `'data/skia_tigersvg_desktop.json'`
- `shared_page_state_class`: `SharedDesktopPageState`

**导航步骤:**
```python
def RunNavigateSteps(self, action_runner):
    action_runner.Navigate(self.url)
    action_runner.Wait(5)
```

与 `tiger8svg` 相同的 5 秒等待策略,适用于静态 SVG 内容。

### SkiaTigersvgDesktopPageSet 类

**测试 URL:**
```python
urls_list = [
    ('http://upload.wikimedia.org/wikipedia/commons/f/fd/'
     'Ghostscript_Tiger.svg'),
]
```

**URL 分析:**
- **域名**: `upload.wikimedia.org` - Wikimedia 的媒体服务器
- **路径**: `/wikipedia/commons/f/fd/` - Commons 文件存储路径
- **文件**: `Ghostscript_Tiger.svg` - 官方 Ghostscript Tiger 文件
- **来源**: 注释显示 "from fmalita" - 可能是 Skia 团队成员 Florin Malita 添加

**Ghostscript Tiger 历史:**
- 最初为 Ghostscript PostScript 解释器创建
- 成为 SVG 转换后的经典测试案例
- 广泛用于图形库基准测试
- 包含老虎图案,展示复杂渐变和路径

## 公共 API 函数

### Telemetry 工作流

该页面集通过 Telemetry 框架执行以下流程:

1. **页面集加载**: `SkiaTigersvgDesktopPageSet` 被实例化
2. **URL 注册**: Tiger SVG URL 被添加为 story
3. **浏览器启动**: 使用桌面配置启动 Chrome
4. **WPR 回放**: 从档案回放 Wikimedia HTTP 响应
5. **页面导航**: 加载 SVG 文件
6. **等待渲染**: 5 秒等待确保完全渲染
7. **SKP 捕获**: 记录 Skia 渲染命令到 `desk_tigersvg.skp`

### 生成的输出

- **SKP 文件**: `desk_tigersvg.skp`
- **命名规则**: `skia_tigersvg_desktop.py` → `desk_tigersvg.skp`
- **用途**: SVG 性能基准测试、回归测试、渲染验证

## 内部实现细节

### Wikimedia 托管

使用 Wikimedia Commons 托管的官方版本:

**优势:**
- **权威性**: 来自 Wikipedia 官方资源
- **公开访问**: 任何人都可以访问验证
- **稳定性**: Wikimedia 基础设施可靠
- **历史版本**: Wikimedia 保留文件历史

**潜在风险:**
- **外部依赖**: 依赖 Wikimedia 服务可用性
- **内容变更**: 理论上文件可能被更新
- **网络访问**: 需要外部网络连接(WPR 档案缓解此问题)

### WPR 档案保护

通过 Web Page Replay 档案:
- **离线测试**: 不需要实际访问 Wikimedia
- **版本锁定**: 档案中的 SVG 内容固定不变
- **性能稳定**: 消除网络延迟影响
- **可重复性**: 每次测试使用相同的 SVG 文件

### SVG 复杂度

Ghostscript Tiger 包含的 SVG 特性:
- **路径元素**: 数百个 `<path>` 元素定义老虎轮廓
- **线性渐变**: 模拟皮毛的渐变效果
- **图案填充**: 条纹图案使用 pattern 元素
- **分组**: 使用 `<g>` 元素组织结构
- **变换**: 平移、缩放、旋转变换
- **不透明度**: 半透明效果营造深度

## 依赖关系

### Chromium SVG 渲染器

依赖 Chrome/Blink 的 SVG 实现:
- **SVG 解析器**: 解析 XML 格式的 SVG
- **DOM 构建**: 创建 SVG DOM 树
- **样式计算**: 应用 CSS 到 SVG 元素
- **布局**: 计算 SVG 元素位置和大小
- **绘制**: 将 SVG 转换为 Skia 绘制命令

### Skia 图形栈

测试的 Skia 组件:
- **路径渲染**: `SkPath` 的光栅化
- **渐变着色器**: `SkGradientShader` 的性能
- **图案着色器**: `SkImageShader` 用于 pattern
- **变换矩阵**: `SkMatrix` 的应用
- **抗锯齿**: 高质量边缘抗锯齿
- **内存管理**: 复杂场景的内存效率

### 外部资源

- Wikimedia 服务器: SVG 文件托管
- WPR 档案: 网络流量记录
- Telemetry 框架: 自动化测试基础设施

## 设计模式与设计决策

### 使用外部托管

选择 Wikimedia 托管而非 Skia 自托管:

**优点:**
- **标准化**: 使用业界认可的标准测试文件
- **可比性**: 可与其他库的测试结果对比
- **维护简单**: 不需要 Skia 自己维护文件

**缓解措施:**
- WPR 档案锁定内容版本
- 可以随时创建 Skia 托管的副本(如 tiger8svg)

### 最小交互设计

简单的导航和等待策略:
```python
action_runner.Navigate(self.url)
action_runner.Wait(5)
```

**设计理念:**
- **专注渲染**: 测试目标是渲染性能,非交互性能
- **确定性**: 简单流程减少变量
- **可重复性**: 每次运行行为一致
- **效率**: 5 秒足够静态 SVG 渲染

### 与 tiger8svg 的互补

Skia 维护两个 Tiger SVG 测试:
- **tigersvg**: 使用官方 Wikimedia 版本,保持与外部标准一致
- **tiger8svg**: 使用 Skia 控制的版本,可能有特定修改或优化

这种双重测试策略:
- 提供标准基准和定制测试
- 验证不同 SVG 变体的渲染
- 增加测试覆盖面

## 性能考量

### SVG 渲染性能

Tiger SVG 测试的关键性能指标:

**路径复杂度:**
- 数百个贝塞尔曲线路径
- 测试路径细分算法效率
- 验证曲线平坦化性能

**填充性能:**
- 复杂路径的填充算法
- 非零绕数规则和偶奇规则
- 路径缓存和重用

**渐变计算:**
- 线性和径向渐变着色器
- 渐变插值计算
- 色彩空间转换

**内存使用:**
- SVG DOM 内存占用
- 渲染缓存大小
- 路径对象缓存

### 与位图渲染的对比

SVG 渲染 vs 位图渲染:
- **矢量优势**: 无损缩放
- **性能挑战**: 每次缩放都需重新渲染
- **内存权衡**: SVG 定义小但渲染内存大
- **质量**: 矢量图形边缘更清晰

### 跨平台性能

Tiger SVG 在不同平台的表现:
- **桌面**: 充足的 CPU/GPU 资源,渲染快
- **移动**: 资源受限,可能需要优化
- **不同 GPU**: 硬件加速的差异
- **软件渲染**: CPU 渲染路径的性能

### 性能回归检测

该测试用于检测以下回归:
- **渲染时间增加**: 路径光栅化变慢
- **内存泄漏**: SVG 对象未释放
- **质量退化**: 抗锯齿或渐变质量下降
- **正确性问题**: 渲染结果不匹配

## 相关文件

### SVG 测试家族

- `skia_tiger8svg_desktop.py`: Skia 托管的 Tiger 变体
- `skia_ynevsvg_desktop.py`: 另一个复杂 SVG 测试
- 其他 SVG 相关页面集

### 原始 SVG 文件

- `http://upload.wikimedia.org/wikipedia/commons/f/fd/Ghostscript_Tiger.svg`: 官方文件
- Wikimedia Commons 页面: 文件历史和元数据
- Ghostscript 项目: SVG 的原始来源

### 数据和输出

- `data/skia_tigersvg_desktop.json`: WPR 配置文件
- `data/skia_tigersvg_desktop_*.wprgo`: 录制的网络流量
- `desk_tigersvg.skp`: 生成的 SKP 文件
- `desk_tigersvg.pdf`: 可选的 PDF 输出

### Skia SVG 实现

- `modules/svg/`: Skia 的 SVG 模块(如果存在)
- `src/svg/`: SVG 核心实现
- SVG 相关的 GM (golden master) 测试
- SVG 单元测试

### 比较和验证

- `render_pictures`: 渲染 SKP 并验证输出
- `render_pdfs`: 生成 PDF 验证矢量保真度
- `debugger`: 交互式检查 SKP 内容
- 金标准图像: 用于视觉回归测试
