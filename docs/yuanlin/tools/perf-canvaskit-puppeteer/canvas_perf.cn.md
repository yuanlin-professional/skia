# CanvasKit Canvas 性能测试集

> 源文件: `tools/perf-canvaskit-puppeteer/canvas_perf.js`

## 概述

此文件定义了 CanvasKit（Skia 的 WebAssembly 版本）的 Canvas 绑定性能测试集合。它包含数十个独立的性能基准测试用例，覆盖了 CanvasKit 的核心绘制操作、矩阵运算、图片解码、段落排版、阴影渲染和字体处理等关键功能。每个测试用例遵循统一的 setup/test/teardown 模式，可通过 `benchmark.js` 框架执行并收集帧时间数据。

## 架构位置

此文件是 CanvasKit 性能测试基础设施的核心组件，位于测试流水线的中间层。

- 所属模块：`tools/perf-canvaskit-puppeteer/`（CanvasKit Puppeteer 性能测试）
- 上游依赖：`benchmark.js` 提供测试框架和计时能力
- 下游消费者：`perf-canvaskit-with-puppeteer.js` 驱动浏览器执行测试
- 输出目标：Skia Perf 数据收集系统

## 主要类与结构体

此文件不使用类，而是使用两个全局数组和辅助函数：

### 全局数组
- **`tests`**：存储所有性能测试用例的数组
- **`onlytests`**：用于调试的过滤数组，仅运行此数组中的测试

### 测试用例结构
每个测试对象包含以下字段：
- `description`：测试描述
- `setup(CanvasKit, ctx)`：初始化函数（可异步）
- `test(CanvasKit, ctx)`：被测代码（可异步）
- `teardown(CanvasKit, ctx)`：清理函数
- `perfKey`：性能数据的唯一标识键

## 公共 API 函数

### 辅助函数
| 函数 | 描述 |
|------|------|
| `randomColorTwo(CanvasKit, i, j)` | 生成指定两通道随机的 Color4f 颜色 |
| `randomColor(CanvasKit)` | 生成全随机 Color4f 颜色 |
| `starPath(CanvasKit, X, Y, R)` | 创建以 (X,Y) 为中心、R 为半径的八角星路径 |
| `htmlImageElementToDataURL(element)` | 将 HTML Image 元素转为 data URL |

### 测试用例列表（按类别）

**Canvas 绘制测试：**
- `canvas_drawColor`：绘制 10K 个彩色矩形裁剪区域
- `canvas_drawOval`：绘制 10K 个彩色椭圆
- `canvas_drawRRect`：绘制 10K 个彩色圆角矩形
- `canvas_drawRect`：绘制 10K 个彩色矩形
- `canvas_drawRect_malloc`：使用 malloc 缓冲区绘制 10K 个矩形
- `canvas_drawRect4f`：使用 4 float API 绘制 10K 个矩形
- `canvas_drawShadow`：绘制带色调阴影
- `canvas_drawHugeGradient`：绘制含 10K 色标的径向渐变
- `canvas_drawPngImage`：绘制 PNG 图片
- `canvas_blur_mask_filter`：绘制带模糊遮罩的路径

**颜色和画笔测试：**
- `computeTonalColors`：计算色调颜色
- `paint_setColor_getColor`：画笔颜色读写
- `paint_setColorComponents`：按分量设置画笔颜色

**图片解码测试（针对 3 种图片尺寸）：**
- `canvas_*_HTMLImageElementDecoding`：浏览器 API 图片解码
- `canvas_*_wasmImageDecoding`：WASM 编解码器图片解码

**3x3 矩阵测试：**
- `skmatrix_multiply`：矩阵乘法
- `skmatrix_transformPoint`：点变换（mapPoints）
- `skmatrix_invert`：矩阵求逆
- `skmatrix_makeShader`：从矩阵创建着色器
- `skmatrix_concat`：画布矩阵连接

**4x4 矩阵测试：**
- `skm44_multiply`：4x4 矩阵乘法
- `skm44_invert`：4x4 矩阵求逆
- `skm44_concat`：4x4 矩阵画布连接

**DOMMatrix 对照测试：**
- `dommatrix_multiply/transformPoint/invert/makeShader`：使用 DOMMatrix 的等效操作

**段落排版测试（5 种变体）：**
- `canvas_drawParagraph_static`：静态段落
- `canvas_drawParagraph_color_changing`：颜色变化段落
- `canvas_drawParagraph_size_changing`：字号变化段落
- `canvas_drawParagraph_layout_changing`：布局宽度变化段落
- `canvas_drawParagraph_everything`：所有属性同时变化

**字体测试（3 种格式）：**
- `font_getGlyphIDs_ttf/woff/woff2`：从不同字体格式获取字形 ID

## 内部实现细节

- **反优化技巧**：多处使用 `if (result.length === 18) { throw 'not possible'; }` 防止 V8 引擎将返回值优化掉
- **Malloc 对比测试**：`canvas_drawRect_malloc` 对比标准 API，测试使用预分配 WASM 内存的性能增益
- **段落测试变体**：通过变量组合（颜色、字号、布局宽度）的变化来模拟不同级别的缓存失效场景
- **图片解码对比**：对比浏览器原生解码与 WASM 内嵌编解码器的性能差异
- **字形缓存测试**：通过每次获取单个字形 ID 来强制缓存未命中，参考 skbug.com/40043207

## 依赖关系

- CanvasKit WebAssembly 模块（运行时依赖）
- `benchmark.js`：提供测试框架中的 `getSurface` 和 `startTimingFrames`
- 外部资源文件：`test_512x512.png`、`test_64x64.png`、`test_1500x959.jpg`
- 字体文件：`Roboto-Regular.ttf`、`.woff`、`.woff2`
- 浏览器 API：`DOMMatrix`、`DOMPoint`、`Image`、`Canvas`

## 设计模式与设计决策

- **数据驱动测试**：所有测试用例以对象形式推入全局数组，由框架统一调度执行
- **上下文对象模式**：`ctx` 对象在 setup 中初始化资源，在 test 中使用，在 teardown 中释放，实现了清晰的资源生命周期管理
- **模板循环生成**：使用 `for` 循环为多种图片尺寸和字体格式生成对应的测试用例，减少代码重复
- **A/B 对比设计**：矩阵操作同时提供 SkMatrix 和 DOMMatrix 的对比测试，便于评估 CanvasKit 相对于原生 API 的性能

## 性能考量

- 每个测试用例中的操作数量（10K 次迭代）经过选择，确保测量到有意义的时间差异
- `canvas_drawRect_malloc` 测试验证了预分配 WASM 内存对性能的影响，这对 CanvasKit 的内存使用优化至关重要
- 段落排版测试的字号变化模式（`size += ctx.frame % 4`）模拟真实应用中的字形缓存刷新
- `surface.flush()` 不在测试函数内调用，由 `benchmark.js` 统一处理，确保测量的一致性
- 画布尺寸固定为 600x600 像素，为所有测试提供一致的渲染目标

## 相关文件

- `tools/perf-canvaskit-puppeteer/benchmark.js` - 基准测试框架和帧计时
- `tools/perf-canvaskit-puppeteer/perf-canvaskit-with-puppeteer.js` - Puppeteer 驱动脚本
- `modules/canvaskit/` - CanvasKit 模块源代码

### 测试分类体系

所有测试用例可按以下维度分类：

**按渲染操作类型：**
- 基础几何绘制：drawRect、drawOval、drawRRect、drawColor
- 图片操作：drawImage、图片解码（HTMLImageElement vs WASM）
- 路径操作：drawPath（带遮罩滤镜）
- 文本排版：drawParagraph（多种变体）
- 阴影和特效：drawShadow、computeTonalColors

**按数学运算类型：**
- 3x3 矩阵运算：乘法、求逆、点变换、着色器创建、画布连接
- 4x4 矩阵运算：乘法、求逆、画布连接
- DOMMatrix 对比：同等操作的浏览器原生实现

**按资源管理模式：**
- 预分配内存：Malloc/Free API 的性能对比
- 每帧创建/销毁：着色器、段落、图片对象的生命周期管理
- 缓存行为：字形 ID 查询的缓存命中/未命中

### 测试结果解读

每个测试的 `perfKey` 用作 Skia Perf 系统中的唯一标识符。测试结果以帧时间的统计数据（平均值、中位数、百分位数）报告，存储在 Skia 的 Perf 数据库中，用于追踪长期性能趋势和检测回归。

### 测试数据文件

测试运行时需要以下外部资源文件：
- `test_512x512.png`：中等分辨率测试图片
- `test_64x64.png`：小尺寸测试图片
- `test_1500x959.jpg`：大尺寸 JPEG 测试图片
- `Roboto-Regular.ttf`：TrueType 字体文件
- `Roboto-Regular.woff`：WOFF 字体文件
- `Roboto-Regular.woff2`：WOFF2 字体文件

这些文件通过 Express 静态文件服务在 `/static/assets/` 路径下提供。

### 与 Skia Perf 系统的集成

测试结果通过以下流程进入 Skia Perf 数据库：
1. 测试框架收集每帧的时间数据
2. 数据序列化为 JSON 格式
3. Puppeteer 驱动程序将 JSON 写入输出文件
4. CI 流水线将输出文件上传到 Skia Perf 服务
5. Perf 服务解析数据并生成时间序列图表

### 扩展新测试

添加新测试用例的步骤：
1. 创建包含 description、setup、test、teardown 和 perfKey 的测试对象
2. 将测试对象推入 `tests` 数组
3. 确保 setup 中正确获取 canvas 和创建所需资源
4. 确保 teardown 中释放所有 CanvasKit 对象（调用 `.delete()`）
5. 不要在 test 函数中调用 `surface.flush()`
