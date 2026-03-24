# SkSL ChildCall（子效果调用表达式）

> 源文件：[src/sksl/ir/SkSLChildCall.h](../../../src/sksl/ir/SkSLChildCall.h)、[src/sksl/ir/SkSLChildCall.cpp](../../../src/sksl/ir/SkSLChildCall.cpp)

## 概述

`ChildCall` 是 SkSL 中间表示（IR）中表示子效果调用的表达式节点。子效果是 SkSL 的运行时效果组合机制，允许着色器程序调用其附加的 `shader`、`colorFilter` 或 `blender` 对象的 `eval()` 方法。`ChildCall` 在 IR 中记录调用的子效果变量、参数列表和返回类型，并在编译阶段验证调用签名的正确性。

## 架构位置

`ChildCall` 位于 SkSL IR 的表达式节点层：

```
SkSL 源代码: myShader.eval(coords)
                |
                v
          Parser（解析为 ChildCall 节点）
                |
                v
          ChildCall（IR 表达式节点）
                |
                v
          Analysis（采样分析）/ CodeGen（代码生成）
```

## 主要类与结构体

### `class ChildCall`

继承自 `Expression`，表示子效果调用：

| 成员 | 类型 | 说明 |
|------|------|------|
| `fChild` | `const Variable&` | 子效果变量的引用 |
| `fArguments` | `ExpressionArray` | 参数列表 |

静态常量：
| 常量 | 值 | 说明 |
|------|----|------|
| `kIRNodeKind` | `Kind::kChildCall` | IR 节点类型标识 |

## 公共 API 函数

### 工厂方法

- **`static Make(context, pos, returnType, child, arguments)`** —— 创建 ChildCall 节点。通过 `SkASSERT` 验证调用签名（仅在 debug 模式下检查）。

### 访问器

- **`child()`** —— 获取子效果变量的引用
- **`arguments()` / `arguments() const`** —— 获取参数列表（可变/不可变）
- **`clone(pos)`** —— 克隆此表达式节点
- **`description(precedence)`** —— 生成文本描述（如 `myShader.eval(coords)`）

## 内部实现细节

### 调用签名验证

`call_signature_is_valid` 函数（仅在 debug 模式下使用）根据子效果类型验证参数：

| 子效果类型 | 期望参数 | 说明 |
|-----------|----------|------|
| `Shader` | `(float2)` | 采样坐标 |
| `ColorFilter` | `(half4)` | 输入颜色 |
| `Blender` | `(half4, half4)` | 源颜色和目标颜色 |

### description 的文本格式

生成格式为 `childName.eval(arg1, arg2, ...)` 的文本表示，使用 `String::Separator()` 生成逗号分隔符。

### clone 的实现

克隆操作创建一个新的 `ChildCall`，深度克隆参数列表（通过 `arguments().clone()`），但共享子效果变量的引用（因为变量是共享的符号）。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLExpression.h` | 表达式基类 |
| `SkSLVariable.h` | 子效果变量 |
| `SkSLType.h` | 类型检查（Shader/ColorFilter/Blender） |
| `SkSLBuiltinTypes.h` | 内置类型（half4、float2） |
| `SkSLString.h` | `String::Separator` 逗号分隔 |
| `SkSLContext.h` | 编译上下文 |

## 设计模式与设计决策

1. **专用 IR 节点**：ChildCall 与 FunctionCall 分离，因为子效果调用有不同的语义（不通过函数表分发，而是直接调用效果对象）。
2. **引用持有**：持有子效果变量的引用（而非指针），确保变量始终有效。
3. **双工厂方法**：`Convert` 用于正常编译路径（报告错误），`Make` 用于已知安全的构造（断言验证），但 ChildCall 仅提供 `Make`。
4. **按值返回类型**：返回类型通过构造函数传入（而非从子效果推导），因为不同的调用形式可能有不同的返回类型。

## 性能考量

- `ChildCall` 本身是轻量级的 IR 节点
- `call_signature_is_valid` 仅在 debug 构建中执行，release 构建中不产生开销
- `ExpressionArray` 使用 `SkTArray` 的内联存储优化

## 相关文件

- `src/sksl/ir/SkSLFunctionCall.h` —— 普通函数调用（与 ChildCall 不同）
- `src/sksl/ir/SkSLExpression.h` —— 表达式基类
- `src/sksl/ir/SkSLVariable.h` —— 变量定义
- `src/sksl/SkSLAnalysis.cpp` —— `MergeSampleUsageVisitor` 分析 ChildCall 的采样方式
- `src/sksl/SkSLInliner.cpp` —— 内联器处理 ChildCall 的克隆和变量重映射
