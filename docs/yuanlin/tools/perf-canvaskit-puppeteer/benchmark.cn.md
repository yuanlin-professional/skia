# CanvasKit 基准测试框架

> 源文件: `tools/perf-canvaskit-puppeteer/benchmark.js`

## 概述

此文件提供了 CanvasKit 性能测试的核心基准测试框架，包含 Surface 创建和帧时间测量两大功能。它在浏览器环境中运行，负责创建 CanvasKit 渲染表面（GPU 或 CPU），并通过 `requestAnimationFrame` 驱动的帧循环精确测量每帧的绘制时间、flush 时间和总帧间隔时间。

## 架构位置

此文件是 CanvasKit 性能测试基础设施的底层框架层。

- 所属模块：`tools/perf-canvaskit-puppeteer/`
- 角色：浏览器端基准测试运行时
- 上游消费者：`canvas_perf.js` 中定义的测试用例
- 通信机制：通过 `window._perfData`、`window._perfReady`、`window._perfDone` 与 Puppeteer 交互

## 主要类与结构体

此文件无类定义，提供两个核心全局函数。

## 公共 API 函数

### `getSurface(CanvasKit, webglversion)`
创建 CanvasKit 渲染表面。

**参数：**
- `CanvasKit`：已初始化的 CanvasKit 模块
- `webglversion`：WebGL 版本号

**行为：**
- 检查 URL hash 判断 GPU 或 CPU 模式
- GPU 模式：调用 `MakeWebGLCanvasSurface`，检测是否回退到 CPU
- CPU 模式：调用 `MakeSWCanvasSurface`
- 错误时设置 `window._error` 并返回 null

**返回值：** CanvasKit Surface 对象或 null

### `startTimingFrames(drawFn, surface, warmupFrames, maxFrames, timeoutMillis)`
执行帧计时测量。

**参数：**
- `drawFn`：零参数绘制函数
- `surface`：CanvasKit 表面
- `warmupFrames`：预热帧数（不计入测量）
- `maxFrames`：最大测量帧数
- `timeoutMillis`：超时毫秒数（可选）

**返回值：** Promise，resolve 时携带包含三种时间序列的对象：
- `total_frame_ms`：相邻帧起始时间的间隔（最常用的指标）
- `with_flush_ms`：绘制 + flush 的总时间
- `without_flush_ms`：仅绘制时间（不含 flush）

## 内部实现细节

### 帧循环机制
1. 使用 `window.requestAnimationFrame` 驱动帧循环
2. 每帧执行三个时间点测量：`start`（绘制前）、`afterDraw`（绘制后）、`end`（flush后）
3. `total_frame_ms` 通过相邻帧的 `start` 时间差计算
4. 预热帧期间仅递增计数器，不记录数据

### 预热机制
- 预热帧允许跳过首次渲染时的着色器编译、纹理上传和缓存建立等一次性开销
- 预热完成后将索引重置为 -1，开始正式测量

### Surface 创建的 GPU 回退检测
- 当 WebGL 上下文创建失败时，CanvasKit 会自动回退到 CPU 并为 canvas 元素添加 `ck-replaced` CSS 类
- `getSurface` 通过检测此类名来确认是否真正使用了 GPU

### 超时机制
- 使用 `performance.now()` 跟踪总测试时间
- 超时时 reject Promise 并输出已完成的帧数

## 依赖关系

- CanvasKit WebAssembly 模块
- 浏览器 API：`window.requestAnimationFrame`、`performance.now()`、`document.getElementById`
- HTML 页面中的 `<canvas id="anim">` 元素
- Puppeteer 交互全局变量：`window._perfData`、`window._error`

## 设计模式与设计决策

- **Promise 异步模式**：帧循环通过 Promise 包装，使调用方可以 await 测量完成
- **三级时间测量**：分离绘制时间、flush 时间和总帧时间，提供多维度的性能分析数据
- **预热消除噪声**：预热机制确保测量数据不受冷启动影响（如着色器编译、JIT 编译）
- **requestAnimationFrame 驱动**：使用浏览器的帧调度机制确保测量条件接近真实渲染场景
- **最小干预原则**：benchmark 框架仅负责计时和 flush，不干预测试代码的绘制逻辑

## 性能考量

- 使用 `Float32Array` 预分配帧数据数组，避免测量期间的内存分配
- `performance.now()` 提供微秒级精度的时间戳
- 帧间 `total_frame_ms` 是最接近用户感知的帧率指标
- `without_flush_ms` 对于非绘制测试（如矩阵运算）更为相关
- 超时保护防止无限循环的测试用例

## 相关文件

- `tools/perf-canvaskit-puppeteer/canvas_perf.js` - 使用此框架的测试定义
- `tools/perf-canvaskit-puppeteer/perf-canvaskit-with-puppeteer.js` - Puppeteer 驱动脚本

### GPU 回退检测机制

当 WebGL 上下文创建失败时，CanvasKit 的行为是：
1. 尝试创建 WebGL surface
2. 如果失败，自动回退到软件渲染（CPU）
3. 为 canvas 元素添加 `ck-replaced` CSS 类标记
4. `getSurface` 通过检测此类名来确认回退并报告错误

这确保了 GPU 基准测试不会在 CPU 模式下运行并产生误导性数据。

### 时间测量精度

`performance.now()` 在现代浏览器中提供微秒级精度（通常 5 微秒分辨率）。在某些浏览器安全配置下（如跨域隔离未启用时），精度可能被降低到毫秒级。为确保最佳精度，Puppeteer 驱动程序应配置适当的安全标志。

### 帧计数与数据数组

使用 `Float32Array` 预分配固定大小的数据数组（maxFrames 长度），避免在测量循环中进行堆内存分配。这是因为 JavaScript 中的垃圾回收暂停可能影响帧时间测量的准确性。

### 与 requestAnimationFrame 的关系

使用 `requestAnimationFrame` 而非 `setTimeout` 或 `while` 循环有以下原因：
1. 确保绘制与浏览器渲染管线同步
2. 允许浏览器在帧之间执行布局和合成
3. 在 GPU 模式下确保前一帧的 flush 完成
4. 模拟真实应用的帧调度方式

### 超时保护

`timeoutMillis` 参数提供了安全阀机制。当测试用例出现错误导致无限循环时，超时保护会中断测试并通过 reject Promise 报告超时信息，而非让测试无限挂起。
