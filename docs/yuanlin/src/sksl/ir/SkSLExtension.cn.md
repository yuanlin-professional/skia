# SkSL Extension (扩展声明)

> 源文件:
> - `src/sksl/ir/SkSLExtension.h`
> - `src/sksl/ir/SkSLExtension.cpp`

## 概述

`Extension` 是 SkSL 编译器中间表示（IR）中用于表示 GLSL `#extension` 预处理指令的类。它对应源代码中 `#extension <name> : enable` 形式的声明，用于启用特定的 GLSL 扩展功能。该类处理扩展的行为模式验证（`enable`、`require`、`warn`、`disable`），并在 Runtime Effect 中禁止使用扩展。

## 架构位置

`Extension` 继承自 `ProgramElement`，是程序顶层元素之一，与函数定义、全局变量声明等并列。

```
ProgramElement (基类)
  |-- Extension           (#extension 声明)
  |-- FunctionDefinition  (函数定义)
  |-- GlobalVarDeclaration(全局变量声明)
  |-- InterfaceBlock      (接口块)
  |-- ...
```

## 主要类与结构体

### `Extension`

`final` 类，继承自 `ProgramElement`。

**关键成员变量：**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fName` | `string_view` | 扩展名称（如 `"GL_OES_standard_derivatives"`） |

**IR 节点类型标识：** `Kind::kExtension`

## 公共 API 函数

### 构造方法

- **`Extension(pos, name)`** -- 直接构造，不进行验证。

### 工厂方法

- **`Convert(context, pos, name, behaviorText)`** -- 完整的转换方法：
  1. 检查是否在 Runtime Effect 中 -- 若是则报错
  2. `"disable"` 行为 -- 返回 `nullptr`（合法但无需 IR 节点）
  3. 验证行为文本为 `"require"`、`"enable"` 或 `"warn"` 之一
  4. 委托给 `Make()` 创建节点

- **`Make(context, pos, name)`** -- 简化构造方法：
  1. 断言不在 Runtime Effect 中
  2. 创建 `Extension` 节点

### 访问器

- **`name()`** -- 返回扩展名称
- **`description()`** -- 返回 `#extension <name> : enable` 格式文本

## 内部实现细节

### Runtime Effect 限制

Runtime Effect（运行时效果）不允许使用 `#extension` 指令，因为 Runtime Effect 被设计为跨平台可移植的着色器代码，依赖特定硬件扩展违反了这一设计原则。`Convert()` 通过 `ProgramConfig::IsRuntimeEffect()` 检查当前编译目标。

### 行为模式处理

GLSL 规范定义了四种扩展行为：
- `require` -- 必须支持该扩展
- `enable` -- 启用该扩展（如不支持则静默）
- `warn` -- 启用但使用时警告
- `disable` -- 禁用该扩展

SkSL 当前不区分 `require`、`enable` 和 `warn` 三种行为，统一作为启用处理。`disable` 行为通过返回 `nullptr` 来实现"无操作"语义。

### 名称存储

`fName` 使用 `string_view` 而非 `string`，意味着扩展名称的生命周期由外部管理（通常由 SymbolTable 或源代码字符串持有）。这避免了额外的字符串拷贝。

## 依赖关系

**内部依赖：**
- `SkSLProgramElement` -- 程序元素基类
- `SkSLIRNode` -- IR 节点基类
- `SkSLPosition` -- 源码位置
- `SkSLContext` -- 编译器上下文
- `SkSLErrorReporter` -- 错误报告
- `SkSLProgramSettings` -- 程序配置（Runtime Effect 检查）

**外部依赖：**
- `<memory>`, `<string>`, `<string_view>` -- 标准库

## 设计模式与设计决策

1. **Convert/Make 双层模式**：`Convert` 处理用户输入验证（行为文本、Runtime Effect 检查），`Make` 处理已验证的构造。

2. **nullable 返回值**：`Convert` 在 `disable` 行为时返回 `nullptr` 而非错误，这是一种合法的"无操作"语义。调用者需检查返回值。

3. **行为统一化**：将 `require`/`enable`/`warn` 统一处理，简化了编译器的后续处理逻辑。这是一个合理的简化，因为 SkSL 的后端代码生成器会根据目标平台自行决定扩展支持。

4. **轻量级节点**：`Extension` 只存储名称的 `string_view`，是最轻量的 IR 节点之一。

## 性能考量

- **零拷贝名称存储**：使用 `string_view` 避免了字符串拷贝，但要求源字符串的生命周期覆盖整个编译过程。
- **编译时验证**：行为模式验证在 `Convert` 阶段完成，不会影响后续处理。
- **最小化 IR**：`disable` 行为不创建 IR 节点，减少后续遍历的工作量。

## 相关文件

- `src/sksl/ir/SkSLProgramElement.h` -- ProgramElement 基类
- `src/sksl/SkSLProgramSettings.h` -- 程序配置（ProgramConfig 定义）
- `src/sksl/SkSLContext.h` -- 编译器上下文
- `src/sksl/SkSLErrorReporter.h` -- 错误报告接口
- `src/sksl/codegen/SkSLGLSLCodeGenerator.h` -- GLSL 代码生成器（输出 #extension）
