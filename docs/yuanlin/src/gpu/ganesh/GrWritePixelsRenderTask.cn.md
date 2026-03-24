# GrWritePixelsRenderTask

> 源文件: src/gpu/ganesh/GrWritePixelsRenderTask.h, src/gpu/ganesh/GrWritePixelsRenderTask.cpp

## 概述

`GrWritePixelsRenderTask` 是 Skia Ganesh GPU 后端中的一个渲染任务,专门用于将 CPU 端的像素数据写入 GPU 纹理表面。它封装了跨颜色空间、多级别 mipmap 的像素传输操作,是实现纹理上传和更新的核心机制。

该类继承自 `GrRenderTask`,融入 Ganesh 的延迟渲染管线,允许像素写入操作与其他渲染任务进行依赖管理和资源分配协调。支持从 CPU 内存直接写入 GPU,处理颜色格式转换,并支持多级 mipmap 数据的批量传输。

## 架构位置

`GrWritePixelsRenderTask` 在 Ganesh 渲染系统中的位置:

- **上层**: 由 `GrDrawingManager` 创建和调度
- **同层**: 与其他 `GrRenderTask` 子类(如 `GrOpsTask`, `GrCopyRenderTask`)并列
- **下层**: 依赖 `GrGpu` 执行实际的 GPU 写入操作

该类是渲染任务 DAG (有向无环图)的一个节点,通过资源分配器管理与其他任务的依赖关系。

## 主要类与结构体

### GrWritePixelsTask 类

**继承关系**:
- 继承自 `GrRenderTask`
- 标记为 `final`,禁止进一步派生

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fLevels` | `skia_private::AutoSTArray<16, GrMipLevel>` | 多级 mipmap 数据数组 |
| `fRect` | `SkIRect` | 目标矩形区域 |
| `fSrcColorType` | `GrColorType` | 源数据颜色格式 |
| `fDstColorType` | `GrColorType` | 目标表面颜色格式 |

**继承的隐藏成员**:
- 从 `GrRenderTask` 继承目标表面代理(`targets`)

**内存优化**:
- `AutoSTArray<16>` 在栈上预分配 16 个 mipmap 级别,避免堆分配

## 公共 API 函数

### GrWritePixelsTask::Make (静态工厂方法)

```cpp
static sk_sp<GrRenderTask> Make(
    GrDrawingManager* dm,
    sk_sp<GrSurfaceProxy> dst,
    SkIRect rect,
    GrColorType srcColorType,
    GrColorType dstColorType,
    const GrMipLevel texels[],
    int levelCount)
```

**功能**: 创建一个写像素渲染任务。

**参数**:
- `dm`: 绘图管理器,用于注册任务
- `dst`: 目标表面代理
- `rect`: 写入区域
- `srcColorType`: 源数据的颜色格式
- `dstColorType`: 目标表面的颜色格式
- `texels`: mipmap 级别数据数组
- `levelCount`: mipmap 级别数量

**返回值**: 智能指针包装的渲染任务,类型擦除为基类 `GrRenderTask`。

**用途**: 这是创建任务的唯一公开方式,隐藏构造函数细节。

## 内部实现细节

### 构造函数

构造函数是私有的,确保只能通过 `Make` 工厂方法创建:

```cpp
GrWritePixelsTask(GrDrawingManager* dm,
                  sk_sp<GrSurfaceProxy> dst,
                  SkIRect rect,
                  GrColorType srcColorType,
                  GrColorType dstColorType,
                  const GrMipLevel texels[],
                  int levelCount)
```

**关键步骤**:
1. 调用 `addTarget()` 将目标表面添加到任务
2. 使用 `std::copy_n` 拷贝 mipmap 数据到内部数组

### gatherProxyIntervals

```cpp
void gatherProxyIntervals(GrResourceAllocator* alloc) const override
```

**功能**: 向资源分配器注册代理的使用区间。

**实现**:
- 添加单个目标代理的区间
- 设置为实际使用(`ActualUse::kYes`)
- 允许回收(`AllowRecycling::kYes`)
- 操作索引为当前操作号

**意义**: 确保目标表面在任务执行时已实例化且不被回收。

### onMakeClosed

```cpp
ExpectedOutcome onMakeClosed(GrRecordingContext*, SkIRect* targetUpdateBounds) override
```

**功能**: 标记任务已关闭,准备执行。

**返回**:
- `targetUpdateBounds`: 设置为 `fRect`,指示更新区域
- 返回 `ExpectedOutcome::kTargetDirty`,表示会修改目标

**作用**: 通知系统目标表面将被修改,影响依赖分析。

### onExecute

```cpp
bool onExecute(GrOpFlushState* flushState) override
```

**功能**: 执行实际的像素写入操作。

**流程**:
1. 检查目标代理是否已实例化
2. 获取底层 `GrSurface` 对象
3. 调用 `GrGpu::writePixels` 执行硬件写入

**返回值**:
- `true`: 写入成功
- `false`: 代理未实例化,写入失败

**错误处理**: 如果代理未实例化,直接返回失败,不执行写入。

### onIsUsed

```cpp
bool onIsUsed(GrSurfaceProxy* proxy) const override
```

**功能**: 查询任务是否使用某个代理。

**实现**: 始终返回 `false`,因为不使用非目标代理。

**特殊性**: 该任务只写入目标,不读取其他资源。

### Debug 支持

```cpp
#if defined(GPU_TEST_UTILS)
    const char* name() const final { return "WritePixels"; }
#endif
```

用于测试和调试时识别任务类型。

### visitProxies_debugOnly

```cpp
#ifdef SK_DEBUG
    void visitProxies_debugOnly(const GrVisitProxyFunc&) const override {}
#endif
```

空实现,因为没有非目标代理需要访问。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrRenderTask` | 基类,提供任务管理框架 |
| `GrDrawingManager` | 创建和调度任务 |
| `GrSurfaceProxy` | 表示延迟实例化的 GPU 表面 |
| `GrGpu` | 执行底层 GPU 写入操作 |
| `GrOpFlushState` | 提供执行时的上下文状态 |
| `GrResourceAllocator` | 管理资源分配和依赖 |
| `GrMipLevel` | 表示单个 mipmap 级别的数据 |

### 被依赖的模块

该任务被以下场景使用:
- 纹理上传(从 CPU 到 GPU)
- 纹理子区域更新
- 动态纹理内容修改
- Mipmap 生成的源数据准备

通常由 `GrSurfaceContext` 或 `GrRenderTargetContext` 间接创建。

## 设计模式与设计决策

### Factory 模式

使用静态工厂方法 `Make` 而非公开构造函数:

**优点**:
- 返回基类指针,隐藏实现细节
- 允许未来返回不同的子类实现
- 强制通过绘图管理器注册任务

### RAII 资源管理

智能指针 `sk_sp` 自动管理表面代理生命周期:
- 构造时自动增加引用计数
- 析构时自动释放,防止泄漏

### 最小接口原则

大部分成员函数为私有,只暴露必要的虚函数覆盖:
- 防止误用
- 明确对外契约

### 类型安全的颜色格式

使用 `GrColorType` 枚举而非原始整数:
- 编译时类型检查
- 自文档化代码
- 防止格式混淆

### 栈优化的数组

`AutoSTArray<16>` 在常见情况下避免堆分配:
- 大多数纹理只有少数 mipmap 级别
- 16 级别覆盖 65536x65536 的纹理
- 超出时自动切换到堆分配

## 性能考量

### 延迟执行

作为渲染任务的一部分,写入操作不是立即执行的:

**优点**:
- 允许资源分配器优化内存布局
- 可与其他任务合并提交
- 避免不必要的 GPU 刷新

**权衡**: 数据必须保持有效直到任务执行,增加内存压力。

### 拷贝开销

构造时使用 `std::copy_n` 拷贝 mipmap 数据:

**原因**:
- 源数据生命周期由调用者控制
- 必须保存副本以保证延迟执行的正确性

**优化**: `AutoSTArray` 的栈分配减少拷贝开销。

### 批量传输

支持一次性传输多个 mipmap 级别:
- 减少 API 调用次数
- 利用 GPU DMA 的批量传输能力

### 失败路径

使用早期返回快速处理错误:

```cpp
if (!dstProxy->isInstantiated()) {
    return false;  // 快速失败
}
```

避免不必要的计算。

### 资源回收

允许回收 (`AllowRecycling::kYes`) 使纹理内存可重用:
- 减少内存碎片
- 提高内存利用率

## 相关文件

| 文件 | 关系 |
|------|------|
| `src/gpu/ganesh/GrRenderTask.h` | 基类定义 |
| `src/gpu/ganesh/GrDrawingManager.h` | 任务创建者 |
| `src/gpu/ganesh/GrGpu.h` | 执行写入的 GPU 接口 |
| `src/gpu/ganesh/GrOpFlushState.h` | 执行时的状态管理 |
| `src/gpu/ganesh/GrResourceAllocator.h` | 资源分配协调 |
| `src/gpu/ganesh/GrSurfaceProxy.h` | 延迟表面代理 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | 颜色类型定义 |
| `src/gpu/ganesh/GrSurface.h` | 实际 GPU 表面对象 |
