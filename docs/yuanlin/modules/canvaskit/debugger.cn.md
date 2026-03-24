# debugger.js

> 源文件: modules/canvaskit/debugger.js

## 概述

`debugger.js` 是 CanvasKit 模块中用于支持 Skia 调试器功能的 JavaScript 绑定文件。它提供了加载和播放 SKP(Skia Picture)文件的能力,使开发者能够在 Web 环境中调试和分析 Skia 图形渲染过程。

该文件创建了 `SkpFilePlayer` 对象,用于将 SKP 文件数据加载到 WebAssembly 内存中,并通过 C++ 端的 `SkpDebugPlayer` 进行解析和播放。这是 Skia 调试工具链的重要组成部分,支持图形渲染的逐帧分析和调试。

## 架构位置

```
skia/
├── modules/
│   └── canvaskit/
│       ├── debugger.js           # 本文件 - 调试器绑定
│       ├── skp.js                # SKP 文件支持
│       ├── canvaskit_bindings.cpp # C++ 绑定
│       └── WasmCommon.h          # WASM 工具
└── tools/
    └── debugger/
        └── SkpDebugPlayer.h      # C++ 调试播放器
```

该文件是 CanvasKit 调试工具的一部分,与 Skia 的调试器工具集成,用于 Web 端的 SKP 文件分析。

## 主要类与结构体

### CanvasKit.SkpFilePlayer

工厂函数,用于创建 SKP 文件播放器实例。

**参数**:
- `file_arraybuf`: ArrayBuffer - SKP 文件的二进制数据

**返回值**: 包含两个属性的对象:
- `error`: 错误信息(如果加载失败)
- `player`: SkpDebugPlayer 实例(如果加载成功)

### SkpDebugPlayer 实例

通过 C++ 绑定创建的播放器对象,提供以下功能:
- `loadSkp(ptr, size)`: 加载 SKP 文件
- 播放和控制 SKP 中记录的绘图命令
- 逐步执行和分析渲染过程

## 公共 API 函数

### CanvasKit.SkpFilePlayer(file_arraybuf)

**功能**: 从 ArrayBuffer 创建 SKP 调试播放器。

**详细流程**:

1. **创建播放器实例**:
```javascript
var player = new this.SkpDebugPlayer();
```
实例化 C++ 端的 `SkpDebugPlayer` 对象。

2. **数据准备**:
```javascript
var fileContents = new Uint8Array(file_arraybuf);
var size = fileContents.byteLength;
```
将 ArrayBuffer 转换为 Uint8Array,获取文件大小。

3. **内存分配**:
```javascript
var fileMemPtr = this._malloc(size);
```
在 WASM 堆上分配足够大小的内存。

4. **内存映射**:
```javascript
var fileMem = new Uint8Array(CanvasKit.HEAPU8.buffer, fileMemPtr, size);
```
创建指向已分配内存的类型化数组视图。

5. **数据复制**:
```javascript
fileMem.set(fileContents);
```
将文件内容复制到 WASM 堆。

6. **加载 SKP**:
```javascript
var error = player.loadSkp(fileMemPtr, size);
```
调用 C++ 方法解析 SKP 数据。

7. **内存释放**:
```javascript
this._free(fileMemPtr);
```
释放临时内存,SKP 数据已被 SkPicture 内部结构持有。

8. **返回结果**:
```javascript
return {
  'error': error,
  'player': player
};
```
返回错误信息和播放器实例。

**使用示例**:
```javascript
fetch('my_drawing.skp')
  .then(resp => resp.arrayBuffer())
  .then(data => {
    const result = CanvasKit.SkpFilePlayer(data);
    if (result.error) {
      console.error('Failed to load SKP:', result.error);
    } else {
      // 使用 result.player 进行调试
    }
  });
```

## 内部实现细节

### 内存管理策略

**临时内存模式**:
- 分配内存 → 复制数据 → 加载 → 立即释放
- 不同于 `skp.js` 的所有权转移模式

**原因**: `SkpDebugPlayer` 内部会复制或引用计数 SKP 数据,因此外部缓冲区可以安全释放。

### 数据转换链

```
ArrayBuffer (用户数据)
    ↓
Uint8Array (JavaScript)
    ↓
WASM 堆内存 (fileMemPtr)
    ↓
C++ SkpDebugPlayer
    ↓
SkPicture 内部结构
```

### 错误处理

`loadSkp` 返回错误信息:
- 如果 SKP 格式无效,返回错误字符串
- 如果加载成功,返回 null 或空字符串

**用户应检查 error 属性**:
```javascript
if (result.error) {
  // 处理错误
}
```

### 类型化数组视图

```javascript
var fileMem = new Uint8Array(CanvasKit.HEAPU8.buffer, fileMemPtr, size);
```

**关键点**:
- 不创建新缓冲区,而是创建现有内存的视图
- `fileMemPtr` 是 WASM 堆中的偏移量
- 直接访问 Emscripten 的堆内存

### 与 skp.js 的对比

**skp.js**:
- 创建 SkPicture 用于渲染
- 所有权转移,不释放内存

**debugger.js**:
- 创建 SkpDebugPlayer 用于调试分析
- 复制数据,释放临时内存
- 提供更丰富的调试功能

## 依赖关系

### JavaScript API 依赖

**CanvasKit 核心**:
- `CanvasKit._malloc`: 内存分配
- `CanvasKit._free`: 内存释放
- `CanvasKit.HEAPU8`: WASM 堆视图
- `CanvasKit.SkpDebugPlayer`: C++ 播放器类

**Web API**:
- `ArrayBuffer`: 二进制数据容器
- `Uint8Array`: 类型化数组

### C++ 依赖

**SkpDebugPlayer**:
- 定义在 `tools/debugger/SkpDebugPlayer.h`
- 提供 SKP 解析和播放功能
- 通过 Emscripten 绑定暴露给 JavaScript

**Skia 核心**:
- `SkPicture`: 图片记录格式
- `SkCanvas`: 绘图表面
- SKP 序列化/反序列化

### 模块关系

```
debugger.js
    ↓ (使用)
SkpDebugPlayer (C++)
    ↓ (依赖)
SkPicture, SkCanvas
```

## 设计模式与设计决策

### 工厂模式

`SkpFilePlayer` 是一个工厂函数,封装了创建和初始化调试播放器的复杂过程:
- 隐藏内存管理细节
- 提供简单的输入输出接口
- 自动处理资源清理

### 对象封装

返回对象包含 `error` 和 `player` 两个属性:
```javascript
{
  'error': error,
  'player': player
}
```

**优点**:
- 明确的错误处理机制
- 不抛出异常,便于错误检查
- 同时返回多个值

### 资源获取即初始化(RAII)

虽然是 JavaScript 代码,但遵循 RAII 原则:
- 分配内存后立即使用
- 使用完毕立即释放
- 避免内存泄漏

### 防御性复制

复制数据到 WASM 堆而非直接使用 ArrayBuffer:
- 确保数据格式正确
- 避免跨边界的内存访问问题
- 提供统一的 C++ 接口

## 性能考量

### 内存开销

**临时双倍内存**:
- JavaScript 端的 ArrayBuffer
- WASM 堆上的副本
- 加载后立即释放 WASM 副本

**优化**: 对于大型 SKP 文件,考虑流式加载或分块处理。

### 数据复制性能

**Uint8Array.set()**: 高度优化的批量内存复制,比逐字节复制快得多。

**复杂度**: O(n),其中 n 是文件大小。

### 典型性能

- **小型 SKP** (< 1MB): 几毫秒内完成加载
- **大型 SKP** (> 10MB): 可能需要几十到几百毫秒
- **瓶颈**: 通常在网络传输而非解析

### 最佳实践

1. **异步加载**: 使用 `fetch` 异步加载 SKP 文件,避免阻塞 UI
2. **进度指示**: 对大文件显示加载进度
3. **错误处理**: 始终检查返回的 error 属性
4. **资源释放**: 使用完播放器后手动释放(如果提供 dispose 方法)
5. **流式处理**: 对超大文件考虑分块或流式处理

## 相关文件

### JavaScript 相关
- `modules/canvaskit/skp.js` - SKP 文件的基本支持(用于渲染)
- `modules/canvaskit/canvaskit_bindings.cpp` - C++ 绑定实现

### C++ 调试器实现
- `tools/debugger/SkpDebugPlayer.h` - 调试播放器头文件
- `tools/debugger/SkpDebugPlayer.cpp` - 调试播放器实现
- `tools/debugger/DebugCanvas.h` - 调试 Canvas 类

### SKP 格式
- `include/core/SkPicture.h` - Picture 接口
- `src/core/SkPictureData.h` - SKP 数据格式
- `src/core/SkPicturePlayback.cpp` - 回放实现

### 相关工具
- `tools/skiaserve/` - Skia 可视化调试服务器
- `tools/viewer/` - Skia Viewer 工具

### 测试文件
- `modules/canvaskit/tests/debugger_test.js` - 调试器功能测试
