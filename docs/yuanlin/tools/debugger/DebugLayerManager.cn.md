# DebugLayerManager

> 源文件: `tools/debugger/DebugLayerManager.h`, `tools/debugger/DebugLayerManager.cpp`

## 概述

DebugLayerManager 是 Skia 调试器中用于管理 mskp 文件（多帧 SkPicture）中离屏层（offscreen layer）的类。在 Android 中，UI 层通过 RenderNode 管理，每个层可以在不同帧上被部分或完整重绘。DebugLayerManager 存储这些层的 SkPicture 绘制事件，并能够按需重建任意帧上任意层的渲染结果。

该类主要服务于 wasm-skp-debugger 动画调试场景，支持 Android HWUI 层的逐帧、逐命令回放。

## 架构位置

```
Skia Debugger
  +-- DebugCanvas         (主画布，解析层注解)
  +-- DebugLayerManager   (层管理器) <-- 本文件
  +-- DrawCommand         (命令系统)
       +-- DrawImageRectLayerCommand (延迟层渲染命令)
```

## 主要类与结构体

### `DebugLayerManager`

### `LayerKey`
- `frame`: 动画帧编号
- `nodeId`: RenderNode ID（层标识）

### `DrawEvent`（私有）
- `fullRedraw`: 是否为完整重绘
- `image`: 缓存的层图像快照
- `debugCanvas`: 用于绘制此事件的 DebugCanvas
- `command`: 当前命令播放头位置
- `layerBounds`: 层尺寸

### `DrawEventSummary`
- `found`, `commandCount`, `layerWidth`, `layerHeight`

### `LayerSummary`
- `nodeId`, `frameOfLastUpdate`, `fullRedraw`, `layerWidth`, `layerHeight`

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `storeSkPicture(nodeId, frame, picture, dirty)` | 存储层的 SkPicture 绘制事件 |
| `setCommand(nodeId, frame, command)` | 设置特定事件的命令播放头 |
| `getLayerAsImage(nodeId, frame)` | 获取指定层在指定帧的渲染结果 |
| `drawLayerEventTo(surface, nodeId, frame)` | 将层事件绘制到指定表面 |
| `event(nodeId, frame)` | 获取单个事件摘要 |
| `summarizeLayers(frame)` | 获取所有层在指定帧的摘要 |
| `listNodesForFrame(frame)` | 获取指定帧上有更新的所有节点 |
| `listFramesForNode(nodeId)` | 获取指定节点有更新的所有帧 |
| `toJSON(writer, urlDataManager, canvas, nodeId, frame)` | 将事件命令序列化为 JSON |
| `getEventDebugCanvas(nodeId, frame)` | 获取事件的 DebugCanvas |
| `setOverdrawViz/setClipVizColor/setDrawGpuOpBounds` | 全局可视化设置 |

## 内部实现细节

### 层图像重建算法（getLayerAsImage）
这是该类最关键的算法，用于重建某层在某帧的外观：

1. 找到目标帧或之前最近的更新帧 N
2. 检查缓存（如有则直接返回）
3. 从帧 N 向前回溯到最近的完整重绘帧
4. 创建离屏 CPU Surface（RGBA8888, Unpremul）
5. 从完整重绘帧开始，依次叠加部分重绘事件直到帧 N
6. 快照并缓存结果

### 缓存失效（setCommand）
当用户调整某事件的命令播放头时，该节点所有帧的缓存图像都被置空，因为之前帧的结果可能影响后续帧。

### 层存储与嵌套支持
`storeSkPicture` 在存储时为每个事件创建 DebugCanvas，并设置 `setLayerManagerAndFrame`，使层可以包含对其他层的引用（嵌套层）。

### 数据结构
使用 `THashMap<LayerKey, DrawEvent>` 存储所有事件，另维护一个 `keys` 向量提供遍历能力（THashMap 无 keys() 方法）。

## 依赖关系

- **Skia 核心**: `SkImage`, `SkSurface`, `SkPicture`
- **调试器**: `DebugCanvas`
- **数据结构**: `THashMap`

## 设计模式与设计决策

1. **按需渲染与缓存**: 层图像仅在请求时渲染，结果被缓存直到失效
2. **增量重绘模型**: 忠实重现 Android HWUI 的增量重绘语义（部分区域脏矩形更新）
3. **CPU 渲染**: 层图像使用 CPU Surface 渲染（注释提到未来应允许用户选择后端）
4. **kUnpremul Alpha**: 匹配 HTML Canvas 的能力限制（wasm debugger 需要渲染到 HTML canvas）
5. **全局可视化设置转发**: 将 overdraw/clip/GPU op bounds 设置转发给所有 DebugCanvas 实例

## 性能考量

- 缓存机制避免重复渲染同一层状态
- setCommand 的缓存失效策略较保守（失效同一节点所有帧），确保正确性但可能导致不必要的重新渲染
- 线性遍历 keys 向量查找相关帧，在大量事件时可能成为瓶颈

## 相关文件

- `tools/debugger/DebugCanvas.h/.cpp` - 主调试 Canvas
- `tools/debugger/DrawCommand.h` - DrawImageRectLayerCommand 使用此管理器
