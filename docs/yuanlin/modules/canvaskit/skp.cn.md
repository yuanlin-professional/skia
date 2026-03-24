# skp.js

> 源文件: modules/canvaskit/skp.js

## 概述

`skp.js` 是 CanvasKit 模块中用于处理 Skia Picture (SKP) 文件格式的 JavaScript 绑定文件。该文件提供了从二进制数据创建 `SkPicture` 对象的功能,使得 Web 应用能够加载和使用 Skia 的图形记录格式。SKP 文件是 Skia 的矢量图形序列化格式,可以记录和回放绘图命令序列。

这个文件通过扩展 CanvasKit 的初始化流程,添加了 `MakePicture` 方法,该方法能够解析 SKP 格式的二进制数据并创建相应的图片对象。

## 架构位置

在 Skia 架构中,`skp.js` 位于以下位置:

```
skia/
├── modules/
│   └── canvaskit/          # CanvasKit WebAssembly 绑定层
│       ├── skp.js          # 本文件 - SKP 格式支持
│       ├── canvaskit_bindings.cpp  # 主要的 C++ 绑定
│       └── WasmCommon.h    # WebAssembly 通用工具
```

该文件是 CanvasKit 模块的一部分,CanvasKit 是 Skia 的 WebAssembly 移植版本,为 Web 应用提供高性能的 2D 图形渲染能力。`skp.js` 作为可选的功能模块,专门负责 SKP 文件格式的支持。

## 主要类与结构体

### CanvasKit._extraInitializations

这是一个数组,用于存储额外的初始化函数。每个函数会在 CanvasKit 主模块加载后执行。

**作用**:
- 提供模块化的初始化机制
- 允许不同功能模块独立添加初始化逻辑
- 确保初始化顺序的可控性

### CanvasKit.MakePicture

这是添加到 CanvasKit 对象上的静态方法,用于从二进制数据创建 `SkPicture` 对象。

**参数**:
- `data`: TypedArray 或 ArrayBuffer - SKP 格式的二进制数据

**返回值**:
- 成功时返回 `SkPicture` 对象
- 失败时返回 `null`

## 公共 API 函数

### CanvasKit.MakePicture(data)

从 SKP 格式的二进制数据创建 SkPicture 对象。

**功能描述**:
该函数接收 SKP 文件的二进制数据(通常通过 `fetch().then(resp => resp.arrayBuffer())` 获取),并将其解析为可以在 Canvas 上绘制的 Picture 对象。

**实现步骤**:
1. 将输入数据转换为 `Uint8Array` 格式
2. 在 WebAssembly 堆上分配内存 (`_malloc`)
3. 将数据复制到分配的内存中
4. 调用底层的 C++ 函数 `_MakePicture` 进行解析
5. 如果解析失败,输出调试信息并返回 `null`
6. 返回创建的 Picture 对象

**使用示例**:
```javascript
// 从网络加载 SKP 文件
fetch('drawing.skp')
  .then(resp => resp.arrayBuffer())
  .then(data => {
    const picture = CanvasKit.MakePicture(data);
    if (picture) {
      // 使用 picture 进行绘制
      const canvas = surface.getCanvas();
      canvas.drawPicture(picture);
    }
  });
```

**错误处理**:
- 如果数据格式无效或损坏,函数会输出 "Could not decode picture" 并返回 `null`
- 调用者需要检查返回值以确保 Picture 创建成功

## 内部实现细节

### 内存管理

该实现采用了特殊的内存管理策略:

**数据所有权转移**:
- 使用 `CanvasKit._malloc` 在 WASM 堆上分配内存
- 通过 `CanvasKit.HEAPU8.set` 将 JavaScript 数据复制到 WASM 堆
- SKP Picture 对象接管分配的内存所有权
- JavaScript 端不需要手动释放内存,由 C++ 端的 Picture 对象负责

这种设计避免了内存泄漏,同时确保数据在 JavaScript 和 C++ 之间正确传递。

### 初始化机制

文件使用了 CanvasKit 的扩展初始化模式:

```javascript
CanvasKit._extraInitializations = CanvasKit._extraInitializations || [];
CanvasKit._extraInitializations.push(function() { ... });
```

**优势**:
- 模块化设计,每个功能可以独立添加初始化代码
- 避免全局命名空间污染
- 支持条件编译,可以选择性包含功能

### C++ 绑定调用

`_MakePicture` 是通过 Emscripten 绑定的 C++ 函数:

**调用流程**:
1. JavaScript 传递内存指针和数据长度
2. C++ 端接收指针,读取 SKP 格式数据
3. 使用 Skia 的 `SkPicture::MakeFromData` 解析数据
4. 返回 Picture 对象的 JavaScript 包装

## 依赖关系

### 内部依赖

**CanvasKit 核心**:
- `CanvasKit._malloc`: 内存分配函数
- `CanvasKit.HEAPU8`: WASM 堆的字节视图
- `CanvasKit._MakePicture`: C++ 绑定函数
- `Debug`: 调试输出函数

### 外部依赖

**Emscripten**:
- 提供 JavaScript 和 WebAssembly 的互操作能力
- 管理 WASM 堆内存

**Skia C++ 库**:
- `SkPicture`: 图片记录和回放类
- `SkData`: 数据封装类
- SKP 格式解析器

### 数据流

```
用户 JavaScript 代码
    ↓ (ArrayBuffer/TypedArray)
CanvasKit.MakePicture
    ↓ (复制到 WASM 堆)
_MakePicture (C++)
    ↓ (解析 SKP 格式)
SkPicture::MakeFromData
    ↓ (返回 SkPicture*)
JavaScript SkPicture 对象
```

## 设计模式与设计决策

### 工厂模式

`MakePicture` 是一个工厂方法,负责创建和初始化 Picture 对象。这种模式的优势:
- 封装复杂的创建逻辑
- 统一的对象创建接口
- 便于错误处理和资源管理

### 适配器模式

该文件充当 JavaScript API 和 C++ 实现之间的适配器:
- 将 JavaScript 的 TypedArray/ArrayBuffer 转换为 C++ 可用的格式
- 处理内存布局差异
- 提供符合 JavaScript 习惯的 API

### 防御性编程

代码包含多处防御性检查:
- 确保 `_extraInitializations` 数组存在
- 检查 Picture 创建是否成功
- 提供明确的错误信息

### 内存所有权设计

**关键决策**: SKP 对象接管内存所有权

**理由**:
- 避免数据复制,提高性能
- 简化内存管理,减少泄漏风险
- 符合 C++ 的 RAII 原则

## 性能考量

### 内存分配策略

**单次分配**: 一次性分配所需的全部内存,避免多次小额分配的开销。

**零拷贝设计**: 在可能的情况下,数据直接在 WASM 堆上处理,避免 JavaScript 和 WASM 之间的多次复制。

### 数据传输优化

**批量复制**: 使用 `HEAPU8.set` 进行批量内存复制,比逐字节复制快得多。

**内存对齐**: WASM 堆的内存布局已针对性能优化。

### 错误路径性能

**早期返回**: 在解析失败时立即返回 `null`,避免不必要的处理。

**调试信息**: 仅在开发模式下输出调试信息,生产环境可以移除以提升性能。

### 使用建议

**预加载**: 对于大型 SKP 文件,考虑在应用启动时预加载,避免运行时的加载延迟。

**缓存 Picture 对象**: 一旦创建,可以重复使用 Picture 对象进行绘制,避免重复解析。

**异步加载**: 使用 `fetch` 和 Promise 进行异步加载,避免阻塞主线程。

## 相关文件

### 核心绑定文件
- `modules/canvaskit/canvaskit_bindings.cpp` - CanvasKit 的主要 C++ 绑定实现
- `modules/canvaskit/WasmCommon.h` - WebAssembly 通用工具和类型定义

### 相关功能模块
- `modules/canvaskit/canvas.js` - Canvas API 的 JavaScript 封装
- `modules/canvaskit/surface.js` - Surface 相关功能
- `modules/canvaskit/image.js` - 图像处理功能

### Skia 核心实现
- `include/core/SkPicture.h` - SkPicture 类的定义
- `src/core/SkPictureData.h` - SKP 格式的数据结构
- `src/core/SkPicturePlayback.cpp` - Picture 回放实现

### 构建配置
- `modules/canvaskit/BUILD.bazel` - Bazel 构建配置
- `modules/canvaskit/compile.sh` - Emscripten 编译脚本

### 测试文件
- `modules/canvaskit/tests/skp_test.js` - SKP 功能的单元测试
