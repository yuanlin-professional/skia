# GrVkVaryingHandler

> 源文件
> - src/gpu/ganesh/vk/GrVkVaryingHandler.h
> - src/gpu/ganesh/vk/GrVkVaryingHandler.cpp

## 概述

`GrVkVaryingHandler` 是 Ganesh Vulkan 后端中用于处理着色器 varying 变量的专用类，负责管理顶点着色器和片段着色器之间传递的插值变量。该类继承自 `GrGLSLVaryingHandler`，并针对 Vulkan 的 location 布局限定符要求进行了特化实现。

主要职责包括：
- 为顶点输入/输出和片段输入/输出变量分配 location 索引
- 确保 varying 变量的 location 分配符合 Vulkan 规范要求
- 计算不同 GLSL 类型占用的 location 数量
- 验证总 location 使用量不超过 Vulkan 的最小保证值（64）

## 架构位置

`GrVkVaryingHandler` 位于 Ganesh 图形管道的 Vulkan 后端着色器编译阶段：

```
Ganesh GPU Backend
└── Vulkan Backend (src/gpu/ganesh/vk/)
    └── Pipeline State Building
        ├── GrVkPipelineStateBuilder (使用 VaryingHandler)
        └── GrVkVaryingHandler (本类)
            └── GrGLSLVaryingHandler (基类)
```

该类在 `GrVkPipelineStateBuilder` 创建管线状态时被实例化，负责处理着色器间的数据传递接口。

## 主要类与结构体

### 类继承关系

```
GrGLSLVaryingHandler (基类)
    └── GrVkVaryingHandler
```

### GrVkVaryingHandler 关键成员

| 成员类型 | 名称 | 说明 |
|---------|------|------|
| 构造函数 | `GrVkVaryingHandler(GrGLSLProgramBuilder*)` | 接受程序构建器指针初始化 |
| 类型别名 | `VarArray` | 从基类继承的变量数组类型 |
| 友元类 | `GrVkPipelineStateBuilder` | 允许管线构建器访问私有成员 |

## 公共 API 函数

### 构造函数

```cpp
GrVkVaryingHandler(GrGLSLProgramBuilder* program)
```

**功能**：初始化 Vulkan varying 处理器
- **参数**：`program` - 指向当前着色器程序构建器的指针
- **继承行为**：直接调用基类构造函数进行初始化

## 内部实现细节

### onFinalize() 实现

```cpp
void GrVkVaryingHandler::onFinalize() override
```

该方法是核心实现，在着色器编译的最终化阶段被调用，负责为所有 varying 变量分配 location：

1. **处理顶点输入变量** (`fVertexInputs`)
2. **处理顶点输出变量** (`fVertexOutputs`)
3. **处理片段输入变量** (`fFragInputs`)
4. **处理片段输出变量** (`fFragOutputs`)

每个变量数组都通过辅助函数 `finalize_helper()` 处理。

### sksltype_to_location_size() 函数

```cpp
static inline int sksltype_to_location_size(SkSLType type)
```

**核心逻辑**：
- 所有标量和向量类型（float/int/bool 及其变体）占用 1 个 location
- 矩阵类型占用多个 location：
  - `float2x2` / `half2x2`：2 个 location
  - `float3x3` / `half3x3`：3 个 location
  - `float4x4` / `half4x4`：4 个 location
- 采样器和特殊类型（texture2D、input 等）：0 个 location
- 深度/模板格式：0 个 location

**设计原则**：假设所有标量值都是 32 位

### finalize_helper() 函数

```cpp
static void finalize_helper(GrVkVaryingHandler::VarArray& vars)
```

**实现步骤**：

1. 初始化 `locationIndex` 为 0
2. 遍历所有变量：
   - 构建 location 限定符字符串（如 `"location = 3"`）
   - 将 location 限定符添加到变量的布局限定符中
   - 计算变量占用的 location 数量：
     ```
     totalLocations = elementSize × numElements
     ```
   - 更新 `locationIndex` 累加器
3. 验证总 location 数 ≤ 64（Vulkan 规范的最小保证）

**关键断言**：
- `elementSize > 0`：确保类型有效
- `numElements > 0`：确保数组大小有效
- `locationIndex <= 64`：符合 Vulkan 规范

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLSLVaryingHandler` | 基类，提供通用 varying 处理框架 |
| `GrShaderVar` | 表示着色器变量 |
| `SkSLType` | 定义着色器语言类型枚举 |
| `SkString` | 用于构建 location 限定符字符串 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| `GrVkPipelineStateBuilder` | 创建管线状态时需要 varying 处理器 |
| Vulkan 着色器编译流程 | 生成符合 Vulkan 规范的 SPIR-V 代码 |

## 设计模式与设计决策

### 1. 模板方法模式

基类 `GrGLSLVaryingHandler` 定义了 varying 处理的框架流程，`GrVkVaryingHandler` 通过重写 `onFinalize()` 实现 Vulkan 特定的 location 分配逻辑。

### 2. 静态辅助函数

`sksltype_to_location_size()` 和 `finalize_helper()` 设计为静态函数，体现了：
- **无状态计算**：纯函数逻辑，便于测试和理解
- **编译时优化**：编译器可以更好地内联优化

### 3. Location 自动分配策略

**设计决策**：顺序分配 location，从 0 开始递增
- **优点**：简单、确定性强、易于调试
- **约束**：依赖 Vulkan 规范的最小保证（64 个 location）
- **扩展性**：如果未来需要支持更多 location，需要添加 capability 查询

### 4. 类型到 Location 的映射

所有向量类型统一占用 1 个 location，矩阵按列占用多个 location，这与 Vulkan/GLSL 规范保持一致：
- 简化了分配逻辑
- 避免了碎片化问题
- 符合 GPU 硬件的对齐要求

## 性能考量

### 1. Location 分配效率

- **时间复杂度**：O(n)，n 为 varying 变量总数
- **空间开销**：仅在编译时产生临时字符串对象
- **优化点**：location 限定符直接添加到现有变量，无需额外存储

### 2. 编译时验证

```cpp
SkASSERT(locationIndex <= 64);
```

在 debug 构建中通过断言提前发现 location 超限问题，避免运行时错误。

### 3. 内存布局

紧凑的 location 分配减少了着色器间数据传递的带宽消耗，对移动 GPU 尤为重要。

### 4. 限制考量

当前实现假设：
- 所有设备至少支持 64 个 input/output location
- 如果超过此限制，程序会在 debug 模式下触发断言
- 生产环境中需要确保着色器设计不超过此限制

**未来改进方向**：
- 添加运行时 capability 查询
- 支持更灵活的 location 分配策略
- 优化矩阵类型的 location 使用

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/glsl/GrGLSLVarying.h` | 基类定义 | 提供平台无关的 varying 处理框架 |
| `src/gpu/ganesh/vk/GrVkPipelineStateBuilder.h` | 使用者 | 在管线构建过程中创建和使用该类 |
| `src/gpu/ganesh/GrShaderVar.h` | 依赖类型 | 表示着色器变量的核心数据结构 |
| `src/core/SkSLTypeShared.h` | 类型定义 | 定义 SkSLType 枚举 |
| `src/gpu/ganesh/vk/GrVkUtil.h` | 同层工具 | 提供其他 Vulkan 相关工具函数 |
| `src/gpu/ganesh/vk/GrVkGpu.h` | 上下文 | Vulkan GPU 接口实现 |
