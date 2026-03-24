# SkSLMemoryLayout — GPU 缓冲区内存布局计算

> 源文件：[`src/sksl/SkSLMemoryLayout.h`](../../src/sksl/SkSLMemoryLayout.h)

## 概述

SkSLMemoryLayout.h 定义了 `MemoryLayout` 类，负责根据不同的 GPU 着色语言标准计算类型在缓冲区中的大小、对齐和步进（stride）。它支持 GLSL std140/std430、Metal、以及 WGSL（WebGPU Shading Language）的内存布局规范。

该文件 243 行，是 SkSL 编译器中处理 uniform buffer 和 storage buffer 布局的核心组件。

## 架构位置

```
SkSL 编译器
  └── 代码生成
        ├── GLSL 代码生成器 → MemoryLayout(k140/k430)
        ├── SPIR-V 代码生成器 → MemoryLayout(k140/k430)
        ├── Metal 代码生成器 → MemoryLayout(kMetal)
        └── WGSL 代码生成器  → MemoryLayout(kWGSL*)
```

`MemoryLayout` 被各后端代码生成器使用，确保生成的缓冲区布局符合目标平台的对齐和大小要求。

## 主要类与结构体

### `MemoryLayout`

```cpp
class MemoryLayout {
public:
    enum class Standard {
        k140, k430, kMetal,
        kWGSLUniform_Base, kWGSLUniform_EnableF16,
        kWGSLStorage_Base, kWGSLStorage_EnableF16,
    };

    MemoryLayout(Standard std);
    size_t alignment(const Type& type) const;
    size_t stride(const Type& type) const;
    size_t size(const Type& type) const;
    size_t isSupported(const Type& type) const;
    size_t roundUpIfNeeded(size_t raw, Type::TypeKind type) const;
    size_t roundUp16(size_t n) const;
    Standard getStandard() const;

private:
    static size_t GetVectorAlignment(size_t componentSize, int columns);
    const Standard fStd;
};
```

### `Standard` 枚举

| 值 | 说明 |
|---|---|
| `k140` | GLSL std140 布局（OpenGL Spec v4.5, 7.6.2.2） |
| `k430` | GLSL std430 布局（仅用于 SSBO，优化了对齐要求） |
| `kMetal` | Metal 着色语言内存布局 |
| `kWGSLUniform_Base` | WGSL uniform 地址空间（f16 当作 32 位 float） |
| `kWGSLUniform_EnableF16` | WGSL uniform 地址空间（f16 当作 16 位 half） |
| `kWGSLStorage_Base` | WGSL storage 地址空间（f16 当作 32 位 float） |
| `kWGSLStorage_EnableF16` | WGSL storage 地址空间（f16 当作 16 位 half） |

## 公共 API 函数

```cpp
size_t alignment(const Type& type) const;
```
- 返回类型作为独立变量使用时的对齐要求（字节数）
- 标量：等于其大小
- 向量：`componentSize * (columns + columns % 2)`（2 列向量按 2 分量对齐，3/4 列向量按 4 分量对齐）
- 矩阵：列向量的对齐，可能向上取整到 16
- 数组：元素类型的对齐，可能向上取整到 16
- 结构体：所有字段对齐的最大值，可能向上取整到 16

```cpp
size_t stride(const Type& type) const;
```
- 返回矩阵或数组中相邻元素之间的字节距离
- 矩阵步进等于其对齐值
- 数组步进为元素大小向上取整到元素对齐后再按需取整到 16

```cpp
size_t size(const Type& type) const;
```
- 返回类型的字节大小
- 标量：通常 4 字节；Metal 低精度数值 2 字节；WGSL 中 bool 返回 0（不可用）
- 原子类型：始终 4 字节
- 向量：`columns * componentSize`（Metal 3 分量向量例外，占 4 分量空间）
- 矩阵/数组：`columns * stride`
- 结构体：累加各字段大小（含对齐填充），向上取整到结构体对齐

```cpp
size_t isSupported(const Type& type) const;
```
- 检查类型在当前内存布局标准下是否受支持
- WGSL 不支持 bool 类型（不可跨主机共享）
- 递归检查复合类型的成员

```cpp
size_t roundUpIfNeeded(size_t raw, Type::TypeKind type) const;
```
- 根据布局标准和类型种类，按需将值向上取整到 16 的倍数
- std140：始终取整
- WGSL uniform：除矩阵外取整
- 其他标准：不取整

```cpp
size_t roundUp16(size_t n) const;
```
- 将 n 向上取整到 16 的最近倍数：`(n + 15) & ~15`

## 内部实现细节

### 向量对齐计算

```cpp
static size_t GetVectorAlignment(size_t componentSize, int columns) {
    return componentSize * (columns + columns % 2);
}
```

这实现了 GPU 着色语言的向量对齐规则：
- 2 分量向量：对齐到 2 * componentSize
- 3 分量向量：对齐到 4 * componentSize（与 4 分量相同）
- 4 分量向量：对齐到 4 * componentSize

### Metal 3 分量向量的特殊处理

在 Metal 布局中，3 分量向量的大小按 4 分量计算（`4 * componentSize`），因为 Metal 的 packed 类型不用于 buffer layout。

### WGSL 对 f16 的双模式支持

WGSL 提供了两种 f16 处理模式：
- `_Base`：将 f16 视为 32 位 float（兼容不支持 f16 的设备）
- `_EnableF16`：将 f16 视为 16 位 half float（启用 f16 扩展的设备）

### 结构体大小计算

结构体大小通过遍历所有字段累加得出：
1. 对每个字段，先添加对齐填充使当前偏移满足字段的对齐要求
2. 累加字段大小
3. 最终总大小向上取整到结构体自身的对齐

## 依赖关系

- `src/sksl/ir/SkSLType.h` — SkSL 类型系统（`Type`, `Type::TypeKind`, `Field`）
- `<algorithm>` — `std::all_of`（用于 `isSupported` 的结构体检查）

## 设计模式与设计决策

- **策略模式**：通过 `Standard` 枚举选择不同的内存布局标准，所有计算方法内部根据标准做分支处理，而非为每种标准创建子类。
- **递归计算**：`size`、`alignment`、`isSupported` 递归处理复合类型（数组、矩阵、结构体），自然地支持嵌套类型。
- **不可变对象**：`fStd` 为 `const`，构造后内存布局标准不可变。
- **按需取整**：`roundUpIfNeeded` 封装了不同标准对 16 字节对齐的不同要求，避免在每个方法中重复判断。

## 性能考量

1. **编译时计算**：内存布局计算在着色器编译期执行，不影响运行时性能。
2. **递归深度**：对于深度嵌套的结构体，递归计算可能较深，但实际 GPU 着色器中的类型嵌套层次通常很浅。
3. **正确性优先**：布局计算的准确性直接影响 GPU buffer 数据传输的正确性，因此代码侧重于正确实现规范而非性能优化。

## 相关文件

- `src/sksl/ir/SkSLType.h` — SkSL 类型系统
- `src/sksl/codegen/SkSLSPIRVCodeGenerator.cpp` — SPIR-V 代码生成（使用 std140/std430）
- `src/sksl/codegen/SkSLGLSLCodeGenerator.cpp` — GLSL 代码生成
- `src/sksl/codegen/SkSLMetalCodeGenerator.cpp` — Metal 代码生成（使用 kMetal）
- `src/sksl/codegen/SkSLWGSLCodeGenerator.cpp` — WGSL 代码生成（使用 kWGSL*）
