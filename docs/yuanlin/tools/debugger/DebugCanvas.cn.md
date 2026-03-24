# DebugCanvas

> 源文件: `tools/debugger/DebugCanvas.h`, `tools/debugger/DebugCanvas.cpp`

## 概述

DebugCanvas 是 Skia 调试器的核心 Canvas 实现，它拦截所有 SkCanvas 绘制调用并将其记录为 DrawCommand 对象序列。记录完成后，可以逐命令回放到任意目标 Canvas，支持命令级别的可见性切换、过度绘制可视化、裁剪区域可视化以及 GPU 操作边界可视化等调试功能。

该类是 SkPicture 调试工作流的核心：SkPicture 被回放到 DebugCanvas 以收集命令列表，然后用户可以在调试器 UI 中逐步执行这些命令。

## 架构位置

```
SkCanvasVirtualEnforcer<SkCanvas>
  +-- DebugCanvas <-- 本文件
       使用: DrawCommand 层次结构
       使用: DebugLayerManager (mskp 层管理)
       使用: GrAuditTrail (GPU 操作追踪, Ganesh)
```

## 主要类与结构体

### `DebugCanvas`
- **继承**: `SkCanvasVirtualEnforcer<SkCanvas>`
- **核心状态**: `fCommandVector` (命令列表), `fMatrix`, `fClip`
- **调试选项**: 过度绘制可视化、裁剪颜色可视化、Android clip 显示、原点显示、GPU op bounds 显示

### `DebugPaintFilterCanvas`（匿名命名空间内）
- 过度绘制可视化使用的 Paint 过滤 Canvas，将所有绘制设为半透明红色

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `DebugCanvas(width, height)` / `DebugCanvas(bounds)` | 构造函数 |
| `draw(canvas)` | 执行所有命令 |
| `drawTo(canvas, index, m)` | 执行到指定索引，可选高亮第 m 个 GPU op |
| `getCurrentMatrix()` / `getCurrentClip()` | 获取当前变换/裁剪状态 |
| `deleteDrawCommandAt(index)` | 删除指定索引的命令 |
| `getDrawCommandAt(index)` | 获取指定索引的命令 |
| `getSize()` | 获取命令总数 |
| `toggleCommand(index, toggle)` | 切换命令可见性 |
| `toJSON(writer, urlDataManager, canvas)` | 序列化所有命令为 JSON |
| `toJSONOpsTask(writer, canvas)` | 序列化 GPU 操作任务为 JSON |
| `getImageIdToCommandMap(udm)` | 获取图像 ID 到使用它的命令索引的映射 |
| `setOverdrawViz(bool)` | 启用过度绘制可视化 |
| `setClipVizColor(color)` | 设置裁剪可视化颜色 |
| `setAndroidClipViz(enable)` | 显示 Android 设备裁剪限制 |
| `setOriginVisible(enable)` | 显示坐标原点 |
| `setDrawGpuOpBounds(bool)` | 显示 GPU 操作边界 |
| `setLayerManagerAndFrame(lm, frame)` | 设置层管理器（mskp 动画） |
| `detachCommands(dst)` | 转移命令所有权 |

## 内部实现细节

### 广域裁剪
构造函数设置一个近乎最大的裁剪矩形，防止 SkPicturePlayback 的 quickReject 跳过命令录制。这确保所有操作都被记录到调试 Canvas 中。

### 命令录制
所有 `on*` 和 `will*` 方法被重写，将参数封装为对应的 DrawCommand 子类并存入 `fCommandVector`。

### drawTo 执行流程
1. 保存 Canvas 状态
2. 根据 `fOverdrawViz` 选择原始 Canvas 或 DebugPaintFilterCanvas
3. 遍历命令到指定索引，仅执行可见命令
4. 在 Ganesh 模式下，每个命令执行前创建 `GrAuditTrail::AutoCollectOps` 以收集 GPU 操作信息
5. 可选绘制裁剪可视化、原点箭头和 Android clip
6. 绘制 GPU 操作边界框（使用色盲友好色方案）

### Android 层注解处理
`onDrawAnnotation` 解析特殊注解：
- `OffscreenLayerDraw|<nodeId>`: 下一个 `drawPicture` 是离屏层绘制
- `SurfaceID|<nodeId>`: 下一个 `drawImageRect` 是层图像绘制
- `AndroidDeviceClipRestriction`: 记录 Android 设备裁剪限制

### GPU 操作可视化
通过 `GrAuditTrail` 收集 GPU 操作的边界框，使用三种颜色区分：
- 紫色 (`kTotalBounds`): 操作总边界
- 红色 (`kCommandOpBounds`): 当前命令的操作
- 橙色 (`kOtherOpBounds`): 其他操作

### JSON 导出
`toJSON` 在 Ganesh 模式下先执行所有命令收集 audit trail，然后遍历命令调用 `toJSON`，并附加 GPU audit trail 信息。

## 依赖关系

- **Skia 核心**: `SkCanvas`, `SkCanvasVirtualEnforcer`, `SkPaintFilterCanvas`
- **调试器**: `DrawCommand`, `DebugLayerManager`
- **Ganesh（条件编译）**: `GrAuditTrail`, `GrDirectContext`, `GrRenderTargetProxy`
- **序列化**: `SkJSONWriter`

## 设计模式与设计决策

1. **拦截器模式**: 通过重写所有 Canvas 虚方法拦截绘制调用并记录
2. **命令列表管理**: 使用 `SkTDArray<DrawCommand*>` 管理命令，支持增删改查
3. **条件可视化**: 多种可视化模式可独立启用/禁用
4. **SkPicture 透明递归**: `onDrawPicture` 递归播放 Picture 到 DebugCanvas，使子 Picture 的命令被展开记录
5. **层命令替换**: 当检测到层注解时，将 `drawImageRect` 替换为 `DrawImageRectLayerCommand`

## 性能考量

- 广域裁剪确保不遗漏命令，但取消了 quickReject 优化
- Ganesh 模式下每个命令执行前需要 flush 上下文以防操作合并影响 audit trail 准确性
- 命令析构时逐个 delete，可考虑使用 arena 分配器

## 相关文件

- `tools/debugger/DrawCommand.h/.cpp` - 命令层次结构
- `tools/debugger/DebugLayerManager.h/.cpp` - 层管理
- `include/utils/SkPaintFilterCanvas.h` - 过度绘制可视化基类
- `src/gpu/ganesh/GrAuditTrail.h` - GPU 操作审计追踪
