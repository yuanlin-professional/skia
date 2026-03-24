# SkSL ConstructorArray - 数组构造器

> 源文件:
> - `src/sksl/ir/SkSLConstructorArray.h`
> - `src/sksl/ir/SkSLConstructorArray.cpp`

## 概述

`ConstructorArray` 表示 SkSL IR 中的数组类型构造操作,例如 `float[5](x, y, z, w, 1)`。该类负责从一组表达式构建数组值,并在构造过程中执行类型检查、参数数量验证以及类型强制转换。

数组构造在 GLSL ES 2.0 中不被支持,因此该类在严格 ES2 模式下会报告错误。它还支持一种特殊情况:当传入一个相同大小的数组参数时,操作会被识别为数组类型转换(cast),并委托给 `ConstructorArrayCast`。

## 架构位置

```
SkSL 编译器
└── IR (中间表示)
    └── 表达式 (Expression)
        └── 构造器 (Constructor)
            └── MultiArgumentConstructor
                └── ConstructorArray  <-- 本文件
```

`ConstructorArray` 继承自 `MultiArgumentConstructor`,支持多个参数的构造模式,与同级的 `ConstructorCompound` 类似但专用于数组类型。

## 主要类与结构体

### `ConstructorArray`

继承自 `MultiArgumentConstructor`,表示数组构造操作。

| 成员 | 说明 |
|------|------|
| `kIRNodeKind` | 静态常量,值为 `Kind::kConstructorArray` |

**关键方法:**

- **`Convert()`** -- 完整类型检查的转换工厂方法,通过 ErrorReporter 报告错误
- **`Make()`** -- 断言验证的工厂方法,仅用于已知合法的构造
- **`clone()`** -- 深拷贝,递归克隆所有参数表达式

## 公共 API 函数

### `ConstructorArray::Convert`

```cpp
static std::unique_ptr<Expression> Convert(const Context& context,
                                           Position pos,
                                           const Type& type,
                                           ExpressionArray args);
```

执行完整的类型检查和数组构造。处理逻辑:

1. **ES2 模式检查**: 在 `strictES2Mode` 下拒绝数组构造
2. **原子类型检查**: 包含原子成员的数组不能被构造
3. **数组转换检测**: 当只有一个参数且是相同大小的可强制转换数组时,转为 `ConstructorArrayCast`
4. **参数数量验证**: 确保参数数量与数组大小匹配
5. **分量类型转换**: 将每个参数强制转换为数组的分量类型
6. **调用 `Make()`**: 最终创建 `ConstructorArray` 节点

### `ConstructorArray::Make`

```cpp
static std::unique_ptr<Expression> Make(const Context& context,
                                        Position pos,
                                        const Type& type,
                                        ExpressionArray args);
```

仅执行断言验证的工厂方法,假定输入已经过类型检查:

- 非严格 ES2 模式
- 类型在 ES2 中被允许
- 参数数量匹配列数
- 不包含原子类型
- 所有参数类型与数组分量类型匹配

## 内部实现细节

### 数组转换优化

当 `Convert()` 检测到以下条件时,会将数组构造转换为 `ConstructorArrayCast`:
- 只有一个参数
- 参数是数组类型
- 参数数组可以强制转换为目标数组类型(允许窄化转换)

这一特性不是 GLSL 标准功能,而是为 Pipeline 阶段代码生成器设计的。当原始编译时启用了"允许窄化转换",而后续需要在不允许窄化的模式下重新编译时,会通过显式转换来修补这些差异。

### 类型强制转换

在参数数量验证通过后,每个参数都会调用 `baseType.coerceExpression()` 进行类型强制转换,确保所有元素的类型与数组分量类型一致。如果某个参数的类型无法转换(例如将 `bool` 强制转换为 `float`),`coerceExpression()` 会返回 null,导致 `Convert()` 整体返回 null。

### Make 方法的断言保护

`Make()` 方法包含以下 `SkASSERT` 断言,这些仅在 debug 构建中执行:

```cpp
SkASSERT(!context.fConfig->strictES2Mode());       // 非严格 ES2 模式
SkASSERT(type.isAllowedInES2(context));             // 类型兼容
SkASSERT(type.columns() == args.size());            // 参数数量匹配
SkASSERT(!type.isOrContainsAtomic());               // 无原子类型
SkASSERT(std::all_of(...));                          // 所有参数类型一致
```

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLConstructor.h` (MultiArgumentConstructor) | 基类 |
| `SkSLConstructorArrayCast.h` | 处理数组类型转换的特殊情况 |
| `SkSLContext.h` | 编译上下文 |
| `SkSLErrorReporter.h` | 错误报告 |
| `SkSLProgramSettings.h` | 程序配置(如 strictES2Mode) |
| `SkSLType.h` | 类型系统,用于分量类型检查和类型强制转换 |
| `SkSLString.h` | 字符串格式化工具(错误消息) |

## 设计模式与设计决策

1. **Convert/Make 双层工厂**: `Convert()` 执行完整的语义验证,适合解析阶段; `Make()` 仅做断言,适合编译器内部已知合法的构造路径
2. **隐式转换识别**: 单参数数组构造被智能识别为可能的类型转换,这是一种优化路径
3. **ES2 兼容性管理**: 通过在 `Convert()` 中显式检查 `strictES2Mode` 来管理跨 GLSL 版本的兼容性
4. **原子类型保护**: 禁止构造包含原子成员的数组,维护原子类型的不可复制语义

## 性能考量

- 单参数数组构造的转换检测在 `Convert()` 阶段完成,避免创建不必要的多参数构造节点
- 参数类型转换通过 `coerceExpression()` 按需执行,仅在类型不匹配时生成额外的转换节点
- `Make()` 方法中的断言在 release 构建中被移除,不影响运行时性能
- 数组构造不支持编译期常量折叠(不同于标量和向量构造器),因此 `ConstructorArray` 不覆盖 `supportsConstantValues()`
- `clone()` 方法需要递归克隆所有参数表达式,对于大数组可能产生较多的内存分配
- 错误消息使用 `String::printf` 进行格式化,仅在检测到错误时才会执行字符串拼接
- `std::all_of` 断言检查在 debug 构建中遍历所有参数以验证类型一致性,release 中被完全移除
- 数组构造的参数列表使用 `ExpressionArray`(基于 `SkTArray`),支持移动语义以避免不必要的拷贝

### 错误消息示例

`Convert()` 方法可能生成的错误消息包括:
- `"construction of array type 'float[3]' is not supported"` (ES2 模式)
- `"construction of array type 'float[3]' with atomic member is not allowed"` (原子类型)
- `"invalid arguments to 'float[3]' constructor (expected 3 elements, but found 2)"` (参数数量不匹配)

## 相关文件

- `src/sksl/ir/SkSLConstructorArrayCast.h` -- 数组类型转换构造器,处理单参数数组到数组的类型转换
- `src/sksl/ir/SkSLConstructorCompound.h` -- 复合向量/矩阵构造器,与 ConstructorArray 类似但用于非数组类型
- `src/sksl/ir/SkSLConstructor.h` -- 构造器基类层次结构,定义 `MultiArgumentConstructor`
- `src/sksl/ir/SkSLType.h` -- 类型系统,定义数组类型和 `componentType()` 方法
- `src/sksl/SkSLContext.h` -- 编译上下文,提供符号表和配置信息
- `src/sksl/SkSLProgramSettings.h` -- 程序设置,包括 `strictES2Mode()` 标志
- `src/sksl/SkSLErrorReporter.h` -- 错误报告器,用于向用户报告编译错误
- `src/sksl/SkSLString.h` -- 字符串工具,提供 `String::printf` 格式化函数
- `src/sksl/ir/SkSLExpression.h` -- 表达式基类,所有构造器的最终基类
- `src/sksl/ir/SkSLIRNode.h` -- IR 节点基类,定义 `Kind` 枚举
- `src/sksl/SkSLDefines.h` -- 定义 `ExpressionArray` 类型和 `SKSL_INT` 类型
