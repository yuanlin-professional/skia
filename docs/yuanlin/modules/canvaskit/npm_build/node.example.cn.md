# CanvasKit Node.js 使用示例 (node.example.js)

> 源文件: `modules/canvaskit/npm_build/node.example.js`

## 概述

`node.example.js` 是一个在 Node.js 环境中使用 CanvasKit 的完整示例程序，约 116 行代码。它演示了两种 CanvasKit 的使用模式：一是通过 Canvas2D 兼容 API（`MakeCanvas` + `getContext('2d')`）进行绘制，二是使用 CanvasKit 原生 API（`MakeSurface` + `Paint` + `Path` + `Font`）进行更精细的绘图控制。两种方式都输出 Base64 编码的 PNG 图像（以 `<img>` 标签形式打印到控制台）。

## 架构位置

该文件位于 `npm_build` 目录下，作为 CanvasKit npm 包的使用示例。它展示了如何在无浏览器的 Node.js 环境中加载和使用 CanvasKit。

```
Node.js 环境
  └── require('./bin/canvaskit.js')
      └── CanvasKitInit() → Promise<CanvasKit>
          ├── Canvas2D 兼容 API（MakeCanvas + getContext('2d')）
          └── CanvasKit 原生 API（MakeSurface + Paint + Path + Font）
```

## 主要类与结构体

无自定义类。使用 CanvasKit 提供的以下核心对象：

- `CanvasKit.Paint` — 画笔
- `CanvasKit.Path` — 路径
- `CanvasKit.Font` — 字体
- `CanvasKit.Typeface` — 字体面
- `CanvasKit.PathEffect` — 路径效果

## 公共 API 函数

### Canvas2D 兼容示例（主流程）

| API 调用 | 说明 |
|---------|------|
| `CanvasKit.MakeCanvas(300, 300)` | 创建 300x300 离屏画布 |
| `canvas.decodeImage(img)` | 从 Buffer 解码图像 |
| `canvas.loadFont(data, descriptor)` | 加载字体 |
| `ctx.fillText()` / `ctx.strokeText()` | 绘制文本 |
| `ctx.drawImage()` | 绘制图像（支持源/目标裁剪） |
| `canvas.toDataURL()` | 导出 Base64 数据 URL |

### CanvasKit 原生 API 示例（fancyAPI）

| API 调用 | 说明 |
|---------|------|
| `CanvasKit.MakeSurface(300, 300)` | 创建渲染表面 |
| `new CanvasKit.Paint()` | 创建画笔 |
| `CanvasKit.Typeface.MakeTypefaceFromData()` | 从数据创建字体面 |
| `new CanvasKit.Font(roboto, 30)` | 创建字体 |
| `CanvasKit.PathEffect.MakeDash()` | 创建虚线效果 |
| `canvas.drawPath()` / `canvas.drawText()` | 绘制路径和文本 |
| `surface.makeImageSnapshot()` | 捕获渲染快照 |
| `img.encodeToBytes()` | 编码为 PNG 字节 |

### starPath 辅助函数

生成八角星形路径，使用极坐标计算 8 个点的位置。

## 内部实现细节

### CanvasKit 加载

使用 `require` 导入 CanvasKit 工厂函数，配置 `locateFile` 回调指向 WASM 文件所在的 `bin` 目录。工厂返回 Promise，在 WASM 加载完成后 resolve。

### 资源加载

使用 `fs.readFileSync` 同步读取图像（`mandrill_512.png`）和字体（`Roboto-Regular.woff`）文件。资源位于 `tests/assets` 目录。

### Canvas2D 兼容模式

演示了 Canvas2D API 的常用操作：旋转、文本绘制、路径绘制、透明度、图像平滑控制、图像裁剪绘制。

### 原生 API 模式

演示了 CanvasKit 特有的功能：虚线路径效果、显式的画笔样式配置、抗锯齿控制、图像快照和 PNG 编码。

### 内存管理

原生 API 示例展示了正确的内存管理模式：所有 C++ 对象（Paint、Path、Font、Typeface、PathEffect）在使用完毕后必须调用 `.delete()` 释放 WASM 堆内存，Surface 使用 `.dispose()` 释放。

### 输出格式

两种模式都输出 Base64 编码的 PNG 图像，以 HTML `<img>` 标签格式打印到控制台。用户可将输出粘贴到 HTML 文件中查看。

## 依赖关系

| 依赖项 | 说明 |
|-------|------|
| `./bin/canvaskit.js` | CanvasKit WASM 模块 |
| `fs` | Node.js 文件系统模块 |
| `path` | Node.js 路径模块 |
| `tests/assets/mandrill_512.png` | 示例图像 |
| `tests/assets/Roboto-Regular.woff` | 示例字体 |

## 设计模式与设计决策

- **双 API 演示**: 同时展示 Canvas2D 兼容层和原生 API，帮助不同背景的开发者快速入门
- **异步初始化**: 使用 Promise 模式等待 WASM 加载，符合 Node.js 异步编程习惯
- **显式内存释放**: 通过 `.delete()` 调用演示 WASM 内存管理的最佳实践
- **完整的资源生命周期**: 从加载 → 使用 → 编码 → 释放的完整流程

## 性能考量

- 使用 `readFileSync` 进行同步 I/O，在示例中简化了代码但不适合生产环境
- `encodeToBytes()` 在 CPU 上执行 PNG 编码，对大图像可能耗时
- 所有对象的 `.delete()` 调用确保不会产生 WASM 内存泄漏
- Base64 编码增加约 33% 的输出大小

## 相关文件

- `modules/canvaskit/npm_build/package.json` — npm 包配置
- `modules/canvaskit/canvaskit_bindings.cpp` — C++ 核心绑定
- `modules/canvaskit/htmlcanvas/` — Canvas2D 兼容层实现
- `tests/assets/` — 测试资源文件
