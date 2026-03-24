# GrSPIRVVaryingHandler

> 源文件
> - src/gpu/ganesh/GrSPIRVVaryingHandler.h
> - src/gpu/ganesh/GrSPIRVVaryingHandler.cpp

## 概述

`GrSPIRVVaryingHandler` 是用于处理 SPIR-V 着色器中 varying 变量(顶点着色器输出到片段着色器的插值变量)的处理器。它继承自 `GrGLSLVaryingHandler`,为 SPIR-V 目标提供了简单直接的 varying 管理策略:按照添加顺序为每个 varying 分配连续的 location 索引。该类主要用于 Vulkan 和 Dawn(WebGPU)后端的着色器编译。

## 架构位置

在 Skia GPU 着色器编译流水线中的位置:

```
GrGLSLProgramBuilder
    ├── GrSPIRVVaryingHandler (SPIR-V 变体)
    │   └── 管理 varying 变量的 location 分配
    ├── 顶点着色器构建
    ├── 片段着色器构建
    └── 生成 SPIR-V 代码
```

该类是着色器代码生成器的辅助组件,负责确保 varying 变量在顶点和片段着色器之间正确匹配。

## 主要类与结构体

### 核心类

| 类名 | 继承关系 | 作用 |
|------|---------|------|
| `GrSPIRVVaryingHandler` | `GrGLSLVaryingHandler` | SPIR-V 的 varying 处理器 |

### 关键成员

从基类 `GrGLSLVaryingHandler` 继承的成员:
- `fVertexInputs`: 顶点输入变量数组
- `fVertexOutputs`: 顶点输出变量数组
- `fFragInputs`: 片段输入变量数组
- `fFragOutputs`: 片段输出变量数组

## 公共 API 函数

### 构造函数

```cpp
GrSPIRVVaryingHandler(GrGLSLProgramBuilder* program);
```

简单地调用基类构造函数,不需要额外的初始化。

### 类型定义

```cpp
typedef GrGLSLVaryingHandler::VarArray VarArray;
```

为基类的 `VarArray` 类型提供便捷别名。

## 内部实现细节

### 核心算法

唯一的实现函数是 `onFinalize`,在所有 varying 添加完成后调用:

```cpp
void GrSPIRVVaryingHandler::onFinalize() {
    finalize_helper(fVertexInputs);
    finalize_helper(fVertexOutputs);
    finalize_helper(fFragInputs);
    finalize_helper(fFragOutputs);
}
```

### Location 分配逻辑

`finalize_helper` 函数实现了 location 分配:

```cpp
static void finalize_helper(GrSPIRVVaryingHandler::VarArray& vars) {
    int locationIndex = 0;
    for (GrShaderVar& var : vars.items()) {
        SkString location;
        location.appendf("location = %d", locationIndex);
        var.addLayoutQualifier(location.c_str());

        int elementSize = sksltype_to_location_size(var.getType());
        SkASSERT(elementSize > 0);
        int numElements = var.isArray() ? var.getArrayCount() : 1;
        SkASSERT(numElements > 0);
        locationIndex += elementSize * numElements;
    }
}
```

**步骤**:
1. 从 location 0 开始
2. 遍历所有变量
3. 为每个变量添加 `layout(location = N)` 限定符
4. 根据变量类型和数组大小累加 location 索引

### Location 大小计算

```cpp
static inline int sksltype_to_location_size(SkSLType type)
```

该函数将 SkSL 类型映射到占用的 location 数量:

| 类型类别 | Location 数量 | 示例 |
|---------|--------------|------|
| 标量和向量 | 1 | `float`, `vec2`, `vec3`, `vec4` |
| 矩阵 2x2 | 2 | `mat2` |
| 矩阵 3x3 | 3 | `mat3` |
| 矩阵 4x4 | 4 | `mat4` |
| 采样器 | 0 | `sampler2D` (不能作为 varying) |

**关键特性**:
- 所有标量值假定为 32 位
- 向量类型(vec2/vec3/vec4)占用 1 个 location
- 矩阵按列数分配 location
- Half 类型和 Float 类型被同等对待

### 数组处理

对于数组类型的 varying:
```cpp
int numElements = var.isArray() ? var.getArrayCount() : 1;
locationIndex += elementSize * numElements;
```

数组的每个元素都占用相应数量的 location。例如:
- `vec4 colors[3]` 占用 3 个 location
- `mat4 transforms[2]` 占用 8 个 location (4 × 2)

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖原因 |
|---------|---------|
| `GrGLSLVaryingHandler` | 基类,提供基础框架 |
| `GrGLSLProgramBuilder` | 程序构建器,提供上下文 |
| `GrShaderVar` | 着色器变量表示 |
| `SkSLType` | 类型系统 |

### 被依赖的模块

| 模块名称 | 使用方式 |
|---------|---------|
| `GrVkPipelineStateBuilder` | Vulkan 管线构建时使用 |
| `GrDawnProgramBuilder` | Dawn/WebGPU 程序构建时使用 |

## 设计模式与设计决策

### 设计模式

1. **策略模式**:
   - `GrGLSLVaryingHandler` 定义抽象接口
   - `GrSPIRVVaryingHandler` 提供 SPIR-V 特定实现
   - 不同后端可以有不同的实现

2. **模板方法模式**:
   - 基类定义流程框架
   - 子类实现 `onFinalize` 钩子方法

3. **辅助函数模式**:
   - 使用静态 helper 函数处理重复逻辑
   - 保持类接口简洁

### 关键设计决策

**为何采用简单的连续分配策略**:
- SPIR-V 规范要求显式指定 location
- 连续分配最简单,易于理解和维护
- 对于大多数着色器来说,location 数量足够

**为何不进行优化或压缩**:
- SPIR-V 编译器和驱动会进行优化
- 过早优化增加复杂性
- 简单策略减少 bug 风险

**为何分离类型到 location 的映射**:
- 便于支持新类型
- 集中管理类型规则
- 便于调试和验证

**为何支持数组**:
- 着色器中常用数组传递多个值
- 按元素累加 location 符合 SPIR-V 规范
- 自动计算避免手动管理

## 性能考量

### Location 限制

SPIR-V 和 Vulkan 规范:
- 顶点输入最少支持 16 个 location
- 顶点输出/片段输入最少支持 64 个 location
- 片段输出最少支持 8 个 location

代码中的 TODO 注释:
```cpp
// TODO: determine the layout limits for SPIR-V, and enforce them via asserts here.
```

表明未来可能添加限制检查。

### 时间复杂度

- `onFinalize`: O(n),n 为 varying 数量
- `sksltype_to_location_size`: O(1),简单的 switch 语句

### 空间效率

- 不使用任何额外的数据结构
- Location 分配是现场计算的
- 只修改现有的 `GrShaderVar` 对象

### 优化机会

**Location 压缩**:
理论上可以将多个小变量打包到一个 location,但:
- 增加复杂度
- 编译器可能已经优化
- 收益有限

**分离标量和向量**:
可以按类型分组分配,但:
- 破坏了变量的原始顺序
- 可能影响调试
- 不是性能瓶颈

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/glsl/GrGLSLVarying.h` | 基类 | Varying 处理的抽象接口 |
| `src/gpu/ganesh/GrShaderVar.h` | 使用 | 着色器变量表示 |
| `src/core/SkSLTypeShared.h` | 使用 | SkSL 类型定义 |
| `src/gpu/ganesh/vk/GrVkPipelineStateBuilder.cpp` | 使用者 | Vulkan 后端 |
| `src/gpu/ganesh/dawn/GrDawnProgramBuilder.cpp` | 使用者 | Dawn 后端 |
| `src/gpu/ganesh/GrSPIRVUniformHandler.h` | 姊妹类 | 处理 uniform 变量 |
