# ContextOptions

> 源文件: `include/gpu/graphite/ContextOptions.h`

## 概述

ContextOptions 定义了 Graphite Context 的配置选项结构体,涵盖性能调优、资源管理、着色器编译、文本渲染、预编译回调等多个方面。它是创建 Context 时传入的核心配置对象,允许客户端精细控制 Graphite 的行为。

## 架构位置

该文件位于 Skia Graphite GPU 后端的公共接口层,属于 `skgpu::graphite` 命名空间。ContextOptions 在 Context 创建时使用,影响整个 Context 生命周期内的行为。它是 Graphite 架构中配置和策略的集中定义点。

## 主要结构体

### ContextOptions

```cpp
struct SK_API ContextOptions {
    ContextOptions() {}
    // ... 各种配置字段
};
```

**职责**: 封装 Context 的所有配置选项,采用结构体而非构造函数参数的设计,便于扩展和维护。

## 配置字段详解

### 驱动与兼容性

#### fDisableDriverCorrectnessWorkarounds

```cpp
bool fDisableDriverCorrectnessWorkarounds = false;
```

- **用途**: 禁用针对特定 GPU、OS 或驱动的正确性修复
- **注意**: 不影响性能优化路径,不覆盖其他 ContextOption 设置
- **适用场景**: 测试、调试或已知环境安全时使用

### 着色器编译

#### fShaderErrorHandler

```cpp
skgpu::ShaderErrorHandler* fShaderErrorHandler = nullptr;
```

- **用途**: 着色器编译失败时的错误处理器
- **默认行为**: 如果为 nullptr,使用 SkDebugf 输出并触发断言
- **生命周期**: 客户端负责保持对象有效

#### fExecutor

```cpp
SkExecutor* fExecutor = nullptr;
```

- **用途**: 处理 Graphite 的多线程工作(主要是 Pipeline 编译)
- **默认**: nullptr 表示所有工作在主线程串行执行
- **生命周期**: 客户端确保在 Context 生命周期内有效
- **性能影响**: 启用后可显著加速着色器编译

### MSAA 配置

#### fInternalMultisampleCount

```cpp
SampleCount fInternalMultisampleCount = SampleCount::k4;
```

- **用途**: Graphite 内部 MSAA 绘制的最大采样数
- **范围**: 如果硬件不支持,会使用更低的值
- **禁用**: 设置为 ≤1 禁用内部 MSAA 路径

#### fInternalMSAATileSize

```cpp
std::optional<SkISize> fInternalMSAATileSize = std::nullopt;
```

- **用途**: MSAA 纹理的最大尺寸限制
- **行为**: Graphite 会将大图切分成多个 tile
- **注意**: 如果后端不支持或有更优 HW 特性,该选项会被忽略

#### fMinimumPathSizeForMSAA

```cpp
float fMinimumPathSizeForMSAA = 0;
```

- **用途**: 路径小于该尺寸(设备空间)时避免 MSAA
- **建议**: 应小于 `fGlyphsAsPathsFontSize`
- **目的**: 避免小路径的 MSAA 内存开销

### 文本渲染配置

#### fGlyphCacheTextureMaximumBytes

```cpp
size_t fGlyphCacheTextureMaximumBytes = 2048 * 1024 * 4;  // 8 MB
```

- **用途**: 字形缓存纹理的最大字节数
- **默认**: 8 MB

#### fMinDistanceFieldFontSize

```cpp
float fMinDistanceFieldFontSize = 18;
```

- **用途**: 小于该尺寸(设备空间)不使用距离场字体
- **原因**: 小字号下 hinting 更重要,距离场字体不支持 hinting

#### fGlyphsAsPathsFontSize

```cpp
#if defined(SK_BUILD_FOR_ANDROID)
    float fGlyphsAsPathsFontSize = 384;
#elif defined(SK_BUILD_FOR_MAC)
    float fGlyphsAsPathsFontSize = 256;
#else
    float fGlyphsAsPathsFontSize = 324;
#endif
```

- **用途**: 大于该尺寸(设备空间)的字形绘制为路径
- **平台差异**: Android、macOS 和其他平台有不同默认值
- **原因**: 超大字形使用路径渲染更高效

#### fAllowMultipleAtlasTextures

```cpp
bool fAllowMultipleAtlasTextures = true;
```

- **用途**: 是否允许字形和路径 atlas 使用多个纹理
- **约束**: 每个纹理仍受 `fGlyphCacheTextureMaximumBytes` 和 `fMaxPathAtlasTextureSize` 限制

#### fSupportBilerpFromGlyphAtlas

```cpp
bool fSupportBilerpFromGlyphAtlas = false;
```

- **用途**: 是否支持从字形 atlas 双线性采样
- **默认**: 关闭(通常字形使用最近邻采样)

### 路径渲染配置

#### fMaxPathAtlasTextureSize

```cpp
int fMaxPathAtlasTextureSize = 8192;
```

- **用途**: 路径 atlas 纹理的最大尺寸
- **注意**: 默认值较大,实际 PathAtlas 可能更小

### Recording 顺序要求

#### fRequireOrderedRecordings

```cpp
bool fRequireOrderedRecordings = false;
```

- **用途**: 是否要求同一 Recorder 的 Recording 按顺序重放
- **性能影响**:
  - `true`: 更好的性能(可做更多假设)
  - `false`: 需要在每个 Recording 开始时刷新缓存
- **Recorder 级别覆盖**: 可通过 RecorderOptions 为单个 Recorder 覆盖该设置
- **跨 Recorder**: 不同 Recorder 的 Recording 总是可以任意顺序插入

### 资源预算

#### fGpuBudgetInBytes

```cpp
static constexpr size_t kDefaultContextBudget = 256 * (1 << 20);  // 256 MB
size_t fGpuBudgetInBytes = kDefaultContextBudget;
```

- **用途**: Context 分配和持有的 GPU 资源预算
- **默认**: 256 MB
- **适用**: 主要针对可重用的 scratch 资源

### 调试与标签

#### fSetBackendLabels

```cpp
#if defined(SK_DEBUG)
    bool fSetBackendLabels = true;
#else
    bool fSetBackendLabels = false;
#endif
```

- **用途**: 是否在后端资源上设置标签(用于调试)
- **默认**: Debug 构建为 true,Release 构建为 false
- **影响**: 便于 GPU 调试工具(如 RenderDoc、Xcode GPU Debugger)查看

### Pipeline 缓存回调

#### 回调上下文

```cpp
using PipelineCallbackContext = void*;
PipelineCallbackContext fPipelineCallbackContext = nullptr;
```

- **用途**: 传递给 Pipeline 回调的客户端上下文

#### PipelineCacheOp

```cpp
enum class PipelineCacheOp {
    kAddingPipeline,   // 添加新 Pipeline
    kPipelineFound,    // 找到已有 Pipeline
};
```

#### fPipelineCachingCallback

```cpp
using PipelineCachingCallback = void (*)(PipelineCallbackContext context,
                                         PipelineCacheOp op,
                                         const std::string& label,
                                         uint32_t uniqueKeyHash,
                                         bool fromPrecompile,
                                         sk_sp<SkData> pipelineData);
PipelineCachingCallback fPipelineCachingCallback = nullptr;
```

- **功能**: Pipeline 缓存事件的通用回调
- **调用时机**:
  - `kAddingPipeline`: 新 Pipeline 添加到缓存时
  - `kPipelineFound`: 缓存命中时
- **参数**:
  - `label`: 人类可读的 Pipeline 描述
  - `uniqueKeyHash`: 32位哈希码(避免重复计算)
  - `fromPrecompile`: 是否来自预编译
  - `pipelineData`: 可序列化的 Pipeline 数据(仅 kAddingPipeline 且可序列化时提供)
- **用途**:
  - 统计 Pipeline 使用频率
  - 识别未使用的预编译 Pipeline
  - 持久化 Pipeline 数据

#### fPipelineCallback (已弃用)

```cpp
using PipelineCallback = void (*)(PipelineCallbackContext context, sk_sp<SkData> pipelineData);
PipelineCallback fPipelineCallback = nullptr;
```

- **功能**: 旧版 Pipeline 回调,仅在添加可序列化 Pipeline 时调用
- **弃用**: 如果设置了 `fPipelineCachingCallback`,该回调被忽略
- **迁移**: 新代码应使用 `fPipelineCachingCallback`

### Runtime Effects

#### fUserDefinedKnownRuntimeEffects

```cpp
SkSpan<sk_sp<SkRuntimeEffect>> fUserDefinedKnownRuntimeEffects;
```

- **用途**: 注册用户定义的已知 Runtime Effects
- **效果**:
  - 这些 Runtime Effects 获得稳定的 key
  - 可用于序列化的 Pipeline key
  - Context 持有引用直至销毁
- **警告**: 修改此列表(增删改序)需要清除序列化的 Pipeline 缓存

### 持久化 Pipeline 存储

#### fPersistentPipelineStorage

```cpp
PersistentPipelineStorage* fPersistentPipelineStorage = nullptr;
```

- **用途**: 跨 Context 生命周期持久化 Pipeline 数据
- **生命周期**: 客户端确保在 Context 生命周期内有效
- **性能**: 显著减少应用启动时的着色器编译时间

### 实验性功能

#### fEnableCapture

```cpp
bool fEnableCapture = false;
```

- **状态**: 实验性,行为和性能可能变化
- **用途**: 启用 startCapture 和 endCapture API
- **功能**: 捕获从 Context 派生的 Recorder 的所有绘制调用和 Surface 创建

### 内部测试选项

#### fOptionsPriv

```cpp
ContextOptionsPriv* fOptionsPriv = nullptr;
```

- **用途**: 仅用于 Skia 内部工具的测试选项
- **可见性**: 内部实现细节,不应在生产代码中使用

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `include/core/SkRefCnt.h` | 引用计数类型 |
| `include/core/SkSize.h` | SkISize 定义 |
| `include/core/SkSpan.h` | SkSpan 容器 |
| `include/gpu/graphite/GraphiteTypes.h` | SampleCount 等类型 |
| `include/private/base/SkAPI.h` | SK_API 宏 |
| `SkExecutor` | 线程池抽象 |
| `SkRuntimeEffect` | Runtime Effect 定义 |
| `skgpu::ShaderErrorHandler` | 着色器错误处理 |
| `PersistentPipelineStorage` | Pipeline 持久化接口 |

### 被依赖的模块

- `Context`: 创建时接受 ContextOptions 参数
- `ContextFactory`: MakeMetal, MakeDawn 等工厂函数
- 平台特定的 Context 实现

## 设计模式与设计决策

### 结构体配置模式

使用结构体而非构造函数参数:
- 易于扩展新选项而不破坏 ABI
- 支持默认值
- 命名参数语义(通过聚合初始化)

### 平台特定默认值

使用预处理器宏为不同平台提供不同默认值:
```cpp
#if defined(SK_BUILD_FOR_ANDROID)
    float fGlyphsAsPathsFontSize = 384;
#elif defined(SK_BUILD_FOR_MAC)
    float fGlyphsAsPathsFontSize = 256;
#else
    float fGlyphsAsPathsFontSize = 324;
#endif
```
- 根据平台特性优化
- 简化跨平台使用

### 回调指针模式

使用函数指针回调而非虚函数接口:
- 轻量级,无虚函数表开销
- 支持 lambda 和自由函数
- 易于与 C API 集成

### 可选值使用

使用 `std::optional` 表示可选配置:
```cpp
std::optional<SkISize> fInternalMSAATileSize = std::nullopt;
```
- 明确区分"未设置"和"设置为某值"
- 类型安全

## 性能考量

### 多线程 Pipeline 编译

```cpp
options.fExecutor = myThreadPool;
```
- **影响**: 可将着色器编译时间减少 50%-80%
- **代价**: 额外的线程开销和同步
- **建议**: 生产环境强烈推荐启用

### MSAA 配置权衡

| 配置 | 质量 | 性能 | 内存 |
|------|------|------|------|
| k1 (无 MSAA) | 低 | 最快 | 最小 |
| k4 | 中 | 中等 | 中等 |
| k8 | 高 | 慢 | 大 |
| k16 | 最高 | 最慢 | 最大 |

### 资源预算调整

```cpp
// 内存受限设备
options.fGpuBudgetInBytes = 128 * (1 << 20);  // 128 MB

// 桌面应用
options.fGpuBudgetInBytes = 512 * (1 << 20);  // 512 MB
```

### Pipeline 缓存的收益

启用持久化缓存后:
- **首次启动**: 无改善(需要编译)
- **后续启动**: 减少 80%-95% 的着色器编译时间
- **磁盘开销**: 通常 1-5 MB

## 使用示例

### 基础配置

```cpp
ContextOptions options;
options.fGpuBudgetInBytes = 256 * (1 << 20);
options.fInternalMultisampleCount = SampleCount::k4;
auto context = ContextFactory::MakeMetal(backendContext, options);
```

### 启用 Pipeline 持久化

```cpp
FilePipelineStorage storage("/path/to/cache.bin");
ContextOptions options;
options.fPersistentPipelineStorage = &storage;
auto context = ContextFactory::MakeMetal(backendContext, options);
```

### Pipeline 统计回调

```cpp
std::map<uint32_t, int> pipelineUsage;

options.fPipelineCachingCallback = [](void* ctx, PipelineCacheOp op,
                                      const std::string& label,
                                      uint32_t hash, bool fromPrecompile,
                                      sk_sp<SkData> data) {
    auto* usage = static_cast<std::map<uint32_t, int>*>(ctx);
    if (op == PipelineCacheOp::kPipelineFound) {
        (*usage)[hash]++;
    }
};
options.fPipelineCallbackContext = &pipelineUsage;
```

### 多线程编译

```cpp
SkTaskExecutor executor(4);  // 4 worker threads
ContextOptions options;
options.fExecutor = &executor;
auto context = ContextFactory::MakeMetal(backendContext, options);
```

### 注册 Runtime Effects

```cpp
std::vector<sk_sp<SkRuntimeEffect>> effects = {
    SkRuntimeEffect::MakeForShader(shaderSrc1),
    SkRuntimeEffect::MakeForShader(shaderSrc2),
};
ContextOptions options;
options.fUserDefinedKnownRuntimeEffects = SkSpan(effects);
auto context = ContextFactory::MakeMetal(backendContext, options);
```

## 平台相关说明

### Android

- `fGlyphsAsPathsFontSize` 默认 384
- 通常需要更保守的内存预算
- 考虑低端设备的 MSAA 设置

### macOS/iOS

- `fGlyphsAsPathsFontSize` 默认 256
- Metal 后端性能优秀,可使用更高 MSAA
- Pipeline 缓存路径需要遵守沙盒限制

### Desktop (Windows/Linux)

- `fGlyphsAsPathsFontSize` 默认 324
- 通常有更充裕的内存和 GPU 资源
- 考虑多显卡场景的兼容性

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/gpu/graphite/Context.h` | Context 创建使用 ContextOptions |
| `include/gpu/graphite/GraphiteTypes.h` | SampleCount 等类型定义 |
| `include/gpu/graphite/PersistentPipelineStorage.h` | Pipeline 持久化接口 |
| `include/core/SkExecutor.h` | 线程池接口 |
| `include/core/SkRuntimeEffect.h` | Runtime Effect 定义 |
| `include/utils/SkShaderErrorHandler.h` | 着色器错误处理 |
