# GrFPArgs

> 源文件: [src/gpu/ganesh/GrFPArgs.h](../../../../src/gpu/ganesh/GrFPArgs.h)

## 概述

`GrFPArgs` 是 Skia Ganesh GPU 后端中的一个参数聚合结构体，用于在创建 Fragment Processor（片段处理器）时传递上下文信息。Fragment Processor 是 Ganesh 着色管线中的核心概念，负责在 GPU 上执行像素级的颜色计算。`GrFPArgs` 将构建 Fragment Processor 所需的绘制上下文信息（表面绘制上下文、目标颜色信息、表面属性和作用域）打包在一起，简化了函数参数传递。

## 架构位置

`GrFPArgs` 位于 Ganesh 着色管线的 Fragment Processor 创建阶段：

```
SkShader / SkColorFilter / SkBlender (Skia 公共着色器 API)
  |
  v (asFragmentProcessor)
GrFPArgs (Fragment Processor 构建参数)
  |
  v
GrFragmentProcessor (GPU 片段处理器)
  |
  v
GrPipeline (渲染管线)
  |
  v
GPU 着色器编译与执行
```

当 Skia 的公共着色器对象（如 `SkShader`、`SkColorFilter`）需要被转换为 GPU 可执行的 Fragment Processor 时，`GrFPArgs` 作为上下文参数传递给 `asFragmentProcessor()` 方法。

## 主要类与结构体

### `GrFPArgs`

参数聚合结构体，包含创建 Fragment Processor 所需的上下文信息。

**嵌套枚举：**

#### `GrFPArgs::Scope`

| 枚举值 | 说明 |
|--------|------|
| `kDefault` | 默认作用域，标准着色器到 Fragment Processor 的转换 |
| `kRuntimeEffect` | 运行时效果作用域，用于 `SkRuntimeEffect` 的 Fragment Processor 构建 |

**成员变量：**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fSurfaceDrawContext` | `skgpu::ganesh::SurfaceDrawContext*` | 表面绘制上下文指针（不可为空） |
| `fDstColorInfo` | `const GrColorInfo*` | 目标颜色信息，描述渲染目标的颜色类型和颜色空间 |
| `fSurfaceProps` | `const SkSurfaceProps&` | 表面属性引用（如像素几何、文本渲染提示） |
| `fScope` | `Scope` | 作用域标记 |

## 公共 API 函数

### 构造函数

```cpp
GrFPArgs(skgpu::ganesh::SurfaceDrawContext* sdc,
         const GrColorInfo* dstColorInfo,
         const SkSurfaceProps& surfaceProps,
         Scope scope)
```

构造 `GrFPArgs` 实例。

- **参数：**
  - `sdc`：表面绘制上下文指针，不可为 `nullptr`（有 `SkASSERT` 检查）
  - `dstColorInfo`：目标颜色信息
  - `surfaceProps`：表面属性（按引用传递）
  - `scope`：作用域标记

## 内部实现细节

1. **非空断言**：构造函数中使用 `SkASSERT(fSurfaceDrawContext)` 确保表面绘制上下文不为空，这是一个强前置条件。

2. **引用成员**：`fSurfaceProps` 使用 `const` 引用而非指针或值，这意味着 `GrFPArgs` 的生命周期必须短于被引用的 `SkSurfaceProps` 对象。

3. **前向声明**：`GrColorInfo`、`SkSurfaceProps` 和 `skgpu::ganesh::SurfaceDrawContext` 均通过前向声明引入，减少头文件依赖。

4. **`Scope` 枚举的设计意图**：`kRuntimeEffect` 作用域用于标识 Fragment Processor 是从 `SkRuntimeEffect`（用户自定义 SKSL 着色器）创建的，某些 FP 的行为可能会因此不同（例如可能禁用某些优化或启用特殊的安全检查）。

## 依赖关系

- **`include/private/base/SkAssert.h`**：提供 `SkASSERT` 宏
- **`GrColorInfo`**（前向声明）：目标颜色空间信息
- **`SkSurfaceProps`**（前向声明）：表面属性
- **`skgpu::ganesh::SurfaceDrawContext`**（前向声明）：表面绘制上下文

## 设计模式与设计决策

1. **参数对象模式（Parameter Object）**：将多个相关参数聚合为一个结构体，避免长参数列表。这使得 `asFragmentProcessor()` 方法的签名更简洁，且新增参数时无需修改所有调用者的签名。

2. **作用域区分**：通过 `Scope` 枚举区分标准着色器和运行时效果，允许 Fragment Processor 的创建逻辑根据上下文做出不同决策。

3. **最小依赖设计**：仅包含 `SkAssert.h`，所有其他类型使用前向声明，最大限度减少编译依赖。这是 Skia 头文件设计的最佳实践。

4. **不可复制的引用语义**：由于包含引用成员 `fSurfaceProps`，该结构体不支持默认赋值操作，强调其作为临时参数包的短生命周期特性。

## 性能考量

- **轻量级结构**：仅包含两个指针、一个引用和一个枚举值，传值开销极低。
- **前向声明**：减少头文件包含链，缩短编译时间。
- **栈上分配**：该结构体通常在栈上创建并在函数调用链中传递，无堆分配开销。

## 相关文件

- `src/gpu/ganesh/GrFragmentProcessor.h`：Fragment Processor 基类
- `src/gpu/ganesh/GrColorInfo.h`：颜色信息类
- `src/gpu/ganesh/SurfaceDrawContext.h`：表面绘制上下文
- `include/core/SkSurfaceProps.h`：表面属性类
- `include/effects/SkRuntimeEffect.h`：运行时效果（与 `Scope::kRuntimeEffect` 相关）
- `src/shaders/SkShaderBase.h`：着色器基类，其 `asFragmentProcessor()` 方法接受 `GrFPArgs`
