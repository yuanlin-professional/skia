# DispatchGroup

> 源文件: src/gpu/graphite/compute/DispatchGroup.h, src/gpu/graphite/compute/DispatchGroup.cpp

## 概述

`DispatchGroup` 是 Skia Graphite 架构中组织和执行计算着色器调度的类。该类管理一组 `ComputeStep` 的执行序列，处理资源依赖、管线创建和 GPU 命令记录。`DispatchGroup` 被用于 Vello 矢量渲染管线，将复杂的计算任务分解为多个有序的计算步骤。

## 架构位置

```
Graphite 计算调度：
  ├── DispatchGroup（调度组）★
  ├── ComputeStep（计算步骤）
  ├── ComputePipeline（计算管线）
  └── CommandBuffer（命令缓冲区）
```

## 主要类与结构体

### DispatchGroup 类

```cpp
class DispatchGroup {
public:
    class Builder {
    public:
        Builder(Recorder* recorder);
        Builder& appendStep(const ComputeStep* step, SkSpan<const BufferView> resources);
        std::unique_ptr<DispatchGroup> finalize();
    };

    void prepareResources(ResourceProvider*);
    void addCommands(CommandBuffer*);

private:
    struct Step {
        const ComputeStep* fStep;
        sk_sp<ComputePipeline> fPipeline;
        std::vector<BufferView> fResources;
    };

    std::vector<Step> fSteps;
};
```

## 公共 API 函数

### Builder::appendStep

```cpp
Builder& appendStep(const ComputeStep* step, SkSpan<const BufferView> resources);
```

向调度组添加计算步骤和资源绑定。

### Builder::finalize

```cpp
std::unique_ptr<DispatchGroup> finalize();
```

完成构建并创建调度组实例。

### prepareResources

```cpp
void prepareResources(ResourceProvider* resourceProvider);
```

为所有步骤准备 GPU 资源和创建计算管线。

### addCommands

```cpp
void addCommands(CommandBuffer* commandBuffer);
```

将所有计算调度命令记录到命令缓冲区。

## 内部实现细节

### 构建器模式

使用 `Builder` 逐步添加计算步骤：
```cpp
DispatchGroup::Builder builder(recorder);
builder.appendStep(step1, resources1);
builder.appendStep(step2, resources2);
auto group = builder.finalize();
```

### 资源准备流程

1. 为每个步骤调用 `prepareResources()`
2. 创建或查找计算管线
3. 绑定资源到管线

### 命令记录流程

```cpp
void DispatchGroup::addCommands(CommandBuffer* commandBuffer) {
    for (const Step& step : fSteps) {
        commandBuffer->bindComputePipeline(step.fPipeline);
        commandBuffer->bindResources(step.fResources);
        commandBuffer->dispatch(step.fStep->calculateGlobalDispatchSize());
    }
}
```

## 依赖关系

### 内部依赖

| 依赖类 | 用途 |
|--------|------|
| `ComputeStep` | 计算步骤定义 |
| `ComputePipeline` | 计算管线 |
| `ResourceProvider` | 资源创建 |
| `CommandBuffer` | 命令记录 |
| `Recorder` | 录制器 |

### 被依赖情况

| 依赖者 | 用途 |
|--------|------|
| `VelloRenderer` | Vello 渲染管线 |
| `Device` | 计算任务执行 |

## 设计模式与设计决策

### 构建器模式

使用 `Builder` 提供流畅的 API 构建调度组。

### 命令模式

`DispatchGroup` 封装计算命令序列，延迟执行。

### 关键设计决策

1. **步骤序列化**: 按添加顺序执行步骤
2. **资源绑定**: 每个步骤独立的资源绑定
3. **管线缓存**: 复用已创建的计算管线
4. **延迟执行**: 构建时不执行，记录时才提交命令

## 性能考量

### 管线复用

相同配置的步骤复用计算管线，减少管线创建开销。

### 资源管理

- 步骤间共享缓冲区，减少内存使用
- 批量准备资源，减少同步点

### 命令批处理

多个调度命令合并到单个命令缓冲区，减少提交开销。

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `src/gpu/graphite/compute/ComputeStep.h` | 计算步骤抽象 |
| `src/gpu/graphite/ComputePipeline.h` | 计算管线 |
| `src/gpu/graphite/CommandBuffer.h` | 命令缓冲区 |
| `src/gpu/graphite/compute/VelloRenderer.h` | Vello 渲染器 |
