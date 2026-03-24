# SkSL ConstructorScalarCast - 标量类型转换构造器

> 源文件:
> - `src/sksl/ir/SkSLConstructorScalarCast.h`
> - `src/sksl/ir/SkSLConstructorScalarCast.cpp`

## 概述

`ConstructorScalarCast` 表示 SkSL IR 中的标量类型转换操作,例如 `float(intVariable)` 或 `int(3.14)`。该类处理一种基本标量类型到另一种标量类型的显式转换。

当转换涉及编译期常量时,该类能够在编译期完成转换(如 `int(4.1)` 直接生成字面量 `4`)。它还支持一种特殊情况:通过字面量类型(`$intLiteral`、`$floatLiteral`)进行的中间转换可以被消除。

## 架构位置

```
SkSL 编译器
└── IR (中间表示)
    └── 表达式 (Expression)
        └── 构造器 (Constructor)
            └── SingleArgumentConstructor
                └── ConstructorScalarCast  <-- 本文件
```

## 主要类与结构体

### `ConstructorScalarCast`

继承自 `SingleArgumentConstructor`。

| 成员 | 说明 |
|------|------|
| `kIRNodeKind` | 值为 `Kind::kConstructorScalarCast` |

## 公共 API 函数

### `ConstructorScalarCast::Convert`

```cpp
static std::unique_ptr<Expression> Convert(const Context& context,
                                           Position pos,
                                           const Type& rawType,
                                           ExpressionArray args);
```

完整类型检查的转换方法:

1. **参数数量**: 恰好一个参数
2. **参数类型**: 必须是标量(向量/矩阵到标量的切片不被允许,建议使用 `.x` 或 `[0][0]`)
3. **值域检查**: 检测编译期常量的越界
4. 调用 `Make()` 创建节点

### `ConstructorScalarCast::Make`

```cpp
static std::unique_ptr<Expression> Make(const Context& context,
                                        Position pos,
                                        const Type& type,
                                        std::unique_ptr<Expression> arg);
```

带优化的工厂方法:

1. **空操作消除**: 类型匹配时直接返回原表达式
2. **常量变量替换**: 通过 `ConstantFolder` 替换常量变量
3. **字面量编译期转换**: 如果参数是字面量,直接计算转换结果值(越界时生成 0 并报错)
4. **中间字面量类型消除**: 如果参数是 `$intLiteral(...)` 或 `$floatLiteral(...)` 形式的转换,消除中间转换

## 内部实现细节

### 向量/矩阵切片拒绝

当参数是向量时,提示使用 `.x` 代替;当参数是矩阵时,提示使用 `[0][0]`。这是 SkSL 不同于某些 GLSL 实现的设计选择。

### 字面量类型中间转换消除

SkSL 内部使用 `$intLiteral` 和 `$floatLiteral` 类型表示类型灵活的字面量。当出现 `float($intLiteral(myBool))` 这样的嵌套转换时,外层转换可以直接作用于最内层的参数,消除中间的字面量类型转换。

### 越界字面量处理

编译期转换时,如果结果值超出目标类型的范围(这可能在代码内联后发生),将值重置为 0.0 并报告错误,而非返回 null。这避免了错误级联。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLConstructor.h` | 基类 |
| `SkSLConstantFolder.h` | 常量变量替换 |
| `SkSLLiteral.h` | 字面量创建 |
| `SkSLType.h` | 类型系统、值域检查 |
| `SkSLContext.h` | 编译上下文 |
| `SkSLErrorReporter.h` | 错误报告 |

## 设计模式与设计决策

1. **编译期折叠**: 字面量的类型转换在编译期完成,生成新的字面量节点
2. **中间类型消除**: 消除字面量类型的中间转换链,简化 IR
3. **容错处理**: 越界值不返回 null(避免错误级联),而是报错并使用安全的默认值
4. **切片禁止**: 不允许向量/矩阵到标量的隐式切片,提供明确的替代建议

## 性能考量

- 字面量的编译期转换避免了运行时类型转换指令
- 空操作和中间转换消除减少了 IR 节点数量
- 常量变量替换在创建阶段完成,为后续优化铺路
- `Convert()` 中的类型检查快速路径:参数数量不为 1 时立即返回错误
- 越界检查使用 `Type::checkForOutOfRangeLiteral()`,仅在参数为字面量时触发

### 类型转换规则

SkSL 标量类型转换遵循以下规则:

| 源类型 | 目标类型 | 行为 |
|--------|----------|------|
| `float` | `int` | 截断(如 `4.7` -> `4`) |
| `int` | `float` | 精确转换(如 `4` -> `4.0`) |
| `bool` | `int` | `false` -> `0`, `true` -> `1` |
| `int` | `bool` | `0` -> `false`, 非零 -> `true` |
| `float` | `half` | 窄化(可能丢失精度) |
| `half` | `float` | 扩展 |

### 与 GLSL 的差异

SkSL 不允许从向量到标量的"切片"操作(如 `float(myVec4)`),而某些 GLSL 实现允许这种操作。SkSL 提供明确的替代方案:
- 向量: 使用 `.x` 混洗
- 矩阵: 使用 `[0][0]` 索引

这种设计选择使代码意图更加清晰,减少了潜在的混淆。

### 字面量类型中间转换示例

```
// 原始表达式
float x = myBool ? 1 : 0;

// 内部表示
// 三元表达式结果类型为 $intLiteral
// 然后需要转换: float($intLiteral(myBool ? 1 : 0))

// 优化后:消除中间的 $intLiteral 层
// float(myBool ? 1 : 0) -- 直接从 int 到 float 转换
```

## 相关文件

- `src/sksl/ir/SkSLConstructorCompoundCast.h` -- 复合类型(向量/矩阵)的类型转换
- `src/sksl/ir/SkSLConstructorArrayCast.h` -- 数组类型转换
- `src/sksl/ir/SkSLLiteral.h` -- 字面量节点(编译期转换的结果)
- `src/sksl/ir/SkSLType.h` -- 类型系统(标量类型定义和值域)
- `src/sksl/SkSLConstantFolder.h` -- 常量折叠工具(变量替换)
- `src/sksl/ir/SkSLSwizzle.h` -- 混洗操作(使用标量转换处理降维混洗)
