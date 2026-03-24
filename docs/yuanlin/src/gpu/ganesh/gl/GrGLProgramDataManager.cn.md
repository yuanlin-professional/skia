# GrGLProgramDataManager

> 源文件
> - src/gpu/ganesh/gl/GrGLProgramDataManager.h
> - src/gpu/ganesh/gl/GrGLProgramDataManager.cpp

## 概述

`GrGLProgramDataManager` 是 Skia Ganesh OpenGL 后端中负责管理着色器程序数据资源的核心类。它继承自 `GrGLSLProgramDataManager`，专门处理 OpenGL 程序的 uniform 变量上传和管理。该类提供了类型安全的接口，用于向 GPU 着色器传递各种类型的数据，包括标量、向量、矩阵等。

该类的设计目标是简化应用程序代码与着色器资源之间的通信，提供统一的 API 来设置整数、浮点数、向量和矩阵等 uniform 值。它封装了底层 OpenGL uniform 上传的复杂性，并提供类型检查和数组边界验证（在调试模式下）。

## 架构位置

```
GrGLSLProgramDataManager (抽象基类)
    └── GrGLProgramDataManager (GL具体实现)

调用链:
GrGLProgram -> GrGLProgramDataManager -> OpenGL glUniform* APIs
```

该类位于 Skia 渲染管线的程序数据层，是 `GrGLProgram` 的重要组成部分。它作为中间层，将高层的数据设置请求转换为底层的 OpenGL uniform 调用。

## 主要类与结构体

### GrGLProgramDataManager

**继承关系:**
- 继承自: `GrGLSLProgramDataManager`

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fUniforms` | `skia_private::TArray<Uniform, true>` | uniform 数组，存储所有 uniform 信息 |
| `fGpu` | `GrGLGpu*` | 指向 OpenGL GPU 对象的指针 |

### Uniform 结构体

**成员变量 (DEBUG 模式):**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fLocation` | `GrGLint` | OpenGL uniform 位置 |
| `fType` | `SkSLType` (DEBUG) | uniform 的 GLSL 类型 |
| `fArrayCount` | `int` (DEBUG) | 数组元素个数 |

### GLUniformInfo 结构体

**继承自** `GrGLSLUniformHandler::UniformInfo`

**新增成员:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fLocation` | `GrGLint` | uniform 的 GL 位置 |

### VaryingInfo 结构体

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fVariable` | `GrShaderVar` | varying 变量信息 |
| `fLocation` | `GrGLint` | varying 的 GL 位置 |

## 公共 API 函数

### 构造与初始化
- `GrGLProgramDataManager(GrGLGpu*, const UniformInfoArray&)` - 构造函数，初始化 uniform 管理器

### Sampler 管理
- `void setSamplerUniforms(const UniformInfoArray& samplers, int startUnit) const` - 设置采样器 uniform

### 整数 Uniform 上传
- `void set1i(UniformHandle, int32_t) const` - 设置单个整数
- `void set1iv(UniformHandle, int arrayCount, const int32_t v[]) const` - 设置整数数组
- `void set2i(UniformHandle, int32_t, int32_t) const` - 设置 int2
- `void set2iv(UniformHandle, int arrayCount, const int32_t v[]) const` - 设置 int2 数组
- `void set3i(UniformHandle, int32_t, int32_t, int32_t) const` - 设置 int3
- `void set3iv(UniformHandle, int arrayCount, const int32_t v[]) const` - 设置 int3 数组
- `void set4i(UniformHandle, int32_t, int32_t, int32_t, int32_t) const` - 设置 int4
- `void set4iv(UniformHandle, int arrayCount, const int32_t v[]) const` - 设置 int4 数组

### 浮点数 Uniform 上传
- `void set1f(UniformHandle, float) const` - 设置单个浮点数
- `void set1fv(UniformHandle, int arrayCount, const float v[]) const` - 设置浮点数数组
- `void set2f(UniformHandle, float, float) const` - 设置 float2
- `void set2fv(UniformHandle, int arrayCount, const float v[]) const` - 设置 float2 数组
- `void set3f(UniformHandle, float, float, float) const` - 设置 float3
- `void set3fv(UniformHandle, int arrayCount, const float v[]) const` - 设置 float3 数组
- `void set4f(UniformHandle, float, float, float, float) const` - 设置 float4
- `void set4fv(UniformHandle, int arrayCount, const float v[]) const` - 设置 float4 数组

### 矩阵 Uniform 上传
- `void setMatrix2f(UniformHandle, const float matrix[]) const` - 设置 2x2 矩阵
- `void setMatrix3f(UniformHandle, const float matrix[]) const` - 设置 3x3 矩阵
- `void setMatrix4f(UniformHandle, const float matrix[]) const` - 设置 4x4 矩阵
- `void setMatrix2fv(UniformHandle, int arrayCount, const float matrices[]) const` - 设置 2x2 矩阵数组
- `void setMatrix3fv(UniformHandle, int arrayCount, const float matrices[]) const` - 设置 3x3 矩阵数组
- `void setMatrix4fv(UniformHandle, int arrayCount, const float matrices[]) const` - 设置 4x4 矩阵数组

## 内部实现细节

### Uniform 位置管理

构造函数从 `UniformInfoArray` 中提取 uniform 信息并存储：

```cpp
GrGLProgramDataManager::GrGLProgramDataManager(GrGLGpu* gpu, const UniformInfoArray& uniforms)
        : fGpu(gpu) {
    fUniforms.push_back_n(uniforms.count());
    int i = 0;
    for (const GLUniformInfo& builderUniform : uniforms.items()) {
        Uniform& uniform = fUniforms[i++];
        uniform.fLocation = builderUniform.fLocation;
        // DEBUG 模式下保存类型和数组信息
        SkDEBUGCODE(
            uniform.fArrayCount = builderUniform.fVariable.getArrayCount();
            uniform.fType = builderUniform.fVariable.getType();
        )
    }
}
```

### 类型安全检查

在调试模式下，所有 set 函数都会验证类型匹配：

```cpp
void GrGLProgramDataManager::set1i(UniformHandle u, int32_t i) const {
    const Uniform& uni = fUniforms[u.toIndex()];
    SkASSERT(uni.fType == SkSLType::kInt || uni.fType == SkSLType::kShort);
    SkASSERT(GrShaderVar::kNonArray == uni.fArrayCount);
    if (kUnusedUniform != uni.fLocation) {
        GR_GL_CALL(fGpu->glInterface(), Uniform1i(uni.fLocation, i));
    }
}
```

### 数组边界检查

使用宏 `ASSERT_ARRAY_UPLOAD_IN_BOUNDS` 验证数组上传的边界：

```cpp
#define ASSERT_ARRAY_UPLOAD_IN_BOUNDS(UNI, COUNT) \
    SkASSERT((COUNT) <= (UNI).fArrayCount || \
             (1 == (COUNT) && GrShaderVar::kNonArray == (UNI).fArrayCount))
```

### 矩阵上传模板化

使用模板特化实现不同维度矩阵的上传：

```cpp
template<> struct set_uniform_matrix<2> {
    inline static void set(const GrGLInterface* gli, const GrGLint loc, int cnt, const float m[]) {
        GR_GL_CALL(gli, UniformMatrix2fv(loc, cnt, false, m));
    }
};

template<> struct set_uniform_matrix<3> {
    inline static void set(const GrGLInterface* gli, const GrGLint loc, int cnt, const float m[]) {
        GR_GL_CALL(gli, UniformMatrix3fv(loc, cnt, false, m));
    }
};

template<> struct set_uniform_matrix<4> {
    inline static void set(const GrGLInterface* gli, const GrGLint loc, int cnt, const float m[]) {
        GR_GL_CALL(gli, UniformMatrix4fv(loc, cnt, false, m));
    }
};
```

### 未使用 Uniform 优化

对于被优化掉的 uniform（location == -1），直接跳过上传：

```cpp
static constexpr GrGLint kUnusedUniform = -1;

if (kUnusedUniform != uni.fLocation) {
    GR_GL_CALL(fGpu->glInterface(), Uniform1i(uni.fLocation, i));
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLGpu` | 访问 GL 接口 |
| `GrGLInterface` | OpenGL 函数指针接口 |
| `GrShaderVar` | 着色器变量描述 |
| `SkSLType` | SkSL 类型系统 |
| `GrGLSLProgramDataManager` | 基类接口 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrGLProgram` | 使用该类上传 uniform 数据 |
| `GrGeometryProcessor::ProgramImpl` | 通过该类设置几何处理器数据 |
| `GrFragmentProcessor::ProgramImpl` | 通过该类设置片段处理器数据 |
| `GrXferProcessor::ProgramImpl` | 通过该类设置传输处理器数据 |

## 设计模式与设计决策

### 1. 类型别名 (Type Aliasing)

提供清晰的类型别名以简化代码：

```cpp
typedef SkTBlockList<GLUniformInfo> UniformInfoArray;
typedef SkTBlockList<VaryingInfo>   VaryingInfoArray;
```

### 2. Handle 模式

使用 `UniformHandle` 作为不透明句柄，隐藏内部索引：

```cpp
const Uniform& uni = fUniforms[u.toIndex()];
```

**优点**: 提供类型安全性，防止索引误用

### 3. 条件编译 (Conditional Compilation)

调试信息仅在 DEBUG 模式下存储：

```cpp
#ifdef SK_DEBUG
    SkSLType    fType;
    int         fArrayCount;
#endif
```

**优点**: 减少发布版本的内存开销

### 4. 模板元编程

使用模板特化处理不同维度的矩阵：

```cpp
template<int N> inline void setMatrices(UniformHandle u, int arrayCount, const float matrices[]) const {
    const Uniform& uni = fUniforms[u.toIndex()];
    if (kUnusedUniform != uni.fLocation) {
        set_uniform_matrix<N>::set(fGpu->glInterface(), uni.fLocation, arrayCount, matrices);
    }
}
```

## 性能考量

### 1. 未使用 Uniform 跳过

通过检查 `fLocation` 避免调用 OpenGL API：

```cpp
if (kUnusedUniform != uni.fLocation) {
    // 仅对实际使用的 uniform 进行 GL 调用
}
```

**优势**: 减少驱动开销和验证时间

### 2. 数组内联存储

使用 `TArray<Uniform, true>` 内联存储小数组：

```cpp
skia_private::TArray<Uniform, true> fUniforms;
```

**优势**: 小数组避免堆分配，提高缓存局部性

### 3. 类型检查仅在 DEBUG 模式

发布版本跳过类型检查，减少运行时开销：

```cpp
#ifdef SK_DEBUG
    SkASSERT(uni.fType == SkSLType::kFloat);
#endif
```

### 4. 矩阵列主序优化

OpenGL 默认使用列主序矩阵，传递 `false` 参数避免转置：

```cpp
GR_GL_CALL(gli, UniformMatrix4fv(loc, cnt, false, m));
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/glsl/GrGLSLProgramDataManager.h` | 基类 | 平台无关的数据管理器接口 |
| `src/gpu/ganesh/gl/GrGLProgram.h` | 使用者 | GL 程序对象 |
| `src/gpu/ganesh/gl/GrGLGpu.h` | 依赖 | GPU 接口访问 |
| `src/gpu/ganesh/GrShaderVar.h` | 依赖 | 着色器变量描述 |
| `src/core/SkSLTypeShared.h` | 依赖 | SkSL 类型定义 |
| `src/gpu/ganesh/glsl/GrGLSLUniformHandler.h` | 依赖 | Uniform 处理器接口 |
