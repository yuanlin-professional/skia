# DrawCommand

> 源文件: `tools/debugger/DrawCommand.h`, `tools/debugger/DrawCommand.cpp`

## 概述

DrawCommand 是 Skia 调试器（Debugger）的核心命令系统，定义了一套完整的绘制命令层次结构，用于记录、回放和序列化 SkCanvas 上的所有绘制操作。每个具体命令类封装了一个特定的 Canvas 操作（如 drawRect、clipPath、save 等），支持执行、渲染预览和 JSON 序列化。

该模块是 Skia Debugger 工具（包括 wasm-skp-debugger）的基础设施，使开发者能够逐命令调试 SkPicture 的渲染过程。

## 架构位置

```
Skia Debugger 工具
  +-- DebugCanvas       (录制和回放 Canvas)
  +-- DrawCommand       (命令基类和具体命令) <-- 本文件
  +-- DebugLayerManager (离屏层管理)
  +-- JsonWriteBuffer   (JSON 序列化辅助)
  +-- UrlDataManager    (二进制数据管理)
```

## 主要类与结构体

### `DrawCommand`（基类）
- **OpType 枚举**: 定义 36+ 种操作类型（kClear, kClipPath, kDrawRect, kSave, kSaveLayer 等）
- **核心虚方法**: `execute()`, `render()`, `toJSON()`
- **可见性控制**: `isVisible()` / `setVisible()` 用于调试时切换命令执行

### 具体命令类（部分列表）

| 类名 | 对应 Canvas 操作 |
|------|------------------|
| `ClearCommand` | `canvas->clear()` |
| `ClipPathCommand` | `canvas->clipPath()` |
| `ClipRectCommand` | `canvas->clipRect()` |
| `ClipRRectCommand` | `canvas->clipRRect()` |
| `ClipShaderCommand` | `canvas->clipShader()` |
| `ConcatCommand` / `Concat44Command` | `canvas->concat()` |
| `DrawImageCommand` | `canvas->drawImage()` |
| `DrawImageRectCommand` | `canvas->drawImageRect()` |
| `DrawImageRectLayerCommand` | 延迟层图像渲染（Debugger 特有） |
| `DrawPathCommand` | `canvas->drawPath()` |
| `DrawRectCommand` / `DrawRRectCommand` | 矩形/圆角矩形绘制 |
| `DrawTextBlobCommand` | `canvas->drawTextBlob()` |
| `DrawShadowCommand` | `canvas->drawShadow()` |
| `SaveCommand` / `SaveLayerCommand` | `canvas->save()` / `saveLayer()` |
| `RestoreCommand` | `canvas->restore()` |
| `SetMatrixCommand` / `SetM44Command` | 矩阵设置 |
| `DrawEdgeAAQuadCommand` | Edge AA 四边形 |
| `DrawEdgeAAImageSetCommand` | Edge AA 图像集合 |

### `DrawImageRectLayerCommand`（特殊命令）
Debugger 特有的延迟命令，在执行时通过 `DebugLayerManager` 获取层图像。用于支持 Android mskp 文件中的离屏层渲染。

## 公共 API 函数

### DrawCommand 基类方法

| 函数 | 说明 |
|------|------|
| `execute(canvas)` | 纯虚函数，在 canvas 上执行此命令 |
| `render(canvas)` | 独立渲染此命令的预览（裁剪和路径等） |
| `toJSON(writer, urlDataManager)` | 序列化为 JSON |
| `GetCommandString(type)` | 获取操作类型的字符串名称 |
| `getOpType()` | 获取操作类型 |

### JSON 辅助静态方法

| 函数 | 说明 |
|------|------|
| `MakeJsonColor()` / `MakeJsonColor4f()` | 颜色序列化 |
| `MakeJsonPoint()` / `MakeJsonPoint3()` | 点序列化 |
| `MakeJsonRect()` / `MakeJsonIRect()` | 矩形序列化 |
| `MakeJsonMatrix()` / `MakeJsonMatrix44()` | 矩阵序列化 |
| `MakeJsonPath()` / `MakeJsonRegion()` | 路径/区域序列化 |
| `MakeJsonPaint()` | Paint 完整序列化（含 shader、filter 等） |
| `MakeJsonLattice()` | 九宫格参数序列化 |
| `flatten()` | SkFlattenable/SkImage/SkBitmap 序列化 |
| `WritePNG()` | 位图 PNG 编码 |

## 内部实现细节

### JSON 序列化系统
使用大量 `DEBUGCANVAS_ATTRIBUTE_*` 宏定义 JSON 属性名，确保序列化输出与前端 debugger 一致。JSON 输出包含：
- 命令类型和可见性
- 绘制参数（坐标、颜色、矩阵等）
- Paint 属性（样式、描边、混合模式、shader、filter 等）
- 路径数据（fill type + verb 序列）
- 图像数据（PNG 编码后通过 UrlDataManager 管理）

### 渲染预览（render）
部分命令（ClipPath、DrawPath、DrawRRect 等）提供独立渲染预览。预览会自动缩放和居中到 canvas 范围内（90% 留白），以纯黑描边绘制。

### Paint 序列化
`MakeJsonPaint` 完整序列化 SkPaint 的所有属性，包括：颜色、样式、描边参数、混合模式、MaskFilter（模糊检测）、PathEffect（虚线检测）、Shader、ImageFilter、ColorFilter 等。

### 图像扁平化
支持两种模式：
- **MSKP 模式**（有 imageIndex）：仅记录图像 ID
- **普通模式**: 读取像素并编码为 PNG，通过 UrlDataManager 存储

## 依赖关系

- **Skia 核心**: SkCanvas 全套绘制类型（SkPaint, SkPath, SkImage, SkTextBlob, SkVertices 等）
- **编码**: SkPngEncoder
- **序列化**: SkJSONWriter, SkWriteBuffer
- **调试器**: DebugLayerManager, JsonWriteBuffer, UrlDataManager
- **Ganesh（条件编译）**: GrRecordingContext, GrImageContext

## 设计模式与设计决策

1. **命令模式**: 经典的命令模式实现，每个绘制操作封装为独立的命令对象
2. **访问者模式变体**: `toJSON` 和 `render` 作为命令对象上的替代执行方式
3. **可见性切换**: 允许调试时禁用特定命令而不删除它们，便于定位渲染问题
4. **延迟层命令**: `DrawImageRectLayerCommand` 在执行时才解析图像引用，支持 Android 离屏层的延迟渲染

## 性能考量

- PNG 编码使用最低压缩级别（`fZLibLevel = 1`）和无过滤（`kNone`），优先编码速度
- 路径序列化将 dump 数据和 verb 数组都包含在 JSON 中，可能产生较大输出
- 图像数据通过 UrlDataManager 的 URL 引用方式避免 JSON 中嵌入大量 base64 数据

## 相关文件

- `tools/debugger/DebugCanvas.h/.cpp` - 使用 DrawCommand 的调试 Canvas
- `tools/debugger/JsonWriteBuffer.h/.cpp` - JSON 序列化缓冲
- `tools/debugger/DebugLayerManager.h/.cpp` - 离屏层管理
- `tools/UrlDataManager.h` - URL 数据管理
- `src/utils/SkJSONWriter.h` - JSON 写入器
