# SkSurface_Ganesh - Ganesh GPU 表面实现

> 源文件: `src/gpu/ganesh/surface/SkSurface_Ganesh.h`, `src/gpu/ganesh/surface/SkSurface_Ganesh.cpp`

## 概述

`SkSurface_Ganesh` 是 `SkSurface` 在 Ganesh GPU 后端的具体实现。它将公共表面 API（如像素写入、图像快照、异步读取、延迟显示列表绘制等）桥接到底层的 `skgpu::ganesh::Device` 设备。每个 `SkSurface_Ganesh` 拥有一个 Ganesh Device，通过它完成所有 GPU 渲染操作。

## 架构位置

```
SkSurface (公共 API)
    |
SkSurface_Base (内部基类)
    |
SkSurface_Ganesh (本文件)
    |
skgpu::ganesh::Device -> SurfaceDrawContext -> GrOps -> GrGpu
```

## 主要类与结构体

### `SkSurface_Ganesh`

继承自 `SkSurface_Base`。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fDevice` | `sk_sp<skgpu::ganesh::Device>` | Ganesh 绘图设备 |

## 公共 API 函数

| 方法 | 说明 |
|------|------|
| `imageInfo()` | 返回表面的图像信息 |
| `replaceBackendTexture()` | 替换后端纹理 |
| `onNewCanvas()` | 创建绑定到此表面的新画布 |
| `onNewSurface()` | 创建兼容的新表面 |
| `onNewImageSnapshot()` | 创建表面内容的图像快照 |
| `onWritePixels()` | 写入像素数据 |
| `onCopyOnWrite()` | 写时复制（支持内容保留/丢弃模式） |
| `onDiscard()` | 丢弃表面内容 |
| `onWait()` | 等待 GPU 信号量 |
| `onCharacterize()` / `onIsCompatible()` | DDL 表面特征化和兼容性检查 |
| `onDraw()` | 将此表面绘制到另一画布 |
| `asyncRescaleAndReadPixels*()` | 异步像素读取 |
| `getBackendTexture()` / `getBackendRenderTarget()` | 获取后端句柄 |
| `resolveMSAA()` | 解析 MSAA |
| `draw(GrDeferredDisplayList)` | 执行延迟显示列表 |

## 内部实现细节

所有操作直接委托给 `fDevice`。`onCopyOnWrite` 实现写时复制语义，在需要时替换 Device 的后备代理以保护已创建的图像快照不被修改。

## 依赖关系

- **上游依赖**: `SkSurface_Base`、`SkCanvas`。
- **核心依赖**: `skgpu::ganesh::Device`。
- **被依赖**: `SkSurfaces::RenderTarget()`、`SkSurfaces::WrapBackendTexture()` 等工厂函数。

## 设计模式与设计决策

1. **委托模式**: 几乎所有方法直接委托给 Device，保持表面层的简洁。
2. **写时复制**: 通过 `replaceBackingProxy` 实现，确保已快照的图像数据不被后续绘制修改。

## 性能考量

- 图像快照在无修改时零拷贝（共享代理）。
- 仅在实际发生写操作后才触发 Copy-on-Write。

## 相关文件

- `src/gpu/ganesh/Device.h` - Ganesh 设备
- `src/image/SkSurface_Base.h` - 表面基类
- `include/gpu/ganesh/SkSurfaceGanesh.h` - 公共 Ganesh 表面 API
