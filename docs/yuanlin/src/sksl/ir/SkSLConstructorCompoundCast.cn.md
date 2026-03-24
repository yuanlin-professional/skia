# SkSLConstructorCompoundCast

> 源文件: src/sksl/ir/SkSLConstructorCompoundCast.h, src/sksl/ir/SkSLConstructorCompoundCast.cpp

## 概述

`ConstructorCompoundCast` 类是 SkSL（Skia Shading Language）中间表示(IR)中的构造函数表达式类型，专门用于表示向量或矩阵的类型转换，例如 `half3(myInt3)` 或 `float4x4(myHalf4x4)`。它继承自 `SingleArgumentConstructor` 类，总是包含一个维度匹配的向量或矩阵参数。该类与 `ConstructorMatrixResize` 不同，后者处理矩阵尺寸改变（如 `float3x3` 到 `float4x4`），而本类仅处理相同维度下的分量类型转换（如 `int` 到 `float`）。该类实现了编译时常量折叠优化，能够在编译期对常量复合类型进行类型转换。

## 架构位置

`ConstructorCompoundCast` 位于 Skia 的 SkSL 编译器的 IR 表达式层中：

```
skia/
  src/
    sksl/
      ir/
        SkSLIRNode.h                         # IR 节点基类
        SkSLExpression.h                     # 表达式基类
        SkSLConstructor.h                    # 构造函数基类
          ├─ SingleArgumentConstructor       # ConstructorCompoundCast 的父类
          └─ MultiArgumentConstructor
        SkSLConstructorCompoundCast.h/cpp    # 本文件，复合类型转换
        SkSLConstructorScalarCast.h          # 标量类型转换
        SkSLConstructorSplat.h               # 单值扩展构造
        SkSLConstructorDiagonalMatrix.h      # 对角矩阵构造
        SkSLConstructorCompound.h            # 复合构造
        SkSLConstructorMatrixResize.h        # 矩阵尺寸改变
      SkSLConstantFolder.h                   # 常量折叠
      SkSLAnalysis.h                         # IR 分析工具
```

在优化流程中的位置：
```
解析阶段 → 类型转换识别 → Make (优化) → IR 节点或常量表达式
                                  ↓
                        常量折叠（编译时求值）
```

## 主要类与结构体

### ConstructorCompoundCast 类

```cpp
class ConstructorCompoundCast final : public SingleArgumentConstructor {
public:
    inline static constexpr Kind kIRNodeKind = Kind::kConstructorCompoundCast;

    // 构造函数
    ConstructorCompoundCast(Position pos, const Type& type, std::unique_ptr<Expression> arg);

    // 工厂方法：创建复合类型转换（带优化）
    static std::unique_ptr<Expression> Make(const Context& context,
                                            Position pos,
                                            const Type& type,
                                            std::unique_ptr<Expression> arg);

    // 克隆表达式
    std::unique_ptr<Expression> clone(Position pos) const override;

private:
    using INHERITED = SingleArgumentConstructor;
};
```

### 继承层次

```
Expression (基类)
  └─ SingleArgumentConstructor (单参数构造函数基类)
      └─ ConstructorCompoundCast (复合类型转换，终结类)
```

`SingleArgumentConstructor` 提供：
- 单参数管理（`Expression* argument()`）
- 基本的构造函数接口

## 公共 API 函数

### 构造函数

```cpp
ConstructorCompoundCast(Position pos, const Type& type, std::unique_ptr<Expression> arg)
```

**功能**: 创建复合类型转换表达式对象。

**参数**:
- `pos`: 表达式在源代码中的位置
- `type`: 目标类型（向量或矩阵）
- `arg`: 源表达式（必须是相同维度的向量或矩阵）

**注意**: 通常不直接调用，而是通过 `Make` 工厂方法创建。

### Make (工厂方法)

```cpp
static std::unique_ptr<Expression> Make(const Context& context,
                                        Position pos,
                                        const Type& type,
                                        std::unique_ptr<Expression> arg)
```

**功能**: 创建复合类型转换表达式，并应用编译时优化。

**参数**:
- `context`: 编译上下文
- `pos`: 源代码位置
- `type`: 目标类型（向量或矩阵）
- `arg`: 源表达式

**断言验证**:
1. 目标类型是向量或矩阵（`type.isVector() || type.isMatrix()`）
2. 目标类型在 ES2 中合法（`type.isAllowedInES2(context)`）
3. 源和目标的向量/矩阵属性匹配：
   - `arg->type().isVector() == type.isVector()`
   - `arg->type().isMatrix() == type.isMatrix()`
4. 维度完全匹配：
   - `type.columns() == arg->type().columns()`
   - `type.rows() == arg->type().rows()`

**优化策略**:

1. **无操作转换消除**:
   ```cpp
   if (type.matches(arg->type())) {
       arg->setPosition(pos);
       return arg;  // 类型相同，直接返回原表达式
   }
   ```

2. **常量变量展开**:
   ```cpp
   arg = ConstantFolder::MakeConstantValueForVariable(pos, std::move(arg));
   ```
   将常量变量引用替换为其编译时常量值。

3. **编译时常量折叠**:
   ```cpp
   if (Analysis::IsCompileTimeConstant(*arg)) {
       return cast_constant_composite(context, pos, type, std::move(arg));
   }
   ```
   如果参数是编译时常量，直接在编译期执行类型转换。

4. **运行时转换**:
   如果优化不适用，创建 `ConstructorCompoundCast` 节点。

**返回**: 可能是原表达式、常量表达式或 `ConstructorCompoundCast` 对象。

### clone

```cpp
std::unique_ptr<Expression> clone(Position pos) const override
```

**功能**: 克隆复合类型转换表达式到新位置。

**实现**: 递归克隆参数表达式（`argument()->clone()`），保留类型信息。

## 内部实现细节

### 编译时常量折叠

辅助函数 `cast_constant_composite` 处理编译时常量转换：

```cpp
static std::unique_ptr<Expression> cast_constant_composite(
    const Context& context,
    Position pos,
    const Type& destType,
    std::unique_ptr<Expression> constCtor)
```

**处理流程**:

1. **Splat 优化**:
   ```cpp
   if (constCtor->is<ConstructorSplat>()) {
       // half4(7) → int4(7)
       ConstructorSplat& splat = constCtor->as<ConstructorSplat>();
       return ConstructorSplat::Make(
           context, pos, destType,
           ConstructorScalarCast::Make(context, pos, scalarType, splat.argument()));
   }
   ```
   将单值扩展构造的类型转换简化为单值类型转换。

2. **对角矩阵优化**:
   ```cpp
   if (constCtor->is<ConstructorDiagonalMatrix>() && destType.isMatrix()) {
       // float3x3(2) → half3x3(2)
       ConstructorDiagonalMatrix& matrixCtor = constCtor->as<ConstructorDiagonalMatrix>();
       return ConstructorDiagonalMatrix::Make(
           context, pos, destType,
           ConstructorScalarCast::Make(context, pos, scalarType, matrixCtor.argument()));
   }
   ```
   将对角矩阵构造的类型转换简化为对角值类型转换。

3. **逐分量转换**:
   ```cpp
   size_t numSlots = destType.slotCount();
   double typecastArgs[16];
   for (size_t index = 0; index < numSlots; ++index) {
       std::optional<double> slotVal = constCtor->getConstantValue(index);
       if (scalarType.checkForOutOfRangeLiteral(context, *slotVal, constCtor->fPosition)) {
           *slotVal = 0.0;  // 越界时置零，避免错误级联
       }
       typecastArgs[index] = *slotVal;
   }
   return ConstructorCompound::MakeFromConstants(context, pos, destType, typecastArgs);
   ```

   **步骤**:
   - 提取源表达式的每个分量常量值
   - 检查每个值是否在目标类型范围内
   - 越界值替换为 0（已报告错误）
   - 从常量数组创建复合构造表达式

### 常量值提取

使用 `getConstantValue(int n)` 接口提取分量值：
```cpp
std::optional<double> slotVal = constCtor->getConstantValue(index);
```

**slot（槽位）概念**:
- 向量：每个分量一个槽位（`vec3` 有 3 个槽位）
- 矩阵：按列优先顺序排列（`mat2x3` 有 6 个槽位）

### 范围检查

类型转换时验证值是否溢出：
```cpp
if (scalarType.checkForOutOfRangeLiteral(context, *slotVal, constCtor->fPosition)) {
    *slotVal = 0.0;
}
```

**示例**:
- `byte(300)` → 越界，报错并置零
- `int(-1)` → `uint` 转换 → 越界，报错并置零

### 优化输出质量

特殊处理 Splat 和对角矩阵以生成更简洁的代码：
```cpp
// 优化前: half4(half(0), half(0), half(0), half(0))
// 优化后: half4(0)

// 优化前: half3x3(half(1), 0, 0, 0, half(1), 0, 0, 0, half(1))
// 优化后: half3x3(1)
```

## 依赖关系

### 直接依赖

**头文件**:
- `SkSLConstructor.h`: 构造函数基类
- `SkSLExpression.h`: 表达式接口
- `SkSLType.h`: 类型系统
- `SkSLPosition.h`: 位置信息

**实现文件额外依赖**:
- `SkSLConstantFolder.h`: 常量折叠工具
- `SkSLAnalysis.h`: IR 分析（编译时常量检测）
- `SkSLConstructorScalarCast.h`: 标量类型转换
- `SkSLConstructorSplat.h`: 单值扩展
- `SkSLConstructorDiagonalMatrix.h`: 对角矩阵
- `SkSLConstructorCompound.h`: 复合构造

### 被依赖关系

- **类型转换系统**: 隐式或显式类型转换时创建 `ConstructorCompoundCast`
- **优化传递**: 常量传播和表达式简化
- **代码生成器**: 将类型转换映射到目标语言（GLSL, SPIR-V, Metal）

### 相关构造函数类型

- **ConstructorScalarCast**: 标量类型转换（如 `int` → `float`）
- **ConstructorMatrixResize**: 矩阵尺寸改变（如 `mat2x2` → `mat3x3`）
- **ConstructorSplat**: 单值扩展（如 `vec4(1)` → `vec4(1, 1, 1, 1)`）
- **ConstructorCompound**: 多参数复合构造

## 设计模式与设计决策

### 设计模式

1. **工厂方法模式**: `Make` 方法封装创建逻辑和优化策略
2. **策略模式**: 根据参数类型选择不同的常量折叠策略
3. **模板方法模式**: 继承 `SingleArgumentConstructor` 的通用构造逻辑

### 设计决策

**为什么区分 CompoundCast 和 MatrixResize？**
- **CompoundCast**: 维度不变，仅分量类型改变（`int3` → `float3`）
- **MatrixResize**: 分量类型不变，矩阵尺寸改变（`float2x2` → `float3x3`）
- 分离职责，简化代码生成和优化逻辑

**为什么总是单参数？**
- 类型转换的语义要求：源和目标维度完全匹配
- 多参数构造使用 `ConstructorCompound`
- 单参数简化类型检查和优化

**为什么优先优化 Splat 和对角矩阵？**
- 提升输出代码可读性（`half4(0)` vs `half4(0,0,0,0)`）
- 减少 IR 节点数量，加速后续传递
- 符合人类编写代码的习惯

**为什么常量折叠使用 double 数组？**
- `double` 可以精确表示所有 SkSL 数值类型的常量值
- 统一的中间表示，简化转换逻辑
- 范围检查在转换到目标类型时进行

**为什么越界值置零而非保留原值？**
- 避免错误级联：后续使用越界值可能导致更多错误
- 错误已报告，置零是安全的回退值
- 编译仍可继续，生成部分可用的 IR

**为什么无操作转换直接返回原表达式？**
- 消除冗余节点，减少 IR 大小
- 避免不必要的代码生成开销
- 保持位置信息（`setPosition`）以便调试

## 性能考量

### 编译时优化收益

**常量折叠的性能提升**:
- **编译期**: 将运行时类型转换提前到编译期
- **运行时**: 消除运行时转换指令，减少 GPU 计算
- **代码大小**: 常量表达式通常更紧凑

**示例**:
```cpp
// 编译前
const int3 v = int3(1, 2, 3);
float3 result = float3(v);  // 运行时转换

// 编译后
float3 result = float3(1.0, 2.0, 3.0);  // 常量
```

### 内存占用

单个 `ConstructorCompoundCast` 对象：
- `SingleArgumentConstructor` 基类: ~24 字节（虚表 + 位置 + 类型 + 参数指针）
- **总计**: ~24 字节

优化后消除：
- 常量折叠成功时，节点被替换为 `ConstructorCompound` 或更简单的表达式
- 无操作转换被完全消除

### 编译时开销

**常量折叠的成本**:
1. **常量检测**: `Analysis::IsCompileTimeConstant` - O(表达式树深度)
2. **值提取**: 遍历所有槽位 - O(分量数)
3. **范围检查**: 每个分量检查 - O(分量数)
4. **构造创建**: 创建新的常量表达式 - O(分量数)

**总体复杂度**: O(分量数 × 表达式深度)

对于典型向量（3-4 分量）和矩阵（9-16 分量），开销可接受。

### 潜在瓶颈

- **大型矩阵转换**: `mat4x4` 有 16 个槽位，提取和检查开销较大
- **深层常量表达式**: 嵌套构造函数的常量检测可能递归多层
- **频繁的无操作转换**: 类型推断不准确导致生成冗余转换节点

## 相关文件

### 核心相关文件

- **src/sksl/ir/SkSLConstructor.h**: 构造函数基类
- **src/sksl/ir/SkSLExpression.h**: 表达式基类
- **src/sksl/ir/SkSLType.h**: 类型系统
- **src/sksl/SkSLConstantFolder.h**: 常量折叠工具

### 其他构造函数类型

- **src/sksl/ir/SkSLConstructorScalarCast.h**: 标量转换
- **src/sksl/ir/SkSLConstructorMatrixResize.h**: 矩阵尺寸改变
- **src/sksl/ir/SkSLConstructorSplat.h**: 单值扩展
- **src/sksl/ir/SkSLConstructorDiagonalMatrix.h**: 对角矩阵
- **src/sksl/ir/SkSLConstructorCompound.h**: 复合构造

### 代码生成相关

- **src/sksl/codegen/SkSLGLSLCodeGenerator.cpp**: GLSL 代码生成
- **src/sksl/codegen/SkSLSPIRVCodeGenerator.cpp**: SPIR-V 代码生成
- **src/sksl/codegen/SkSLMetalCodeGenerator.cpp**: Metal 代码生成

### 使用示例

```cpp
// 用户代码
int3 intVec = int3(1, 2, 3);
float3 floatVec = float3(intVec);  // 复合类型转换

// IR 构建（优化前）
auto cast = ConstructorCompoundCast::Make(
    context,
    pos,
    float3Type,
    std::move(intVecExpr)
);

// 编译时优化（常量折叠）
// intVecExpr 是常量 → cast 被替换为 ConstructorCompound(1.0, 2.0, 3.0)
```
