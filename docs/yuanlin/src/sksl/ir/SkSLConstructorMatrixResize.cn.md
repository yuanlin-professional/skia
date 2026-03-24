# SkSL ConstructorMatrixResize - 矩阵调整大小构造器

> 源文件:
> - `src/sksl/ir/SkSLConstructorMatrixResize.h`
> - `src/sksl/ir/SkSLConstructorMatrixResize.cpp`

## 概述

`ConstructorMatrixResize` 表示 SkSL IR 中的矩阵大小调整操作,例如 `mat4x4(myMat2x2)`。当用一个矩阵构造一个不同大小的矩阵时,源矩阵中存在的单元格被保留,超出部分填充为单位矩阵的对应值(对角线为 1,其余为 0)。

例如,将 2x2 矩阵调整为 3x3:
```
源矩阵:        结果矩阵:
| a  b |   →   | a  b  0 |
| c  d |        | c  d  0 |
                | 0  0  1 |
```

## 架构位置

```
SkSL 编译器
└── IR (中间表示)
    └── 表达式 (Expression)
        └── 构造器 (Constructor)
            └── SingleArgumentConstructor
                └── ConstructorMatrixResize  <-- 本文件
```

## 主要类与结构体

### `ConstructorMatrixResize`

继承自 `SingleArgumentConstructor`。

| 成员 | 说明 |
|------|------|
| `kIRNodeKind` | 值为 `Kind::kConstructorMatrixResize` |

## 公共 API 函数

### `ConstructorMatrixResize::Make`

```cpp
static std::unique_ptr<Expression> Make(const Context& context,
                                        Position pos,
                                        const Type& type,
                                        std::unique_ptr<Expression> arg);
```

创建矩阵大小调整构造器:
1. 验证目标类型为矩阵,参数的分量类型匹配
2. **空操作消除**: 如果行数和列数都相同,直接返回原参数
3. 否则创建新的 `ConstructorMatrixResize` 节点

### `getConstantValue`

```cpp
std::optional<double> getConstantValue(int n) const override;
```

根据线性索引计算结果矩阵中第 `n` 个元素的编译期常量值:

- **在源矩阵范围内**: 将 `n` 重新映射到源矩阵的坐标系,委托给源矩阵的 `getConstantValue()`
- **在对角线上**: 返回 `1.0`
- **其他位置**: 返回 `0.0`

## 内部实现细节

矩阵元素以列主序存储,索引映射:
- `row = n % rows`, `col = n / rows`
- 如果 `col < arg.columns()` 且 `row < arg.rows()`:映射到源矩阵的 `row + col * arg.rows()`
- 否则按单位矩阵填充:`(col == row) ? 1.0 : 0.0`

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLConstructor.h` | 基类 |
| `SkSLType.h` | 类型系统(行列信息) |

## 设计模式与设计决策

1. **单位矩阵填充**: GLSL 规范要求矩阵调整大小时使用单位矩阵填充新增区域
2. **空操作消除**: 当矩阵大小不变时,直接返回原表达式
3. **常量值传播**: `getConstantValue()` 支持编译期完全求值

## 性能考量

- 空操作检查避免创建不必要的 IR 节点
- `getConstantValue()` 是 O(1) 操作

## 相关文件

- `src/sksl/ir/SkSLConstructorDiagonalMatrix.h` -- 从标量构造对角矩阵
- `src/sksl/ir/SkSLConstructorCompound.h` -- 从多个分量构造矩阵
- `src/sksl/ir/SkSLType.h` -- 矩阵类型定义
