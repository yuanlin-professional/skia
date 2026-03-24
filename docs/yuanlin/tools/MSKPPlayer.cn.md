# MSKPPlayer - MSKP 多帧文档播放器

> 源文件:
> - [tools/MSKPPlayer.h](../../tools/MSKPPlayer.h)
> - [tools/MSKPPlayer.cpp](../../tools/MSKPPlayer.cpp)

## 概述

MSKPPlayer 是一个用于播放 MSKP（Multi-SKP，多页 SkPicture 文档）文件的工具类。它能够将 MSKP 文件中的帧/页面渲染到 SkCanvas 上，支持随机访问帧、管理离屏图层（offscreen layers）缓存，以及增量更新图层状态。该类将 MSKP 视为动画帧序列，但也支持静态文档的多页面结构。

## 架构位置

MSKPPlayer 位于 Skia 的 `tools/` 目录下，属于工具层组件。它依赖 Skia 核心渲染 API（SkCanvas、SkPicture、SkSurface）和多页文档格式（SkMultiPictureDocument），主要用于调试工具、查看器（Viewer）和测试场景中对 MSKP 文件的回放。

## 主要类与结构体

### `MSKPPlayer`
主播放器类，管理 MSKP 文件的解析和帧回放。

- **`Cmd`** - 命令基类，定义绘制操作接口（`isFullRedraw`、`draw`、`layerID`）。
- **`PicCmd`** - 绘制 SkPicture 命令，支持可选的裁剪矩形。
- **`DrawLayerCmd`** - 绘制离屏图层命令，存储目标图层 ID、命令索引、源/目标矩形、采样选项和约束条件。
- **`LayerCmds`** - 包含图层的命令序列和尺寸信息。
- **`LayerState`** - 图层播放状态，记录当前命令索引和 SkSurface。
- **`CmdRecordCanvas`** - 继承自 `SkNWayCanvas`，在解析 SkPicture 时录制命令到 LayerCmds 中，处理离屏图层的注解（annotation）驱动的分层逻辑。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `Make(SkStreamSeekable*)` | 静态工厂方法，从 MSKP 流创建播放器实例 |
| `maxDimensions()` | 返回所有帧的最大宽高 |
| `numFrames()` | 返回总帧数 |
| `frameDimensions(int)` | 返回指定帧的尺寸 |
| `playFrame(SkCanvas*, int)` | 将指定帧渲染到画布，支持随机访问 |
| `resetLayers()` | 销毁所有缓存的离屏图层 |
| `rewindLayers()` | 强制所有图层在下次使用时重绘，但保留已分配的 Surface |
| `allocateLayers(SkCanvas*)` | 使用传入画布的 makeSurface 预分配离屏图层 |
| `layerIDs(int frame)` | 获取离屏图层 ID 集合，可按帧过滤 |
| `layerSnapshot(int layerID)` | 获取指定图层的当前内容快照 |

## 内部实现细节

- **解析流程**：`Make()` 使用 `SkMultiPictureDocument::Read` 读取所有页面，并通过 `SkSharingDeserialContext` 进行图像反序列化去重。每个页面通过 `CmdRecordCanvas` 回放，将绘制操作分解为 `PicCmd` 和 `DrawLayerCmd`。
- **注解驱动的图层分离**：`CmdRecordCanvas` 拦截 `onDrawAnnotation`，识别 `OffscreenLayerDraw|<id>` 和 `SurfaceID|<id>` 标记，将后续的 `drawPicture` 或 `drawImageRect` 操作路由到对应的离屏图层。
- **增量更新**：`DrawLayerCmd::draw()` 在绘制图层时检查当前状态是否需要回退重绘。如果当前命令索引超前，则从头重绘；否则查找最近的全屏重绘点以优化。
- **录制上下文切换**：检测画布的 `recordingContext` 变化，自动重置不匹配的图层 Surface。

## 依赖关系

- **Skia 核心**：SkCanvas、SkPicture、SkSurface、SkImage、SkPictureRecorder
- **文档格式**：SkMultiPictureDocument（MSKP 读写）
- **工具辅助**：SkSharingProc（图像序列化共享）、SkNWayCanvas（多路画布代理）
- **GPU 后端**（可选）：GrDirectContext（Ganesh GPU 上下文检测）

## 设计模式与设计决策

- **命令模式**：将绘制操作抽象为 `Cmd` 命令对象，支持延迟执行和状态管理。
- **工厂模式**：通过静态 `Make()` 方法创建实例，隐藏构造细节。
- **不可复制/移动**：明确禁止拷贝和移动，确保图层状态的一致性。
- **注解协议**：依赖 SkPicture 中嵌入的注解字符串来标识离屏图层关系，这是 Android 端 MSKP 捕获格式的约定。

## 性能考量

- **增量图层更新**：避免每帧重绘所有离屏图层，仅在状态落后时增量更新。
- **全屏重绘检测**：通过 `isFullRedraw` 判断跳过不必要的历史命令重放。
- **Surface 复用**：`rewindLayers()` 保留 Surface 分配避免重复创建，`allocateLayers()` 支持预分配。
- **线性搜索图层引用**：`collectReferencedLayers` 中的 `std::find` 是线性复杂度，但注释表明图层数通常较少。

## 相关文件

- `tools/SkSharingProc.h` / `.cpp` - 图像序列化/反序列化共享机制
- `include/docs/SkMultiPictureDocument.h` - MSKP 文档格式定义
- `include/utils/SkNWayCanvas.h` - 多路画布基类
- `tools/viewer/Viewer.cpp` - 使用 MSKPPlayer 的查看器应用
