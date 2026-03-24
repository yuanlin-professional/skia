# SkSL Type - 类型系统

> 源文件:
> - `src/sksl/ir/SkSLType.h`
> - `src/sksl/ir/SkSLType.cpp`

## 概述

`Type` 是 SkSL 编译器类型系统的核心类,表示 SkSL 中的所有类型:标量(float, int, bool, half, uint)、向量(float2-4)、矩阵(mat2-4)、数组、结构体、采样器、纹理、原子类型以及特殊的泛型和字面量类型等。

该文件定义了类型层次结构的基类和工厂方法,以及大量的类型查询接口。`.cpp` 文件包含了所有具体类型子类的实现(AliasType、ArrayType、GenericType、LiteralType、ScalarType、AtomicType、MatrixType、VectorType、StructType 等)。

这是 SkSL IR 中最大的文件之一(头文件 680+ 行,实现文件 1400+ 行),反映了类型系统在着色器语言编译器中的核心地位。

## 架构位置

```
SkSL 编译器
└── IR (中间表示)
    └── 符号 (Symbol)
        └── Type  <-- 本文件 (基类)
            ├── AliasType (类型别名, 如 vec4 -> float4)
            ├── ArrayType (数组)
            ├── GenericType (泛型, 如 $genType)
            ├── LiteralType (字面量类型, 如 $intLiteral)
            ├── ScalarType (标量: float, half, int, uint, bool, short, ushort)
            ├── AtomicType (原子类型: atomicUint)
            ├── MatrixType (矩阵)
            ├── VectorType (向量)
            ├── StructType (结构体)
            ├── TextureType (纹理)
            └── SamplerType (采样器)
```

`Type` 继承自 `Symbol`,可以被添加到符号表中,支持名称查找。

## 主要类与结构体

### `CoercionCost`

类型强制转换的代价结构体,用于重载解析:

| 成员 | 说明 |
|------|------|
| `fNormalCost` | 普通转换代价(如 half -> float) |
| `fNarrowingCost` | 窄化转换代价(如 float -> half) |
| `fImpossible` | 是否不可能转换 |

提供 `Free()`、`Normal(cost)`、`Narrowing(cost)`、`Impossible()` 工厂方法。

### `Field`

结构体字段描述:

| 成员 | 类型 | 说明 |
|------|------|------|
| `fPosition` | `Position` | 源码位置 |
| `fLayout` | `Layout` | 布局限定符 |
| `fModifierFlags` | `ModifierFlags` | 修饰符 |
| `fName` | `std::string_view` | 字段名 |
| `fType` | `const Type*` | 字段类型 |

### `Type` (基类)

#### TypeKind 枚举

| 值 | 说明 |
|----|------|
| kArray | 数组 |
| kAtomic | 原子类型 |
| kGeneric | 泛型 |
| kLiteral | 字面量类型 |
| kMatrix | 矩阵 |
| kOther | 其他(void 等) |
| kSampler | 采样器 |
| kSeparateSampler | 独立采样器 |
| kScalar | 标量 |
| kStruct | 结构体 |
| kTexture | 纹理 |
| kVector | 向量 |
| kVoid | void |
| kColorFilter / kShader / kBlender | Skia 管线阶段类型 |

#### NumberKind 枚举

| 值 | 说明 |
|----|------|
| kFloat | 浮点 |
| kSigned | 有符号整数 |
| kUnsigned | 无符号整数 |
| kBoolean | 布尔 |
| kNonnumeric | 非数值 |

## 公共 API 函数

### 类型创建工厂方法

| 方法 | 说明 |
|------|------|
| `MakeArrayType` | 创建数组类型 |
| `MakeAliasType` | 创建类型别名 |
| `MakeGenericType` | 创建泛型类型 |
| `MakeLiteralType` | 创建字面量类型 |
| `MakeMatrixType` | 创建矩阵类型 |
| `MakeSamplerType` | 创建采样器类型 |
| `MakeScalarType` | 创建标量类型 |
| `MakeSpecialType` | 创建特殊类型 |
| `MakeStructType` | 创建结构体类型 |
| `MakeTextureType` | 创建纹理类型 |
| `MakeVectorType` | 创建向量类型 |
| `MakeAtomicType` | 创建原子类型 |

### 类型查询方法

| 方法 | 说明 |
|------|------|
| `isScalar()`, `isVector()`, `isMatrix()` | 基本类型分类 |
| `isArray()`, `isStruct()`, `isVoid()` | 复合类型分类 |
| `isFloat()`, `isSigned()`, `isUnsigned()`, `isBoolean()`, `isInteger()` | 数值类型查询 |
| `isOpaque()`, `isEffectChild()`, `isAtomic()` | 特殊类型查询 |
| `isLiteral()`, `isGeneric()` | 编译器内部类型查询 |
| `isOrContainsArray()`, `isOrContainsAtomic()`, `isOrContainsBool()` | 递归类型查询 |

### 类型属性方法

| 方法 | 说明 |
|------|------|
| `componentType()` | 分量类型(向量/矩阵的元素类型,数组的基类型) |
| `columnType()` | 矩阵的列类型 |
| `columns()`, `rows()` | 列数和行数 |
| `slotCount()` | 标量槽数 |
| `slotType(n)` | 第 n 个槽的类型 |
| `bitWidth()` | 位宽(32 或 16) |
| `minimumValue()`, `maximumValue()` | 类型的值域 |
| `priority()` | 类型优先级(用于类型提升) |

### 类型转换方法

| 方法 | 说明 |
|------|------|
| `canCoerceTo()` | 是否可以隐式转换到目标类型 |
| `coercionCost()` | 计算转换代价 |
| `coerceExpression()` | 将表达式强制转换为此类型 |
| `toCompound()` | 转换为指定列数/行数的复合类型 |
| `applyQualifiers()` | 应用精度和访问级别限定符 |

### 类型验证方法

| 方法 | 说明 |
|------|------|
| `isAllowedInES2()` | 是否允许在 ES2 中使用 |
| `isAllowedInUniform()` | 是否允许作为 uniform |
| `checkForOutOfRangeLiteral()` | 检测越界字面量 |
| `checkIfUsableInArray()` | 是否可用作数组基类型 |
| `convertArraySize()` | 验证并转换数组大小 |

## 内部实现细节

### 具体类型子类 (在 .cpp 中定义)

#### ScalarType
存储 `NumberKind`、优先级和位宽。定义了各标量类型的最小/最大值(使用 `std::numeric_limits`)。

#### VectorType / MatrixType
存储分量类型和维度信息。`MatrixType` 的 `slotCount()` 为 `columns * rows`。

#### ArrayType
存储分量类型和元素数量。支持未确定大小的数组(`kUnsizedArray = -1`)。禁止多维数组。

#### StructType
存储字段列表。实现结构体嵌套深度限制(最大 `kMaxStructDepth = 8`)。`MakeStructType` 会验证:
- 不允许 void 类型的字段
- 不允许不透明类型的字段
- ES2 模式下不允许数组字段
- 接口块中不允许不透明类型(原子类型除外)

#### GenericType
存储可协变类型列表(最多 9 个)和槽类型。用于内置函数的泛型参数(如 `$genType` 对应 `float`/`float2`/`float3`/`float4`)。

#### LiteralType
表示字面量的"未确定"类型(如 `$intLiteral`),有优先级属性用于类型推导。

#### AliasType
将所有类型查询委托给目标类型,用于 `vec4` → `float4` 这样的别名。

### 类型强制转换 (`coercionCost`)

转换代价计算规则:
1. 类型完全匹配:代价为 `Free()`
2. 数组类型:分量类型的转换代价
3. 向量/矩阵类型:维度匹配时,分量类型的转换代价
4. 字面量类型:根据优先级差计算窄化代价
5. 标量类型:数值类型提升为 `Normal(priority_diff)`,窄化为 `Narrowing(priority_diff)`
6. 其他情况:`Impossible()`

### 表达式类型强制转换 (`coerceExpression`)

1. 如果类型匹配,直接返回
2. 处理字面量类型的特殊情况
3. 对标量使用 `ConstructorScalarCast`
4. 对复合类型使用 `ConstructorCompoundCast`
5. 对数组使用 `ConstructorArrayCast`

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLSymbol.h` | 基类 |
| `SkSLLayout.h` | Field 的布局信息 |
| `SkSLModifierFlags.h` | Field 的修饰符 |
| `spirv.h` | SpvDim_ (纹理维度) |
| `SkSLConstructorScalarCast.h` | 标量类型转换 |
| `SkSLConstructorCompoundCast.h` | 复合类型转换 |
| `SkSLConstructorArrayCast.h` | 数组类型转换 |
| `SkSLConstantFolder.h` | 常量值处理 |
| `SkSLBuiltinTypes.h` | 内置类型引用 |
| `SkSLContext.h` | 编译上下文 |
| `SkSLErrorReporter.h` | 错误报告 |
| `SkSLSymbolTable.h` | 符号表(类型注册) |
| `SkHalf.h` | 半精度浮点值域计算 |

## 设计模式与设计决策

1. **继承层次**: 使用虚函数和子类实现不同类型的行为差异,基类提供默认实现和类型查询接口
2. **实现隐藏**: 具体类型子类(ScalarType、VectorType 等)定义在 `.cpp` 文件中,头文件仅暴露 `Type` 基类
3. **工厂方法**: 所有类型通过静态工厂方法创建,返回 `unique_ptr<Type>`,支持多态
4. **内置类型单例**: 内置类型在根符号表中存在唯一实例,不需要克隆
5. **类型匹配**: `matches()` 通过指针比较(在 `resolve()` 后)实现高效的类型相等判断
6. **别名透明**: `AliasType` 的 `resolve()` 返回目标类型,使别名在类型比较中透明
7. **值域计算**: `ScalarType` 使用 `std::numeric_limits` 精确定义各数值类型的值域范围
8. **结构体嵌套限制**: 通过 `kMaxStructDepth = 8` 防止过深的结构体嵌套

## 性能考量

- 类型匹配 (`matches()`) 通过指针比较实现,O(1) 复杂度
- `coercionCost()` 的计算复杂度与类型深度成正比(数组/结构体)
- 内置类型在根符号表中缓存,不需要重复创建
- `slotCount()` 对于数组和结构体需要累加计算,但结果不缓存(每次调用都重新计算)
- `abbreviatedName` 使用固定大小的字符数组(最大 3+1 字节),完全避免堆分配

## 相关文件

- `src/sksl/SkSLBuiltinTypes.h` -- 所有内置类型的定义和初始化
- `src/sksl/ir/SkSLSymbol.h` -- 符号基类
- `src/sksl/ir/SkSLLayout.h` -- 布局限定符
- `src/sksl/ir/SkSLModifierFlags.h` -- 修饰符标志
- `src/sksl/ir/SkSLConstructorScalarCast.h` -- 标量类型转换
- `src/sksl/ir/SkSLConstructorCompoundCast.h` -- 复合类型转换
- `src/sksl/ir/SkSLConstructorArrayCast.h` -- 数组类型转换
- `src/sksl/ir/SkSLSymbolTable.h` -- 符号表(类型存储)
- `src/sksl/spirv.h` -- SPIR-V 常量(纹理维度等)
