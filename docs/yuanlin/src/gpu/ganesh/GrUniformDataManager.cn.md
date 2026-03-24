# GrUniformDataManager

> 源文件: src/gpu/ganesh/GrUniformDataManager.h, src/gpu/ganesh/GrUniformDataManager.cpp

## 概述

`GrUniformDataManager` 是 Skia Ganesh GPU 后端中用于管理着色器 uniform 数据的核心类。它继承自 `GrGLSLProgramDataManager`,负责在 CPU 端的缓冲区中存储 uniform 值,并支持将这些数据上传到 GPU 的 Uniform Buffer Object (UBO)。

该类采用兼容 Vulkan、Dawn 和 D3D12 的内存布局规范,提供了类型安全的 uniform 设置接口,支持整数、浮点数、向量和矩阵的多种格式。其设计重点包括高效的内存管理、16 位/32 位混合 uniform 支持,以及基于脏标记的更新优化。

## 架构位置

`GrUniformDataManager` 在 Ganesh 着色器系统中的位置:

- **上层**: 由着色器程序调用以设置 uniform 值
- **基类**: `GrGLSLProgramDataManager` 定义抽象接口
- **下层**: 最终通过 GPU 后端将数据传输到 UBO

该类是着色器参数管理的中心枢纽,连接高层渲染逻辑和底层 GPU 资源。

## 主要类与结构体

### GrUniformDataManager 类

**继承关系**:
- 继承自 `GrGLSLProgramDataManager`
- 覆盖所有 uniform 设置的虚函数

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fUniformSize` | `uint32_t` | uniform 缓冲区的总大小(字节) |
| `fWrite16BitUniforms` | `bool` | 是否写入 16 位 uniform(half/short) |
| `fUniforms` | `skia_private::TArray<Uniform, true>` | uniform 元数据数组 |
| `fUniformData` | `mutable SkAutoMalloc` | 实际存储 uniform 数据的缓冲区 |
| `fUniformsDirty` | `mutable bool` | 脏标记,指示数据是否已修改 |

**可变性**: `fUniformData` 和 `fUniformsDirty` 标记为 `mutable`,允许 `const` 方法修改。

### Uniform 结构体

表示单个 uniform 的元数据。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fOffset` | `uint32_t : 24` | 在缓冲区中的字节偏移(24 位) |
| `fType` | `uint32_t : 8` | `SkSLType` 类型编码(8 位) |
| `fArrayCount` | `int32_t` | 数组元素数量(仅 Debug 模式) |

**位域优化**: 使用位域压缩存储,节省内存。

**辅助方法**:
- `type()`: 解码类型为 `SkSLType` 枚举
- `setType()`: 编码类型到位域

## 公共 API 函数

### 构造函数

```cpp
GrUniformDataManager(uint32_t uniformCount, uint32_t uniformSize)
```

**功能**: 初始化 uniform 管理器。

**参数**:
- `uniformCount`: uniform 的数量
- `uniformSize`: 缓冲区总大小

**初始化**:
- 分配 `uniformSize` 字节的数据缓冲区
- 预分配 `uniformCount` 个 `Uniform` 结构体
- 子类负责填充 uniform 元数据

### 标量和向量设置函数

提供完整的类型覆盖:

| 函数签名 | 说明 |
|---------|------|
| `void set1i(UniformHandle, int32_t)` | 设置单个 int/short |
| `void set1iv(UniformHandle, int, const int32_t[])` | 设置 int/short 数组 |
| `void set1f(UniformHandle, float)` | 设置单个 float/half |
| `void set1fv(UniformHandle, int, const float[])` | 设置 float/half 数组 |
| `void set2i/2iv/2f/2fv` | 2 分量向量版本 |
| `void set3i/3iv/3f/3fv` | 3 分量向量版本 |
| `void set4i/4iv/4f/4fv` | 4 分量向量版本 |

**特性**:
- 所有方法标记为 `const`,但会修改缓冲区
- 自动处理 full precision 和 half precision 转换

### 矩阵设置函数

```cpp
void setMatrix2f(UniformHandle, const float matrix[]) const
void setMatrix2fv(UniformHandle, int arrayCount, const float matrices[]) const
void setMatrix3f(UniformHandle, const float matrix[]) const
void setMatrix3fv(UniformHandle, int arrayCount, const float matrices[]) const
void setMatrix4f(UniformHandle, const float matrix[]) const
void setMatrix4fv(UniformHandle, int arrayCount, const float matrices[]) const
```

**约定**: 矩阵按列主序(column-major)存储。

### 脏标记管理

```cpp
void markDirty()
```

**功能**: 手动标记数据为脏,强制下次上传。

**用途**: 用于外部直接修改缓冲区后通知管理器。

## 内部实现细节

### copyUniforms 方法

```cpp
int copyUniforms(void* dest, const void* src, int numUniforms, SkSLType uniformType) const
```

**功能**: 拷贝 uniform 数据,并根据类型执行格式转换。

**转换逻辑**:

| 源类型 | fWrite16BitUniforms | 目标格式 | 转换 |
|--------|---------------------|---------|------|
| `float` | `true` + half 类型 | `SkHalf` | `SkFloatToHalf` |
| `int` | `true` + short 类型 | `short` | 直接截断 |
| 其他 | - | 原样 | `memcpy` |

**返回值**: 每个 uniform 占用的字节数(2 或 4)。

### set 模板方法

```cpp
template <int N, SkSLType FullType, SkSLType HalfType>
void set(UniformHandle u, const void* v) const
```

**功能**: 设置单个 uniform 值。

**流程**:
1. 验证类型匹配(`FullType` 或 `HalfType`)
2. 断言非数组类型
3. 获取缓冲区指针并标记脏
4. 调用 `copyUniforms` 拷贝 `N` 个分量

**类型安全**: 通过模板参数强制类型检查。

### setv 模板方法

```cpp
template <int N, SkSLType FullType, SkSLType HalfType>
void setv(UniformHandle u, int arrayCount, const void* v) const
```

**功能**: 设置 uniform 数组。

**特殊处理**:
- **4 分量向量**: 直接拷贝 `arrayCount * 4` 个元素
- **其他**: 逐个元素拷贝,每个元素占用 4 个 uniform 单元(对齐要求)

**对齐策略**: 遵循 std140/std430 布局的 4 单元对齐。

### setMatrices 模板方法

```cpp
template <int N, SkSLType FullType, SkSLType HalfType>
void setMatrices(UniformHandle u, int arrayCount, const float matrices[]) const
```

**功能**: 设置矩阵数组。

**布局处理**:
- **4x4 矩阵**: 连续拷贝 16 个元素
- **其他**: 按列拷贝,每列占用 4 个 uniform 单元

**原因**: 支持 3x3 矩阵在 4 单元对齐环境中的布局。

### getBufferPtrAndMarkDirty

```cpp
void* getBufferPtrAndMarkDirty(const Uniform& uni) const
```

**功能**: 获取 uniform 的缓冲区指针并设置脏标记。

**实现**:
```cpp
fUniformsDirty = true;
return static_cast<char*>(fUniformData.get()) + uni.fOffset;
```

**关键性**: 确保所有修改都会触发脏标记。

### 类型断言

代码中大量使用静态断言确保类型大小:

```cpp
static_assert(sizeof(int32_t) == 4);
static_assert(sizeof(float) == 4);
static_assert(sizeof(short) == 2);
static_assert(sizeof(SkHalf) == 2);
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLSLProgramDataManager` | 基类,定义抽象接口 |
| `SkAutoMalloc` | 自动内存管理 |
| `SkHalf` | 半精度浮点数转换 |
| `SkSLType` | 着色器类型枚举 |
| `GrShaderVar` | 着色器变量定义(用于常量) |
| `skia_private::TArray` | 动态数组容器 |

### 被依赖的模块

该类被以下模块使用:
- 各 GPU 后端的 Program 类(Vulkan/Metal/D3D/Dawn)
- 着色器构建器和编译器
- 渲染管线状态管理

## 设计模式与设计决策

### Template Method 模式

基类定义接口,子类实现初始化逻辑:

```cpp
// 子类在构造函数中填充 fUniforms
fUniforms.push_back_n(uniformCount);
// subclasses fill in the uniforms in their constructor
```

**优点**: 分离通用逻辑和平台特定代码。

### Const Correctness 的权衡

所有设置方法为 `const`,但修改内部状态:

**理由**:
- uniform 数据是"逻辑上的 const"(不改变对象身份)
- 允许在 `const` 上下文中设置 uniform
- 使用 `mutable` 成员明确标识可变部分

### 位域优化

`Uniform` 结构体使用位域:
- 节省内存(32 位 + Debug 的 32 位)
- 利用 24 位偏移支持最大 16MB 的 UBO

**权衡**: 增加代码复杂度,但内存节省显著。

### 混合精度支持

`fWrite16BitUniforms` 标志控制运行时转换:

**好处**:
- 支持移动 GPU 的 16 位优化
- 在 CPU 端统一使用 32 位,GPU 端选择性使用 16 位
- 减少带宽和寄存器压力

### 延迟更新策略

使用脏标记避免不必要的 GPU 传输:
- 所有 `set` 方法标记脏
- 上传到 GPU 后清除脏标记
- 减少跨总线传输开销

## 性能考量

### 内存布局

`SkAutoMalloc` 预分配整块内存:
- 避免碎片化
- 提高 CPU 缓存局部性
- 支持一次性 DMA 传输

### 对齐和填充

遵循 UBO 对齐要求:
- 向量按 4 单元对齐
- 矩阵列按 4 单元对齐
- 避免跨缓存行访问

### 类型转换开销

16 位转换仅在必要时进行:

```cpp
if (fWrite16BitUniforms) {
    // 执行转换
} else {
    memcpy(dest, src, numUniforms * 4);  // 快速路径
}
```

**优化**: 默认路径为简单内存拷贝。

### 批量操作

数组和矩阵函数减少调用次数:
- 一次设置多个元素
- 减少函数调用和边界检查开销

### Debug 开销

`fArrayCount` 仅在 Debug 模式存在:

```cpp
SkDEBUGCODE(int32_t fArrayCount;)
```

Release 版本不占用空间。

### 4x4 矩阵快速路径

特殊优化最常见的情况:

```cpp
if constexpr (N == 4) {
    this->copyUniforms(buffer, matrices, arrayCount * 16, uni.type());
}
```

避免循环开销。

## 相关文件

| 文件 | 关系 |
|------|------|
| `src/gpu/ganesh/glsl/GrGLSLProgramDataManager.h` | 基类定义 |
| `src/base/SkAutoMalloc.h` | 自动内存管理 |
| `src/base/SkHalf.h` | 半精度浮点数支持 |
| `src/core/SkSLTypeShared.h` | 着色器类型枚举 |
| `src/gpu/ganesh/GrShaderVar.h` | 着色器变量工具 |
| `include/private/base/SkTArray.h` | 动态数组容器 |
| `include/private/base/SkTemplates.h` | 模板工具 |
| `include/private/base/SkAssert.h` | 断言宏 |
