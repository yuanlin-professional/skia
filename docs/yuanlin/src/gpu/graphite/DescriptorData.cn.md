# DescriptorData — Graphite 描述符数据类型

> 源文件: `src/gpu/graphite/DescriptorData.h`

## 概述

本文件定义了 Skia Graphite GPU 后端中描述符 (descriptor) 系统的核心数据类型。描述符用于将 GPU 资源（如 uniform 缓冲区、纹理、采样器等）绑定到着色器管线的特定阶段。文件包含描述符类型枚举 (`DescriptorType`)、管线阶段标志枚举 (`PipelineStageFlags`) 和描述符数据结构体 (`DescriptorData`)。

## 架构位置

```
Graphite 渲染管线
    └── 描述符集布局 (Descriptor Set Layout)
        └── DescriptorData (本文件 - 描述符条目定义)
            ├── Vulkan: VkDescriptorSetLayoutBinding
            ├── Metal: Argument Buffer 绑定
            └── Dawn/WebGPU: BindGroupLayoutEntry
```

`DescriptorData` 是平台无关的描述符绑定描述，由各后端转换为平台特定的绑定格式。

## 主要类与结构体

### DescriptorType 枚举

描述符类型，对应 GPU 资源绑定点：

| 值 | 描述 |
|----|------|
| `kUniformBuffer` (0) | Uniform 缓冲区（只读着色器常量） |
| `kTextureSampler` | 独立的纹理采样器 |
| `kTexture` | 独立的纹理（不含采样器） |
| `kCombinedTextureSampler` | 组合的纹理+采样器（如 OpenGL 风格） |
| `kStorageBuffer` | 存储缓冲区（可读写） |
| `kInputAttachment` | 输入附件（Vulkan 子通道输入） |

计数常量：`kDescriptorTypeCount = 6`

### PipelineStageFlags 枚举

管线阶段位标志，支持位运算组合：

| 值 | 二进制 | 描述 |
|----|--------|------|
| `kVertexShader` | 0b001 | 顶点着色器阶段 |
| `kFragmentShader` | 0b010 | 片段着色器阶段 |
| `kCompute` | 0b100 | 计算着色器阶段 |

通过 `SK_MAKE_BITMASK_OPS` 宏启用 `|`、`&`、`~` 等位运算操作符。

### DescriptorData 结构体

描述符绑定条目：

| 成员 | 类型 | 描述 |
|------|------|------|
| `fType` | `DescriptorType` | 描述符类型 |
| `fCount` | `uint32_t` | 数组元素数量（用于纹理数组等） |
| `fBindingIndex` | `int` | 绑定点索引 |
| `fPipelineStageFlags` | `SkEnumBitMask<PipelineStageFlags>` | 可见的管线阶段 |
| `fImmutableSampler` | `const Sampler*` | 可选的不可变采样器指针 |

## 公共 API 函数

### DescriptorData 构造函数

```cpp
DescriptorData(DescriptorType type, uint32_t count, int bindingIdx,
                SkEnumBitMask<PipelineStageFlags> stageFlags,
                const Sampler* immutableSampler = nullptr);
```

构造描述符数据条目。`immutableSampler` 默认为 nullptr，仅在需要不可变采样器时（如 YCbCr 转换采样器）指定。

## 内部实现细节

1. **SkEnumBitMask**: `PipelineStageFlags` 使用 `SkEnumBitMask` 模板包装，提供类型安全的位运算。可以组合多个阶段，如 `kVertexShader | kFragmentShader` 表示资源在两个阶段都可见。

2. **不可变采样器**: `fImmutableSampler` 指向预创建的采样器对象。在 Vulkan 中，不可变采样器被嵌入描述符集布局中，用于 YCbCr 采样器转换等场景。指针不拥有所指对象。

3. **描述符数量**: `fCount` 允许单个绑定点关联多个描述符（如纹理数组）。值为 1 表示单个描述符。

4. **Input Attachment**: `kInputAttachment` 类型特定于 Vulkan 子通道模式，允许片段着色器读取同一渲染通道中先前子通道的输出。

## 依赖关系

- **`src/base/SkEnumBitMask.h`**: 类型安全的枚举位掩码模板
- **`<cstdint>`**: `uint8_t`, `uint32_t`

## 设计模式与设计决策

1. **平台无关抽象**: `DescriptorType` 枚举覆盖了所有主流 GPU API 的描述符类型。`kCombinedTextureSampler` 对应 OpenGL/Vulkan 的组合采样器，而 `kTexture` + `kTextureSampler` 分离模式对应 Metal/DirectX 的分离绑定。

2. **位标志管线可见性**: 使用位标志而非枚举允许一个资源同时对多个管线阶段可见，这在 Vulkan 和 Metal 中是常见需求（如共享的 uniform 缓冲区）。

3. **不可变采样器指针**: 使用裸指针而非智能指针，因为 `DescriptorData` 是轻量级描述结构体，采样器的生命周期由外部管理。

4. **类型计数常量**: `kDescriptorTypeCount` 用于静态数组大小或循环上界，确保与枚举值同步更新。

## 性能考量

- 结构体大小约 24 字节（含指针和对齐），适合在数组中存储和传递。
- 枚举使用 `uint8_t` 底层类型，最小化内存占用。
- 描述符布局通常在管线创建时构建一次，然后在渲染期间重复使用，因此构建开销可忽略。
- 不可变采样器嵌入布局避免了每帧绑定采样器的开销。

## 相关文件

- `src/gpu/graphite/vk/VulkanDescriptorSet.h` — Vulkan 描述符集实现
- `src/gpu/graphite/vk/VulkanDescriptorPool.h` — Vulkan 描述符池
- `src/gpu/graphite/GraphicsPipelineDesc.h` — 图形管线描述
- `src/gpu/graphite/Sampler.h` — 采样器基类
- `src/base/SkEnumBitMask.h` — 位掩码工具模板
- `src/gpu/graphite/ResourceProvider.h` — 描述符集创建
