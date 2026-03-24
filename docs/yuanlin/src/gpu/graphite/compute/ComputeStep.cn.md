# ComputeStep

> 源文件: src/gpu/graphite/compute/ComputeStep.h, src/gpu/graphite/compute/ComputeStep.cpp

## 概述

`ComputeStep` 是 Skia Graphite 架构中表示计算着色器执行步骤的抽象基类。该类定义了计算通道的配置接口，包括工作组大小、资源绑定、着色器代码生成等。`ComputeStep` 被 `DispatchGroup` 使用，用于组织和执行 GPU 计算任务，特别用于 Vello 矢量渲染管线。

## 架构位置

```
Graphite 计算系统：
  ├── ComputeStep（计算步骤抽象）★
  ├── DispatchGroup（调度组）
  ├── VelloComputeSteps（Vello 步骤实现）
  └── ComputePipeline（计算管线）
```

## 主要类与结构体

### ComputeStep 抽象类

```cpp
class ComputeStep {
public:
    virtual ~ComputeStep() = default;

    // 工作组配置
    virtual WorkgroupSize calculateGlobalDispatchSize() const = 0;
    virtual WorkgroupSize localDispatchSize() const = 0;

    // 资源绑定
    virtual std::string computeSkSL() const = 0;
    virtual void prepareResources(ResourceProvider*,
                                  const RuntimeEffectDictionary*,
                                  ComputeResourceBindings*) const = 0;

    // 元数据
    virtual const char* name() const = 0;
    virtual size_t calculateBufferSize(const DrawParams&) const { return 0; }

protected:
    ComputeStep() = default;
};
```

## 公共 API 函数

### calculateGlobalDispatchSize

```cpp
virtual WorkgroupSize calculateGlobalDispatchSize() const = 0;
```

计算全局调度尺寸（工作组数量 × 工作组大小）。

### localDispatchSize

```cpp
virtual WorkgroupSize localDispatchSize() const = 0;
```

返回单个工作组的线程数（如 {256, 1, 1}）。

### computeSkSL

```cpp
virtual std::string computeSkSL() const = 0;
```

生成计算着色器的 SkSL 代码。

### prepareResources

```cpp
virtual void prepareResources(ResourceProvider*,
                              const RuntimeEffectDictionary*,
                              ComputeResourceBindings*) const = 0;
```

准备计算步骤需要的 GPU 资源（缓冲区、纹理等）。

### name

```cpp
virtual const char* name() const = 0;
```

返回步骤名称（用于调试和性能追踪）。

### calculateBufferSize

```cpp
virtual size_t calculateBufferSize(const DrawParams&) const;
```

计算步骤所需的缓冲区大小（可选实现）。

## 内部实现细节

### WorkgroupSize 结构

```cpp
struct WorkgroupSize {
    uint32_t x, y, z;
};
```

### 全局 vs 局部调度

- **局部**: 单个工作组的线程数（如 256）
- **全局**: 总线程数 = 工作组数 × 局部大小

### 资源绑定流程

1. `prepareResources()` 创建缓冲区和纹理
2. 资源绑定到计算管线
3. 着色器通过绑定索引访问资源

## 依赖关系

### 内部依赖

| 依赖类 | 用途 |
|--------|------|
| `ResourceProvider` | 资源创建 |
| `ComputeResourceBindings` | 资源绑定管理 |
| `RuntimeEffectDictionary` | 运行时效果 |

### 被依赖情况

| 依赖者 | 用途 |
|--------|------|
| `DispatchGroup` | 执行计算步骤 |
| `VelloComputeSteps` | Vello 渲染步骤实现 |

## 设计模式与设计决策

### 模板方法模式

基类定义执行流程，子类实现具体步骤。

### 策略模式

不同的 `ComputeStep` 实现不同的计算策略。

### 关键设计决策

1. **抽象基类**: 允许多种计算步骤实现
2. **虚函数接口**: 灵活的步骤定义
3. **资源准备分离**: 资源创建与执行分离
4. **工作组配置**: 灵活的并行化策略

## 性能考量

### 工作组优化

- 局部大小应为 warp/wavefront 的倍数（通常32或64）
- 全局大小应充分利用 GPU 核心

### 资源管理

- 避免每帧重新分配缓冲区
- 复用跨步骤的资源

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `src/gpu/graphite/compute/DispatchGroup.h` | 调度组 |
| `src/gpu/graphite/compute/VelloComputeSteps.h` | Vello 步骤实现 |
| `src/gpu/graphite/ComputePipeline.h` | 计算管线 |
| `src/gpu/graphite/ResourceProvider.h` | 资源创建 |
