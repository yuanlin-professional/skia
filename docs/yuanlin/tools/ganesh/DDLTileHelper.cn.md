# DDLTileHelper

> 源文件: `tools/ganesh/DDLTileHelper.h`, `tools/ganesh/DDLTileHelper.cpp`

## 概述

DDLTileHelper 是 Skia 的延迟显示列表（Deferred Display List, DDL）分块渲染辅助工具。它将一个大的渲染目标分割为多个小块（tile），每个 tile 可以在独立线程上录制 DDL，然后在 GPU 线程上回放。这种机制是 Chromium 合成器中分块渲染架构的测试工具，用于验证 DDL API 的正确性和性能。

DDL 是 Ganesh 的一个特性（通过 Chromium 私有 API 暴露），允许在没有 GPU 上下文的线程上录制绘制命令，然后在 GPU 线程上回放。

## 架构位置

```
DDL 分块渲染系统
  +-- DDLTileHelper       (分块管理器) <-- 本文件
       +-- TileData       (单个 tile 数据)
  +-- DDLPromiseImageHelper (Promise Image 辅助)
  +-- GrDeferredDisplayList (DDL 核心)
  +-- GrDeferredDisplayListRecorder (DDL 录制器)
```

## 主要类与结构体

### `DDLTileHelper`
- **成员**:
  - `fNumXDivisions`, `fNumYDivisions`: 水平/垂直分块数
  - `fTiles`: TileData 数组
  - `fComposeDDL`: 合成 DDL
  - `fDstCharacterization`: 目标 Surface 特征

### `DDLTileHelper::TileData`
- **成员**: ID、裁剪矩形、填充偏移、回放特征、回调上下文、Tile Surface、DDL
- **生命周期**: init -> createDDL -> draw -> reset

## 公共 API 函数

### DDLTileHelper

| 函数 | 说明 |
|------|------|
| `DDLTileHelper(ctx, dstChar, viewport, xDiv, yDiv, addPadding)` | 构造函数，初始化所有 tile |
| `kickOffThreadedWork(recordGroup, gpuGroup, ctx, picture)` | 启动多线程 DDL 录制和 GPU 回放 |
| `createDDLsInParallel(picture)` | 并行创建所有 tile 的 DDL |
| `createComposeDDL()` | 创建合成 DDL，将 tile 图像组合到最终输出 |
| `interleaveDDLCreationAndDraw(ctx, picture)` | 单线程交错创建和绘制（基准测试） |
| `drawAllTilesDirectly(ctx, picture)` | 直接绘制不用 DDL（基准测试） |
| `createBackendTextures(taskGroup, ctx)` | 创建所有 tile 的后端纹理 |
| `deleteBackendTextures(taskGroup, ctx)` | 删除所有后端纹理 |

### TileData

| 函数 | 说明 |
|------|------|
| `init(id, ctx, dstChar, clip, padding)` | 初始化 tile |
| `createDDL(picture)` | 从 SkPicture 录制 DDL |
| `precompile(ctx)` | 预编译 DDL 中的着色器程序 |
| `draw(ctx)` | 将 DDL 回放到 tile surface |
| `drawSKPDirectly(ctx, picture)` | 直接绘制 SKP（无 DDL，基准对比） |
| `makePromiseImageForDst(proxy)` | 创建 Promise Image 用于合成 |

## 内部实现细节

### Tile 初始化
将视口按 X/Y 方向均匀分割，可选择添加随机填充（0-64 像素）以测试非对齐情况。每个 tile 创建一个 `GrSurfaceCharacterization` 和 `PromiseImageCallbackContext`。

### DDL 录制
1. 创建比实际 tile 小的录制特征（无填充）
2. 使用 `GrDeferredDisplayListRecorder` 获取录制 Canvas
3. 裁剪到 tile 区域并偏移坐标
4. 绘制 SkPicture 到录制 Canvas
5. 分离 DDL

### 合成 DDL
为每个 tile 创建 Promise Image（由后端纹理支撑），将所有 Promise Image 绘制到最终目标的正确位置。

### 多线程流水线（kickOffThreadedWork）
- 录制线程组：为每个 tile 创建 DDL，完成后调度到 GPU 线程组
- GPU 线程组：预编译着色器、回放 DDL、释放 DDL
- 合成 DDL 也在录制线程组中创建

### 后端纹理生命周期
- `CreateBackendTexture`: 创建后端纹理并设置到回调上下文
- `DeleteBackendTexture`: 释放 tile surface 和回调上下文
- 纹理在 tile surface 和 promise image 之间共享（别名）

## 依赖关系

- **Chromium 私有 API**: `GrDeferredDisplayList`, `GrDeferredDisplayListRecorder`, `GrSurfaceCharacterization`
- **Ganesh**: `GrDirectContext`, `GrCaps`
- **Promise Image**: `SkImages::PromiseTextureFrom`, `PromiseImageCallbackContext`
- **Skia 核心**: `SkCanvas`, `SkPicture`, `SkSurface`, `SkImage`
- **并发**: `SkTaskGroup`

## 设计模式与设计决策

1. **生产者-消费者流水线**: 录制线程生产 DDL，GPU 线程消费并回放
2. **Promise Image 机制**: 合成 DDL 通过 Promise Image 引用 tile 纹理，实现了延迟纹理绑定
3. **后端纹理别名**: Tile surface 和 Promise Image 共享同一后端纹理，避免额外拷贝
4. **随机填充测试**: 可选的随机填充验证非对齐场景的正确性
5. **基准对比支持**: `interleaveDDLCreationAndDraw` 和 `drawAllTilesDirectly` 用于测量 DDL 开销

## 性能考量

- DDL 并行录制利用多核 CPU
- 预编译着色器减少首次绘制延迟
- 交错创建和绘制防止 GPU 饥饿
- 后端纹理创建可通过 SkTaskGroup 并行化
- Promise Image 避免了 tile 间的数据拷贝

## 相关文件

- `tools/ganesh/DDLPromiseImageHelper.h` - Promise Image 回调上下文
- `include/private/chromium/GrDeferredDisplayList.h` - DDL 定义
- `include/private/chromium/GrSurfaceCharacterization.h` - Surface 特征描述
- `include/private/chromium/SkImageChromium.h` - Chromium Promise Image API
