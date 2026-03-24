# GrGLSLProgramDataManager

> 源文件: `src/gpu/ganesh/glsl/GrGLSLProgramDataManager.h`, `src/gpu/ganesh/glsl/GrGLSLProgramDataManager.cpp`

## 概述

`GrGLSLProgramDataManager` 是一个抽象基类，定义了向 GPU 着色器程序上传 uniform 数据的接口。它提供了设置标量、向量、矩阵类型 uniform 变量的完整 API，同时支持 SkMatrix、SkM44 的便捷上传，以及 SkRuntimeEffect uniform 的批量设置。

## 架构位置

该类处于着色器数据管理层，作为处理器 ProgramImpl 和具体后端 uniform 实现之间的桥梁。GL 后端通过 `GrGLProgramDataManager` 继承实现，Vulkan 后端通过 uniform 缓冲区实现。它被所有处理器的 `setData()` 方法使用。

## 主要类与结构体

### `GrGLSLProgramDataManager`
- 不可拷贝（继承 `SkNoncopyable`）
- 定义 `UniformHandle` 资源句柄类型
- 定义 `Specialized` 枚举用于 runtime effect uniform 的特化标记

## 公共 API 函数

### 标量/向量上传（纯虚函数）
- `set1i/set1iv` - 设置 int/int 数组
- `set1f/set1fv` ~ `set4f/set4fv` - 设置 float1 到 float4 及其数组
- `set2i/set2iv` ~ `set4i/set4iv` - 设置 int2 到 int4 及其数组

### 矩阵上传（纯虚函数）
- `setMatrix2f/3f/4f` - 设置单个 2x2/3x3/4x4 矩阵（列主序）
- `setMatrix2fv/3fv/4fv` - 设置矩阵数组

### 便捷方法
- `setSkMatrix()` - 上传 SkMatrix 到 3x3 uniform（转换为列主序）
- `setSkM44()` - 上传 SkM44 到 4x4 uniform

### Runtime Effect 支持
- `setRuntimeEffectUniforms()` - 批量设置 SkRuntimeEffect 的 uniform 值，支持特化（跳过编译时常量）

## 内部实现细节

- `setSkMatrix()` 将 SkMatrix 的 9 个元素手动排列为列主序的 float 数组，然后调用 `setMatrix3f()`
- `setRuntimeEffectUniforms()` 通过 `SkRuntimeEffect::Uniform::Type` 判断类型，分发到对应的 `set*` 方法
- 特化的 uniform（`Specialized::kYes`）被跳过，handle 数组中只包含非特化 uniform 的句柄

## 依赖关系

- **SkMatrix / SkM44** - Skia 矩阵类型
- **SkRuntimeEffect::Uniform** - Runtime Effect 的 uniform 描述
- **GrResourceHandle** - uniform 句柄基础设施

## 设计模式与设计决策

1. **抽象接口模式**: 纯虚函数让各后端自由实现 uniform 上传机制
2. **句柄类型安全**: `UniformHandle` 封装为强类型，避免误用
3. **特化支持**: 允许 runtime effect 中的编译时常量不占用 uniform 槽位

## 性能考量

- 避免不必要的 uniform 上传是使用者的责任（如比较新旧值再决定是否上传）
- 矩阵 uniform 使用列主序格式，直接兼容 GLSL/SPIR-V 的期望布局

## 相关文件

- `src/gpu/ganesh/gl/GrGLProgramDataManager.h` - GL 后端实现
- `src/gpu/ganesh/glsl/GrGLSLUniformHandler.h` - uniform 声明管理
- `include/effects/SkRuntimeEffect.h` - runtime effect uniform 定义
