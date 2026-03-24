# CanvasKit Debugger Bindings - SKP 调试播放器绑定

> 源文件: `modules/canvaskit/debugger_bindings.cpp`

## 概述

debugger_bindings.cpp 定义了 `SkpDebugPlayer` 类及其 Emscripten JavaScript 绑定。该类加载 SKP（Skia Picture）或 MSKP（Multi-Picture）文件，并提供详细的播放控制、命令检查、可视化调试功能。它是 Skia Debugger Web 应用的核心后端，支持逐命令回放、过绘制可视化、裁剪区域显示、图层检查以及像素级命令查找等调试功能。

## 架构位置

该文件属于 CanvasKit 的调试工具扩展，独立于核心渲染功能。它连接了 Skia 的 DebugCanvas 调试基础设施和浏览器端的调试器 UI。

```
浏览器端调试器 UI (JavaScript)
  └── Emscripten 绑定 (本文件)
        └── SkpDebugPlayer
              ├── DebugCanvas (单帧绘制记录)
              ├── DebugLayerManager (多帧图层管理)
              ├── UrlDataManager (资源缓存)
              └── Skia 反序列化管线
                    ├── SkPicture::MakeFromStream
                    └── SkMultiPictureDocument::Read
```

## 主要类与结构体

### `SkpDebugPlayer`
核心调试播放器类，管理 SKP/MSKP 文件的加载、渲染和检查。

**成员变量**：
- `frames`：`vector<unique_ptr<DebugCanvas>>`，每帧一个调试画布
- `fp`：当前帧索引
- `fBoundsArray`：每帧的边界矩形数组
- `fImages`：文件中的图像资源
- `udm`：`UrlDataManager`，资源 ID 缓存
- `fLayerManager`：`DebugLayerManager`，MSKP 图层管理器
- `fInspectedLayer`：当前检查的图层 ID（-1 表示顶层）

### `ImageInfoNoColorspace`
简化的图像信息结构（不含色彩空间），用于跨 WASM 边界传递：
```cpp
struct ImageInfoNoColorspace {
    int width, height;
    SkColorType colorType;
    SkAlphaType alphaType;
};
```

## 公共 API 函数

### 文件加载

#### `loadSkp(cptr, length) -> string`
- **功能**：从 WASM 内存加载 SKP 或 MSKP 文件
- **参数**：`cptr` 为 WASM 内存指针（`uintptr_t`），`length` 为字节长度
- **返回值**：空字符串表示成功，否则为错误信息
- **行为**：自动检测单帧/多帧格式（通过 `kMultiMagic` 签名）

### 渲染控制

#### `drawTo(surface, index)`
- **功能**：从第一条命令绘制到指定命令索引
- **行为**：区分顶层帧渲染和图层事件渲染

#### `draw(surface)`
- **功能**：完整绘制当前帧

#### `changeFrame(index)`
- **功能**：切换到指定帧

### 调试信息

#### `getSize() -> int`
- **功能**：获取当前帧/图层的命令数量

#### `getFrameCount() -> int`
- **功能**：获取总帧数

#### `jsonCommandList(surface) -> string`
- **功能**：以 JSON 格式输出当前帧的命令列表

#### `lastCommandInfo() -> string`
- **功能**：获取最后绘制命令的变换矩阵和裁剪区域（JSON 格式）

#### `getBounds() / getBoundsForFrame(frame) -> SkIRect`
- **功能**：获取帧的边界矩形

### 可视化调试

#### `setOverdrawVis(on)`
- **功能**：启用/禁用过绘制可视化

#### `setGpuOpBounds(on)`
- **功能**：显示/隐藏 GPU 操作边界

#### `setClipVizColor(color)`
- **功能**：设置裁剪区域可视化颜色

#### `setAndroidClipViz(on)`
- **功能**：启用/禁用 Android 裁剪可视化

#### `setOriginVisible(on)`
- **功能**：显示/隐藏坐标原点

### 命令控制

#### `deleteCommand(index)`
- **功能**：删除指定索引的绘制命令

#### `setCommandVisibility(index, visible)`
- **功能**：切换命令的可见性

### 图像资源

#### `getImageResource(index) -> string`
- **功能**：获取资源图像的 base64 PNG 编码（带 data URI 前缀）

#### `getImageCount() -> int`
- **功能**：获取资源图像数量

#### `getImageInfo(index) -> ImageInfoNoColorspace`
- **功能**：获取资源图像的基本信息

#### `imageUseInfo(frame, nodeid) -> JSObject`
- **功能**：获取图像在命令中的使用信息

### 图层检查

#### `setInspectedLayer(nodeId)`
- **功能**：设置要检查的图层（-1 返回顶层）

#### `getLayerSummariesJs() -> JSArray`
- **功能**：获取当前帧所有可用图层的摘要

#### `getLayerKeys() -> JSArray`
- **功能**：获取所有图层键（frame + nodeId）

### 像素查找

#### `findCommandByPixel(surface, x, y, commandIndex) -> int`
- **功能**：查找最后修改指定像素颜色的命令
- **算法**：二分搜索，O(log n) 复杂度

## 内部实现细节

### 文件格式检测

通过检查魔数 `"Skia Multi-Picture Doc\n\n"` 区分单帧 SKP 和多帧 MSKP 格式。

### 反序列化管线

```cpp
SkDeserialProcs procs;
procs.fImageDataProc = deserializeImage;      // 图像反序列化
procs.fTypefaceCtx = &fallback;               // 字体回退
procs.fTypefaceStreamProc = deserializeTypeface; // 字体反序列化
```

- **图像**：通过 `SkCodec` 解码，强制光栅化（非延迟加载）
- **字体**：使用 FreeType + Empty FontMgr 回退
- **多帧**：使用 `SkSharingDeserialContext` 处理跨帧图像共享

### 像素查找二分算法

```cpp
int findCommandByPixel(surface, x, y, commandIndex) {
    SkColor finalColor = evaluateCommandColor(surface, commandIndex, x, y);
    int lo = 0, hi = commandIndex;
    while (hi - lo > 1) {
        int mid = (hi - lo) / 2 + lo;
        if (evaluateCommandColor(surface, mid, x, y) == finalColor)
            hi = mid;
        else
            lo = mid;
    }
    return hi;
}
```
通过重复渲染到指定命令并读取像素颜色，使用二分搜索找到颜色变化的边界。

### Emscripten 绑定

通过 `EMSCRIPTEN_BINDINGS` 注册：
- `SkpDebugPlayer` 类的 24+ 个方法
- `SkIRect`、`LayerSummary`、`ImageInfoNoColorspace` 值对象
- `VectorLayerSummary` 向量类型

### WebGL 支持

通过 `#ifdef CK_ENABLE_WEBGL` 条件编译：
- 包含 Ganesh GPU 后端头文件
- 在 `drawTo` 和 `draw` 后调用 `skgpu::ganesh::Flush`

## 依赖关系

- **Skia 核心**：`SkPicture`、`SkSurface`、`SkCanvas`、`SkImage`、`SkCodec`、`SkStream`
- **Skia 文档**：`SkMultiPictureDocument`（MSKP 格式支持）
- **Skia 调试工具**：`DebugCanvas`、`DebugLayerManager`、`DrawCommand`、`UrlDataManager`
- **Skia 编码**：`SkPngEncoder`（图像资源导出）
- **Skia 工具**：`SkSharingProc`（图像共享反序列化）、`SkJSONWriter`
- **Skia 字体**：`SkFontMgr_empty`、`SkTypeface_FreeType`
- **Emscripten**：`<emscripten.h>`、`<emscripten/bind.h>`

## 设计模式与设计决策

1. **全局调试状态**：过绘制、GPU 边界等可视化设置应用于所有帧和图层，因为它们是全局调试选项。

2. **图层检查模式**：通过 `fInspectedLayer` 在顶层帧和图层事件之间切换，使用同一套 API 检查不同层级。

3. **二分像素查找**：利用了"绘制命令单调递增影响像素"的假设，以 O(log n) 效率替代 O(n) 的逐命令检查。注释承认可能不是绝对精确。

4. **Base64 图像导出**：`getImageResource` 将图像编码为 PNG 再转 Base64，便于浏览器 `<img>` 标签直接显示。

5. **JSObject 互操作**：使用 Emscripten 的 `val::object()` 和 `val::array()` 构建 JavaScript 对象，实现 C++ 到 JS 的结构化数据传递。

## 性能考量

- `findCommandByPixel` 的二分搜索每次需要渲染到指定命令并读取像素，对复杂 SKP 可能较慢
- `jsonCommandList` 生成完整的 JSON 命令列表可能产生大量数据
- `getImageResource` 涉及 PNG 编码 + Base64 转换，仅在调试器请求时执行
- MSKP 加载需要反序列化所有帧，初始加载可能较慢
- WebGL 模式下每次 `drawTo/draw` 后都调用 `Flush` 确保 GPU 命令提交

## 相关文件

- `tools/debugger/DebugCanvas.h` - DebugCanvas 调试画布
- `tools/debugger/DebugLayerManager.h` - 图层管理器
- `tools/debugger/DrawCommand.h` - 绘制命令抽象
- `tools/UrlDataManager.h` - URL 数据管理
- `tools/SkSharingProc.h` - 图像共享上下文
- `include/docs/SkMultiPictureDocument.h` - MSKP 文档格式
- `modules/canvaskit/externs.js` - SkpDebugPlayer JavaScript 声明
