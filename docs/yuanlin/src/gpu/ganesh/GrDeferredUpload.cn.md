# GrDeferredUpload

> 源文件
> - src/gpu/ganesh/GrDeferredUpload.h

## 概述

`GrDeferredUpload` 定义了 Skia Ganesh 渲染引擎中延迟纹理上传的核心接口和机制。该模块使用函数式编程风格，通过 `std::function` 类型别名定义了延迟上传的函数签名，支持异步上传（ASAP Upload）和内联上传（Inline Upload）两种模式。

延迟上传机制允许将纹理数据上传操作推迟到合适的时机执行，避免读写冲突，并优化GPU命令流的组织。该模块广泛用于图集（Atlas）管理、软件裁剪遮罩和软件路径渲染等场景。

## 架构位置

`GrDeferredUpload` 位于 Skia GPU 纹理上传架构的核心层：

```
Skia GPU Texture Upload Architecture
├── Atlas Management (图集管理)
│   ├── GrDrawOpAtlas
│   └── GrAtlasManager
├── Upload Scheduling (上传调度)
│   ├── GrDeferredUpload ← 当前模块
│   ├── GrDeferredUploadTarget (调度接口)
│   └── skgpu::TokenTracker (令牌追踪)
├── Upload Execution (上传执行)
│   ├── GrOpFlushState
│   └── GrGpu (GPU接口)
└── Data Preparation (数据准备)
    └── GrDeferredProxyUploader (代理上传器)
```

该模块在架构中的职责：
- 定义延迟上传的函数接口
- 提供上传调度的抽象接口
- 管理上传的令牌（Token）系统
- 支持ASAP和内联两种上传模式

## 主要类与结构体

### 核心类型定义

#### GrDeferredTextureUploadWritePixelsFn
```cpp
using GrDeferredTextureUploadWritePixelsFn = std::function<bool(
    GrTextureProxy* proxy,
    SkIRect rect,
    GrColorType srcColorType,
    const void* buffer,
    size_t rowBytes)>;
```
写入像素数据的函数类型，由上传执行器提供。

**参数说明：**
- `proxy`: 目标纹理代理
- `rect`: 上传的矩形区域
- `srcColorType`: 源数据颜色类型
- `buffer`: 像素数据缓冲区
- `rowBytes`: 行字节数

**返回值：** 上传是否成功

#### GrDeferredTextureUploadFn
```cpp
using GrDeferredTextureUploadFn = std::function<void(GrDeferredTextureUploadWritePixelsFn&)>;
```
延迟上传函数类型，接受写入函数作为参数。

**调用时机：** 当上传应该执行时，在绘制/上传序列中被调用。

### 核心接口类

#### GrDeferredUploadTarget
```cpp
class GrDeferredUploadTarget {
public:
    virtual ~GrDeferredUploadTarget() {}

    virtual const skgpu::TokenTracker* tokenTracker() = 0;

    virtual skgpu::Token addInlineUpload(GrDeferredTextureUploadFn&&) = 0;

    virtual skgpu::Token addASAPUpload(GrDeferredTextureUploadFn&& upload) = 0;
};
```
延迟上传调度接口，负责接受和调度上传任务。

### 接口方法

| 方法 | 返回值 | 说明 |
|-----|-------|------|
| `tokenTracker()` | `const skgpu::TokenTracker*` | 获取令牌追踪器 |
| `addInlineUpload(...)` | `skgpu::Token` | 添加内联上传，返回上传前的绘制令牌 |
| `addASAPUpload(...)` | `skgpu::Token` | 添加ASAP上传，返回刷新后的首个令牌 |

## 公共 API 函数

该模块主要提供类型定义和抽象接口，具体实现由子类完成：

### tokenTracker
```cpp
virtual const skgpu::TokenTracker* tokenTracker() = 0;
```
获取令牌追踪器，用于查询绘制操作的刷新状态。

### addInlineUpload
```cpp
virtual skgpu::Token addInlineUpload(GrDeferredTextureUploadFn&& uploadFn) = 0;
```
添加内联上传任务，在特定绘制操作之前执行。

**使用场景：** 当存在读写数据冲突时，必须在依赖旧纹理内容的绘制之后、依赖新纹理内容的绘制之前执行上传。

**返回值：** 上传将在此令牌对应的绘制之前发生

### addASAPUpload
```cpp
virtual skgpu::Token addASAPUpload(GrDeferredTextureUploadFn&& uploadFn) = 0;
```
添加ASAP（尽快）上传任务，在帧开始时执行。

**使用场景：** 没有读写冲突时，优先使用ASAP上传以提高性能。

**返回值：** 自上次刷新以来的首个令牌

## 内部实现细节

### 令牌（Token）系统

延迟上传机制的核心是基于令牌的依赖追踪：

1. **令牌分配**：每个绘制操作被分配一个唯一的令牌
2. **资源标记**：资源（或其部分）标记最近读取它的绘制令牌
3. **冲突检测**：上传前检查依赖该资源的绘制是否已刷新
4. **调度决策**：
   - 如果依赖的绘制已刷新 → ASAP上传
   - 如果依赖的绘制未刷新 → 内联上传

### ASAP上传 vs 内联上传

**ASAP上传（异步上传）：**
```
时间线：
[刷新开始] → [ASAP上传] → [绘制操作1] → [绘制操作2] → ... → [刷新结束]
```

**优点：**
- 在帧开始时完成，减少中间等待
- 可以批量处理多个上传
- GPU可以并行执行其他操作

**内联上传（同步上传）：**
```
时间线：
[绘制操作A（读旧数据）] → [内联上传] → [绘制操作B（读新数据）]
```

**必要性：**
- 解决读写数据冲突
- 确保绘制顺序正确性

### 使用模式示例

```cpp
// 操作与图集交互时的典型流程
class MyOp : public GrOp {
    void onExecute(GrOpFlushState* flushState) {
        // 检查资源是否需要更新
        skgpu::Token lastUseToken = atlas->getLastUseToken(region);

        if (flushState->tokenTracker()->hasTokenBeenFlushed(lastUseToken)) {
            // 安全：旧数据已刷新，可以ASAP上传
            flushState->addASAPUpload([=](GrDeferredTextureUploadWritePixelsFn& writePixels) {
                writePixels(proxy, rect, colorType, newData, rowBytes);
            });
        } else {
            // 冲突：需要内联上传
            skgpu::Token uploadBeforeToken = flushState->addInlineUpload(
                [=](GrDeferredTextureUploadWritePixelsFn& writePixels) {
                    writePixels(proxy, rect, colorType, newData, rowBytes);
                });

            // 确保当前操作在上传之后
            flushState->recordUploadToken(uploadBeforeToken);
        }
    }
};
```

### 函数式设计

使用 `std::function` 允许灵活地捕获上下文：

```cpp
// 捕获局部变量
void scheduleUpload() {
    sk_sp<GrTextureProxy> proxy = ...;
    SkIRect rect = ...;
    void* data = ...;

    target->addASAPUpload([proxy, rect, data](auto& writePixels) {
        writePixels(proxy.get(), rect, kRGBA_8888_GrColorType, data, rect.width() * 4);
    });
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `skgpu::TokenTracker` | 令牌追踪，查询刷新状态 |
| `skgpu::Token` | 令牌类型 |
| `GrTextureProxy` | 纹理代理 |
| `GrColorType` | 颜色类型枚举 |
| `SkIRect` | 矩形区域 |
| `std::function` | 函数对象 |
| `GrAtlasTypes.h` | 图集类型定义 |

### 被依赖的模块

| 模块 | 使用方式 |
|-----|---------|
| `GrDrawOpAtlas` | 使用延迟上传更新图集 |
| `GrOpFlushState` | 实现 `GrDeferredUploadTarget` 接口 |
| `GrDeferredProxyUploader` | 使用延迟上传机制 |
| `GrOp` 子类 | 调度纹理上传 |
| 软件路径渲染器 | 上传路径遮罩 |
| 软件裁剪系统 | 上传裁剪遮罩 |

## 设计模式与设计决策

### 回调模式（Callback Pattern）

使用函数对象作为回调，延迟执行上传操作：
```cpp
using GrDeferredTextureUploadFn = std::function<void(GrDeferredTextureUploadWritePixelsFn&)>;
```

**优点：**
- 灵活的上下文捕获
- 类型安全
- 支持lambda表达式

### 策略模式（Strategy Pattern）

通过 `GrDeferredUploadTarget` 接口抽象上传调度策略，不同实现可以有不同的调度算法。

### 依赖注入（Dependency Injection）

上传函数接受写入函数作为参数，实现解耦：
```cpp
void uploadFn(GrDeferredTextureUploadWritePixelsFn& writePixels) {
    writePixels(proxy, rect, colorType, data, rowBytes);
}
```

### 令牌化（Tokenization）

使用令牌系统追踪依赖关系，避免使用复杂的依赖图。

### 双模式设计

提供ASAP和内联两种模式，平衡性能和正确性：
- **默认使用ASAP**：优化常见情况
- **按需使用内联**：处理特殊冲突

### 设计决策

1. **使用std::function**：提供最大的灵活性，代价是虚函数调用开销
2. **接口与实现分离**：`GrDeferredUploadTarget` 仅定义接口，具体实现在 `GrOpFlushState` 中
3. **令牌系统**：相比依赖图更轻量，适合动态场景
4. **函数式风格**：简化API，减少类层次

## 性能考量

### ASAP上传优化

ASAP上传在帧开始时批量执行：
- **减少状态切换**：连续的上传操作可以合并
- **并行机会**：GPU可以在上传时执行其他命令
- **减少同步点**：避免中间插入上传导致的管线停顿

### 内联上传开销

内联上传会打断绘制流程：
- **管线刷新**：可能需要刷新GPU管线
- **状态保存/恢复**：切换到上传状态后需要恢复
- **同步开销**：等待上传完成

因此应该尽量使用ASAP上传。

### 函数对象开销

`std::function` 有一定开销：
- **虚函数调用**：通过函数指针调用
- **内存分配**：捕获大量数据时可能动态分配
- **拷贝开销**：函数对象传递时可能拷贝捕获的变量

**缓解措施：**
- 使用移动语义（`std::move`）
- 捕获指针而非大对象
- 编译器优化（内联）

### 令牌查询效率

令牌追踪器使用高效的数据结构，查询 `O(1)` 复杂度：
```cpp
bool hasTokenBeenFlushed(Token token) const;
```

### 避免不必要的上传

操作应该智能地检测是否真正需要上传：
```cpp
if (atlas->hasSpace(requiredSize)) {
    // 重用现有空间，无需上传
} else {
    // 需要更新，调度上传
    scheduleUpload();
}
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrAtlasTypes.h` | 依赖 | 图集类型定义（包含Token） |
| `src/gpu/ganesh/GrOpFlushState.h` | 实现 | 实现 `GrDeferredUploadTarget` 接口 |
| `src/gpu/ganesh/GrDrawOpAtlas.h` | 使用 | 图集使用延迟上传 |
| `src/gpu/ganesh/GrDeferredProxyUploader.h` | 使用 | 代理上传器 |
| `src/gpu/ganesh/text/GrAtlasManager.h` | 使用 | 图集管理器 |
| `src/gpu/ganesh/GrTextureProxy.h` | 依赖 | 纹理代理 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | 依赖 | GPU类型定义 |
