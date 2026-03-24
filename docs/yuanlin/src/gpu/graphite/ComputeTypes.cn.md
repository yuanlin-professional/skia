# ComputeTypes - Graphite 计算管线类型定义

> 源文件: `src/gpu/graphite/ComputeTypes.h`

## 概述

`ComputeTypes.h` 定义了 Skia Graphite 计算管线（Compute Pipeline）所需的基础类型和常量。该文件包含计算着色器的工作组大小定义、间接分派参数结构、以及数据流槽位限制等关键常量。这些类型是 Graphite 计算子系统的类型基础。

## 架构位置

```
Graphite 计算子系统
  ├── ComputeTypes.h (本文件 - 基础类型定义)
  ├── ComputeStep.h (计算步骤抽象)
  ├── ComputePipelineDesc.h (管线描述符)
  ├── DispatchGroup.h (调度组)
  └── 后端实现 (Vulkan/Metal/Dawn Compute Pipeline)
```

`ComputeTypes.h` 处于计算子系统的最底层，被所有计算相关组件引用。

## 主要类与结构体

### `WorkgroupSize`

定义计算着色器工作组的三维大小：

```cpp
struct WorkgroupSize {
    uint32_t fWidth = 1;
    uint32_t fHeight = 1;
    uint32_t fDepth = 1;
};
```

- 默认构造为 (1, 1, 1)，即单线程工作组
- `scalarSize()` 返回总线程数（三维乘积）
- 既用于表示全局大小（工作组数量），也用于表示本地大小（工作组内线程数）

### `IndirectDispatchArgs`

间接分派参数结构，与 GPU API 的间接分派缓冲区布局对齐：

```cpp
struct IndirectDispatchArgs {
    uint32_t global_size_x;
    uint32_t global_size_y;
    uint32_t global_size_z;
};
```

## 公共 API 函数

| 成员/常量 | 类型 | 说明 |
|-----------|------|------|
| `WorkgroupSize()` | 构造函数 | 默认 (1,1,1) 或指定三维大小 |
| `WorkgroupSize::scalarSize()` | `uint32_t` | 返回工作组总线程数 (W * H * D) |
| `kMaxComputeDataFlowSlots` | `int` (28) | DispatchGroup 中 ComputeStep 的最大共享资源绑定槽数 |
| `kIndirectDispatchArgumentSize` | `size_t` | 间接分派参数结构的字节大小 |

## 内部实现细节

### 工作组模型

文件注释详细描述了 GPU 计算的层次执行模型：

1. **全局大小（Global Size / Work Group Count）**: 定义问题空间中工作组的数量，三维结构
2. **本地大小（Local Size）**: 每个工作组内的并行执行单元数（原始线程数）
3. **子组（Subgroup）**: 固定大小的 SIMD 单元（Vulkan 术语），对应 Metal 的 "SIMD groups"、OpenCL 的 "wavefronts"、CUDA 的 "warps"

### 硬件限制查询

本地大小必须基于硬件能力确定，通过以下 Caps 方法查询：
- `Caps::maxComputeWorkgroupSize()` - 每个维度的最大值
- `Caps::maxComputeInvocationsPerWorkgroup()` - 总调用数上限

### 数据流槽位限制

`kMaxComputeDataFlowSlots = 28` 限制了 DispatchGroup 内 ComputeStep 之间可共享的资源绑定槽位数量。这是一个经验值，平衡了灵活性和资源管理复杂度。

## 依赖关系

- **\<cstddef\>**: `size_t` 类型
- **\<cstdint\>**: `uint32_t` 类型

该文件的依赖非常轻量，仅使用标准库类型，体现了底层类型定义的最小依赖原则。

## 设计模式与设计决策

### 跨 API 抽象

`WorkgroupSize` 和 `IndirectDispatchArgs` 的设计抽象了不同 GPU API（Vulkan、Metal、D3D12）中计算分派的共同概念。结构成员名使用通用术语（如 `global_size_x`），而非特定 API 术语。

### 双重用途类型

`WorkgroupSize` 同时用于表示全局大小和本地大小。这种复用简化了 API 设计，因为两者在数学上具有相同的结构（三维整数向量）。

## 性能考量

- `WorkgroupSize` 为 12 字节值类型，按值传递效率高
- `scalarSize()` 为简单乘法运算，可由编译器内联优化
- `kIndirectDispatchArgumentSize` 使用 `sizeof` 在编译时确定，确保与实际缓冲区布局一致
- `IndirectDispatchArgs` 的布局与 GPU 间接分派缓冲区的内存布局直接对应，避免运行时转换

## 相关文件

- `src/gpu/graphite/compute/ComputeStep.h` - 计算步骤基类（使用 WorkgroupSize）
- `src/gpu/graphite/ComputePipelineDesc.h` - 计算管线描述符
- `src/gpu/graphite/compute/DispatchGroup.h` - 调度组（使用 kMaxComputeDataFlowSlots）
- `src/gpu/graphite/Caps.h` - GPU 能力查询（工作组大小限制）
