# SkSL Program - 程序表示

> 源文件:
> - `src/sksl/ir/SkSLProgram.h`
> - `src/sksl/ir/SkSLProgram.cpp`

## 概述

`Program` 结构体表示一个完整的 SkSL 程序,是编译完成后的最终产物,包含所有程序元素(函数定义、全局变量声明、结构体定义等)、符号表、程序配置和使用分析数据。它是代码生成阶段的输入。

该文件还定义了 `UniformInfo`(uniform 变量信息)和 `ProgramInterface`(程序输入输出接口)等辅助结构体。

## 架构位置

```
SkSL 编译器
└── 编译产物
    └── Program  <-- 本文件
        ├── ProgramConfig (编译配置)
        ├── Context (编译上下文)
        ├── SymbolTable (符号表)
        ├── ProgramUsage (使用分析)
        ├── OwnedElements (程序拥有的元素)
        ├── SharedElements (模块共享的元素)
        └── ProgramInterface (接口信息)
```

## 主要类与结构体

### `UniformInfo`

描述程序中的 uniform 变量列表:

| 成员 | 说明 |
|------|------|
| `fUniforms` | uniform 变量数组 |
| `fUniformSlotCount` | uniform 总槽数 |

每个 `Uniform` 包含:名称、数值类型、列数、行数、起始槽位。

### `ProgramInterface`

描述程序的输入输出特性:

| 成员 | 类型 | 说明 |
|------|------|------|
| `fRTFlipUniform` | `uint8_t` | RTFlip uniform 需求(FragCoord/Clockwise/Derivative) |
| `fUseLastFragColor` | `bool` | 是否使用上一帧的颜色 |
| `fOutputSecondaryColor` | `bool` | 是否输出第二颜色 |

RTFlip 标志使用位域:
- `kRTFlip_FragCoord` (0x01): 片段坐标需要翻转
- `kRTFlip_Clockwise` (0x02): 顺时针方向需要翻转
- `kRTFlip_Derivative` (0x04): 导数需要翻转

### `Program`

| 成员 | 类型 | 说明 |
|------|------|------|
| `fSource` | `unique_ptr<string>` | 源代码 |
| `fConfig` | `unique_ptr<ProgramConfig>` | 程序配置 |
| `fContext` | `shared_ptr<Context>` | 编译上下文(共享) |
| `fUsage` | `unique_ptr<ProgramUsage>` | 使用分析数据 |
| `fSymbols` | `unique_ptr<SymbolTable>` | 符号表 |
| `fPool` | `unique_ptr<Pool>` | 内存池 |
| `fOwnedElements` | `vector<unique_ptr<ProgramElement>>` | 程序拥有的元素 |
| `fSharedElements` | `vector<const ProgramElement*>` | 模块共享的元素(只读) |
| `fInterface` | `ProgramInterface` | 接口信息 |

### `ElementsCollection`

内部迭代器类,用于统一遍历 `fSharedElements`(共享)和 `fOwnedElements`(自有)元素:

- 先迭代共享元素,再迭代自有元素
- 迭代器值类型为 `const ProgramElement*`(不可修改)

## 公共 API 函数

### `Program::elements`

```cpp
ElementsCollection elements() const;
```

返回迭代器集合,遍历所有程序元素(共享 + 自有)。返回只读指针,确保共享数据不被意外修改。

### `Program::getFunction`

```cpp
const FunctionDeclaration* getFunction(const char* functionName) const;
```

按名称查找函数声明。仅返回有定义(函数体)的函数,否则返回 null。

### `Program::description`

```cpp
std::string description() const;
```

生成程序的 SkSL 文本表示,包括版本声明和所有元素的描述。

### `Program::usage`

```cpp
const ProgramUsage* usage() const;
```

返回程序使用分析数据(变量引用计数等)。

## 内部实现细节

### 构造函数

在构造函数中:
1. 接管所有传入的所有权参数
2. 调用 `Analysis::GetUsage(*this)` 分析程序使用情况

### 析构函数

析构函数特别注意内存管理顺序:
1. **先附加内存池**: 调用 `AutoAttachPoolToThread` 将池附加到当前线程
2. **清理元素**: `fOwnedElements.clear()` -- 某些元素可能在池中分配
3. **清理上下文和符号表**: `fContext.reset()`, `fSymbols.reset()`

这个顺序至关重要,因为 IR 元素可能在池中分配,直接 `delete` 会导致错误。附加池后,池中的内存会被正确释放。

### 元素所有权模型

- **fOwnedElements**: 程序独占的元素(如用户定义的函数、变量等)
- **fSharedElements**: 来自内置模块的共享元素(如内置函数声明),程序不拥有所有权

`fSymbols` 的定义顺序在 `fOwnedElements` 之前很重要,因为 IR 元素在析构时可能会访问符号表。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLType.h` | 类型系统(UniformInfo 的 NumberKind) |
| `SkSLProgramElement.h` | 程序元素基类 |
| `SkSLFunctionDeclaration.h` | 函数查找 |
| `SkSLSymbolTable.h` | 符号表 |
| `SkSLAnalysis.h` | 使用分析(GetUsage) |
| `SkSLPool.h` | 内存池 |
| `SkSLProgramSettings.h` | 程序配置 |
| `SkSLProgramUsage.h` | 使用分析数据 |

## 设计模式与设计决策

1. **共享/自有元素分离**: 将模块的共享元素和程序自有元素分开存储,避免不必要的拷贝和所有权问题
2. **统一迭代器**: `ElementsCollection` 提供统一的遍历接口,隐藏了双列表的实现细节
3. **内存池生命周期管理**: 析构函数中精心安排的清理顺序确保池中分配的对象被正确释放
4. **上下文共享**: `fContext` 使用 `shared_ptr`,允许多个程序共享同一编译上下文
5. **RTFlip 接口**: 使用位域紧凑地表示 Y 轴翻转相关的需求

## 性能考量

- `ElementsCollection` 迭代器不创建副本,直接引用两个底层容器的迭代器
- 使用内存池(`Pool`)管理 IR 节点分配,减少碎片化和分配开销
- `getFunction()` 通过符号表查找,是 O(1) 哈希表操作
- `description()` 在每次调用时遍历所有元素生成字符串,适用于调试而非性能敏感路径

## 相关文件

- `src/sksl/SkSLCompiler.h` -- 编译器主类,生成 Program
- `src/sksl/ir/SkSLProgramElement.h` -- 程序元素基类
- `src/sksl/ir/SkSLFunctionDefinition.h` -- 函数定义(程序的主要元素)
- `src/sksl/ir/SkSLSymbolTable.h` -- 符号表
- `src/sksl/analysis/SkSLProgramUsage.h` -- 使用分析数据
- `src/sksl/SkSLPool.h` -- 内存池
- `src/sksl/SkSLProgramSettings.h` -- 程序配置
