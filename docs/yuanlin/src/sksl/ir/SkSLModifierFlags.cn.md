# SkSL ModifierFlags (修饰符标志)

> 源文件:
> - `src/sksl/ir/SkSLModifierFlags.h`
> - `src/sksl/ir/SkSLModifierFlags.cpp`

## 概述

`ModifierFlags` 是 SkSL 编译器中用于表示变量、函数参数和其他声明的修饰符（qualifier）的位掩码类。它封装了所有 GLSL 标准修饰符（如 `const`、`uniform`、`in`、`out`）以及 SkSL 特有的扩展修饰符（如 `$export`、`$pure`、`inline`）。通过位运算实现高效的修饰符组合、检测和验证。

## 架构位置

`ModifierFlags` 位于 SkSL IR 层的基础设施中。它被广泛应用于变量声明、函数声明、参数定义等所有需要修饰符的 IR 节点中。在编译流程中，解析器（Parser）将源代码中的修饰符文本转换为 `ModifierFlags`，随后在语义分析、代码生成等阶段通过该标志进行修饰符检查。

```
Parser -> ModifierFlags -> IR 节点（Variable, FunctionDeclaration 等）
                        -> CodeGen（生成对应后端的修饰符语法）
```

## 主要类与结构体

### `ModifierFlag`（枚举类）

定义所有可用的修饰符标志位，使用 `int` 作为底层类型，每个标志占一个位。

| 标志 | 位偏移 | 说明 |
|------|--------|------|
| `kNone` | 0 | 无修饰符 |
| `kFlat` | 0 | 插值限定符：平面着色 |
| `kNoPerspective` | 1 | 插值限定符：无透视校正 |
| `kConst` | 2 | 常量限定符 |
| `kUniform` | 3 | uniform 变量 |
| `kIn` | 4 | 输入参数/变量 |
| `kOut` | 5 | 输出参数/变量 |
| `kHighp` | 6 | 高精度 |
| `kMediump` | 7 | 中精度 |
| `kLowp` | 8 | 低精度 |
| `kReadOnly` | 9 | 只读 |
| `kWriteOnly` | 10 | 只写 |
| `kBuffer` | 11 | buffer 存储 |
| `kPixelLocal` | 12 | 像素局部存储（对应 GLSL `__pixel_localEXT`） |
| `kWorkgroup` | 13 | 工作组共享（对应 GLSL `shared`，仅计算着色器） |
| `kExport` | 14 | SkSL 扩展：导出标记 |
| `kES3` | 15 | SkSL 扩展：ES3 特性标记 |
| `kPure` | 16 | SkSL 扩展：纯函数标记 |
| `kInline` | 17 | SkSL 扩展：内联提示 |
| `kNoInline` | 18 | SkSL 扩展：禁止内联 |

### `ModifierFlags`（类）

继承自 `SkEnumBitMask<ModifierFlag>`，提供修饰符的组合操作和便捷查询方法。

## 公共 API 函数

### 描述方法

- **`description()`** -- 返回修饰符的文本表示，不含尾部空格。例如 `"const uniform"`。
- **`paddedDescription()`** -- 返回修饰符的文本表示，每个修饰符后带一个空格。用于在声明中拼接使用。

### 验证方法

- **`checkPermittedFlags(context, pos, permittedModifierFlags)`** -- 检查当前修饰符是否都在允许的修饰符集合中。如果存在不允许的修饰符，通过 `ErrorReporter` 报告错误并返回 `false`。

### 便捷查询方法

提供 14 个 `bool` 查询方法，每个对应一个修饰符标志：

- `isConst()`, `isUniform()`, `isReadOnly()`, `isWriteOnly()`
- `isBuffer()`, `isPixelLocal()`, `isWorkgroup()`, `isExport()`
- `isES3()`, `isPure()`, `isInline()`, `isNoInline()`
- `isFlat()`, `isNoPerspective()`

所有查询方法均通过位与运算和 `SkToBool` 实现。

## 内部实现细节

### 修饰符文本输出顺序

`paddedDescription()` 按照特定顺序输出修饰符文本，该顺序遵循 GLSL 4.1 及以下版本的规范要求：

1. SkSL 扩展修饰符（`$export`, `$es3`, `$pure`, `inline`, `noinline`）
2. 插值限定符（`flat`, `noperspective`）
3. 存储限定符（`const`, `uniform`）
4. 参数方向（`in`/`out`/`inout` -- 当 `in` 和 `out` 同时存在时输出 `inout`）
5. 精度限定符（`highp`, `mediump`, `lowp`）
6. 访问限定符（`readonly`, `writeonly`）
7. 存储类型（`buffer`）
8. 特殊存储（`pixel_local`, `workgroup`）

### 权限检查机制

`checkPermittedFlags()` 使用一个静态数组遍历所有修饰符标志。对于每个被设置的标志，检查它是否在 `permittedModifierFlags` 中。这确保了所有标志都被检查，并在最后通过 `SkASSERT` 验证没有未知标志位。

### 位掩码操作

通过 `SK_MAKE_BITMASK_OPS` 宏为 `ModifierFlag` 枚举生成位操作符（`|`, `&`, `~` 等），使得 `ModifierFlags` 可以方便地进行组合和测试。

## 依赖关系

**内部依赖：**
- `SkEnumBitMask` -- 位掩码基类模板
- `SkToBool` -- 位掩码到布尔值的转换
- `SkSLContext` -- 编译器上下文
- `SkSLErrorReporter` -- 错误报告
- `SkSLPosition` -- 源码位置信息

**外部依赖：**
- `<string>` -- 字符串处理

## 设计模式与设计决策

1. **位掩码模式**：使用单个整数的不同位来表示多个布尔属性。这是修饰符表示的经典做法，允许高效的组合、检查和存储。

2. **类型安全的枚举位操作**：通过 `SkEnumBitMask` 模板和 `SK_MAKE_BITMASK_OPS` 宏，在保持类型安全的同时提供位运算能力。

3. **SkSL 扩展与 GLSL 兼容分离**：修饰符被分为 GLSL 标准修饰符和 SkSL 扩展修饰符两组。SkSL 扩展使用 `$` 前缀（如 `$export`、`$pure`）以明确区分。

4. **上下文相关的验证**：`checkPermittedFlags` 的设计允许不同声明上下文（如变量声明 vs 函数参数）指定不同的允许修饰符集合，实现灵活的语义检查。

5. **in/out 合并输出**：当 `kIn` 和 `kOut` 同时设置时，输出 `inout` 而非 `in out`，符合 GLSL 的语法规范。

## 性能考量

- **位运算效率**：所有修饰符查询和组合操作均为 O(1) 的位运算，无内存分配。
- **内联友好**：便捷查询方法均在头文件中定义为内联函数，编译器可直接内联。
- **文本生成的延迟求值**：`description()` 和 `paddedDescription()` 仅在需要时才生成字符串，避免不必要的内存分配。

## 相关文件

- `src/base/SkEnumBitMask.h` -- 位掩码基类
- `src/sksl/ir/SkSLVariable.h` -- 使用 ModifierFlags 的变量声明
- `src/sksl/ir/SkSLFunctionDeclaration.h` -- 使用 ModifierFlags 的函数声明
- `src/sksl/SkSLContext.h` -- 编译器上下文
- `src/sksl/SkSLErrorReporter.h` -- 错误报告接口
