# SkSL Module（模块系统）

> 源文件：[src/sksl/SkSLModule.h](../../src/sksl/SkSLModule.h)、[src/sksl/SkSLModule.cpp](../../src/sksl/SkSLModule.cpp)

## 概述

`SkSLModule` 定义了 SkSL 编译器的模块系统基础结构。模块是预编译的 SkSL 代码单元，包含内置函数、类型和变量的声明。SkSL 程序在编译时会继承来自特定模块的符号，从而获得对应着色器类型（如片段着色器、顶点着色器等）的内置能力。该文件定义了 `Module` 结构体、`ModuleType` 枚举以及模块类型的管理宏。

## 架构位置

模块系统位于 SkSL 编译器的基础层，为所有编译操作提供预定义的符号环境：

```
程序源代码 -> 解析器 -> IR 树
                 ^
                 |
       Module（提供内置符号）
         ^
         |
    ModuleLoader（加载和缓存模块）
```

模块形成层级结构，子模块继承父模块的符号：
```
rootModule -> sksl_shared -> sksl_gpu -> sksl_frag / sksl_vert / sksl_compute
                          -> sksl_public -> sksl_rt_shader
```

## 主要类与结构体

### `enum class ModuleType : int8_t`

通过 X-Macro (`SKSL_MODULE_LIST`) 定义的模块类型枚举：

| 值 | 说明 |
|----|------|
| `program` (0) | 非模块代码，即用户程序 |
| `unknown` (1) | 未在列表中的模块 |
| `sksl_shared` | 所有着色器类型共享的基础模块 |
| `sksl_compute` | 计算着色器模块 |
| `sksl_frag` | 片段着色器模块 |
| `sksl_gpu` | GPU 通用模块 |
| `sksl_public` | 公共 Runtime Effect 模块 |
| `sksl_rt_shader` | Runtime Shader 私有模块 |
| `sksl_vert` | 顶点着色器模块 |
| `sksl_graphite_frag` | Graphite 片段着色器模块 |
| `sksl_graphite_vert` | Graphite 顶点着色器模块 |

### `struct Module`

模块的核心数据结构：

| 字段 | 类型 | 说明 |
|------|------|------|
| `fParent` | `const Module*` | 父模块指针，形成模块继承链 |
| `fSymbols` | `std::unique_ptr<SymbolTable>` | 模块的符号表 |
| `fElements` | `std::vector<std::unique_ptr<ProgramElement>>` | 模块中的程序元素（函数、变量等） |
| `fModuleType` | `ModuleType` | 模块的类型标识 |

## 公共 API 函数

### `const char* ModuleTypeToString(ModuleType type)`

将 `ModuleType` 枚举值转换为其字符串名称。使用 X-Macro 自动生成 switch-case，对于未知类型返回 `"unknown"`。

### `std::string GetModuleData(ModuleType type, const char* filename)`

获取指定模块的源代码数据。该函数声明在头文件中，具体实现取决于构建配置（嵌入式或文件系统加载）。

## 内部实现细节

### X-Macro 技术

`SKSL_MODULE_LIST` 宏使用 X-Macro 模式统一管理模块列表。这允许在一处定义所有模块名称，然后在多处自动展开：

```cpp
#define SKSL_MODULE_LIST(M)   \
    M(sksl_shared)            \
    M(sksl_compute)           \
    ...

// 生成枚举值
#define M(type) type,
    SKSL_MODULE_LIST(M)
#undef M

// 生成字符串转换
#define M(type) case ModuleType::type: return #type;
    SKSL_MODULE_LIST(M)
#undef M
```

### 极简的 cpp 实现

`SkSLModule.cpp` 仅包含 `ModuleTypeToString` 的实现，使用与头文件相同的 `SKSL_MODULE_LIST` 宏自动生成字符串映射。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLProgramElement.h` | 模块中的程序元素基类 |
| `SkSLSymbolTable.h` | 模块符号表 |

## 设计模式与设计决策

1. **X-Macro 模式**：使用 X-Macro 保证枚举定义和字符串转换的一致性，添加新模块时只需修改一处。
2. **模块继承链**：通过 `fParent` 指针形成模块树，子模块自动继承父模块的所有符号。
3. **值类型设计**：`Module` 使用 `struct` 而非 `class`，所有字段公开，强调其作为数据容器的角色。
4. **延迟加载**：模块数据通过 `GetModuleData` 按需获取，与 `ModuleLoader` 配合实现懒加载。

## 性能考量

- 模块的符号表通过指针链接，避免复制开销
- 模块一旦加载即缓存，不会重复编译
- `ModuleType` 使用 `int8_t` 底层类型，最小化枚举存储开销

## 相关文件

- `src/sksl/SkSLModuleLoader.h` / `.cpp` —— 模块加载器，管理模块的加载和缓存
- `src/sksl/SkSLCompiler.h` / `.cpp` —— 编译器使用模块初始化编译上下文
- `src/sksl/ir/SkSLSymbolTable.h` —— 符号表定义
- `src/sksl/ir/SkSLProgramElement.h` —— 程序元素基类
