# SkSL DoStatement - Do-While 循环语句

> 源文件:
> - `src/sksl/ir/SkSLDoStatement.h`
> - `src/sksl/ir/SkSLDoStatement.cpp`

## 概述

`DoStatement` 表示 SkSL IR 中的 `do-while` 循环语句,即先执行循环体再检查条件的循环结构:

```glsl
do {
    // 循环体
} while (condition);
```

该循环类型在 GLSL ES 2.0 中不被支持,因此在严格 ES2 模式下会被拒绝。

## 架构位置

```
SkSL 编译器
└── IR (中间表示)
    └── 语句 (Statement)
        └── DoStatement  <-- 本文件
```

与 `ForStatement` 一起构成 SkSL 的循环语句体系。

## 主要类与结构体

### `DoStatement`

继承自 `Statement`。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fStatement` | `unique_ptr<Statement>` | 循环体 |
| `fTest` | `unique_ptr<Expression>` | 循环条件 |

## 公共 API 函数

### `DoStatement::Convert`

```cpp
static std::unique_ptr<Statement> Convert(const Context& context,
                                          Position pos,
                                          std::unique_ptr<Statement> stmt,
                                          std::unique_ptr<Expression> test);
```

完整验证的创建方法:
1. **ES2 检查**: 在 `strictES2Mode` 下报告"do-while 循环不被支持"
2. **条件类型转换**: 将条件表达式强制转换为 `bool` 类型
3. **作用域检查**: 通过 `Analysis::DetectVarDeclarationWithoutScope` 检测循环体中的裸变量声明
4. 调用 `Make()` 创建节点

### `DoStatement::Make`

```cpp
static std::unique_ptr<Statement> Make(const Context& context,
                                       Position pos,
                                       std::unique_ptr<Statement> stmt,
                                       std::unique_ptr<Expression> test);
```

仅做断言验证的工厂方法:
- 非严格 ES2 模式
- 条件类型为 `bool`
- 循环体中无裸变量声明

### 访问方法

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `statement()` | `unique_ptr<Statement>&` | 循环体(可变/常量版本) |
| `test()` | `unique_ptr<Expression>&` | 循环条件(可变/常量版本) |
| `description()` | `std::string` | 文本描述 |

## 内部实现细节

- `description()` 生成格式: `do <statement> while (<test>);`
- 条件表达式通过 `fTypes.fBool->coerceExpression()` 强制转换,确保非 bool 表达式(如整数)被正确处理
- `DetectVarDeclarationWithoutScope` 防止在没有块作用域的循环体中声明变量(如 `do int x = 1; while(...)`)

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLStatement.h` | 基类 |
| `SkSLExpression.h` | 条件表达式 |
| `SkSLAnalysis.h` | 作用域变量声明检测 |
| `SkSLBuiltinTypes.h` | `fBool` 类型 |
| `SkSLContext.h` | 编译上下文 |
| `SkSLErrorReporter.h` | 错误报告 |
| `SkSLProgramSettings.h` | ES2 模式检查 |

## 设计模式与设计决策

1. **ES2 合规性**: 在 Convert 阶段显式拒绝 do-while(GLSL ES 1.0 不支持)
2. **作用域安全**: 检测循环体中的裸变量声明以防止作用域问题
3. **类型强制**: 条件表达式自动转换为 bool 类型

## 性能考量

- `DoStatement` 是轻量级节点,不涉及编译期优化
- 验证仅在 IR 构建时执行一次

## 相关文件

- `src/sksl/ir/SkSLForStatement.h` -- for 循环
- `src/sksl/ir/SkSLStatement.h` -- 语句基类
- `src/sksl/SkSLAnalysis.h` -- 分析工具
