# SkSL ConstructorDiagonalMatrix - 对角矩阵构造器

> 源文件:
> - `src/sksl/ir/SkSLConstructorDiagonalMatrix.h`
> - `src/sksl/ir/SkSLConstructorDiagonalMatrix.cpp`

## 概述

`ConstructorDiagonalMatrix` 表示 SkSL IR 中的对角矩阵构造操作,例如 `half3x3(n)`。该操作使用一个标量值构造一个矩阵,将标量值放置在矩阵的对角线位置上,其他位置填零。这是 GLSL/SkSL 中使用单个标量初始化矩阵的标准方式。

例如,`mat3(2.0)` 构造如下矩阵:
```
| 2  0  0 |
| 0  2  0 |
| 0  0  2 |
```

## 架构位置

```
SkSL 编译器
└── IR (中间表示)
    └── 表达式 (Expression)
        └── 构造器 (Constructor)
            └── SingleArgumentConstructor
                └── ConstructorDiagonalMatrix  <-- 本文件
```

与 `ConstructorSplat` 同属 `SingleArgumentConstructor` 分支,但目标类型为矩阵而非向量。

## 主要类与结构体

### `ConstructorDiagonalMatrix`

继承自 `SingleArgumentConstructor`,用于从单个标量构造对角矩阵。

| 成员 | 说明 |
|------|------|
| `kIRNodeKind` | 值为 `Kind::kConstructorDiagonalMatrix` |

**关键方法:**
- **`Make()`** -- 工厂方法,执行常量折叠
- **`clone()`** -- 深拷贝节点
- **`supportsConstantValues()`** -- 返回 `true`
- **`getConstantValue(int n)`** -- 根据位置返回对角线上的标量值或零

## 公共 API 函数

### `ConstructorDiagonalMatrix::Make`

```cpp
static std::unique_ptr<Expression> Make(const Context& context,
                                        Position pos,
                                        const Type& type,
                                        std::unique_ptr<Expression> arg);
```

创建对角矩阵构造器:
1. 验证目标类型为矩阵,在 ES2 中被允许
2. 验证参数为标量,且类型与矩阵分量类型匹配
3. 通过 `ConstantFolder::MakeConstantValueForVariable` 替换常量变量
4. 构造并返回 `ConstructorDiagonalMatrix` 节点

### `getConstantValue`

```cpp
std::optional<double> getConstantValue(int n) const override;
```

根据线性索引 `n` 计算对应的行列位置:
- `row = n % rows`, `col = n / rows`
- 对角线位置 (`col == row`): 返回参数的常量值
- 非对角线位置: 返回 `0.0`

## 内部实现细节

- 矩阵元素按列主序(column-major)存储,因此线性索引 `n` 对应 `row = n % rows, col = n / rows`
- 常量变量在 `Make()` 阶段被替换,使得 `mat4(five)` 可以被优化为 `mat4(5.0)`
- 对角线判定通过简单的 `col == row` 实现,非对角线位置固定返回 `0.0`

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLConstructor.h` (SingleArgumentConstructor) | 基类 |
| `SkSLConstantFolder.h` | 常量变量替换 |
| `SkSLType.h` | 类型系统(矩阵行列信息) |

## 设计模式与设计决策

1. **常量值语义**: 通过 `getConstantValue()` 使编译器能在编译期求出矩阵的任意元素值,为常量折叠提供支持
2. **列主序存储**: 与 GLSL 的矩阵存储约定一致,`n = row + col * rows`
3. **常量变量早期替换**: 在 `Make()` 阶段即完成,为后续优化创造条件

## 性能考量

- `getConstantValue()` 是 O(1) 操作,仅涉及简单的算术运算
- 常量变量替换避免了运行时的变量查找

## 相关文件

- `src/sksl/ir/SkSLConstructorSplat.h` -- 向量展开构造器(类似模式,用于向量)
- `src/sksl/ir/SkSLConstructorMatrixResize.h` -- 矩阵调整大小构造器
- `src/sksl/ir/SkSLConstructorCompound.h` -- 从多个分量构造矩阵
- `src/sksl/ir/SkSLPrefixExpression.cpp` -- 使用对角矩阵构造器进行取反优化
