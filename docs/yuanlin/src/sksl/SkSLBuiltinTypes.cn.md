# SkSLBuiltinTypes

> 源文件: src/sksl/SkSLBuiltinTypes.h, src/sksl/SkSLBuiltinTypes.cpp

## 概述

`BuiltinTypes` 类是SkSL类型系统的核心,包含了所有内置类型的定义。它提供了SkSL语言中使用的基本标量类型(如`float`, `int`, `bool`)、向量类型(如`float2`, `int3`)、矩阵类型(如`float3x3`)、纹理类型(如`sampler2D`)以及特殊类型(如`shader`, `colorFilter`)。这些类型在编译器初始化时创建,并在整个编译过程中保持不变。

该类采用了独特的设计:所有类型都作为`const std::unique_ptr<Type>`成员存储,确保类型对象的唯一性和生命周期管理。这种设计使得类型比较可以通过指针比较完成,显著提升了性能。BuiltinTypes还提供了GLSL兼容的别名类型(如`vec2`映射到`float2`),以及泛型类型用于函数重载匹配。

## 架构位置

在SkSL编译器架构中,BuiltinTypes位于基础设施层,是类型系统的根基:

```
编译器架构:
    BuiltinTypes (内置类型系统) ←── 当前组件
        ↓ 被引用
    Context (编译上下文)
        ↓ 使用
    Parser → TypeResolver → Optimizer → CodeGenerator
```

BuiltinTypes在编译器初始化时创建一次,然后通过Context传递给所有需要类型信息的组件。

## 主要类与结构体

### BuiltinTypes 类

类包含175个类型定义,涵盖以下类别:

#### 1. 标量类型 (Scalar Types)
```cpp
const std::unique_ptr<Type> fFloat;   // 32位浮点数
const std::unique_ptr<Type> fHalf;    // 16位浮点数
const std::unique_ptr<Type> fInt;     // 32位有符号整数
const std::unique_ptr<Type> fUInt;    // 32位无符号整数
const std::unique_ptr<Type> fShort;   // 16位有符号整数
const std::unique_ptr<Type> fUShort;  // 16位无符号整数
const std::unique_ptr<Type> fBool;    // 布尔类型
```

每个标量类型都有对应的向量类型(2/3/4分量):
- `fFloat2`, `fFloat3`, `fFloat4`
- `fHalf2`, `fHalf3`, `fHalf4`
- 等等

#### 2. 矩阵类型 (Matrix Types)
```cpp
// Float矩阵
const std::unique_ptr<Type> fFloat2x2;  // 2列2行
const std::unique_ptr<Type> fFloat3x3;  // 3列3行
const std::unique_ptr<Type> fFloat4x4;  // 4列4行
// ... 其他尺寸的float矩阵

// Half矩阵
const std::unique_ptr<Type> fHalf2x2;
const std::unique_ptr<Type> fHalf3x3;
// ... 其他half矩阵
```

#### 3. 特殊类型 (Special Types)
```cpp
const std::unique_ptr<Type> fVoid;          // void类型
const std::unique_ptr<Type> fInvalid;       // 无效类型(错误标记)
const std::unique_ptr<Type> fPoison;        // 中毒类型(错误传播)
const std::unique_ptr<Type> fFloatLiteral;  // 浮点字面量类型
const std::unique_ptr<Type> fIntLiteral;    // 整数字面量类型
```

#### 4. 纹理和采样器类型 (Texture & Sampler Types)
```cpp
// sample访问的纹理
const std::unique_ptr<Type> fTexture2D_sample;
const std::unique_ptr<Type> fTextureExternalOES;
const std::unique_ptr<Type> fTexture2DRect;

// read/write访问的纹理
const std::unique_ptr<Type> fTexture2D;
const std::unique_ptr<Type> fReadOnlyTexture2D;
const std::unique_ptr<Type> fWriteOnlyTexture2D;

// 采样器
const std::unique_ptr<Type> fSampler2D;
const std::unique_ptr<Type> fSamplerExternalOES;
```

#### 5. GLSL兼容别名 (GLSL Aliases)
```cpp
const std::unique_ptr<Type> fVec2;   // 别名到 float2
const std::unique_ptr<Type> fVec3;   // 别名到 float3
const std::unique_ptr<Type> fIVec2;  // 别名到 int2
const std::unique_ptr<Type> fMat2;   // 别名到 float2x2
```

#### 6. 泛型类型 (Generic Types)
```cpp
const std::unique_ptr<Type> fGenType;   // {float, float2, float3, float4}
const std::unique_ptr<Type> fGenHType;  // {half, half2, half3, half4}
const std::unique_ptr<Type> fGenIType;  // {int, int2, int3, int4}
const std::unique_ptr<Type> fMat;       // 所有float矩阵
const std::unique_ptr<Type> fVec;       // {float2, float3, float4}
```

## 公共 API 函数

### 构造函数

```cpp
BuiltinTypes();
```

**功能**: 初始化所有内置类型。

**实现细节**:

1. **标量类型创建**: 使用`Type::MakeScalarType`
   ```cpp
   fFloat(Type::MakeScalarType("float", "f", Type::NumberKind::kFloat,
                               /*priority=*/10, /*bitWidth=*/32))
   ```

2. **向量类型创建**: 使用`Type::MakeVectorType`
   ```cpp
   fFloat2(Type::MakeVectorType("float2", "f2", *fFloat, /*columns=*/2))
   ```

3. **矩阵类型创建**: 使用`Type::MakeMatrixType`
   ```cpp
   fFloat3x3(Type::MakeMatrixType("float3x3", "f33", *fFloat,
                                  /*columns=*/3, /*rows=*/3))
   ```

4. **别名类型创建**: 使用`Type::MakeAliasType`
   ```cpp
   fVec2(Type::MakeAliasType("vec2", *fFloat2))
   ```

5. **泛型类型创建**: 使用`Type::MakeGenericType`
   ```cpp
   fGenType(Type::MakeGenericType("$genType",
            {{fFloat.get(), fFloat2.get(), fFloat3.get(), fFloat4.get()}},
            fFloat.get()))
   ```

## 内部实现细节

### 类型优先级系统

每个数值类型都有一个优先级(priority),用于类型转换规则:
- `float`: 10 (最高)
- `half`: 9
- `$floatLiteral`: 8
- `int`: 7
- `uint`: 6
- `$intLiteral`: 5
- `short`: 4
- `ushort`: 3
- `bool`: 0

较高优先级的类型在混合运算中保留,例如`int + float` → `float`。

### 类型缩写 (Type Abbreviations)

每个类型都有一个缩写字符串,用于名称修饰(name mangling):
- `f` - float
- `h` - half
- `i` - int
- `I` - uint
- `b` - bool
- `f3` - float3
- `f44` - float4x4

### 泛型类型的内部表示

泛型类型存储一组可能的具体类型:
```cpp
fGenType = {float, float2, float3, float4}
```

在函数重载解析时,编译器检查参数是否匹配泛型类型中的任何一个具体类型。

### 纹理访问权限

纹理类型分为三种访问模式:
- **kSample**: 用于传统的采样操作(`texture2D`)
- **kRead**: 只读访问(`readonlyTexture2D`)
- **kWrite**: 只写访问(`writeonlyTexture2D`)
- **kReadWrite**: 读写访问(`texture2D`)

### Poison类型机制

`fPoison`类型使用特殊标记`Compiler::POISON_TAG`,用于:
- 标记发生错误的表达式
- 防止错误级联(一个错误不会触发多个错误消息)
- 在错误恢复后继续编译

## 依赖关系

### 内部依赖

| 依赖项 | 用途 |
|--------|------|
| `ir/SkSLType.h` | Type类的定义和工厂方法 |
| `SkSLCompiler.h` | POISON_TAG常量 |
| `spirv.h` | SPIR-V维度常量(SpvDim2D等) |

### 外部使用者

| 使用者 | 用途 |
|--------|------|
| `Context` | 持有BuiltinTypes的引用 |
| `Parser` | 解析类型名称 |
| `TypeResolver` | 类型检查和转换 |
| `ConstantFolder` | 类型范围检查 |

## 设计模式与设计决策

### 1. 单例模式的变体

BuiltinTypes在Compiler中创建一次,通过Context共享。这避免了全局单例的问题,同时保证了类型对象的唯一性。

### 2. 不可变对象

所有类型都是`const std::unique_ptr<Type>`,一旦创建就不能修改。这确保了类型系统的稳定性。

### 3. 类型标识通过指针

由于类型对象唯一,可以通过指针比较判断类型相等:
```cpp
if (exprType == context.fTypes.fFloat.get()) { ... }
```

这比字符串比较快得多。

### 4. X-Macro 模式

虽然在头文件中没有使用,但相关的模块系统使用X-Macro来管理类型列表,保持代码的一致性。

## 性能考量

### 1. 类型比较性能

指针比较是O(1)操作:
```cpp
type1 == type2  // 比较指针地址,非常快
```

### 2. 内存局部性

所有类型都在BuiltinTypes对象中连续存储,具有良好的缓存局部性。

### 3. 避免动态分配

类型在编译器初始化时一次性创建,编译过程中不再分配类型对象。

### 4. 优化的类型查找

通过Context直接访问类型,无需哈希表查找或字符串比较。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/sksl/ir/SkSLType.h` | 依赖 | Type类定义 |
| `src/sksl/SkSLContext.h` | 使用者 | 持有BuiltinTypes引用 |
| `src/sksl/SkSLCompiler.h` | 依赖 | 提供POISON_TAG |
| `src/sksl/SkSLParser.h` | 使用者 | 解析类型 |
| `spirv.h` | 依赖 | SPIR-V常量 |
