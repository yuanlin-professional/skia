# SkSL ConstructorSplat - 向量展开构造器

> 源文件:
> - `src/sksl/ir/SkSLConstructorSplat.h`
> - `src/sksl/ir/SkSLConstructorSplat.cpp`

## 概述

`ConstructorSplat` 表示 SkSL 中间表示(IR)中的向量展开(splat)构造操作。当一个标量值被用于构造一个向量类型时,该标量值会被复制到向量的每一个分量中。例如,`half3(n)` 会创建一个三分量向量,其每个分量的值都等于 `n`。

该类是 SkSL 编译器类型构造系统的一部分,用于处理从标量到向量的隐式或显式展开操作。它始终只包含一个标量参数。

## 架构位置

`ConstructorSplat` 位于 SkSL 编译器的 IR 层:

```
SkSL 编译器
└── IR (中间表示)
    └── 表达式 (Expression)
        └── 构造器 (Constructor)
            └── SingleArgumentConstructor
                └── ConstructorSplat  <-- 本文件
```

它属于 SkSL 构造器家族中的 `SingleArgumentConstructor` 分支,与 `ConstructorDiagonalMatrix`、`ConstructorScalarCast` 等同级。

## 主要类与结构体

### `ConstructorSplat`

继承自 `SingleArgumentConstructor`,表示向量展开构造。

| 成员 | 说明 |
|------|------|
| `kIRNodeKind` | 静态常量,值为 `Kind::kConstructorSplat`,用于 RTTI 类型识别 |

**关键方法:**

- **构造函数** `ConstructorSplat(Position, const Type&, unique_ptr<Expression>)` -- 直接构造,不做优化
- **`Make()`** -- 工厂方法,带优化逻辑(静态)
- **`clone()`** -- 深拷贝当前节点
- **`supportsConstantValues()`** -- 返回 `true`,表示支持编译期常量求值
- **`getConstantValue(int n)`** -- 返回第 n 个分量的常量值(实际上对所有分量都返回参数的第 0 个值)

## 公共 API 函数

### `ConstructorSplat::Make`

```cpp
static std::unique_ptr<Expression> Make(const Context& context,
                                        Position pos,
                                        const Type& type,
                                        std::unique_ptr<Expression> arg);
```

创建向量展开表达式的工厂方法。执行以下逻辑:

1. **断言验证**: 目标类型必须是标量或向量;参数必须是标量;参数的标量类型必须与目标类型的分量类型匹配
2. **标量优化**: 如果目标类型是标量(即"展开"到标量),则为空操作,直接返回原参数
3. **常量折叠**: 调用 `ConstantFolder::MakeConstantValueForVariable` 将常量变量替换为其对应的字面值
4. **构造节点**: 返回新的 `ConstructorSplat` 节点

### `getConstantValue`

```cpp
std::optional<double> getConstantValue(int n) const override;
```

返回向量第 `n` 个分量的编译期常量值。由于展开构造器的每个分量值相同,始终返回 `argument()->getConstantValue(0)`。

## 内部实现细节

- 标量到标量的"展开"在 `Make()` 中被识别为空操作(no-op),直接返回原始参数表达式并更新其位置信息
- 常量变量替换确保了 `float3(five)` 这样的表达式可以在编译期被折叠为 `float3(5.0)`
- `getConstantValue(n)` 对所有有效的 `n` 都返回相同的值,这是展开操作的语义保证

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLConstructor.h` (SingleArgumentConstructor) | 基类 |
| `SkSLExpression.h` | 表达式基类 |
| `SkSLConstantFolder.h` | 常量折叠优化 |
| `SkSLType.h` | 类型系统 |
| `SkSLPosition.h` | 源码位置信息 |

## 设计模式与设计决策

1. **工厂方法模式**: `Make()` 静态方法封装了对象创建逻辑,包含优化路径;直接构造函数仅供内部使用
2. **空操作消除**: 标量到标量的展开在构造阶段即被消除,避免了不必要的 IR 节点
3. **常量值传播**: 通过 `supportsConstantValues()` 和 `getConstantValue()` 支持编译期常量求值,使上层优化器能够进一步折叠常量表达式
4. **不可变语义**: 展开操作的常量值在整个向量中是统一的,这通过简单地委托到参数的 `getConstantValue(0)` 来实现

## 性能考量

- 标量展开到标量的空操作被直接消除,避免生成多余的 IR 节点
- 常量变量在构造时立即被替换为字面值,为后续的常量折叠优化铺平道路
- `getConstantValue()` 是 O(1) 操作,不涉及额外的内存分配

## 相关文件

- `src/sksl/ir/SkSLConstructor.h` -- 构造器基类 (`SingleArgumentConstructor`)
- `src/sksl/ir/SkSLConstructorCompound.h` -- 复合向量/矩阵构造器
- `src/sksl/ir/SkSLConstructorDiagonalMatrix.h` -- 对角矩阵构造器(类似的单参数模式)
- `src/sksl/ir/SkSLSwizzle.h` -- 向量混洗操作(使用展开构造器替代标量的 `.xxx` 混洗)
- `src/sksl/SkSLConstantFolder.h` -- 常量折叠工具
