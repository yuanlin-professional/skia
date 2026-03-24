# GrRecordingContext

> 源文件
> - include/gpu/ganesh/GrRecordingContext.h
> - src/gpu/ganesh/GrRecordingContext.cpp

## 概述

`GrRecordingContext` 是 Skia Ganesh GPU 后端的核心上下文类,负责记录绘制命令而无需立即执行。它继承自 `GrImageContext`,是 `GrDirectContext` 的基类。该类的主要职责是管理绘制命令的记录、资源代理的创建、以及绘制操作的组织和优化。

该上下文支持两种模式:
1. **常规录制模式**: 绘制命令最终会在同一上下文中执行
2. **DDL(Deferred Display List)模式**: 绘制命令被记录到可序列化的列表中,稍后在其他上下文中回放

`GrRecordingContext` 管理多个关键组件,包括绘制管理器(`GrDrawingManager`)、代理提供器(`GrProxyProvider`)、内存分配器等,为上层 SkCanvas 和 SkSurface API 提供 GPU 绘制基础设施。

## 架构位置

在 Skia GPU 架构中的位置:

```
应用层 (SkCanvas, SkSurface, SkImage)
    ↓
上下文管理层
    ├─ GrDirectContext (执行上下文)
    ├─ GrRecordingContext (录制上下文) ← 当前模块
    └─ GrImageContext (基础上下文)
    ↓
绘制管理层 (GrDrawingManager, GrProxyProvider)
    ↓
GPU 后端实现层 (GrGpu, GrOpsTask)
```

## 主要类与结构体

### GrRecordingContext

GPU 绘制命令录制的核心上下文类。

**继承关系:**
```
GrContext_Base
    ↓
GrImageContext
    ↓
GrRecordingContext ← 当前类
    ↓
GrDirectContext
```

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fAuditTrail` | `std::unique_ptr<GrAuditTrail>` | 绘制操作审计跟踪(调试用) |
| `fArenas` | `OwnedArenas` | 内存分配器集合,管理录制期间的临时数据 |
| `fDrawingManager` | `std::unique_ptr<GrDrawingManager>` | 绘制管理器,组织和优化绘制任务 |
| `fProxyProvider` | `std::unique_ptr<GrProxyProvider>` | 纹理和渲染目标代理创建器 |
| `fCPUContext` | `std::unique_ptr<skcpu::ContextImpl>` | CPU 渲染上下文(备用) |
| `fRecorder` | `std::unique_ptr<SkGaneshRecorder>` | Ganesh 录制器接口 |
| `fStats` | `Stats` | 性能统计信息 |

### Arenas

管理不同类型内存分配器的轻量级聚合器。

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fRecordTimeAllocator` | `SkArenaAlloc*` | 用于管线和复杂数据的分配器 |
| `fRecordTimeSubRunAllocator` | `sktext::gpu::SubRunAllocator*` | 文本子运行专用分配器 |

### OwnedArenas

持有内存分配器所有权的容器类。

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fDDLRecording` | `bool` | 是否为 DDL 录制模式 |
| `fRecordTimeAllocator` | `std::unique_ptr<SkArenaAlloc>` | 拥有所有权的主分配器 |
| `fRecordTimeSubRunAllocator` | `std::unique_ptr<sktext::gpu::SubRunAllocator>` | 拥有所有权的文本分配器 |

### ProgramData

封装着色器程序描述和信息。

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fDesc` | `std::unique_ptr<const GrProgramDesc>` | 程序描述符 |
| `fInfo` | `const GrProgramInfo*` | 程序信息(不拥有所有权) |

### Stats

性能统计收集器。

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fNumPathMasksGenerated` | `int` | 生成的路径遮罩数量 |
| `fNumPathMaskCacheHits` | `int` | 路径遮罩缓存命中次数 |

## 公共 API 函数

| 函数签名 | 功能说明 |
|---------|---------|
| `bool abandoned() override` | 检查上下文是否已被放弃 |
| `bool colorTypeSupportedAsSurface(SkColorType) const` | 检查颜色类型是否可作为表面 |
| `int maxTextureSize() const` | 获取最大纹理尺寸 |
| `int maxRenderTargetSize() const` | 获取最大渲染目标尺寸 |
| `bool colorTypeSupportedAsImage(SkColorType) const` | 检查颜色类型是否可作为图像 |
| `bool supportsProtectedContent() const` | 检查是否支持受保护内容 |
| `int maxSurfaceSampleCountForColorType(SkColorType) const` | 获取颜色类型的最大采样数 |
| `sk_sp<const SkCapabilities> skCapabilities() const` | 获取能力描述 |
| `SkRecorder* asRecorder()` | 转换为录制器接口 |
| `std::unique_ptr<skcpu::Recorder> makeCPURecorder()` | 创建 CPU 录制器 |

### 内部/受保护 API

| 函数签名 | 功能说明 |
|---------|---------|
| `GrDrawingManager* drawingManager()` | 获取绘制管理器 |
| `void destroyDrawingManager()` | 销毁绘制管理器 |
| `Arenas arenas()` | 获取内存分配器集合 |
| `OwnedArenas&& detachArenas()` | 分离并转移分配器所有权 |
| `GrProxyProvider* proxyProvider()` | 获取代理提供器 |
| `void addOnFlushCallbackObject(GrOnFlushCallbackObject*)` | 注册刷新回调 |

## 内部实现细节

### 初始化流程

构造函数创建核心组件:

```cpp
GrRecordingContext::GrRecordingContext(sk_sp<GrContextThreadSafeProxy> proxy,
                                       bool ddlRecording)
        : GrImageContext(std::move(proxy))
        , fAuditTrail(new GrAuditTrail())
        , fArenas(ddlRecording) {
    fProxyProvider = std::make_unique<GrProxyProvider>(this);
    fCPUContext = std::make_unique<skcpu::ContextImpl>();
    fRecorder = std::make_unique<SkGaneshRecorder>(this);
}
```

`init()` 方法完成剩余初始化:
1. 调用父类 `GrImageContext::init()`
2. 配置路径渲染器链选项
3. 确定任务拆分策略
4. 创建 `GrDrawingManager`

### 内存分配器按需创建

`OwnedArenas::get()` 采用延迟初始化:

```cpp
GrRecordingContext::Arenas GrRecordingContext::OwnedArenas::get() {
    if (!fRecordTimeAllocator && fDDLRecording) {
        fRecordTimeAllocator = std::make_unique<SkArenaAlloc>(1024);
    }
    if (!fRecordTimeSubRunAllocator) {
        fRecordTimeSubRunAllocator = std::make_unique<sktext::gpu::SubRunAllocator>();
    }
    return {fRecordTimeAllocator.get(), fRecordTimeSubRunAllocator.get()};
}
```

在 DDL 模式下才创建主分配器,文本分配器始终创建。

### 任务拆分策略

根据能力和选项决定是否减少任务拆分:

```cpp
bool reduceOpsTaskSplitting = true;
if (this->caps()->avoidReorderingRenderTasks()) {
    reduceOpsTaskSplitting = false;
} else if (GrContextOptions::Enable::kYes == this->options().fReduceOpsTaskSplitting) {
    reduceOpsTaskSplitting = true;
} else if (GrContextOptions::Enable::kNo == this->options().fReduceOpsTaskSplitting) {
    reduceOpsTaskSplitting = false;
}
```

这影响绘制命令的组织和优化策略。

### 上下文放弃流程

```cpp
void GrRecordingContext::abandonContext() {
    GrImageContext::abandonContext();
    this->destroyDrawingManager();
}
```

放弃时销毁绘制管理器,释放所有待处理的绘制命令。

### 统计信息收集

在 `GR_GPU_STATS` 宏启用时,收集路径遮罩生成和缓存命中统计:

```cpp
void incNumPathMasksGenerated() { fNumPathMasksGenerated++; }
void incNumPathMasksCacheHits() { fNumPathMaskCacheHits++; }
```

## 依赖关系

**依赖的模块:**

| 模块名 | 依赖说明 |
|--------|---------|
| `GrImageContext` | 父类,提供基础上下文功能 |
| `GrDrawingManager` | 绘制任务的组织和调度 |
| `GrProxyProvider` | 资源代理的创建和管理 |
| `GrAuditTrail` | 绘制操作审计跟踪 |
| `SkArenaAlloc` | 高效的竞技场式内存分配器 |
| `SubRunAllocator` | 文本渲染子运行专用分配器 |
| `GrContextThreadSafeProxy` | 线程安全的上下文代理 |
| `SkCapabilities` | 能力描述接口 |

**被依赖的模块:**

| 模块名 | 使用场景 |
|--------|---------|
| `GrDirectContext` | 继承并扩展为可执行上下文 |
| `SkCanvas` | 使用录制上下文进行 GPU 绘制 |
| `SkSurface` | GPU 表面基于录制上下文创建 |
| `SkImage` | GPU 图像使用录制上下文操作 |
| `GrDeferredDisplayList` | DDL 依赖录制上下文记录命令 |
| `GrOpsTask` | 操作任务在录制上下文中创建 |

## 设计模式与设计决策

### 继承层次与职责分离

三层上下文继承:
- `GrImageContext`: 最小上下文,支持图像操作
- `GrRecordingContext`: 添加命令录制能力
- `GrDirectContext`: 添加命令执行能力

这种分层使得 DDL 可以在录制上下文中创建,稍后在直接上下文中执行。

### 资源与配置的所有权分离

- `Arenas`: 轻量级,不拥有所有权,可随意复制和传递
- `OwnedArenas`: 拥有所有权,管理生命周期,仅支持移动

这种分离使得分配器可以在 DDL 创建时转移所有权。

### 虚拟方法用于 DDL 扩展

```cpp
virtual void recordProgramInfo(const GrProgramInfo*) {}
virtual void detachProgramData(skia_private::TArray<ProgramData>*) {}
```

DDL 录制上下文可以重写这些方法来缓存程序信息,普通上下文则为空操作。

### 统计信息条件编译

使用 `GR_GPU_STATS` 宏控制统计功能:
- 启用时: 完整的统计收集和报告
- 禁用时: 空函数,编译器完全优化掉

这避免了生产环境的性能开销。

### 友元类精细化访问控制

大量友元类声明,精确控制内部 API 的访问:
```cpp
friend class GrRecordingContextPriv;
friend class GrDeferredDisplayList;
friend class GrDeferredDisplayListPriv;
```

这比 public API 更灵活,但比完全 private 更可测试。

## 性能考量

### 竞技场分配器

使用 `SkArenaAlloc` 进行批量分配:
- 减少单独的堆分配调用
- 提升缓存局部性
- 整体释放,无需逐个析构
- DDL 模式下分配器生命周期与命令列表匹配

### 任务拆分优化

`reduceOpsTaskSplitting` 标志控制:
- 启用时: 合并更多操作到单个任务,减少状态切换
- 禁用时: 更细粒度的任务,允许更多并行机会

不同 GPU 架构的最优策略不同。

### 延迟初始化

`OwnedArenas::get()` 按需创建分配器,避免不必要的内存分配,特别是在非 DDL 模式下。

### 路径遮罩缓存

统计 `fNumPathMaskCacheHits` 表明路径遮罩被缓存和重用,避免重复光栅化复杂路径。

### 线程安全缓存

通过 `threadSafeCache()` 访问共享缓存,多个录制上下文可以共享编译好的着色器等资源。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `include/private/gpu/ganesh/GrImageContext.h` | 父类定义 |
| `include/gpu/ganesh/GrDirectContext.h` | 子类,添加执行能力 |
| `src/gpu/ganesh/GrDrawingManager.h` | 绘制管理器接口 |
| `src/gpu/ganesh/GrProxyProvider.h` | 代理提供器接口 |
| `src/gpu/ganesh/GrAuditTrail.h` | 审计跟踪实现 |
| `src/base/SkArenaAlloc.h` | 竞技场分配器 |
| `src/text/gpu/SubRunAllocator.h` | 文本子运行分配器 |
| `src/gpu/ganesh/GrCaps.h` | GPU 能力检测 |
| `src/gpu/ganesh/GrContextOptions.h` | 上下文配置选项 |
| `src/gpu/ganesh/ops/GrOpsTask.h` | 操作任务定义 |
