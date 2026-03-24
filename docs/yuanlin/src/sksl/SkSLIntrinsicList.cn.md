# SkSL IntrinsicList（内置函数列表）

> 源文件：[src/sksl/SkSLIntrinsicList.h](../../src/sksl/SkSLIntrinsicList.h)、[src/sksl/SkSLIntrinsicList.cpp](../../src/sksl/SkSLIntrinsicList.cpp)

## 概述

`SkSLIntrinsicList` 定义了 SkSL 着色语言支持的所有内置函数（intrinsic）的完整列表。它使用 X-Macro 技术统一管理超过 100 个内置函数名称，自动生成对应的枚举值和查找映射表。内置函数涵盖了数学运算（三角函数、指数、取整等）、向量/矩阵运算、纹理采样、原子操作、颜色空间转换等类别。

## 架构位置

`IntrinsicList` 位于 SkSL 编译器的核心定义层，被解析器、分析器和代码生成器广泛引用：

```
SkSL 源代码 -> 解析器（匹配函数名到 IntrinsicKind）
                  |
            Analysis（检查是否调用了特定内置函数）
                  |
            代码生成器（将 IntrinsicKind 映射到目标平台指令）
```

## 主要类与结构体

### `SKSL_INTRINSIC_LIST` 宏

使用 X-Macro 模式定义的内置函数列表，包含以下类别：

| 类别 | 函数示例 |
|------|----------|
| 三角函数 | `sin`, `cos`, `tan`, `asin`, `acos`, `atan` |
| 双曲函数 | `sinh`, `cosh`, `tanh`, `asinh`, `acosh`, `atanh` |
| 指数函数 | `exp`, `exp2`, `log`, `log2`, `pow`, `sqrt`, `inversesqrt` |
| 取整函数 | `floor`, `ceil`, `round`, `roundEven`, `trunc`, `fract` |
| 数值函数 | `abs`, `sign`, `min`, `max`, `clamp`, `mix`, `step`, `smoothstep`, `saturate` |
| 向量函数 | `length`, `distance`, `dot`, `cross`, `normalize`, `faceforward`, `reflect`, `refract` |
| 矩阵函数 | `matrixCompMult`, `matrixInverse`, `outerProduct`, `transpose`, `determinant`, `inverse` |
| 比较函数 | `lessThan`, `lessThanEqual`, `greaterThan`, `greaterThanEqual`, `equal`, `notEqual` |
| 位操作 | `bitCount`, `findLSB`, `findMSB` |
| 类型转换 | `floatBitsToInt`, `floatBitsToUint`, `intBitsToFloat`, `uintBitsToFloat` |
| 打包/解包 | `packHalf2x16`, `unpackHalf2x16`, `packSnorm2x16`, `unpackSnorm2x16` 等 |
| 纹理操作 | `sample`, `sampleLod`, `sampleGrad`, `textureRead`, `textureWrite`, `textureWidth`, `textureHeight` |
| 原子操作 | `atomicAdd`, `atomicLoad`, `atomicStore` |
| 屏障 | `storageBarrier`, `workgroupBarrier` |
| 颜色转换 | `toLinearSrgb`, `fromLinearSrgb` |
| 求导 | `dFdx`, `dFdy`, `fwidth` |
| 子通道 | `subpassLoad` |
| 子效果 | `eval` |
| 其他 | `fma`, `frexp`, `ldexp`, `modf`, `mod`, `isinf`, `isnan`, `degrees`, `radians`, `not`, `all`, `any` |

### `enum IntrinsicKind : int8_t`

通过 `SKSL_INTRINSIC_LIST` 宏自动生成的枚举，每个内置函数对应一个值（如 `k_abs_IntrinsicKind`、`k_sin_IntrinsicKind`）。特殊值 `kNotIntrinsic = -1` 表示非内置函数。

### `IntrinsicMap`

类型别名 `skia_private::THashMap<std::string_view, IntrinsicKind>`，用于从函数名快速查找其 `IntrinsicKind`。

## 公共 API 函数

### `const IntrinsicMap& GetIntrinsicMap()`

返回包含所有内置函数名称到 `IntrinsicKind` 映射的全局哈希表。使用 `SkNoDestructor` 保证单例生命周期，首次调用时初始化。

### `IntrinsicKind FindIntrinsicKind(std::string_view functionName)`

根据函数名查找对应的 `IntrinsicKind`。
- 自动去除 `$` 前缀（私有函数标记）
- 如果函数不是内置函数，返回 `kNotIntrinsic`

## 内部实现细节

### X-Macro 的多重展开

同一个 `SKSL_INTRINSIC_LIST` 宏在不同上下文中展开为不同的代码：

```cpp
// 头文件中：展开为枚举值
#define SKSL_INTRINSIC(name) k_##name##_IntrinsicKind,
enum IntrinsicKind : int8_t { ... SKSL_INTRINSIC_LIST };

// cpp 文件中：展开为哈希表条目
#define SKSL_INTRINSIC(name) {#name, k_##name##_IntrinsicKind},
static const IntrinsicMap kAllIntrinsics(IntrinsicMap{ SKSL_INTRINSIC_LIST });
```

### SkNoDestructor 的使用

全局 `IntrinsicMap` 使用 `SkNoDestructor` 包装，避免在程序退出时析构静态对象可能导致的问题（如静态析构顺序问题），同时确保线程安全的延迟初始化。

### `$` 前缀处理

`FindIntrinsicKind` 会自动去除函数名中的 `$` 前缀。这是因为 SkSL 内部使用 `$` 前缀标记私有内置函数（如 `$sin`），但查找时需要匹配无前缀的名称。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkTHash.h` | 哈希映射实现（`THashMap`） |
| `SkNoDestructor.h` | 安全的静态对象生命周期管理 |
| `SkStringView.h` | `starts_with` 字符串前缀检测 |

## 设计模式与设计决策

1. **X-Macro 模式**：所有内置函数在一处集中定义，避免枚举值和查找表之间的不一致。
2. **`int8_t` 枚举底层类型**：100+ 个内置函数使用 `int8_t` 存储足够（-128 到 127），最大限度节省内存。
3. **全局单例映射**：`IntrinsicMap` 只创建一次，所有编译器实例共享，减少初始化开销。
4. **字符串视图键**：使用 `string_view` 作为哈希表键，避免查找时的字符串拷贝。

## 性能考量

- 哈希表查找为 O(1) 平均时间复杂度，适合在解析阶段高频调用
- `SkNoDestructor` 避免了退出时的析构开销
- `string_view` 键避免了每次查找的字符串分配
- `int8_t` 枚举类型紧凑，适合在 IR 节点中存储

## 相关文件

- `src/sksl/SkSLAnalysis.cpp` —— 使用 `IntrinsicKind` 检测特定内置函数的调用
- `src/sksl/SkSLCompiler.h` —— 编译器在编译过程中使用内置函数信息
- `src/sksl/codegen/` 目录下的代码生成器 —— 将 `IntrinsicKind` 映射到目标平台
- `src/sksl/ir/SkSLFunctionDeclaration.h` —— 函数声明中持有 `IntrinsicKind` 值
