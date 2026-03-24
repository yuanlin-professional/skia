# GraphiteTypes

> 源文件: `include/gpu/graphite/GraphiteTypes.h`

## 概述

GraphiteTypes.h 定义了 Graphite GPU 后端的核心类型、枚举和结构体,包括 Recording 插入状态、提交信息、采样计数、绘制类型标志等。这是 Graphite 架构中最基础的类型定义文件,为上层 API 提供了类型安全的接口。

## 架构位置

该文件位于 Skia Graphite GPU 后端的公共接口层,属于 `skgpu::graphite` 命名空间。它是整个 Graphite 类型系统的基础,被 Context、Recorder、Recording 等核心类广泛使用,提供了跨平台的类型抽象。

## 主要类型与枚举

### 回调函数类型定义

```cpp
using GpuFinishedContext = void*;
using GpuFinishedProc = void (*)(GpuFinishedContext finishedContext, CallbackResult);
using GpuFinishedWithStatsProc = void (*)(GpuFinishedContext finishedContext,
                                          CallbackResult,
                                          const GpuStats&);
```

**用途**: GPU 工作完成时的回调机制
- `GpuFinishedContext`: 客户端上下文指针
- `GpuFinishedProc`: 基础完成回调
- `GpuFinishedWithStatsProc`: 带统计信息的完成回调

## 主要类与结构体

### InsertStatus

```cpp
class InsertStatus {
    enum V {
        kSuccess,
        kInvalidRecording,
        kPromiseImageInstantiationFailed,
        kAddCommandsFailed,
        kAsyncShaderCompilesFailed,
        kOutOfOrderRecording,
    };
};
```

**职责**: 表示 `Context::insertRecording()` 的操作状态,支持详细的错误信息。

**设计特点**:
- 类包装的枚举,支持关联错误消息
- 可隐式转换为 bool (kSuccess 为 true,其他为 false)
- 兼容旧版返回 bool 的 API

**状态值说明**:
| 状态 | 含义 | CommandBuffer 状态 |
|------|------|--------------------|
| `kSuccess` | 成功添加到 CommandBuffer | 已修改 |
| `kInvalidRecording` | Recording 或参数无效 | 未修改 |
| `kPromiseImageInstantiationFailed` | Promise 图像实例化失败 | 未修改 |
| `kAddCommandsFailed` | 内部失败,CB 部分修改 | 不可恢复 |
| `kAsyncShaderCompilesFailed` | 异步着色器编译失败 | 不可恢复 |
| `kOutOfOrderRecording` | Recording 顺序错误 | 未修改,可能不可恢复 |

**关键成员函数**:
```cpp
const std::string& message() const;  // 获取错误消息
operator bool() const;               // 转换为 bool
```

### InsertRecordingInfo

```cpp
struct InsertRecordingInfo {
    Recording* fRecording = nullptr;

    SkSurface* fTargetSurface = nullptr;
    SkIVector fTargetTranslation = {0, 0};
    SkIRect fTargetClip = {0, 0, 0, 0};
    MutableTextureState* fTargetTextureState = nullptr;

    size_t fNumWaitSemaphores = 0;
    BackendSemaphore* fWaitSemaphores = nullptr;
    size_t fNumSignalSemaphores = 0;
    BackendSemaphore* fSignalSemaphores = nullptr;

    GpuStatsFlags fGpuStatsFlags = GpuStatsFlags::kNone;
    GpuFinishedContext fFinishedContext = nullptr;
    GpuFinishedProc fFinishedProc = nullptr;
    GpuFinishedWithStatsProc fFinishedWithStatsProc = nullptr;

    InsertStatus fSimulatedStatus = InsertStatus::kSuccess;
};
```

**职责**: 封装插入 Recording 时的所有参数和配置。

**关键字段说明**:

#### Recording 相关
- `fRecording`: 要插入的 Recording 对象

#### Deferred Canvas 目标
- `fTargetSurface`: 延迟画布的目标 Surface
- `fTargetTranslation`: 额外的平移变换
- `fTargetClip`: 额外的裁剪区域(在 fTargetTranslation 之后应用)
- `fTargetTextureState`: 目标纹理状态

#### 同步原语
- `fWaitSemaphores/fNumWaitSemaphores`: GPU 在执行前等待的信号量
- `fSignalSemaphores/fNumSignalSemaphores`: GPU 在执行后发信号的信号量
- 信号量的等待/发信时机取决于平台实现

#### 回调机制
- `fFinishedProc`: 完成回调(基础版)
- `fFinishedWithStatsProc`: 完成回调(带统计信息)
- 如果两者都提供,优先使用 `fFinishedWithStatsProc`
- 回调保证被调用一次(无论成功或失败)

#### 测试支持
- `fSimulatedStatus`: 用于单元测试模拟失败状态

### InsertFinishInfo

```cpp
struct InsertFinishInfo {
    GpuFinishedContext fFinishedContext = nullptr;
    GpuFinishedProc fFinishedProc = nullptr;
    GpuFinishedWithStatsProc fFinishedWithStatsProc = nullptr;
    GpuStatsFlags fGpuStatsFlags = GpuStatsFlags::kNone;
};
```

**职责**: 简化版的完成信息,用于提交时附加回调。

**构造函数**:
```cpp
InsertFinishInfo() = default;
InsertFinishInfo(GpuFinishedContext context, GpuFinishedProc proc);
InsertFinishInfo(GpuFinishedContext context, GpuFinishedWithStatsProc proc);
```

### SubmitInfo

```cpp
struct SubmitInfo {
    SyncToCpu fSync = SyncToCpu::kNo;
    MarkFrameBoundary fMarkBoundary = MarkFrameBoundary::kNo;
    uint64_t fFrameID = 0;

    GpuFinishedProc fFinishedProc = nullptr;
    GpuFinishedContext fFinishedContext = nullptr;
};
```

**职责**: 封装 `Context::submit()` 的参数。

**关键字段**:
- `fSync`: 是否同步等待 GPU 完成
- `fMarkBoundary`: 是否标记帧边界(用于性能分析)
- `fFrameID`: 帧 ID(当 fMarkBoundary 为 kYes 时使用)
- `fFinishedProc/fFinishedContext`: 完成回调

**便捷构造函数**:
```cpp
constexpr SubmitInfo(SyncToCpu sync);
constexpr SubmitInfo(SyncToCpu sync, uint64_t frameID);
```

### SyncToCpu

```cpp
enum class SyncToCpu : bool {
    kYes = true,
    kNo = false
};
```

**用途**: 指示是否同步等待 GPU 完成工作。

### MarkFrameBoundary

```cpp
enum class MarkFrameBoundary : bool {
    kYes = true,
    kNo = false
};
```

**用途**: 标记帧边界,用于性能追踪和调试工具。

### Volatile (Promise Images)

```cpp
enum class Volatile : bool {
    kNo = false,   // 只实例化一次
    kYes = true    // 每次插入时都实例化
};
```

**用途**: Promise Image 的实例化策略
- `kNo`: 图像内容不变,只在首次使用时实例化
- `kYes`: 图像内容可能变化,每次插入 Recording 时都重新实例化

### DepthStencilFlags

```cpp
enum class DepthStencilFlags : int {
    kNone         = 0b000,
    kDepth        = 0b001,
    kStencil      = 0b010,
    kDepthStencil = kDepth | kStencil,
};
```

**用途**: 指示渲染目标需要的深度/模板缓冲。

### SampleCount

```cpp
enum class SampleCount : uint8_t {
    k1  = 1,
    k2  = 2,
    k4  = 4,
    k8  = 8,
    k16 = 16
};
```

**用途**: 多重采样抗锯齿(MSAA)的采样数。

**工具函数**:
```cpp
constexpr SampleCount ToSampleCount(uint32_t sampleCount);
```
- 将任意整数转换为有效的 SampleCount(向下取整)

### DrawTypeFlags

```cpp
enum DrawTypeFlags : uint16_t {
    kNone             = 0,
    kBitmapText_Mask  = 1 << 0,
    kBitmapText_LCD   = 1 << 1,
    kBitmapText_Color = 1 << 2,
    kSDFText          = 1 << 3,
    kSDFText_LCD      = 1 << 4,
    kDrawVertices     = 1 << 5,
    kCircularArc      = 1 << 6,
    kAnalyticRRect    = 1 << 7,
    kPerEdgeAAQuad    = 1 << 8,
    kNonAAFillRect    = 1 << 9,
    kSimpleShape      = kAnalyticRRect | kPerEdgeAAQuad | kNonAAFillRect,
    kNonSimpleShape   = 1 << 10,
    kDropShadows      = 1 << 11,
    kAnalyticClip     = 1 << 12,
    kLast = kAnalyticClip,
};
```

**职责**: 用于 Precompilation API,标识不同的绘制类型。

**主要分类**:

#### 文本渲染
- `kBitmapText_Mask`: 位图文本(遮罩模式)
- `kBitmapText_LCD`: 位图文本(LCD 亚像素渲染)
- `kBitmapText_Color`: 位图文本(彩色)
- `kSDFText`: 有向距离场文本
- `kSDFText_LCD`: SDF 文本(LCD)

#### 几何绘制
- `kDrawVertices`: 顶点绘制(三角形、三角带,带/不带纹理和颜色)
- `kCircularArc`: 圆弧绘制
- `kAnalyticRRect`: 分析式圆角矩形
- `kPerEdgeAAQuad`: 每边抗锯齿的四边形
- `kNonAAFillRect`: 非抗锯齿填充矩形

#### 复合类型
- `kSimpleShape`: 简单形状组合
- `kNonSimpleShape`: 复杂形状(覆盖遮罩、曲面细分等)
- `kDropShadows`: 阴影绘制
- `kAnalyticClip`: 分析式裁剪

**用途示例**:
从 GraphicsPipeline 打印信息映射到预编译参数:
```cpp
DrawTypeFlags types = kAnalyticRRect | kPerEdgeAAQuad | kSDFText;
```

## 内部实现细节

### InsertStatus 的设计权衡

**为什么是类而非 enum class**:
- 需要关联错误消息字符串
- 需要隐式转换为 bool (向后兼容)
- enum class 不支持这些特性

**bool 转换的设计**:
```cpp
operator bool() const {
    return fValue == kSuccess;
}
```
- 非 explicit,允许在 if 条件和返回语句中直接使用
- 简化了从旧 bool API 的迁移

### 信号量的平台差异

文档明确指出信号量的等待/发信时机:
- **某些平台**: 在 Recording 命令前/后立即执行
- **其他平台**: 在整个 CommandBuffer 前/后执行
- 客户端应该假设最宽松的语义

### Deferred Canvas 机制

`InsertRecordingInfo` 中的目标 Surface 相关字段用于延迟画布:
1. Recording 包含延迟画布的绘制命令
2. 插入时提供 `fTargetSurface`
3. 应用 `fTargetTranslation` 和 `fTargetClip`
4. 将绘制重放到目标 Surface

### 回调调用保证

完成回调的行为保证:
- **调用次数**: 总是恰好一次
- **调用时机**:
  - 成功: GPU 工作完成后(通常在 submit 期间)
  - 失败: 检测到失败时立即调用
- **CallbackResult**:
  - `kSuccess`: GPU 成功完成
  - `kFailed`: 任何失败情况

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `include/core/SkPoint.h` | SkIVector 定义 |
| `include/core/SkRect.h` | SkIRect 定义 |
| `include/core/SkTypes.h` | 基础类型定义 |
| `include/gpu/GpuTypes.h` | CallbackResult, GpuStats, Mipmapped 等 |

### 被依赖的模块

- `Context`: 使用 InsertRecordingInfo, SubmitInfo
- `Recorder`: 使用 SampleCount, DrawTypeFlags
- `Recording`: 被 InsertRecordingInfo 引用
- `TextureInfo`: 使用 SampleCount, DepthStencilFlags
- Precompilation API: 使用 DrawTypeFlags

## 设计模式与设计决策

### 类型安全的枚举

使用 enum class 而非普通 enum:
- 避免名称冲突
- 类型安全(不会隐式转换为 int)
- 更好的 IDE 支持

### 位标志组合

`DrawTypeFlags` 使用位运算支持组合:
```cpp
DrawTypeFlags flags = kAnalyticRRect | kPerEdgeAAQuad;
```
- 紧凑的表示(单个 uint16_t)
- 高效的测试(位运算)

### 结构体初始化列表

使用 C++11 默认成员初始化:
```cpp
struct InsertRecordingInfo {
    Recording* fRecording = nullptr;
    // ...
};
```
- 避免未初始化的成员
- 提供合理的默认值

### 测试支持的设计

`fSimulatedStatus` 字段专门用于测试:
- 允许单元测试模拟各种失败场景
- 不影响生产代码逻辑
- 在测试中设置,实现中检查

## 性能考量

### SyncToCpu 的影响

```cpp
SubmitInfo info;
info.fSync = SyncToCpu::kYes;  // 阻塞等待,性能差
info.fSync = SyncToCpu::kNo;   // 异步,高性能
```
- `kYes`: 阻塞等待 GPU,延迟高但简化同步
- `kNo`: 异步提交,需要手动同步但性能好

### 信号量开销

- 等待信号量会阻塞 GPU
- 发信号信号量有轻微开销
- 只在必要时使用(跨 API 同步)

### DrawTypeFlags 的使用

预编译时应该精确指定需要的类型:
- 过多标志会编译不必要的 Pipeline
- 过少标志会导致运行时编译
- 通过性能分析确定实际使用的类型

### SampleCount 的内存影响

| SampleCount | 内存倍数 | 性能影响 |
|-------------|----------|----------|
| k1 | 1x | 基线 |
| k2 | 2x | 轻微 |
| k4 | 4x | 中等 |
| k8 | 8x | 显著 |
| k16 | 16x | 很大 |

## 使用示例

### 插入 Recording

```cpp
InsertRecordingInfo info;
info.fRecording = recording.get();
info.fFinishedProc = [](void* ctx, CallbackResult result) {
    if (result == CallbackResult::kSuccess) {
        // GPU 完成
    }
};

InsertStatus status = context->insertRecording(info);
if (!status) {
    SkDebugf("Insert failed: %s\n", status.message().c_str());
}
```

### 提交工作

```cpp
// 异步提交
context->submit(SubmitInfo{SyncToCpu::kNo});

// 同步提交
context->submit(SubmitInfo{SyncToCpu::kYes});

// 带帧标记
SubmitInfo info{SyncToCpu::kNo, frameID};
info.fMarkBoundary = MarkFrameBoundary::kYes;
context->submit(info);
```

### 预编译 Pipelines

```cpp
DrawTypeFlags types = kAnalyticRRect | kSDFText | kAnalyticClip;
precompiler->precompile(types, paintOptions);
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/gpu/graphite/Context.h` | 使用 InsertRecordingInfo, SubmitInfo |
| `include/gpu/graphite/Recording.h` | 被 InsertRecordingInfo 引用 |
| `include/gpu/graphite/BackendSemaphore.h` | 信号量类型定义 |
| `include/gpu/GpuTypes.h` | CallbackResult, GpuStats 等基础类型 |
| `include/core/SkSurface.h` | fTargetSurface 类型 |
