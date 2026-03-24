# GrTextureResolveRenderTask

> 源文件: src/gpu/ganesh/GrTextureResolveRenderTask.h, src/gpu/ganesh/GrTextureResolveRenderTask.cpp

## 概述

`GrTextureResolveRenderTask` 是 Ganesh GPU 后端中专门负责纹理解析（resolve）操作的渲染任务类。它继承自 `GrRenderTask`，主要处理两种解析操作：

1. **MSAA 解析**：将多重采样的渲染目标解析为单采样纹理
2. **Mipmap 生成**：为纹理重新生成 mipmap 级别

该任务在渲染任务图（Render Task DAG）中作为独立节点，确保在需要使用纹理内容之前完成解析操作。它支持批量处理多个解析操作，提高渲染效率。

## 架构位置

`GrTextureResolveRenderTask` 位于 Skia GPU 渲染任务系统中：

```
Skia GPU 渲染任务系统
└── GrRenderTask                    # 渲染任务基类
    ├── GrOpsTask                   # 操作任务（绘制命令）
    ├── GrCopyRenderTask            # 复制任务
    ├── GrTextureResolveRenderTask  # 纹理解析任务（本类）
    └── GrTransferFromRenderTask    # 传输任务
```

在渲染管线中的位置：
```
绘制操作 → GrOpsTask → GrTextureResolveRenderTask → 后续使用纹理
                       (标记 MSAA 脏/Mipmap 脏)  (解析操作)
```

## 主要类与结构体

### 继承关系

```
GrRenderTask
    ↑
    │
GrTextureResolveRenderTask
```

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fResolves | skia_private::STArray&lt;4, Resolve&gt; | 待执行的解析操作列表 |
| fTargets | 继承自基类 | 目标代理列表（在基类中） |

### 内部结构体

**Resolve 结构体**：

| 成员 | 类型 | 说明 |
|-----|------|------|
| fFlags | GrSurfaceProxy::ResolveFlags | 解析标志（MSAA、Mipmap 或两者） |
| fMSAAResolveRect | SkIRect | MSAA 解析的矩形区域 |

**GrSurfaceProxy::ResolveFlags 枚举**：
- `kNone`: 无解析操作
- `kMSAA`: 解析 MSAA
- `kMipMaps`: 重新生成 mipmap
- 可通过位运算组合

## 公共 API 函数

### 添加解析代理

```cpp
void addProxy(GrDrawingManager* drawingMgr,
             sk_sp<GrSurfaceProxy> proxy,
             GrSurfaceProxy::ResolveFlags flags,
             const GrCaps& caps)
```
添加需要解析的代理对象。如果代理已存在，会更新其解析标志。

### 测试工具函数

```cpp
#if defined(GPU_TEST_UTILS)
GrSurfaceProxy::ResolveFlags flagsForProxy(sk_sp<GrSurfaceProxy>) const
#endif
```
获取特定代理的解析标志（仅用于测试）。

## 内部实现细节

### addProxy 实现逻辑

```cpp
void addProxy(GrDrawingManager*, sk_sp<GrSurfaceProxy> proxyRef,
             ResolveFlags flags, const GrCaps&)
```

**执行流程**：

1. **检查现有代理**：使用 `std::find` 在 `fTargets` 中查找代理
   - 如果找到：更新现有条目的标志（按位或运算）
   - 如果未找到：创建新的 `Resolve` 条目

2. **处理 MSAA 解析**（`ResolveFlags::kMSAA`）：
   - 获取 `GrRenderTargetProxy` 指针
   - 断言渲染目标已标记为 MSAA 脏
   - 记录脏区域矩形（`msaaDirtyRect()`）
   - 调用 `markMSAAResolved()` 清除脏标志

3. **处理 Mipmap 生成**（`ResolveFlags::kMipMaps`）：
   - 获取 `GrTextureProxy` 指针
   - 断言纹理包含 mipmap 且已标记为脏
   - 调用 `markMipmapsClean()` 清除脏标志

4. **添加依赖关系**（仅对新代理）：
   - 将代理作为依赖添加到任务图
   - 作为目标添加到 `fTargets`

**关键设计点**：
- 标志更新使用增量方式（`newFlags = ~resolve->fFlags & flags`）
- 确保最后操作代理的渲染任务已关闭
- 在更新代理状态后才添加到任务图（避免断言失败）

### gatherProxyIntervals 实现

```cpp
void gatherProxyIntervals(GrResourceAllocator*) const override
```

该方法为资源分配器提供代理的使用间隔信息：
- 创建假的操作编号（`fakeOp`）
- 为每个目标添加间隔，标记为 `ActualUse::kYes`
- 允许资源回收（`AllowRecycling::kYes`）
- 调用 `incOps()` 保持操作索引同步

这确保 `fEndOfOpsTaskOpIndices` 数组保持正确，即使此任务没有"正常"操作。

### onExecute 实现

```cpp
bool onExecute(GrOpFlushState* flushState) override
```

**执行分为两个阶段**：

**阶段 1：MSAA 解析**
```cpp
for (int i = 0; i < fResolves.size(); ++i) {
    if (resolve.fFlags & ResolveFlags::kMSAA) {
        GrRenderTarget* renderTarget = proxy->peekRenderTarget();
        if (renderTarget) {
            flushState->gpu()->resolveRenderTarget(renderTarget,
                                                   resolve.fMSAAResolveRect);
        }
    }
}
```

**阶段 2：Mipmap 重新生成**
```cpp
for (int i = 0; i < fResolves.size(); ++i) {
    if (resolve.fFlags & ResolveFlags::kMipMaps) {
        GrTexture* texture = this->target(i)->peekTexture();
        if (texture && texture->mipmapsAreDirty()) {
            flushState->gpu()->regenerateMipMapLevels(texture);
        }
    }
}
```

**设计原因**：
- 所有 MSAA 解析在 mipmap 生成之前完成
- 这样 mipmap 生成可以使用已解析的内容
- 处理实例化失败的情况（`peekRenderTarget/peekTexture` 可能返回 nullptr）

### 其他重写方法

**onIsUsed()**：总是返回 `false`
- 该任务不"使用"代理，而是修改它们
- 避免在依赖图中创建循环

**onMakeClosed()**：返回 `ExpectedOutcome::kTargetUnchanged`
- 表示目标的视觉内容不变（虽然内部表示改变）

**visitProxies_debugOnly()**：空实现
- 代理已通过基类的 `fTargets` 访问

## 依赖关系

### 依赖的模块

| 模块 | 依赖关系 | 说明 |
|-----|---------|------|
| GrRenderTask | 继承 | 渲染任务基类 |
| GrSurfaceProxy | 使用 | 表面代理 |
| GrTextureProxy | 使用 | 纹理代理 |
| GrRenderTargetProxy | 使用 | 渲染目标代理 |
| GrGpu | 使用 | GPU 接口（执行解析） |
| GrDrawingManager | 使用 | 管理任务图 |
| GrResourceAllocator | 使用 | 资源分配 |
| GrOpFlushState | 使用 | 刷新状态 |

### 被依赖的模块

| 模块 | 使用方式 | 说明 |
|-----|---------|------|
| GrDrawingManager | 创建和管理 | 创建解析任务并插入任务图 |
| GrTextureResolveManager | 使用 | 通过管理器创建任务 |
| GrRenderTaskDAG | 调度 | 在渲染任务图中调度执行 |

## 设计模式与设计决策

### 批处理模式

该类支持批量处理多个解析操作：
- 使用 `STArray<4, Resolve>` 存储，小数组（≤4）无堆分配
- 减少任务对象数量
- 提高 GPU 命令批处理效率

### 状态清理策略

在 `addProxy()` 中清除脏标志，而不是在 `onExecute()` 中：
- 避免重复解析
- 允许任务图优化（合并任务）
- 确保标志状态与任务创建一致

### 两阶段执行

MSAA 解析和 mipmap 生成分开执行：
```
所有 MSAA 解析 → 所有 Mipmap 生成
```

**优势**：
- GPU 可以批量处理相同类型的操作
- Mipmap 生成使用已解析的 MSAA 结果
- 更好的缓存局部性

### 增量标志更新

```cpp
newFlags = ~resolve->fFlags & flags;
resolve->fFlags |= flags;
```
只处理新增的标志，避免重复处理已有的解析请求。

## 性能考量

### 小数组优化

使用 `STArray<4, Resolve>` 而不是 `std::vector`：
- 前 4 个元素栈分配，避免堆分配
- 大多数情况下只有少量解析操作
- 减少内存分配开销

### 批量操作

- 将多个解析操作合并到一个任务
- 减少任务切换和同步开销
- 提高 GPU 利用率

### 矩形区域解析

MSAA 解析支持部分区域（`fMSAAResolveRect`）：
- 只解析脏区域，减少像素处理量
- 渲染目标追踪脏区域（`msaaDirtyRect()`）
- 对于小更新区域显著提升性能

### 资源分配优化

通过 `gatherProxyIntervals()` 提供使用信息：
- 允许资源分配器优化内存使用
- 支持资源回收和复用
- 减少峰值内存占用

### 懒执行

解析操作延迟到实际需要时：
- 避免不必要的解析
- 允许任务图优化和合并
- 支持 DDL 录制和延迟执行

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/gpu/ganesh/GrRenderTask.h | 基类 | 渲染任务基类 |
| src/gpu/ganesh/GrSurfaceProxy.h | 使用 | 表面代理及解析标志 |
| src/gpu/ganesh/GrTextureProxy.h | 使用 | 纹理代理 |
| src/gpu/ganesh/GrRenderTargetProxy.h | 使用 | 渲染目标代理 |
| src/gpu/ganesh/GrDrawingManager.h | 使用 | 绘制管理器 |
| src/gpu/ganesh/GrGpu.h | 使用 | GPU 接口 |
| src/gpu/ganesh/GrTextureResolveManager.h | 管理 | 解析管理器 |
| src/gpu/ganesh/GrResourceAllocator.h | 使用 | 资源分配器 |
| src/gpu/ganesh/GrOpFlushState.h | 使用 | 刷新状态 |
