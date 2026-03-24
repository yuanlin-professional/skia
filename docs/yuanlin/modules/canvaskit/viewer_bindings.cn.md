# CanvasKit Viewer 绑定 (viewer_bindings)

> 源文件: `modules/canvaskit/viewer_bindings.cpp`

## 概述

`viewer_bindings.cpp` 是 CanvasKit 中用于将 Skia Viewer 工具功能暴露给 WebAssembly 环境的绑定文件。它通过 Emscripten 的 `embind` 机制，将 Slide（幻灯片/演示页）的创建、加载、动画和交互功能绑定到 JavaScript 端，支持 SKP 文件、SVG 文件和特定 Sample 示例的渲染与交互。该文件是 Skia Viewer Web 版本的核心绑定层。

## 架构位置

该文件位于 CanvasKit 模块中，属于 Viewer 工具链的 WebAssembly 前端部分。它连接 JavaScript 前端与 Skia 的 `tools/viewer` 中的 Slide 抽象体系。

```
Web 前端 (JavaScript)
  └── viewer_bindings.cpp (Emscripten 绑定)
      ├── SKPSlide  ← SKP 格式的演示页
      ├── SvgSlide  ← SVG 格式的演示页
      ├── SampleSlide ← 内置示例
      └── Slide 基类 (load, animate, draw, onChar, onMouse)
```

## 主要类与结构体

### Slide（绑定到 JS）

Skia Viewer 的核心抽象类，代表一个可渲染和可交互的演示页面：

| 方法 | 说明 |
|------|------|
| `load(w, h)` | 加载 Slide，传入画布宽高 |
| `animate(nanos)` | 按时间戳推进动画 |
| `draw(canvas)` | 在 SkCanvas 上绘制当前帧 |
| `onChar(ch)` | 处理键盘字符输入 |
| `onMouse(x, y, state, modifiers)` | 处理鼠标输入事件 |

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `MakeSlide(name)` | 根据名称创建内置 Sample Slide（目前支持 "PathText" 和 "TessellatedWedge"） |
| `MakeSkpSlide(name, skpData)` | 从 SKP 二进制数据创建 Slide |
| `MakeSvgSlide(name, svgText)` | 从 SVG 文本数据创建 Slide |

### 枚举绑定

| 枚举 | 值 | 说明 |
|------|-----|------|
| `InputState` | Down, Up, Move, Right, Left | 输入状态（鼠标/触摸） |
| `ModifierKey` | None, Shift, Control, Option, Command, FirstPress | 修饰键 |

## 内部实现细节

### Slide 创建工厂

`MakeSlide` 使用硬编码的名称匹配来创建特定的 Sample 示例。通过 `extern` 声明引用在其他编译单元中定义的工厂函数（如 `MakePathTextSample`），然后使用 `SampleSlide` 包装。未匹配的名称返回 nullptr。

### SKP 和 SVG Slide 的数据传递

`MakeSkpSlide` 和 `MakeSvgSlide` 接收 `std::string` 格式的数据（Emscripten 自动处理 JS ArrayBuffer/String 的转换），创建 `SkMemoryStream` 并设置 `copyData=true` 以确保数据独立于 JS 端的生命周期。

### draw 方法的包装

`Slide::draw` 原本接收 `SkCanvas*` 指针，绑定使用 `optional_override` 将其转换为引用形式，以适配 Emscripten 的绑定约定。

### 智能指针管理

Slide 使用 `sk_sp<Slide>` 智能指针管理，通过 `.smart_ptr<sk_sp<Slide>>` 声明让 Emscripten 正确处理引用计数。

## 依赖关系

| 依赖项 | 说明 |
|-------|------|
| `include/core/SkCanvas.h` | 绘图画布 |
| `include/core/SkSurface.h` | 绘图表面 |
| `tools/skui/InputState.h` | 输入状态枚举 |
| `tools/skui/ModifierKey.h` | 修饰键枚举 |
| `tools/viewer/SKPSlide.h` | SKP 格式 Slide |
| `tools/viewer/SampleSlide.h` | 示例 Slide 包装 |
| `tools/viewer/SvgSlide.h` | SVG 格式 Slide |
| `<emscripten/bind.h>` | Emscripten 绑定 |
| `<GLES3/gl3.h>` | OpenGL ES 3.0（WebGL 后端） |

## 设计模式与设计决策

- **工厂模式**: 通过 `MakeSlide`, `MakeSkpSlide`, `MakeSvgSlide` 三个工厂函数创建不同类型的 Slide 实例
- **Slide 多态**: 所有 Slide 类型共享相同的 JS 接口（load/animate/draw/onChar/onMouse），利用 C++ 虚函数实现多态
- **硬编码示例列表**: `MakeSlide` 目前仅支持两个命名示例，扩展性有限但实现简洁
- **数据拷贝策略**: SKP/SVG 数据在创建 Stream 时设置 `copyData=true`，确保 C++ 端持有数据的独立副本，不受 JS 垃圾回收影响
- **最小化绑定面**: 只暴露 Slide 的必要交互接口，不暴露底层渲染管线细节

## 性能考量

- SKP/SVG 数据在传入时会进行一次完整拷贝（`copyData=true`），对大文件可能产生可观的内存分配开销
- Slide 的 draw 调用直接转发到 C++ 端，不涉及额外的数据序列化
- 智能指针 `sk_sp<Slide>` 确保正确的引用计数和自动释放
- 文件仅绑定少量函数和枚举，对 WASM 模块大小影响较小

## 相关文件

- `tools/viewer/SKPSlide.h` / `tools/viewer/SKPSlide.cpp` — SKP Slide 实现
- `tools/viewer/SvgSlide.h` / `tools/viewer/SvgSlide.cpp` — SVG Slide 实现
- `tools/viewer/SampleSlide.h` — Sample 包装 Slide
- `tools/skui/InputState.h` / `tools/skui/ModifierKey.h` — 输入枚举定义
- `modules/canvaskit/canvaskit_bindings.cpp` — CanvasKit 主绑定文件
