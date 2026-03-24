# SkSL ConstructorArrayCast - 数组类型转换构造器

> 源文件:
> - `src/sksl/ir/SkSLConstructorArrayCast.h`
> - `src/sksl/ir/SkSLConstructorArrayCast.cpp`

## 概述

`ConstructorArrayCast` 表示 SkSL IR 中的数组类型转换操作。数组在 SkSL(和 GLSL)中不能直接进行类型转换,但当启用窄化转换(narrowing conversions)时,可能会隐式地需要对数组进行类型转换。例如,表达式 `myHalf2Array == float[2](a, b)` 在允许窄化的模式下应该是合法的。

该构造器始终包含一个相同大小的数组参数,且永远不是编译期常量(除非其内容可以被完全常量折叠)。

## 架构位置

```
SkSL 编译器
└── IR (中间表示)
    └── 表达式 (Expression)
        └── 构造器 (Constructor)
            └── SingleArgumentConstructor
                └── ConstructorArrayCast  <-- 本文件
```

## 主要类与结构体

### `ConstructorArrayCast`

继承自 `SingleArgumentConstructor`。

| 成员 | 说明 |
|------|------|
| `kIRNodeKind` | 值为 `Kind::kConstructorArrayCast` |

## 公共 API 函数

### `ConstructorArrayCast::Make`

```cpp
static std::unique_ptr<Expression> Make(const Context& context,
                                        Position pos,
                                        const Type& type,
                                        std::unique_ptr<Expression> arg);
```

创建数组类型转换表达式:

1. **断言验证**: 目标类型为数组,参数为数组,大小相同
2. **空操作消除**: 如果类型完全匹配,直接返回原表达式
3. **常量变量替换**: 通过 `ConstantFolder` 替换常量变量
4. **编译期常量折叠**: 如果参数是编译期常量,调用 `cast_constant_array` 在编译期执行转换

## 内部实现细节

### 常量数组转换 (`cast_constant_array`)

当参数是编译期常量的 `ConstructorArray` 时,逐元素执行类型转换:
- 标量元素使用 `ConstructorScalarCast::Make`
- 复合类型元素(向量等)使用 `ConstructorCompoundCast::Make`
- 最终用转换后的元素构造一个新的 `ConstructorArray`

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLConstructor.h` | 基类 |
| `SkSLConstantFolder.h` | 常量变量替换和编译期常量检测 |
| `SkSLAnalysis.h` | `IsCompileTimeConstant` 检测 |
| `SkSLConstructorArray.h` | 常量转换后构造新数组 |
| `SkSLConstructorScalarCast.h` | 标量元素的类型转换 |
| `SkSLConstructorCompoundCast.h` | 复合元素的类型转换 |
| `SkSLType.h` | 类型系统 |

## 设计模式与设计决策

1. **Pipeline 阶段兼容**: 该类的存在主要是为了支持 Pipeline 阶段代码生成器,处理原始编译时允许窄化但后续不允许的情况
2. **编译期折叠**: 对常量数组在编译期执行逐元素转换,避免运行时开销
3. **空操作消除**: 类型匹配时直接返回原参数

## 性能考量

- 常量数组的类型转换在编译期完成,不生成运行时代码
- 空操作检查避免了不必要的 IR 节点

## 相关文件

- `src/sksl/ir/SkSLConstructorArray.h` -- 数组构造器(检测并创建 ArrayCast)
- `src/sksl/ir/SkSLConstructorScalarCast.h` -- 标量类型转换
- `src/sksl/ir/SkSLConstructorCompoundCast.h` -- 复合类型转换
