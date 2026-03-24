# ComputePipelineDesc - 计算管线描述符

> 源文件: `src/gpu/graphite/ComputePipelineDesc.h`

## 概述

`ComputePipelineDesc` 是 Skia Graphite 中用于描述计算管线（Compute Pipeline）创建所需状态的轻量级类。它封装了一个 `ComputeStep` 指针，作为后端特定计算管线创建的输入描述符。该类的设计极为简洁，仅 38 行源码，体现了单一职责原则。

## 架构位置

```
Graphite 计算管线系统
  ├── ComputeStep (定义计算步骤的抽象)
  │     └── ComputePipelineDesc (本文件 - 管线创建描述符)
  │           └── 后端 ComputePipeline 实现 (Vulkan/Metal/Dawn)
  └── DispatchGroup (调度组，组织多个计算步骤)
```

`ComputePipelineDesc` 是 `ComputeStep`（逻辑描述）与后端 `ComputePipeline`（GPU 对象）之间的桥梁。

## 主要类与结构体

### `ComputePipelineDesc`

计算管线描述符类，持有一个 `const ComputeStep*` 非拥有指针。

关键约束：`ComputeStep` 必须在 `ComputePipelineDesc` 的生命周期内保持有效。

## 公共 API 函数

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `ComputePipelineDesc(const ComputeStep*)` | 构造函数 | 从 ComputeStep 构造描述符 |
| `operator==(const ComputePipelineDesc&)` | `bool` | 基于 ComputeStep 唯一 ID 比较 |
| `computeStep()` | `const ComputeStep*` | 获取关联的 ComputeStep |
| `uniqueID()` | `uint32_t` | 获取唯一标识（委托给 ComputeStep） |

## 内部实现细节

### 相等性比较

两个 `ComputePipelineDesc` 的相等性通过 `ComputeStep::uniqueID()` 判断，而非指针比较。这意味着即使是不同的 `ComputeStep` 对象实例，只要它们代表相同的计算步骤（具有相同的唯一 ID），其描述符也被视为相等。这在管线缓存查找中至关重要。

### 非拥有语义

`ComputePipelineDesc` 使用原始指针而非智能指针，因为它是短生命周期的描述符对象，在管线创建过程中使用后即可丢弃。

## 依赖关系

- **src/gpu/graphite/compute/ComputeStep.h**: ComputeStep 类定义
- **\<cstdint\>**: `uint32_t` 类型

## 设计模式与设计决策

### 描述符模式（Descriptor Pattern）

`ComputePipelineDesc` 遵循 GPU API 常见的描述符模式：将创建 GPU 对象所需的状态打包到一个不可变的描述结构中。与渲染管线描述符（`GraphicsPipelineDesc`）相比，计算管线描述符更简单，因为计算管线不涉及顶点布局、混合状态等复杂配置。

### 最小化设计

该类仅包含创建计算管线所必需的最小信息——一个 `ComputeStep` 引用。所有计算着色器代码、资源绑定布局等信息都由 `ComputeStep` 本身提供。

## 性能考量

- 类大小为单个指针（8 字节），拷贝开销极低
- `uniqueID()` 为常量时间操作，直接读取 ComputeStep 中预计算的 ID
- 相等性比较为单次 `uint32_t` 比较，适合作为管线缓存键
- 构造函数为 `explicit`，防止隐式转换带来的不必要临时对象
- 不涉及堆分配或引用计数操作

### 管线缓存场景

在 `ResourceProvider` 的管线缓存中，`ComputePipelineDesc` 的高效相等性比较是关键性能因素。典型工作流程如下：

1. DispatchGroup 创建 `ComputePipelineDesc`
2. 通过 `uniqueID()` 查询管线缓存
3. 缓存命中则直接复用已编译的管线
4. 缓存未命中则触发管线编译

### 与 GraphicsPipelineDesc 的对比

计算管线描述符远比图形管线描述符简单：
- `ComputePipelineDesc`: 仅 1 个指针（1 个 uniqueID 用于比较）
- `GraphicsPipelineDesc`: 包含 RenderStep ID、PaintParamsKey ID 等多个字段

这种简洁性来源于计算管线不涉及光栅化状态（深度/模板、混合、顶点布局等），所有状态由 `ComputeStep` 内部定义。

## 相关文件

- `src/gpu/graphite/compute/ComputeStep.h` - 计算步骤基类，定义着色器代码和资源绑定
- `src/gpu/graphite/ComputePipeline.h` - 计算管线基类，后端实现的抽象
- `src/gpu/graphite/compute/DispatchGroup.h` - 调度组，组织多个计算步骤的执行
- `src/gpu/graphite/ResourceProvider.h` - 管线缓存与创建，使用 ComputePipelineDesc 作为缓存键
- `src/gpu/graphite/GraphicsPipelineDesc.h` - 图形管线描述符，作为对比参考
