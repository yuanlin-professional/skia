# SkSL StructDefinition - 结构体定义

> 源文件:
> - `src/sksl/ir/SkSLStructDefinition.h`
> - `src/sksl/ir/SkSLStructDefinition.cpp`

## 概述

`StructDefinition` 表示 SkSL IR 中全局作用域的结构体定义,例如:

```glsl
struct RenderData {
    float3 color;
    bool highQuality;
};
```

该类是一个程序元素(`ProgramElement`),负责在编译时将结构体类型注册到符号表中。结构体类型的实际定义(字段列表、布局等)存储在关联的 `Type` 对象中。

## 架构位置

```
SkSL 编译器
└── IR (中间表示)
    └── 程序元素 (ProgramElement)
        └── StructDefinition  <-- 本文件
            └── 引用 Type (结构体类型)
```

`StructDefinition` 继承自 `ProgramElement`,与 `FunctionDefinition`、`GlobalVarDeclaration` 等并列作为程序的顶层元素。

## 主要类与结构体

### `StructDefinition`

| 成员 | 类型 | 说明 |
|------|------|------|
| `fType` | `const Type*` | 指向结构体类型 |

## 公共 API 函数

### `StructDefinition::Convert`

```cpp
static std::unique_ptr<StructDefinition> Convert(const Context& context,
                                                 Position pos,
                                                 std::string_view name,
                                                 TArray<Field> fields);
```

从源代码创建结构体定义:
1. 调用 `Type::MakeStructType()` 创建结构体类型对象(包含字段验证)
2. 将类型添加到当前符号表
3. 返回新的 `StructDefinition`

### `StructDefinition::Make`

```cpp
static std::unique_ptr<StructDefinition> Make(Position pos, const Type& type);
```

从已有类型创建结构体定义,不执行额外验证。

### `description`

```cpp
std::string description() const override;
```

生成结构体的 SkSL 文本表示,遍历所有字段并输出其布局、修饰符、类型和名称。

## 内部实现细节

- `Convert()` 委托 `Type::MakeStructType()` 进行字段验证和类型创建
- 结构体类型通过 `context.fSymbolTable->add()` 注册到符号表,使其可以被后续代码引用
- `description()` 遍历 `type().fields()` 生成文本,每个字段输出格式为 `layout_desc modifier_desc type_name field_name;`

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLProgramElement.h` | 基类 |
| `SkSLType.h` | 类型系统(结构体类型创建和字段定义) |
| `SkSLSymbolTable.h` | 符号表(类型注册) |
| `SkSLContext.h` | 编译上下文 |
| `SkSLLayout.h` | 字段布局信息 |
| `SkSLModifierFlags.h` | 字段修饰符 |

## 设计模式与设计决策

1. **类型与定义分离**: `StructDefinition` 仅是一个"壳",实际类型信息存储在 `Type` 对象中。这使得类型可以在没有定义节点的情况下存在(如内置类型)
2. **符号表集成**: `Convert()` 将类型自动注册到符号表,确保结构体类型在定义后立即可用
3. **程序元素**: 作为 `ProgramElement`,结构体定义可以出现在程序的顶层元素列表中

## 性能考量

- `StructDefinition` 本身非常轻量,仅持有一个指向 `Type` 的指针
- 类型创建和符号表注册仅在编译时发生一次

## 相关文件

- `src/sksl/ir/SkSLType.h` -- 类型系统,包含 `Field` 结构体和 `MakeStructType()` 方法
- `src/sksl/ir/SkSLProgramElement.h` -- 程序元素基类
- `src/sksl/ir/SkSLSymbolTable.h` -- 符号表
- `src/sksl/ir/SkSLVariable.h` -- 变量(结构体实例)
- `src/sksl/ir/SkSLFieldAccess.h` -- 字段访问表达式
