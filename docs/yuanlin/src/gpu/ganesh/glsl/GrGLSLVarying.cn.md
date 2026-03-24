# GrGLSLVarying

> 源文件: `src/gpu/ganesh/glsl/GrGLSLVarying.h`, `src/gpu/ganesh/glsl/GrGLSLVarying.cpp`

## 概述

`GrGLSLVarying` 和 `GrGLSLVaryingHandler` 共同管理 GLSL 着色器之间的 varying 变量。`GrGLSLVarying` 表示单个 varying 变量的类型和作用域信息，而 `GrGLSLVaryingHandler` 负责 varying 的注册、属性发射、插值修饰符设置以及最终声明的生成。

## 架构位置

这些类位于 GLSL 着色器代码生成层，被 `GrGLSLProgramBuilder` 持有和使用。它们在几何处理器和片段处理器的代码发射过程中，负责在顶点和片段着色器之间传递数据。

## 主要类与结构体

### `GrGLSLVarying`
- 表示一个 varying 变量
- 定义 `Scope` 枚举：`kVertToFrag`、`kVertToGeo`、`kGeoToFrag`
- 不支持矩阵类型（Metal 不支持 varying 矩阵）
- 提供 `vsOut()` / `fsIn()` 访问变量名

### `GrGLSLVaryingHandler`
- 管理所有 varying 变量的注册和声明
- 持有 `VaryingList fVaryings` 和 `VarArray` 用于输入/输出声明
- 支持 `noperspective` 插值优化
- 定义 `Interpolation` 枚举：`kInterpolated`、`kCanBeFlat`、`kMustBeFlat`

## 公共 API 函数

### `GrGLSLVaryingHandler`
- `addVarying()` - 注册一个 varying，指定名称和插值模式
- `addPassThroughAttribute()` - 将顶点属性直接传递到片段着色器输出变量
- `emitAttributes()` - 发射几何处理器的顶点和实例属性
- `setNoPerspective()` - 启用 noperspective 插值（当无透视时可获得更高性能）
- `finalize()` - 将所有 varying 转换为着色器输入/输出声明
- `getVertexDecls()` / `getFragDecls()` - 获取声明字符串

## 内部实现细节

- `addVarying()` 使用 `nameVariable('v', name)` 生成修饰过的变量名，避免命名冲突
- flat 插值的决策基于 `GrShaderCaps::fPreferFlatInterpolation`（Qualcomm GPU 上 flat 较慢）
- `addPassThroughAttribute()` 自动在顶点和片段着色器中生成赋值代码
- `finalize()` 为每个 varying 生成带插值修饰符（flat 或 noperspective）的声明
- 属性去重：`addAttribute()` 检查名称避免重复添加

## 依赖关系

- **GrGLSLProgramBuilder** - 程序构建器，提供 `nameVariable()` 和着色器能力查询
- **GrGLSLShaderBuilder** - 用于获取 noperspective 特性位
- **GrGeometryProcessor** - 提供顶点和实例属性
- **GrShaderCaps** - 查询 flat/noperspective 插值支持

## 设计模式与设计决策

1. **两阶段模式**: 先通过 `addVarying()` 注册，然后通过 `finalize()` 生成声明
2. **Metal 兼容性**: 禁止矩阵类型的 varying，确保跨平台兼容
3. **插值优化**: `kCanBeFlat` 让着色器能力决定是否使用 flat 插值
4. **noperspective 全局设置**: 通过 `setNoPerspective()` 为所有 varying 设置默认插值修饰符

## 性能考量

- noperspective 插值在非透视场景下减少 GPU 插值计算开销
- flat 插值避免不必要的插值，但在某些 GPU（Qualcomm）上可能更慢
- `kVaryingsPerBlock = 8` 控制 SkTBlockList 的分配粒度

## 相关文件

- `src/gpu/ganesh/glsl/GrGLSLShaderBuilder.h` - 着色器构建器基类
- `src/gpu/ganesh/glsl/GrGLSLProgramBuilder.h` - 程序构建器
- `src/gpu/ganesh/GrGeometryProcessor.h` - 几何处理器
- `src/gpu/ganesh/GrShaderVar.h` - 着色器变量定义
