# SkSL FunctionDefinition - 函数定义

> 源文件:
> - `src/sksl/ir/SkSLFunctionDefinition.h`
> - `src/sksl/ir/SkSLFunctionDefinition.cpp`

## 概述

`FunctionDefinition` 表示 SkSL IR 中的函数定义,即函数声明(`FunctionDeclaration`)加上函数体(`Statement` / `Block`)。它是一个顶层程序元素(`ProgramElement`),负责在编译时对函数体进行语义验证、优化以及特殊处理(如顶点着色器的 `sk_Position` 修正)。

## 架构位置

```
SkSL 编译器
└── IR (中间表示)
    └── 程序元素 (ProgramElement)
        └── FunctionDefinition  <-- 本文件
            ├── FunctionDeclaration (函数声明)
            └── Statement / Block (函数体)
```

`FunctionDefinition` 继承自 `ProgramElement`,与 `StructDefinition`、`GlobalVarDeclaration` 等并列。

## 主要类与结构体

### `FunctionDefinition`

| 成员 | 类型 | 说明 |
|------|------|------|
| `fDeclaration` | `const FunctionDeclaration*` | 指向函数声明 |
| `fBody` | `unique_ptr<Statement>` | 函数体 |

## 公共 API 函数

### `FunctionDefinition::Convert`

```cpp
static std::unique_ptr<FunctionDefinition> Convert(const Context& context,
                                                   Position pos,
                                                   const FunctionDeclaration& function,
                                                   std::unique_ptr<Statement> body);
```

从源代码创建函数定义,执行全面的语义验证:

1. **内置函数保护**: 禁止为内置函数(intrinsic)提供定义
2. **函数体格式**: 函数体必须是一个带作用域的 Block
3. **重复定义检查**: 一个函数只能有一个定义
4. **Finalizer 遍历**: 运行内部的 `Finalizer` 访问者进行深度验证
5. **顶点着色器修正**: 为顶点着色器的 `main()` 追加 `sk_Position` 的 RTAdjust 修正
6. **返回路径检查**: 验证函数不能在没有返回值的情况下退出

### `FunctionDefinition::Make`

```cpp
static std::unique_ptr<FunctionDefinition> Make(const Context& context,
                                                Position pos,
                                                const FunctionDeclaration& function,
                                                std::unique_ptr<Statement> body);
```

仅做断言验证的工厂方法。

## 内部实现细节

### Finalizer 访问者

`Convert()` 方法中定义了一个内部类 `Finalizer`(继承 `ProgramWriter`),对函数体进行深度优先遍历:

#### 变量声明处理
- 跟踪函数使用的局部变量槽数(`fSlotsUsed`)
- 当超过 `kVariableSlotLimit` 时报告栈大小限制错误
- 不对未确定大小的数组计算槽数

#### 返回语句验证
- 有返回值的函数:将返回表达式强制转换为声明的返回类型
- void 函数:如果包含返回值表达式则报错
- 非 void 函数:如果缺少返回值表达式则报错
- 顶点着色器的 `main()` 函数不允许提前返回

#### 控制流验证
- **break**: 必须在循环或 switch 中(通过 `fBreakableLevel` 跟踪)
- **continue**: 必须在循环中,不能在 switch 内(通过 `fContinuableLevel` 栈跟踪)

#### 变量声明与初始化融合

当优化开启时,`Finalizer` 会尝试将分离的变量声明和后续赋值合并:
```
int i;     → int i = 1;
i = 1;     → (nop)
```

融合条件:
- 紧随声明之后的表达式语句
- 是简单赋值(`=`)到声明的变量
- 右值不引用被赋值的变量

### RTAdjust 修正 (`append_rtadjust_fixup_to_vertex_main`)

为顶点着色器的 `main()` 函数追加位置修正代码:

```glsl
sk_Position = float4(
    sk_Position.xy * rtAdjust.xz + sk_Position.ww * rtAdjust.yw,
    0,
    sk_Position.w
);
```

该修正使用 `IRHelpers` 工具类构建 IR 节点。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLProgramElement.h` | 基类 |
| `SkSLFunctionDeclaration.h` | 函数声明 |
| `SkSLStatement.h` / `SkSLBlock.h` | 函数体 |
| `SkSLAnalysis.h` | 返回路径分析、变量包含检查 |
| `SkSLCompiler.h` | RTAdjust 和 Position 名称常量 |
| `SkSLIRHelpers.h` | IR 构建辅助工具(RTAdjust 修正) |
| `SkSLProgramWriter.h` | 语句/表达式遍历框架 |
| `SkSafeMath.h` | 安全整数加法(槽数计算) |
| `SkSLReturnStatement.h` | 返回语句处理 |
| `SkSLVarDeclarations.h` | 变量声明处理 |
| `SkSLNop.h` | 空操作语句(声明融合后替换原赋值) |

## 设计模式与设计决策

1. **声明与定义分离**: `FunctionDeclaration` 和 `FunctionDefinition` 分离,支持前向声明、函数引用等场景
2. **Finalizer 访问者模式**: 使用 `ProgramWriter` 遍历框架进行函数体验证,将多种检查集中在一次遍历中
3. **声明-初始化融合**: 在编译期将分离的声明和赋值合并,简化后端代码生成
4. **容错设计**: 即使检测到错误也返回 `FunctionDefinition`(而非 null),避免连锁的"函数未定义"错误
5. **RTAdjust 注入**: 顶点着色器的位置修正在编译期注入到函数体末尾

## 性能考量

- `Finalizer` 在函数体上执行一次遍历,完成所有验证和优化
- 变量槽数使用 `SkSafeMath::Add` 进行安全加法,防止溢出
- 声明-初始化融合在同一遍历中完成,不需要额外的 pass
- 栈大小限制通过 `kVariableSlotLimit` 常量控制,仅在首次超限时报错

## 相关文件

- `src/sksl/ir/SkSLFunctionDeclaration.h` -- 函数声明
- `src/sksl/ir/SkSLFunctionCall.h` -- 函数调用
- `src/sksl/ir/SkSLBlock.h` -- 块语句(函数体)
- `src/sksl/ir/SkSLReturnStatement.h` -- 返回语句
- `src/sksl/ir/SkSLVarDeclarations.h` -- 变量声明
- `src/sksl/ir/SkSLIRHelpers.h` -- IR 构建辅助工具
- `src/sksl/transform/SkSLProgramWriter.h` -- 程序遍历框架
- `src/sksl/SkSLAnalysis.h` -- 分析工具(返回路径、变量引用)
