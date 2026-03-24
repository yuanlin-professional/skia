# SkSL SwitchCase - Switch 语句分支

> 源文件:
> - `src/sksl/ir/SkSLSwitchCase.h`
> - `src/sksl/ir/SkSLSwitchCase.cpp`

## 概述

`SwitchCase` 表示 SkSL IR 中 `switch` 语句的单个分支(case)。每个 `SwitchCase` 包含一个整数匹配值和对应的语句体,或者作为 `default` 分支(没有匹配值)。

该类遵循 C 风格的 switch-case 语义,其中每个 case 可以关联一条语句(通常是一个 Block)。`SwitchCase` 是 `SwitchStatement` 的组成部分。

## 架构位置

```
SkSL 编译器
└── IR (中间表示)
    └── 语句 (Statement)
        └── SwitchCase  <-- 本文件
            └── (被 SwitchStatement 聚合)
```

`SwitchCase` 继承自 `Statement`,作为 `SwitchStatement` 的子元素存在。

## 主要类与结构体

### `SwitchCase`

继承自 `Statement`,表示 switch 的一个分支。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fDefault` | `bool` | 是否为 default 分支 |
| `fValue` | `SKSL_INT` | 匹配的整数值(非 default 时有效) |
| `fStatement` | `unique_ptr<Statement>` | 分支执行的语句体 |

## 公共 API 函数

### `SwitchCase::Make`

```cpp
static std::unique_ptr<SwitchCase> Make(Position pos,
                                        SKSL_INT value,
                                        std::unique_ptr<Statement> statement);
```

创建一个带值的 case 分支,如 `case 42: ...`。

### `SwitchCase::MakeDefault`

```cpp
static std::unique_ptr<SwitchCase> MakeDefault(Position pos,
                                               std::unique_ptr<Statement> statement);
```

创建一个 default 分支。内部将 `fDefault` 设为 `true`,`fValue` 设为 `-1`(无意义占位值)。

### 访问方法

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `isDefault()` | `bool` | 是否为 default 分支 |
| `value()` | `SKSL_INT` | 获取匹配值(仅非 default 时可调用) |
| `statement()` | `unique_ptr<Statement>&` | 获取语句体(可变版本和常量版本) |
| `description()` | `std::string` | 生成文本描述 |

## 内部实现细节

- 构造函数为 `private`,必须通过 `Make` 或 `MakeDefault` 工厂方法创建
- `value()` 方法包含断言保护,在 `isDefault()` 为 `true` 时调用会触发断言失败
- `description()` 方法生成形如 `"case 42: \n..."` 或 `"default: \n..."` 的文本

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLStatement.h` | 基类 |
| `SkSLDefines.h` | `SKSL_INT` 类型定义 |
| `SkSLPosition.h` | 源码位置信息 |
| `SkSLIRNode.h` | IR 节点基类 |

## 设计模式与设计决策

1. **工厂方法模式**: 使用 `Make` 和 `MakeDefault` 区分带值和默认分支,构造函数私有化
2. **类型安全**: `value()` 在 default 分支时触发断言,防止误用
3. **统一表示**: default 和普通 case 使用同一个类,通过 `fDefault` 标志区分

## 性能考量

- `SwitchCase` 是轻量级节点,仅持有一个整数值和一个语句指针
- 不涉及任何动态分配(除了语句体本身)

## 相关文件

- `src/sksl/ir/SkSLSwitchStatement.h` -- switch 语句,聚合多个 `SwitchCase`
- `src/sksl/ir/SkSLStatement.h` -- 语句基类
- `src/sksl/SkSLDefines.h` -- `SKSL_INT` 类型定义
