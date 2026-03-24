# SkSLContext

> 源文件: src/sksl/SkSLContext.h, src/sksl/SkSLContext.cpp

## 概述

`Context` 是SkSL编译器的核心上下文类,负责管理编译器范围内的对象和状态。它作为编译过程中各个组件之间的中心协调器,持有对内置类型系统、错误报告器、程序配置、模块信息和符号表的引用。每个编译任务都需要一个Context实例来维护编译过程中的必要信息。

该类采用轻量级设计,仅存储指针和引用,不拥有大多数资源的所有权。它在编译器初始化时创建,在编译完成后销毁,生命周期与单次编译任务相对应。Context的设计使得SkSL编译器能够支持并发编译(通过为每个编译任务创建独立的Context实例),同时确保编译过程中的状态一致性。

## 架构位置

在SkSL编译器的架构中,Context位于核心层,作为各个编译阶段的状态容器:

```
编译流程:
    Compiler (编译器入口)
        ↓
    Context (编译上下文) ←── 当前组件
        ├── 引用 BuiltinTypes (内置类型)
        ├── 引用 ErrorReporter (错误报告)
        ├── 引用 ProgramConfig (程序配置)
        ├── 引用 Module (模块)
        └── 引用 SymbolTable (符号表)
        ↓
    Parser → Optimizer → CodeGenerator
```

Context是编译器和各个子系统之间的桥梁,它不执行具体的编译工作,而是提供编译过程所需的所有上下文信息。

## 主要类与结构体

### Context 类

```cpp
class Context {
public:
    Context(const BuiltinTypes& types, ErrorReporter& errors);
    ~Context();

    const BuiltinTypes& fTypes;        // 内置类型系统
    ProgramConfig* fConfig = nullptr;  // 程序配置
    ErrorReporter* fErrors;            // 错误报告器
    const Module* fModule = nullptr;   // 内置声明模块
    SymbolTable* fSymbolTable = nullptr; // 当前符号表

    void setErrorReporter(ErrorReporter* e);
};
```

**成员字段说明**:

- **fTypes**: 对`BuiltinTypes`的常量引用,提供对所有内置类型的访问(如`float`, `int`, `vec3`等)。这是在Context创建时传入的,在整个编译过程中保持不变。

- **fConfig**: 指向`ProgramConfig`的指针,包含当前正在编译的程序的配置信息(如程序类型、优化设置等)。这个指针在编译开始前由编译器设置。

- **fErrors**: 指向`ErrorReporter`的指针,用于报告编译过程中的所有错误和警告。可以通过`setErrorReporter`方法动态更改。

- **fModule**: 指向`Module`的常量指针,包含当前程序所使用的内置声明模块(如顶点着色器模块、片段着色器模块等)。

- **fSymbolTable**: 指向`SymbolTable`的指针,代表当前正在处理的代码的符号表。这个指针在编译过程中会随着进入和退出作用域而变化。

## 公共 API 函数

### 构造函数

```cpp
Context(const BuiltinTypes& types, ErrorReporter& errors)
```

**参数**:
- `types`: 内置类型系统的引用,必须在Context的整个生命周期内保持有效
- `errors`: 错误报告器的引用,用于报告编译错误

**功能**: 初始化编译上下文,设置类型系统和错误报告器。

**实现细节**: 构造函数会断言当前线程没有附加内存池(`Pool`),确保每次编译都是在干净的状态下开始。这是通过`SkASSERT(!Pool::IsAttached())`实现的。

### 析构函数

```cpp
~Context()
```

**功能**: 清理编译上下文资源。

**实现细节**: 析构函数同样会断言当前线程没有附加内存池,确保资源被正确清理。这是一种防御性编程实践,可以在开发阶段捕获资源泄漏问题。

### setErrorReporter

```cpp
void setErrorReporter(ErrorReporter* e)
```

**参数**: `e` - 新的错误报告器指针,不能为空

**功能**: 动态更改错误报告器。

**使用场景**: 在某些情况下,可能需要临时使用不同的错误报告器(例如,在测试中使用模拟的错误报告器,或在不同的编译阶段使用不同的错误处理策略)。

**安全性**: 函数使用`SkASSERT(e)`确保传入的指针不为空,防止空指针解引用。

## 内部实现细节

### 内存池断言机制

在构造函数和析构函数中都使用了`SkASSERT(!Pool::IsAttached())`断言。这个检查确保:

1. **构造时**: 没有残留的内存池附加到当前线程,避免资源污染
2. **析构时**: 内存池已被正确分离和释放,防止资源泄漏

这种双重检查机制为SkSL的内存管理提供了额外的安全保障,特别是在调试模式下可以快速定位内存管理问题。

### 指针初始化策略

Context使用成员初始化列表和默认值初始化:
```cpp
Context::Context(const BuiltinTypes& types, ErrorReporter& errors)
        : fTypes(types)
        , fErrors(&errors) {
    // fConfig默认为nullptr
    // fModule默认为nullptr
    // fSymbolTable默认为nullptr
}
```

这种设计意味着:
- 类型系统和错误报告器在创建时就必须提供
- 其他成员会在编译过程的不同阶段被设置
- 明确区分了"必需的上下文"和"编译阶段相关的上下文"

### 生命周期管理

Context采用浅拷贝语义(只存储指针和引用),不拥有所指对象的所有权。这意味着:
- Context的创建和销毁非常轻量
- 调用者负责确保被引用对象的生命周期
- 适合在栈上创建Context实例

## 依赖关系

### 内部依赖

| 依赖项 | 类型 | 用途 |
|--------|------|------|
| `BuiltinTypes` | 类引用 | 提供所有内置类型定义 |
| `ErrorReporter` | 类指针 | 错误和警告的报告机制 |
| `ProgramConfig` | 结构体指针 | 编译配置信息 |
| `Module` | 结构体指针 | 内置模块定义 |
| `SymbolTable` | 类指针 | 符号查找和作用域管理 |
| `Pool` | 类(静态方法) | 内存池管理 |

### 外部依赖

Context被整个SkSL编译器系统广泛使用:

| 使用者 | 关系 | 说明 |
|--------|------|------|
| `Compiler` | 创建和管理 | 为每次编译创建Context实例 |
| `Parser` | 使用 | 在语法分析时访问符号表和类型系统 |
| `ConstantFolder` | 使用 | 常量折叠时需要访问配置和错误报告器 |
| `Inliner` | 使用 | 函数内联时需要访问符号表和配置 |
| `CodeGenerator` | 使用 | 代码生成时需要访问类型系统和配置 |

## 设计模式与设计决策

### 1. 中心化上下文模式

Context采用了经典的"上下文对象"模式,将编译过程中需要的所有全局状态集中在一个对象中。这种设计的优点包括:
- 避免了全局变量的使用
- 使得单元测试更加容易(可以创建独立的测试上下文)
- 支持并发编译(每个编译任务使用独立的Context)

### 2. 引用语义与指针语义的混合使用

Context对不同类型的依赖使用了不同的语义:
- **引用** (`const BuiltinTypes& fTypes`): 用于生命周期由外部管理且不会改变的对象
- **指针** (`ErrorReporter* fErrors`): 用于可能需要动态更改的对象

这种区分使得API的意图更加明确:引用表示"必需且不变",指针表示"可选或可变"。

### 3. 延迟初始化策略

除了类型系统和错误报告器,其他成员都默认为`nullptr`,在编译过程的不同阶段被设置。这种设计:
- 使得Context的创建成本最小化
- 明确了编译过程的阶段性
- 允许在不同阶段重用同一个Context实例

### 4. 防御性编程

通过在构造和析构时检查内存池状态,Context实现了一种防御性编程策略。这些断言在调试版本中提供了额外的安全保障,而在发布版本中会被编译器优化掉,不影响性能。

## 性能考量

### 1. 轻量级设计

Context只包含指针和引用,整个对象的大小约为40-48字节(在64位系统上):
```
fTypes引用:      8字节
fConfig指针:     8字节
fErrors指针:     8字节
fModule指针:     8字节
fSymbolTable指针: 8字节
总计:           40字节 (+ 可能的对齐填充)
```

这使得Context可以高效地在栈上创建和传递,避免了动态内存分配的开销。

### 2. 缓存友好性

Context的所有成员都是指针或引用,在访问时会产生额外的间接寻址开销。但是,由于这些被指向的对象(如BuiltinTypes)在编译过程中会被频繁访问,它们很可能已经在CPU缓存中,因此间接寻址的额外开销在实际使用中是可以接受的。

### 3. 避免虚函数调用

Context本身不是虚基类,所有成员函数都是非虚函数。这意味着对Context方法的调用可以被编译器内联优化,没有虚函数调用的开销。

### 4. 内存池集成

通过在构造和析构时检查内存池状态,Context确保了SkSL的内存池机制能够正确工作。这种集成使得编译过程中的大量临时对象可以使用高效的内存池分配,而不是标准的堆分配,显著提升了编译性能。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/sksl/SkSLCompiler.h` | 创建者 | Compiler类创建和管理Context实例 |
| `src/sksl/SkSLBuiltinTypes.h` | 依赖 | 提供内置类型系统 |
| `src/sksl/SkSLErrorReporter.h` | 依赖 | 提供错误报告机制 |
| `src/sksl/SkSLModule.h` | 依赖 | 定义模块结构 |
| `src/sksl/SkSLProgramSettings.h` | 依赖 | 定义程序配置 |
| `src/sksl/ir/SkSLSymbolTable.h` | 依赖 | 提供符号表功能 |
| `src/sksl/SkSLPool.h` | 内存管理 | 内存池状态检查 |
| `src/sksl/SkSLParser.h` | 使用者 | 解析器使用Context进行语法分析 |
| `src/sksl/SkSLConstantFolder.h` | 使用者 | 常量折叠使用Context的配置信息 |
