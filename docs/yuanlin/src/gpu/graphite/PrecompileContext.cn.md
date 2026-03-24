# PrecompileContext

> 源文件
> - include/gpu/graphite/PrecompileContext.h
> - src/gpu/graphite/PrecompileContext.cpp

## 概述

`PrecompileContext` 是 Skia Graphite 渲染系统中专门用于后台着色器预编译的辅助上下文对象。它允许应用在非渲染线程上提前编译图形管线（Graphics Pipeline），减少运行时首次渲染时的卡顿（shader jank）。

预编译是现代图形应用优化的重要技术，特别是在移动设备和桌面应用中：
- 避免首次绘制时的长时间编译等待
- 利用多核并行编译
- 支持持久化管线缓存（Pipeline Cache）
- 提供管线使用统计和缓存命中率分析

`PrecompileContext` 是轻量级对象，可以从主 `Context` 创建后移动到工作线程使用。

## 架构位置

`PrecompileContext` 位于 Graphite 的资源管理层：

- **上层**：被应用的后台线程使用，执行预编译任务
- **同层**：与 `Context` 共享 `SharedContext`，但拥有独立的 `ResourceProvider`
- **下层**：调用 `ResourceProvider` 创建管线，访问 `GlobalCache` 管理缓存
- **所属模块**：`gpu/graphite` - 渲染优化支持

该对象是线程局部的（通过 `SingleOwner` 保护），但可以在不同线程间转移所有权。

## 主要类与结构体

### PrecompileContext 类

**继承关系**：
- 无继承，独立实现
- 不可复制、不可移动（通过友元控制创建）

**关键成员变量**：
| 成员变量 | 类型 | 用途 |
|---------|------|------|
| `fSingleOwner` | `mutable SingleOwner` | 线程安全守护，确保单线程访问 |
| `fSharedContext` | `sk_sp<SharedContext>` | 共享的后端上下文 |
| `fResourceProvider` | `std::unique_ptr<ResourceProvider>` | 独立的资源提供者（零预算） |

### StatOptions 枚举

定义统计报告的选项：
```cpp
enum class StatOptions {
    kPrecompile,     // 预编译管线统计（使用率、命中率）
    kPipelineCache,  // 管线缓存统计（缓存大小、驱逐率）
};
```

## 公共 API 函数

### 资源清理

```cpp
void purgePipelinesNotUsedInMs(std::chrono::milliseconds msNotUsed)
```

**功能**：清理指定时间内未使用的管线，无视缓存预算限制。

**参数**：
- `msNotUsed`：时间阈值，超过此时间未使用的管线将被清除

**实现**：
```cpp
auto purgeTime = skgpu::StdSteadyClock::now() - msNotUsed;
fSharedContext->globalCache()->purgePipelinesNotUsedSince(purgeTime);
```

**使用场景**：
- 应用切换到后台时释放资源
- 场景切换后清理旧资源
- 内存压力下主动回收

### 统计报告

```cpp
void reportPipelineStats(StatOptions option = StatOptions::kPrecompile)
```

**功能**：发送管线使用统计到直方图系统（`SK_HISTOGRAM*` 宏）。

**统计类型**：

#### kPrecompile 统计
- **Skia.Graphite.Precompile.NormalPreemptedByPrecompile**：被预编译抢占的常规编译次数
- **Skia.Graphite.Precompile.UnpreemptedPrecompilePipelines**：未被抢占的预编译管线数
- **Skia.Graphite.Precompile.UnusedPrecompiledPipelines**：未被使用的预编译管线数

#### kPipelineCache 统计
- **Skia.Graphite.PipelineCache.PipelineUsesInEpoch**：每个 epoch 中管线的使用次数

**使用场景**：
- 性能分析和优化
- 监控预编译效果
- 调整预编译策略

### 管线预编译

```cpp
bool precompile(sk_sp<SkData> serializedPipelineKey)
```

**功能**：编译单个序列化的管线描述符。

**参数**：
- `serializedPipelineKey`：序列化的管线键（通过 `ContextOptions::PipelineCallback` 获取）

**返回值**：
- `true`：管线创建成功
- `false`：解析失败或编译失败

**实现流程**（当 `SK_ENABLE_PRECOMPILE` 定义时）：
1. 创建 `RuntimeEffectDictionary`
2. 反序列化管线描述符：
   - `GraphicsPipelineDesc`：渲染步骤、着色器配置
   - `RenderPassDesc`：渲染通道配置
3. 创建管线句柄：
   ```cpp
   GraphicsPipelineHandle handle = fResourceProvider->createGraphicsPipelineHandle(
       pipelineDesc, renderPassDesc, PipelineCreationFlags::kForPrecompilation);
   ```
4. 提交异步编译任务：
   ```cpp
   fResourceProvider->startPipelineCreationTask(rtEffectDict, handle);
   ```

**注意**：未定义 `SK_ENABLE_PRECOMPILE` 时直接返回 false。

### 管线标签查询

```cpp
std::string getPipelineLabel(sk_sp<SkData> serializedPipelineKey)
```

**功能**：将序列化的管线键转换为人类可读的标签（用于调试）。

**返回值**：
- 成功：描述性字符串（如 "DrawAtlas-Solid-Premul"）
- 失败：空字符串 ""

**实现**：
1. 反序列化管线描述符
2. 查找对应的 `RenderStep`
3. 调用 `GetPipelineLabel` 生成标签

## 内部实现细节

### 构造函数

```cpp
PrecompileContext::PrecompileContext(sk_sp<SharedContext> sharedContext)
    : fSharedContext(sharedContext)
```

**关键点**：
- 友元访问：仅 `Context` 可调用
- 创建独立的 `ResourceProvider`（零预算）：
  ```cpp
  static constexpr size_t kEmptyBudget = 0;
  fResourceProvider = fSharedContext->makeResourceProvider(
      &fSingleOwner, SK_InvalidGenID, kEmptyBudget);
  ```
- 零预算确保不与主 Context 竞争内存

### 析构函数

```cpp
PrecompileContext::~PrecompileContext() {
    ASSERT_SINGLE_OWNER
}
```
仅验证单线程访问，资源由成员自动释放。

### 管线序列化格式

序列化键包含：
- **GraphicsPipelineDesc**：
  - `renderStepID`：渲染步骤标识
  - `paintParamsID`：绘制参数标识
- **RenderPassDesc**：
  - 颜色附件格式
  - 深度模板格式
  - 样本数

通过 `DataToPipelineDesc` 函数解析二进制数据。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `SharedContext` | 共享的后端配置和全局缓存 |
| `ResourceProvider` | 创建 GPU 资源和管线 |
| `GlobalCache` | 全局管线缓存管理 |
| `GraphicsPipelineDesc` | 管线描述符 |
| `RenderPassDesc` | 渲染通道描述符 |
| `RendererProvider` | 查找渲染步骤实现 |
| `RuntimeEffectDictionary` | 运行时效果字典 |
| `SerializationUtils` | 序列化工具 |

### 被依赖的模块

- **Context**：通过 `makePrecompileContext()` 创建
- **应用后台线程**：执行预编译任务
- **构建系统**：收集管线键用于预编译

## 设计模式与设计决策

### 独立资源提供者

每个 `PrecompileContext` 拥有独立的 `ResourceProvider`：
- 零预算：不与主 Context 竞争内存
- 独立生命周期：可在不同线程上销毁
- 避免资源共享冲突

### 线程局部性

使用 `SingleOwner` 确保单线程访问：
- 简化并发控制
- 避免锁竞争
- 可在线程间转移所有权

### 条件编译支持

通过 `SK_ENABLE_PRECOMPILE` 宏控制：
- 减少非启用平台的代码体积
- 避免未使用的依赖
- 灵活适配不同构建配置

### 异步编译模型

管线编译是异步的：
- `startPipelineCreationTask` 提交任务到后台线程
- 避免阻塞调用线程
- 支持多核并行编译

## 性能考量

### 预编译时机

理想的预编译时机：
- **应用启动时**：后台线程预编译常用管线
- **场景加载时**：根据场景类型预编译相关管线
- **空闲时**：利用空闲 CPU 时间预编译

### 预编译策略

**激进策略**：
- 预编译所有可能的管线组合
- 优点：覆盖率高
- 缺点：编译时间长、内存占用大

**保守策略**：
- 仅预编译高频使用的管线
- 优点：开销小、效率高
- 缺点：可能遗漏低频管线

**自适应策略**（推荐）：
- 运行时收集管线使用数据
- 持久化高频管线键
- 下次启动时预编译

### 统计驱动优化

通过 `reportPipelineStats` 收集数据：
- 计算预编译命中率
- 识别未使用的预编译
- 优化预编译列表

### 内存管理

- 零预算避免内存膨胀
- 已编译管线存储在 `GlobalCache`（与主 Context 共享）
- 通过 `purgePipelinesNotUsedInMs` 主动清理

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/gpu/graphite/Context.h` | 主 Context 定义（创建 PrecompileContext） |
| `include/gpu/graphite/ContextOptions.h` | 定义管线回调接口 |
| `src/gpu/graphite/SharedContext.h` | 共享上下文实现 |
| `src/gpu/graphite/ResourceProvider.h` | 资源提供者 |
| `src/gpu/graphite/GlobalCache.h` | 全局管线缓存 |
| `src/gpu/graphite/GraphicsPipelineDesc.h` | 管线描述符 |
| `src/gpu/graphite/SerializationUtils.h` | 序列化工具 |
| `src/gpu/graphite/ContextUtils.h` | 管线标签生成 |
