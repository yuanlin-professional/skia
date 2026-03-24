# SkSLSymbol

> 源文件: src/sksl/ir/SkSLSymbol.h, src/sksl/ir/SkSLSymbol.cpp

## 概述

`Symbol` 类是 SkSL（Skia Shading Language）中间表示(IR)的核心基类，代表符号表中的条目。它为所有类型的符号提供统一的抽象接口，包括变量、函数、类型、字段等。作为 `IRNode` 的直接子类，`Symbol` 建立了符号表管理和表达式实例化的基础架构。该类的主要职责是存储符号的基本元信息（名称、类型、种类），并提供将符号转换为具体表达式的实例化机制。

## 架构位置

`Symbol` 位于 Skia 的 SkSL 编译器架构的 IR 层中：

```
skia/
  src/
    sksl/
      ir/
        SkSLIRNode.h              # Symbol 的基类
        SkSLSymbol.h/cpp          # 本文件，符号基类
        SkSLVariable.h            # 变量符号（Symbol 子类）
        SkSLFunctionDeclaration.h # 函数声明符号（Symbol 子类）
        SkSLType.h                # 类型符号（Symbol 子类）
        SkSLFieldSymbol.h         # 字段符号（Symbol 子类）
        SkSLExpression.h          # 表达式基类
        SkSLVariableReference.h   # 变量引用表达式
        SkSLFunctionReference.h   # 函数引用表达式
        SkSLTypeReference.h       # 类型引用表达式
        SkSLFieldAccess.h         # 字段访问表达式
      SkSLSymbolTable.h           # 符号表管理
      SkSLContext.h               # 编译上下文
```

在编译流程中的位置：
- **词法/语法分析 → 符号表构建 → `Symbol` 实例化 → IR 生成 → 代码生成**
- `Symbol` 是连接符号表和表达式 IR 的桥梁

## 主要类与结构体

### Symbol 类

```cpp
class Symbol : public IRNode {
public:
    using Kind = SymbolKind;

    // 构造函数：初始化符号的位置、种类、名称和类型
    Symbol(Position pos, Kind kind, std::string_view name, const Type* type = nullptr);

    // 核心方法：将符号实例化为对应的表达式
    std::unique_ptr<Expression> instantiate(const Context& context, Position pos) const;

    // 访问器
    const Type& type() const;
    Kind kind() const;
    std::string_view name() const;
    void setName(std::string_view newName);  // 需通过 SymbolTable::renameSymbol 调用

private:
    std::string_view fName;   // 符号名称（字符串视图，无拷贝）
    const Type* fType;        // 符号类型（可为 nullptr）
};
```

### 符号种类 (SymbolKind)

虽然定义在其他文件中，但 `Symbol` 支持的主要类型包括：
- `kFunctionDeclaration`: 函数声明符号
- `kVariable`: 变量符号
- `kField`: 结构体/接口块字段符号
- `kType`: 类型定义符号
- 其他扩展符号类型

## 公共 API 函数

### 构造函数

```cpp
Symbol(Position pos, Kind kind, std::string_view name, const Type* type = nullptr)
```

**功能**: 创建符号对象，初始化所有基本属性。

**参数**:
- `pos`: 符号在源代码中的位置信息
- `kind`: 符号种类（函数、变量、类型等）
- `name`: 符号名称（使用 `string_view` 避免不必要的字符串拷贝）
- `type`: 符号关联的类型（可选，某些符号如类型定义本身可能不需要）

**断言**: 确保 `kind` 在有效范围内 (`kFirst` 到 `kLast`)。

### instantiate

```cpp
std::unique_ptr<Expression> instantiate(const Context& context, Position pos) const
```

**功能**: 将符号转换为相应的表达式对象，是符号到表达式的核心转换逻辑。

**参数**:
- `context`: 编译上下文，提供类型系统和其他编译信息
- `pos`: 表达式实例化的位置（可能与符号定义位置不同）

**返回**: 对应的表达式对象智能指针，具体类型取决于符号种类

**转换规则**:
- `kFunctionDeclaration` → `FunctionReference` 表达式
- `kVariable` → `VariableReference` 表达式（默认读取模式）
- `kField` → `FieldAccess` 表达式（包含匿名接口块字段访问）
- `kType` → `TypeReference` 表达式
- 其他类型 → 调试失败，返回 `nullptr`

### 访问器方法

```cpp
const Type& type() const
```
返回符号的类型，带断言确保类型已设置。

```cpp
Kind kind() const
```
返回符号的种类枚举值。

```cpp
std::string_view name() const
```
返回符号名称的字符串视图。

```cpp
void setName(std::string_view newName)
```
修改符号名称。**重要**: 应通过 `SymbolTable::renameSymbol` 调用，而非直接调用此方法，以维护符号表一致性。

## 内部实现细节

### 字符串视图优化

使用 `std::string_view` 而非 `std::string` 存储符号名称，避免内存分配和字符串拷贝。这假定符号名称的生命周期由外部（如符号表或AST节点）管理。

### 实例化策略

`instantiate` 方法采用工厂模式，根据符号种类动态创建对应的表达式类型：

1. **函数引用**: 直接包装函数声明为 `FunctionReference`
2. **变量引用**: 创建 `VariableReference`，默认为读模式（`kRead`），写模式由后续分析阶段修正
3. **字段访问**: 复合创建逻辑
   - 先创建字段所属变量的 `VariableReference`
   - 再创建 `FieldAccess` 包装，指定字段索引
   - 标记为匿名接口块所有者类型
4. **类型引用**: 调用 `TypeReference::Convert` 进行类型转换

### 内存管理

- 使用 `std::unique_ptr` 返回表达式对象，明确所有权语义
- `fType` 指针不拥有内存，由类型系统统一管理
- `fName` 字符串视图不拥有字符串内存

## 依赖关系

### 直接依赖

**头文件依赖**:
- `SkSLIRNode.h`: 提供 `IRNode` 基类
- `SkSLPosition.h`: 位置信息类
- `SkAssert.h`: 断言宏

**实现文件额外依赖**:
- `SkSLExpression.h`: 表达式基类
- `SkSLFieldAccess.h`: 字段访问表达式
- `SkSLFieldSymbol.h`: 字段符号
- `SkSLFunctionDeclaration.h`: 函数声明
- `SkSLFunctionReference.h`: 函数引用表达式
- `SkSLType.h`: 类型系统
- `SkSLTypeReference.h`: 类型引用表达式
- `SkSLVariable.h`: 变量符号
- `SkSLVariableReference.h`: 变量引用表达式

### 被依赖关系

所有具体符号类型（`Variable`, `FunctionDeclaration`, `Type`, `FieldSymbol` 等）都继承自 `Symbol`，符号表系统依赖本类进行符号管理。

### 循环依赖处理

头文件中使用前向声明（`class Context`, `class Expression`, `class Type`）避免循环包含，实现文件中才包含完整定义。

## 设计模式与设计决策

### 设计模式

1. **模板方法模式**: `Symbol` 定义符号的基本接口，子类实现具体符号行为
2. **工厂模式**: `instantiate` 方法根据符号类型创建相应表达式对象
3. **策略模式**: 不同符号种类对应不同的实例化策略

### 设计决策

**为什么使用 `string_view`？**
- 避免字符串拷贝开销，尤其在频繁查询符号表时
- 符号名称通常由 AST 节点或字符串池管理，生命周期有保证
- 权衡：需要确保字符串来源的生命周期大于符号对象

**为什么 `type()` 有断言而构造函数允许 `nullptr`？**
- 某些符号（如类型定义本身）在创建时可能不需要关联类型
- 访问 `type()` 的代码通常期望类型存在，断言可早期发现逻辑错误

**为什么 `setName` 标注不直接调用？**
- 符号表内部维护名称到符号的映射
- 直接修改名称会导致映射不一致
- 通过 `SymbolTable::renameSymbol` 确保映射同步更新

**为什么字段访问需要特殊处理？**
- 匿名接口块的字段在 GLSL/SkSL 中可以直接使用字段名访问
- 内部实际是 `接口块变量.字段` 的访问模式
- `instantiate` 需要自动展开这种隐式访问

## 性能考量

### 优化策略

1. **零拷贝语义**: 使用 `string_view` 避免字符串拷贝
2. **轻量级基类**: 仅存储两个指针大小的成员（名称视图 + 类型指针）
3. **惰性实例化**: 只在需要表达式时才创建，而非在符号创建时
4. **内联友好**: 小型访问器方法可被编译器内联

### 内存开销

- **基类开销**: `IRNode` 的虚表指针 + 位置信息 + 种类标记
- **本类开销**: 16 字节（`string_view`: 16字节，`Type*`: 8字节，在64位系统）
- **总计**: 约 32-40 字节/符号对象（取决于 `IRNode` 实现）

### 潜在瓶颈

- **实例化开销**: 每次引用符号都需要创建新表达式对象，大量符号引用可能影响性能
- **虚函数调用**: `instantiate` 通过符号种类分支，比虚函数调度快，但仍有开销
- **内存分配**: `make_unique` 会触发堆分配

## 相关文件

### 核心相关文件

- **src/sksl/ir/SkSLIRNode.h**: IR 节点基类
- **src/sksl/SkSLSymbolTable.h**: 符号表管理，使用 `Symbol` 存储符号
- **src/sksl/SkSLContext.h**: 编译上下文，提供类型系统和实例化环境

### 具体符号类型实现

- **src/sksl/ir/SkSLVariable.h**: 变量符号
- **src/sksl/ir/SkSLFunctionDeclaration.h**: 函数声明符号
- **src/sksl/ir/SkSLType.h**: 类型符号
- **src/sksl/ir/SkSLFieldSymbol.h**: 字段符号

### 表达式类型

- **src/sksl/ir/SkSLExpression.h**: 表达式基类
- **src/sksl/ir/SkSLVariableReference.h**: 变量引用表达式
- **src/sksl/ir/SkSLFunctionReference.h**: 函数引用表达式
- **src/sksl/ir/SkSLTypeReference.h**: 类型引用表达式
- **src/sksl/ir/SkSLFieldAccess.h**: 字段访问表达式

### 使用示例

符号解析和实例化流程：
```cpp
// 1. 符号表查找符号
const Symbol* symbol = symbolTable.find("myVariable");

// 2. 实例化为表达式
std::unique_ptr<Expression> expr = symbol->instantiate(context, currentPosition);

// 3. 在 IR 中使用表达式
// expr 现在是 VariableReference 或其他表达式类型
```
