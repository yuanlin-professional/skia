# CanvasKit Skottie JavaScript 辅助层 (skottie.js)

> 源文件: `modules/canvaskit/skottie.js`

## 概述

`skottie.js` 是 CanvasKit 中 Skottie（Lottie 动画引擎）的 JavaScript 辅助层。它提供了创建受管动画（ManagedAnimation）的工厂函数、文本属性的初始化助手，以及 `Animation` 和 `ManagedAnimation` 原型方法的 JavaScript 端增强。该文件负责在 JS 端进行资源打包、内存序列化和类型转换，再调用底层 C++ 绑定完成实际的动画创建和操作。

## 架构位置

该文件位于 CanvasKit 的 JavaScript 辅助层，依赖 `memory.js` 进行数据序列化，与 `skottie_bindings.cpp` 中的 C++ 实现协同工作。

```
JavaScript 应用
  └── CanvasKit.MakeManagedAnimation()  ← skottie.js
      └── CanvasKit._MakeManagedAnimation()  ← skottie_bindings.cpp
          └── skottie::Animation / ManagedAnimation (C++)
              └── Lottie JSON 解析与渲染
```

## 主要类与结构体

### CanvasKit.Animation（原型扩展）

基础动画类，由 `MakeAnimation` 创建，支持简单的 Lottie 动画播放。

### CanvasKit.ManagedAnimation（原型扩展）

受管动画类，支持属性控制（颜色、透明度、文本、变换）、插槽系统和文本编辑器集成。

### SlottableTextProperty

文本属性值对象，用于设置 Lottie 动画中文本图层的各种参数：

| 属性 | 默认值 | 说明 |
|------|--------|------|
| `text` | `""` | 文本内容 |
| `textSize` | `0` | 字体大小 |
| `minTextSize` / `maxTextSize` | `0` / `MAX_VALUE` | 自适应文本大小范围 |
| `strokeWidth` | `0` | 描边宽度 |
| `lineHeight` / `lineShift` | `0` | 行高与行偏移 |
| `ascent` | `0` | 上升高度 |
| `maxLines` | `0` | 最大行数 |
| `horizAlign` | `TextAlign.Left` | 水平对齐 |
| `vertAlign` | `VerticalTextAlign.Top` | 垂直对齐 |
| `fillColor` / `strokeColor` | `TRANSPARENT` | 填充/描边颜色 |
| `boundingBox` | `[0,0,0,0]` | 文本边界框 |
| `direction` | `TextDirection.LTR` | 文本方向 |
| `linebreak` / `resize` / `strokeJoin` | 各自默认值 | 换行/缩放/连接策略 |

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `CanvasKit.MakeManagedAnimation(json, assets, prop_filter_prefix, soundMap, logger)` | 从 JSON 和资源集创建受管动画 |
| `CanvasKit.SlottableTextProperty(t)` | 初始化并填充文本属性对象的默认值 |

### Animation 原型方法

| 方法 | 说明 |
|------|------|
| `render(canvas, dstRect)` | 在指定矩形区域渲染动画帧 |
| `size(optSize)` | 获取动画尺寸 |

### ManagedAnimation 原型方法

| 方法 | 说明 |
|------|------|
| `render(canvas, dstRect)` | 在指定矩形区域渲染动画帧 |
| `seek(t, optDamageRect)` | 按归一化时间 [0,1] 定位，返回损伤矩形 |
| `seekFrame(frame, optDamageRect)` | 按帧号定位，返回损伤矩形 |
| `setColor(key, color)` | 设置命名颜色属性 |
| `setColorSlot(key, color)` | 通过插槽系统设置颜色 |
| `getColorSlot(key)` | 获取插槽颜色值 |
| `setVec2Slot(key, vec)` | 设置 2D 向量插槽 |
| `getVec2Slot(key)` | 获取 2D 向量插槽值 |
| `setTextSlot(key, textValue)` | 设置文本插槽 |
| `setTransform(key, anchor, position, scale, rotation, skew, skew_axis)` | 设置变换属性 |
| `size(optSize)` | 获取动画尺寸 |

## 内部实现细节

### 资源打包流程（MakeManagedAnimation）

1. 遍历 `assets` 字典中的每个键值对
2. 将资源数据（ArrayBuffer）拷贝到 WASM 堆：`CanvasKit._malloc` + `HEAPU8.set`
3. 将资源名称转换为 UTF-8 null-terminated 字符串：`stringToUTF8`（Emscripten 内置函数）
4. 将名称指针数组、数据指针数组和大小数组分别拷贝到 WASM 堆
5. 调用 C++ `_MakeManagedAnimation` 传入所有参数
6. 释放 JS 端分配的临时指针（C++ 端已完成数据拷贝）

### 损伤矩形返回模式

`seek` 和 `seekFrame` 方法使用 scratch 缓冲区 `_scratchFourFloatsAPtr` 接收 C++ 端写入的损伤矩形。如果调用方提供了 `optDamageRect`，则拷贝结果到该数组中；否则返回新的切片拷贝。

### 文本插槽设置

`setTextSlot` 需要将 fillColor、strokeColor 和 boundingBox 分别序列化到不同的 scratch 指针中，然后将这些指针地址作为属性附加到文本值对象上，再传入 C++。

### 颜色插槽的哨兵值

`getColorSlot` 使用 `[-1, -1, -1, -1]` 作为"未找到"的哨兵值。如果 C++ 端返回的颜色第一个分量为 -1，则 JS 端返回 null。

### 初始化钩子机制

文件使用 `_extraInitializations` 数组注册延迟执行的初始化函数，确保原型方法在 WASM 模块完全加载后才添加。

## 依赖关系

| 依赖项 | 说明 |
|-------|------|
| `memory.js` | `copy1dArray`, `copyRectToWasm`, `copyColorToWasm`, `copyColorFromWasm` |
| `skottie_bindings.cpp` | C++ 端的 `_MakeManagedAnimation`, `Animation`, `ManagedAnimation` 类 |
| Emscripten | `lengthBytesUTF8`, `stringToUTF8` 字符串处理函数 |
| `CanvasKit.TextAlign` 等枚举 | 文本属性的默认值 |

## 设计模式与设计决策

- **资源预打包**: 在 JS 端完成资源的内存布局和指针数组构造，一次性传入 C++，避免多次跨边界调用
- **可选参数模式**: `soundMap` 和 `logger` 为可选参数，直接透传给 C++，由 C++ 端处理 null 检查
- **原型增强**: 使用 JavaScript 原型方法包装 C++ 的底层方法（如 `_render`, `_seek`），在 JS 端处理数据序列化，C++ 端专注于核心逻辑
- **哨兵值而非异常**: 使用特殊值（-1, -1, ...）表示"未找到"，避免在 WASM 边界抛出异常
- **Scratch 缓冲区复用**: 多个方法共享同一批 scratch 指针，减少内存分配

## 性能考量

- 资源创建时有一次性的批量内存分配和拷贝开销，但之后 C++ 端持有独立副本，不再产生跨边界拷贝
- `seek`/`seekFrame` 使用 scratch 缓冲区返回损伤矩形，避免每帧分配新内存
- `render` 方法每帧只需拷贝一个 Rect（4 个 float）到 WASM 堆
- `setTransform` 将 9 个浮点数打包到 scratch 矩阵缓冲区中，利用已有的 3x3 矩阵 scratch 空间
- Emscripten 字符串函数（`lengthBytesUTF8`, `stringToUTF8`）直接操作 WASM 堆，避免中间分配

## 相关文件

- `modules/canvaskit/skottie_bindings.cpp` — Skottie C++ 绑定实现
- `modules/canvaskit/memory.js` — WASM 堆内存管理工具
- `modules/skottie/include/Skottie.h` — Skottie 动画核心头文件
- `modules/skottie/include/SlotManager.h` — 插槽管理器
- `modules/skottie/include/SkottieProperty.h` — 动画属性系统
