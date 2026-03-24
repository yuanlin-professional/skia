# SkSL IR (中间表示) - Skia着色器语言的抽象语法树与类型系统

## 概述

`src/sksl/ir` 目录是 Skia 着色器语言 (SkSL) 编译器的核心组成部分，包含了**中间表示 (Intermediate Representation, IR)** 的完整定义。SkSL 是 Skia 图形库自研的着色器语言，语法上与 GLSL 高度相似，但提供了跨平台的着色器编译能力，可以将统一的着色器源码转换为 GLSL、HLSL、Metal Shading Language、SPIR-V 等多种后端目标代码。

IR 是编译器前端（词法分析、语法分析）和后端（代码生成）之间的桥梁。当 SkSL 源代码经过解析器处理后，会被转换为一棵由 `IRNode` 派生类组成的完全解析 (fully-resolved) 的语法树。在这棵树中，所有类型已经确定、所有标识符已经解析、所有隐式类型转换已经插入、所有语义验证已经完成。这意味着后端代码生成器可以直接遍历 IR 树来产出目标代码，无需再进行任何类型推断或名称解析。

本目录共包含约 108 个文件（含 `.h` 头文件和 `.cpp` 实现文件，以及一个 `BUILD.bazel` 构建文件），涵盖了表达式 (Expression)、语句 (Statement)、类型 (Type)、符号 (Symbol)、程序元素 (ProgramElement) 等所有 IR 节点类型。每个 IR 节点类都遵循统一的设计范式：通过 `Convert()` 方法进行带类型检查的构造（错误通过 ErrorReporter 报告），通过 `Make()` 方法进行已验证的快速构造（错误通过 ASSERT 断言），并通过 `description()` 方法提供可读的文本表示。

整个 IR 系统采用基于内存池 (Pool) 的分配策略，所有 `IRNode` 继承自 `Poolable` 基类，支持高效的批量分配与释放。同时，IR 节点禁止拷贝构造和赋值操作，确保树结构的唯一所有权语义，子节点通过 `std::unique_ptr` 管理生命周期。

## 架构图

```
                        +-----------+
                        |  Poolable |  (内存池分配基类)
                        +-----+-----+
                              |
                        +-----+-----+
                        |  IRNode   |  (IR节点抽象基类，含Position和Kind)
                        +-----+-----+
                              |
            +-----------------+-----------------+------------------+
            |                 |                 |                  |
    +-------+-------+ +------+------+  +--------+-------+ +-------+--------+
    | ProgramElement| |  Statement  |  |   Expression   | |    Symbol      |
    | (顶层程序元素) | |  (语句)     |  |   (表达式)     | |  (符号表条目)   |
    +-------+-------+ +------+------+  +--------+-------+ +-------+--------+
            |                |                  |                  |
    +-------+------+  +------+------+  +--------+------+  +-------+--------+
    |FunctionDef   |  |ForStatement |  |BinaryExpr    |  |Type            |
    |GlobalVarDecl |  |IfStatement  |  |FunctionCall  |  |Variable        |
    |InterfaceBlock|  |Block        |  |Literal       |  |FuncDeclaration |
    |StructDef     |  |ReturnStmt   |  |Swizzle       |  |FieldSymbol     |
    |Extension     |  |SwitchStmt   |  |Constructor*  |  +----------------+
    |ModifiersDecl |  |DoStatement  |  |FieldAccess   |
    |FuncPrototype |  |VarDecl      |  |IndexExpr     |
    +--------------+  |BreakStmt    |  |TernaryExpr   |
                      |ContinueStmt|  |VarReference   |
                      |DiscardStmt |  |Prefix/Postfix |
                      |ExprStmt    |  |TypeReference  |
                      |Nop         |  |EmptyExpr      |
                      |SwitchCase  |  |Poison         |
                      +-------------+  +---------------+

    +------------------+          +------------------+
    |   SymbolTable    |          |     Program      |
    | (符号表/作用域链) |          | (完整编译程序)    |
    +------------------+          +------------------+

    辅助类:
    +----------+  +----------------+  +---------------+  +-----------+
    |  Layout  |  | ModifierFlags  |  | CoercionCost  |  | IRHelpers |
    +----------+  +----------------+  +---------------+  +-----------+
```

## 目录结构

```
src/sksl/ir/
├── BUILD.bazel                         # Bazel 构建配置
│
│  ===== 核心基类 =====
├── SkSLIRNode.h                        # IR 节点抽象基类，定义所有 Kind 枚举
├── SkSLExpression.h / .cpp             # 表达式基类
├── SkSLStatement.h                     # 语句基类
├── SkSLProgramElement.h                # 顶层程序元素基类
├── SkSLSymbol.h / .cpp                 # 符号(标识符)基类
│
│  ===== 程序与类型系统 =====
├── SkSLProgram.h / .cpp                # 完整编译程序表示
├── SkSLType.h / .cpp                   # 类型系统（标量、向量、矩阵、数组、结构体等）
├── SkSLSymbolTable.h / .cpp            # 符号表（名称到符号的映射，支持作用域链）
├── SkSLLayout.h / .cpp                 # layout 限定符 (location, binding, set 等)
├── SkSLModifierFlags.h / .cpp          # 修饰符标志 (const, uniform, in, out 等)
├── SkSLModifiers.h                     # 修饰符聚合结构 (Layout + ModifierFlags)
├── SkSLModifiersDeclaration.h / .cpp   # 修饰符声明（顶层程序元素）
│
│  ===== 表达式类 =====
├── SkSLBinaryExpression.h / .cpp       # 二元表达式 (a + b, a = b)
├── SkSLPrefixExpression.h / .cpp       # 前缀表达式 (-a, !b, ++c)
├── SkSLPostfixExpression.h / .cpp      # 后缀表达式 (a++, b--)
├── SkSLTernaryExpression.h / .cpp      # 三元表达式 (a ? b : c)
├── SkSLLiteral.h / .cpp                # 字面量 (int, float, bool 常量)
├── SkSLVariableReference.h / .cpp      # 变量引用 (读/写/读写)
├── SkSLFieldAccess.h / .cpp            # 字段访问 (struct.field)
├── SkSLIndexExpression.h / .cpp        # 索引表达式 (array[i], vec[0])
├── SkSLSwizzle.h / .cpp                # 分量重排 (vec.xyzw, vec.rgba)
├── SkSLFunctionCall.h / .cpp           # 函数调用
├── SkSLFunctionReference.h             # 函数引用（未调用的函数名）
├── SkSLMethodReference.h               # 方法引用
├── SkSLChildCall.h / .cpp              # 子效果调用 (shader/colorFilter/blender)
├── SkSLTypeReference.h / .cpp          # 类型引用（未构造的类型名）
├── SkSLSetting.h / .cpp                # sk_Caps 设置表达式
├── SkSLEmptyExpression.h               # 空表达式占位符
├── SkSLPoison.h                        # 毒化表达式（错误恢复用）
│
│  ===== 构造器类 (Constructor) =====
├── SkSLConstructor.h / .cpp            # 构造器基类与工厂（AnyConstructor, Single/Multi）
├── SkSLConstructorArray.h / .cpp       # 数组构造 float[3](1,2,3)
├── SkSLConstructorArrayCast.h / .cpp   # 数组类型转换
├── SkSLConstructorCompound.h / .cpp    # 复合构造 float4(1,2,3,4)
├── SkSLConstructorCompoundCast.h / .cpp# 复合类型转换 half4(floatVec)
├── SkSLConstructorDiagonalMatrix.h/.cpp# 对角矩阵构造 mat3(1.0)
├── SkSLConstructorMatrixResize.h / .cpp# 矩阵尺寸调整 mat3(mat4Val)
├── SkSLConstructorScalarCast.h / .cpp  # 标量类型转换 float(intVal)
├── SkSLConstructorSplat.h / .cpp       # 标量展开 float4(1.0)
├── SkSLConstructorStruct.h / .cpp      # 结构体构造
│
│  ===== 语句类 =====
├── SkSLBlock.h / .cpp                  # 语句块 { ... }
├── SkSLForStatement.h / .cpp           # for 循环 (含循环展开信息)
├── SkSLDoStatement.h / .cpp            # do-while 循环
├── SkSLIfStatement.h / .cpp            # if-else 语句
├── SkSLSwitchStatement.h / .cpp        # switch 语句
├── SkSLSwitchCase.h / .cpp             # switch case 分支
├── SkSLReturnStatement.h               # return 语句
├── SkSLBreakStatement.h                # break 语句
├── SkSLContinueStatement.h             # continue 语句
├── SkSLDiscardStatement.h / .cpp       # discard 语句（片段着色器专用）
├── SkSLExpressionStatement.h / .cpp    # 表达式语句（表达式作为语句使用）
├── SkSLVarDeclarations.h / .cpp        # 变量声明语句 + GlobalVarDeclaration
├── SkSLNop.h                           # 空操作语句
│
│  ===== 符号类 =====
├── SkSLVariable.h / .cpp               # 变量符号 (含 ExtendedVariable)
├── SkSLFunctionDeclaration.h / .cpp    # 函数声明符号
├── SkSLFieldSymbol.h                   # 字段符号（结构体字段的符号表条目）
│
│  ===== 顶层程序元素 =====
├── SkSLFunctionDefinition.h / .cpp     # 函数定义 (声明 + 函数体)
├── SkSLFunctionPrototype.h             # 函数原型（前向声明）
├── SkSLInterfaceBlock.h / .cpp         # 接口块 (uniform block 等)
├── SkSLStructDefinition.h / .cpp       # 结构体定义
├── SkSLExtension.h / .cpp              # GLSL 扩展声明 (#extension ...)
│
│  ===== 辅助类 =====
├── SkSLIRHelpers.h                     # IR 构造辅助工具（简化手动创建IR节点）
```

## 关键类与函数

### 1. IRNode - IR 节点基类 (`SkSLIRNode.h`)

所有 IR 节点的根基类，继承自 `Poolable`（支持内存池分配）。

```cpp
class IRNode : public Poolable {
public:
    Position fPosition;       // 源码位置，用于错误报告
    int fKind;                // 节点类型标识

    template <typename T> bool is() const;  // 类型检查: node.is<ReturnStatement>()
    template <typename T> const T& as() const;  // 安全向下转型: node.as<ReturnStatement>()
    virtual std::string description() const = 0;  // 文本表示
};
```

`fKind` 字段可存放四种枚举之一：`ProgramElementKind`、`SymbolKind`、`StatementKind`、`ExpressionKind`。这四种枚举的数值范围互不重叠，使得 `is<T>()` 和 `as<T>()` 可以在所有 IR 节点间安全地进行类型判定和转换。

### 2. Expression - 表达式基类 (`SkSLExpression.h`)

所有表达式的抽象基类，持有类型信息。

```cpp
class Expression : public IRNode {
public:
    const Type& type() const;                // 获取表达式的类型
    bool isAnyConstructor() const;           // 是否为构造器表达式
    bool isIntLiteral() const;               // 是否为整数字面量
    bool isFloatLiteral() const;             // 是否为浮点字面量
    virtual ComparisonResult compareConstant(const Expression& other) const;  // 常量比较
    virtual std::optional<double> getConstantValue(int n) const;  // 获取第n个槽位的常量值
    virtual std::unique_ptr<Expression> clone(Position pos) const = 0;  // 深拷贝
    CoercionCost coercionCost(const Type& target) const;  // 到目标类型的转换代价
};
```

**关键表达式种类（ExpressionKind 枚举，共25种）：**
- `kBinary` - 二元运算（加减乘除、赋值、比较等）
- `kLiteral` - 字面量常量
- `kVariableReference` - 变量引用
- `kFunctionCall` - 函数调用
- `kSwizzle` - 向量分量重排
- `kFieldAccess` - 结构体字段访问
- `kIndex` - 数组/向量索引
- `kTernary` - 三元条件表达式
- `kConstructorArray/Compound/ScalarCast/...` - 各类构造器（共9种）
- `kPrefix/kPostfix` - 前缀/后缀运算
- `kChildCall` - 子效果调用
- `kPoison` - 错误恢复占位符

### 3. Statement - 语句基类 (`SkSLStatement.h`)

所有语句的抽象基类，极为简洁。

```cpp
class Statement : public IRNode {
public:
    Kind kind() const;
    virtual bool isEmpty() const;  // 判断是否为空语句
};
```

**语句种类（StatementKind 枚举，共13种）：**
- `kBlock` - 语句块
- `kFor/kDo` - 循环语句
- `kIf` - 条件语句
- `kSwitch/kSwitchCase` - 分支语句
- `kReturn/kBreak/kContinue/kDiscard` - 控制流语句
- `kVarDeclaration` - 变量声明
- `kExpression` - 表达式语句
- `kNop` - 空操作

### 4. Type - 类型系统 (`SkSLType.h`)

SkSL 类型系统的核心，继承自 `Symbol`，支持丰富的类型种类。

```cpp
class Type : public Symbol {
public:
    enum class TypeKind : int8_t {
        kArray, kAtomic, kGeneric, kLiteral, kMatrix, kOther,
        kSampler, kSeparateSampler, kScalar, kStruct, kTexture,
        kVector, kVoid, kColorFilter, kShader, kBlender
    };
    enum class NumberKind : int8_t {
        kFloat, kSigned, kUnsigned, kBoolean, kNonnumeric
    };

    // 工厂方法
    static std::unique_ptr<Type> MakeArrayType(...);
    static std::unique_ptr<Type> MakeVectorType(...);
    static std::unique_ptr<Type> MakeMatrixType(...);
    static std::unique_ptr<Type> MakeStructType(...);
    static std::unique_ptr<Type> MakeScalarType(...);
    static std::unique_ptr<Type> MakeTextureType(...);
    static std::unique_ptr<Type> MakeSamplerType(...);
    static std::unique_ptr<Type> MakeAtomicType(...);

    // 类型查询
    bool isFloat() const;       // float, half
    bool isInteger() const;     // int, short, uint, ushort
    bool isBoolean() const;     // bool
    bool isVector() const;      // float2, int3, ...
    bool isMatrix() const;      // float3x3, half2x4, ...
    bool isArray() const;       // float[10]
    bool isStruct() const;      // struct { ... }
    bool isOpaque() const;      // sampler, texture, atomic 等不透明类型

    // 维度信息
    int columns() const;        // 列数
    int rows() const;           // 行数
    size_t slotCount() const;   // 标量槽位数

    // 类型转换
    CoercionCost coercionCost(const Type& other) const;
    const Type& toCompound(const Context& context, int columns, int rows) const;
    std::unique_ptr<Expression> coerceExpression(...) const;
};
```

`CoercionCost` 结构体用于计算隐式类型转换的代价，支持三种级别：`Free`（无代价）、`Normal`（常规转换）、`Narrowing`（窄化转换）和 `Impossible`（不可转换）。函数重载解析时，选择总转换代价最低的候选函数。

### 5. Program - 编译后程序 (`SkSLProgram.h`)

表示一个完整的编译后程序，是代码生成器的输入。

```cpp
struct Program {
    std::unique_ptr<std::string> fSource;          // 原始源码
    std::unique_ptr<ProgramConfig> fConfig;        // 编译配置
    std::shared_ptr<Context> fContext;              // 编译上下文
    std::unique_ptr<ProgramUsage> fUsage;          // 使用统计
    std::unique_ptr<SymbolTable> fSymbols;         // 符号表
    std::unique_ptr<Pool> fPool;                   // 内存池
    std::vector<std::unique_ptr<ProgramElement>> fOwnedElements;   // 自有元素
    std::vector<const ProgramElement*> fSharedElements;            // 共享内建元素
    ProgramInterface fInterface;                   // 程序接口（RTFlip等）

    ElementsCollection elements() const;  // 迭代所有元素（自有+共享）
    const FunctionDeclaration* getFunction(const char* name) const;
};
```

`Program` 通过 `ElementsCollection` 提供了一个自定义迭代器，将 `fSharedElements`（来自内建模块的共享元素）和 `fOwnedElements`（程序自有元素）合并为统一的遍历序列。

### 6. SymbolTable - 符号表 (`SkSLSymbolTable.h`)

实现了支持作用域链的符号表，是名称解析的核心数据结构。

```cpp
class SymbolTable {
public:
    SymbolTable* fParent = nullptr;  // 父作用域

    const Symbol* find(std::string_view name) const;       // 查找符号（含父作用域）
    const Symbol* findBuiltinSymbol(std::string_view name) const;  // 仅查内建符号
    std::unique_ptr<Expression> instantiateSymbolRef(...);  // 生成符号引用表达式

    template <typename T> T* add(const Context&, std::unique_ptr<T>);     // 添加符号（带所有权）
    template <typename T> T* inject(std::unique_ptr<T>);                  // 强制注入符号
    void addWithoutOwnership(const Context&, Symbol*);                    // 添加但不转移所有权

    const Type* addArrayDimension(const Context&, const Type*, int);      // 创建数组类型
    void renameSymbol(const Context&, Symbol*, std::string_view);         // 重命名符号
    std::unique_ptr<Symbol> removeSymbol(const Symbol*);                  // 移除符号
};
```

### 7. Constructor 体系 - 构造器家族

构造器是 SkSL IR 中最精细化的类体系之一，采用三层继承结构：

```
Expression
  └── AnyConstructor          (构造器抽象基类，提供 argumentSpan() 和常量折叠)
        ├── SingleArgumentConstructor   (单参数构造器基类)
        │     ├── ConstructorArrayCast       - 数组类型转换
        │     ├── ConstructorCompoundCast    - 复合类型转换 half4(f4)
        │     ├── ConstructorDiagonalMatrix  - 对角矩阵 mat3(1.0)
        │     ├── ConstructorMatrixResize    - 矩阵尺寸调整
        │     ├── ConstructorScalarCast      - 标量转换 float(i)
        │     └── ConstructorSplat           - 标量展开 float4(1.0)
        │
        └── MultiArgumentConstructor  (多参数构造器基类)
              ├── ConstructorArray           - 数组构造 float[3](1,2,3)
              ├── ConstructorCompound        - 复合构造 float4(1,2,3,4)
              └── ConstructorStruct          - 结构体构造
```

`Constructor::Convert()` 命名空间函数是统一入口，根据参数的数量和类型自动选择最合适的具体构造器类型。

### 8. Variable 与 VariableReference (`SkSLVariable.h`, `SkSLVariableReference.h`)

`Variable` 表示变量本身（存储位置），`VariableReference` 表示对变量的引用。同一个变量在代码中可以被多次引用。

```cpp
// Variable 的存储类别
enum class VariableStorage : int8_t {
    kGlobal,          // 全局变量
    kInterfaceBlock,  // 接口块变量
    kLocal,           // 局部变量
    kParameter,       // 函数参数
};

// VariableReference 的引用类型
enum class VariableRefKind : int8_t {
    kRead,      // 读取: x + 1
    kWrite,     // 写入: x = 1 (赋值左侧)
    kReadWrite, // 读写: x += 1
    kPointer    // 取地址
};
```

`ExtendedVariable` 是 `Variable` 的子类，为需要额外信息（Layout、接口块关联、名称修饰）的变量提供扩展存储，避免为所有变量都分配这些较少使用的字段。

### 9. FunctionDeclaration 与 FunctionDefinition

函数在 IR 中被拆分为声明和定义两个独立的节点：

- **FunctionDeclaration** (`SkSLFunctionDeclaration.h`)：符号表中的函数条目，包含名称、参数列表、返回类型、修饰符、内联属性 (intrinsic) 等。通过 `fNextOverload` 链表支持函数重载。
- **FunctionDefinition** (`SkSLFunctionDefinition.h`)：顶层程序元素，将 `FunctionDeclaration` 与函数体 (`Statement`) 关联。

```cpp
class FunctionDeclaration final : public Symbol {
    const FunctionDefinition* fDefinition;    // 关联的定义（可为空）
    FunctionDeclaration* fNextOverload;       // 下一个重载
    TArray<Variable*> fParameters;            // 参数列表
    const Type* fReturnType;                  // 返回类型
    IntrinsicKind fIntrinsicKind;             // 内建函数标识
    bool fIsMain;                             // 是否为 main 函数
};
```

### 10. IRHelpers - IR 构造辅助工具 (`SkSLIRHelpers.h`)

为编译器内部的 IR 变换（如函数内联、代码优化）提供便捷的 IR 节点构造方法：

```cpp
struct IRHelpers {
    std::unique_ptr<Expression> Ref(const Variable* var) const;    // 创建变量引用
    std::unique_ptr<Expression> Float(float value) const;          // 创建浮点字面量
    std::unique_ptr<Expression> Int(int value) const;              // 创建整数字面量
    std::unique_ptr<Expression> Add(expr l, expr r) const;         // 创建加法
    std::unique_ptr<Expression> Mul(expr l, expr r) const;         // 创建乘法
    std::unique_ptr<Expression> Swizzle(expr base, components);    // 创建分量重排
    std::unique_ptr<Statement> Assign(expr l, expr r) const;       // 创建赋值语句
};
```

## 依赖关系

### 内部依赖（IR 模块内）

```
SkSLProgram  ──────>  SkSLProgramElement  ──>  SkSLIRNode  ──>  SkSLPool
                │           │                       ^                │
                │     SkSLFunctionDefinition         │          (Poolable)
                │     SkSLGlobalVarDeclaration       │
                │     SkSLInterfaceBlock             │
                │     SkSLStructDefinition           │
                │                                    │
                ├──>  SkSLExpression  ───────────────>┤
                │        │                           │
                │     SkSLBinaryExpression           │
                │     SkSLFunctionCall               │
                │     SkSLConstructor*               │
                │     SkSLSwizzle                    │
                │     SkSLLiteral                    │
                │     SkSLVariableReference          │
                │                                    │
                ├──>  SkSLStatement  ────────────────>┤
                │        │                           │
                │     SkSLBlock                      │
                │     SkSLForStatement               │
                │     SkSLIfStatement                │
                │     SkSLVarDeclarations            │
                │                                    │
                ├──>  SkSLSymbolTable  ──>  SkSLSymbol
                │                              │
                └──>  SkSLType  ───────────────┘
                      SkSLLayout
                      SkSLModifierFlags
```

### 外部依赖（SkSL 编译器其他模块）

| 外部模块 | 依赖文件 | 用途 |
|---------|---------|------|
| `src/sksl/SkSLPool.h` | `SkSLIRNode.h` | 内存池分配基类 `Poolable` |
| `src/sksl/SkSLPosition.h` | 几乎所有 IR 类 | 源码位置追踪 |
| `src/sksl/SkSLOperator.h` | `SkSLBinaryExpression.h` | 运算符枚举定义 |
| `src/sksl/SkSLContext.h` | `SkSLLiteral.h`, `SkSLIRHelpers.h` | 编译上下文（内建类型、配置） |
| `src/sksl/SkSLBuiltinTypes.h` | `SkSLLiteral.h` | 内建类型常量引用 |
| `src/sksl/SkSLDefines.h` | 多个文件 | `SKSL_INT`, `SKSL_FLOAT`, `ExpressionArray` 等定义 |
| `src/sksl/SkSLAnalysis.h` | `SkSLIRHelpers.h` | 静态分析工具（变量引用类型更新等） |
| `src/sksl/SkSLIntrinsicList.h` | `SkSLFunctionDeclaration.h` | 内建函数标识枚举 |
| `src/sksl/SkSLModule.h` | `SkSLFunctionDeclaration.h` | 模块类型枚举 |
| `src/sksl/spirv.h` | `SkSLType.h` | SPIR-V 维度枚举（`SpvDim_`） |
| `include/core/SkSpan.h` | 多个文件 | 非拥有的数组视图 |
| `include/private/base/SkTArray.h` | 多个文件 | Skia 动态数组 |
| `src/core/SkTHash.h` | `SkSLSymbolTable.h` | 哈希表实现 |
| `src/core/SkChecksum.h` | `SkSLSymbolTable.h` | 符号名称哈希 |

## 设计模式分析

### 1. Convert/Make 双层工厂模式

这是 SkSL IR 中最普遍且最重要的设计模式。几乎所有 IR 节点都提供两种静态工厂方法：

- **`Convert()`**：面向编译器前端，接受"原始"输入，执行完整的类型检查、类型转换和语义验证，通过 `ErrorReporter` 报告错误，允许返回 `nullptr` 表示失败。
- **`Make()`**：面向编译器内部变换，假设输入已经过验证，仅通过 `SkASSERT` 断言错误，永远不返回 `nullptr`。

```cpp
// Convert: 用于解析阶段，会检查类型兼容性并报错
static std::unique_ptr<Expression> BinaryExpression::Convert(
    const Context& context, Position pos,
    std::unique_ptr<Expression> left, Operator op,
    std::unique_ptr<Expression> right);

// Make: 用于优化/内联阶段，假设已验证，可能进行常量折叠
static std::unique_ptr<Expression> BinaryExpression::Make(
    const Context& context, Position pos,
    std::unique_ptr<Expression> left, Operator op,
    std::unique_ptr<Expression> right);
```

### 2. 访问者模式替代方案 - Kind 枚举 + is/as 模板

传统编译器 IR 通常使用访问者模式 (Visitor Pattern) 遍历节点。SkSL 选择了一种更轻量的方案：

- 所有节点共享统一的 `fKind` 整数字段
- 四种枚举 (`ProgramElementKind`, `SymbolKind`, `StatementKind`, `ExpressionKind`) 的值域互不重叠
- 每个具体类声明 `inline static constexpr Kind kIRNodeKind`
- 通过模板方法 `is<T>()` 和 `as<T>()` 进行类型安全的判定和转换

```cpp
// 使用示例
if (stmt.is<ReturnStatement>()) {
    const ReturnStatement& ret = stmt.as<ReturnStatement>();
    // ...
}
```

### 3. 唯一所有权与内存池

- 所有 IR 子节点通过 `std::unique_ptr` 持有，确保树状唯一所有权
- `IRNode` 禁止拷贝构造和赋值，防止意外共享
- 提供显式 `clone()` 方法进行深拷贝
- 所有 `IRNode` 通过 `Poolable` 基类支持内存池分配，编译结束后整个池一次性释放

### 4. 职责分离模式 (Variable vs VariableReference)

变量的**声明**（存储位置）与**使用**（读写引用）被清晰分离为两个类：

- `Variable`：符号表中的条目，代表一个存储位置，全程序唯一
- `VariableReference`：表达式节点，代表对该存储位置的一次访问（读/写/读写）

同一变量 `x` 在 `x = x + 1` 中产生一个 `Variable` 和两个 `VariableReference`（一个写引用、一个读引用）。

### 5. 策略模式 - 构造器分类

不同类型的构造表达式被分解为独立的策略类（9种 Constructor 子类），`Constructor::Convert()` 充当策略选择器，根据参数类型和目标类型自动路由到正确的构造器实现。这使得每种构造器可以独立实现自己的常量折叠和简化逻辑。

### 6. 组合模式 - 语句块

`Block` 类实现了经典的组合模式，可以包含多个子语句作为一个整体语句使用。`Block` 还区分三种语义：`kBracedScope`（花括号作用域）、`kUnbracedBlock`（无花括号分组）和 `kCompoundStatement`（复合语句如 `int a, b;`）。

## 数据流

### 编译管线中的 IR 生命周期

```
    SkSL 源代码                  (字符串)
        │
        v
    ┌───────────────┐
    │  Lexer (词法)  │           Token 流
    └───────┬───────┘
            v
    ┌───────────────┐
    │ Parser (语法)  │    调用各 IR 节点的 Convert() 方法
    │               │    进行类型检查、隐式转换、语义验证
    └───────┬───────┘
            v
    ┌───────────────────────┐
    │   IR Tree (中间表示)   │    Program {
    │   (本目录定义的节点)    │      ProgramElement* --> FunctionDefinition
    │                       │                           --> GlobalVarDeclaration
    │   完全解析的 AST：     │                           --> InterfaceBlock
    │   - 类型已确定         │      SymbolTable (作用域链)
    │   - 名称已解析         │      ProgramUsage (引用计数)
    │   - 隐式转换已插入     │    }
    └───────┬───────────────┘
            │
    ┌───────┴──────────┐
    │  Optimizer (优化)  │   常量折叠、死代码消除、函数内联
    │  使用 Make() 方法  │   通过 IRHelpers 构造新节点
    └───────┬──────────┘
            │
            v
    ┌───────────────────────────────────┐
    │       Code Generator (代码生成)    │
    │  遍历 IR 树，输出目标代码：         │
    │  - GLSLCodeGenerator  --> GLSL    │
    │  - MetalCodeGenerator --> MSL     │
    │  - SPIRVCodeGenerator --> SPIR-V  │
    │  - HLSLCodeGenerator  --> HLSL    │
    │  - WGSLCodeGenerator  --> WGSL    │
    │  - SkVMCodeGenerator  --> SkVM    │
    └───────────────────────────────────┘
```

### 关键数据流路径

**1. 表达式类型推断与转换**

```
源码 "a + 1.0"
    │
    v
Parser 识别为二元表达式
    │
    v
BinaryExpression::Convert(context, pos, left=VarRef(a:int), op=PLUS, right=Literal(1.0:float))
    │
    ├── 计算 coercionCost: int -> float (Normal cost)
    ├── 插入隐式转换: ConstructorScalarCast::Make(float, VarRef(a:int))
    │
    v
BinaryExpression { left=ConstructorScalarCast(VarRef(a)), op=+, right=Literal(1.0), type=float }
```

**2. 构造器路由**

```
源码 "float4(1.0)"
    │
    v
Constructor::Convert(context, pos, type=float4, args=[Literal(1.0)])
    │
    ├── 参数数量=1，目标为向量类型，参数为标量
    ├── 路由到 ConstructorSplat
    │
    v
ConstructorSplat { type=float4, argument=Literal(1.0) }
    // 等价于 float4(1.0, 1.0, 1.0, 1.0)
```

**3. 符号表查找链**

```
查找标识符 "x"
    │
    v
当前 SymbolTable (局部作用域)
    ├── 未找到 -> fParent
    │
    v
函数作用域 SymbolTable
    ├── 找到 Variable "x" -> 返回
    │
    v (如未找到)
模块 SymbolTable (fAtModuleBoundary=true)
    │
    v
内建 SymbolTable (fBuiltin=true)
    ├── 包含 float, int, vec4, texture2D 等内建类型
    └── 包含 sin, cos, mix, clamp 等内建函数
```

**4. 函数重载解析**

```
FunctionCall::Convert(context, pos, "mix", args=[float, float, float])
    │
    v
FindBestFunctionForCall:
    ├── 遍历 FunctionDeclaration 链表 (fNextOverload)
    ├── 对每个重载: determineFinalTypes() 解析泛型
    ├── 计算每个参数的 coercionCost 并求和
    ├── 选择总代价最低的重载
    │
    v
FunctionCall { function=mix(float,float,float)->float, args=[...] }
```

## 相关文档与参考

### 源码目录
- **SkSL 编译器主目录**: `src/sksl/` - 包含解析器、优化器、代码生成器
- **SkSL IR 目录**: `src/sksl/ir/` - 本文档描述的目录
- **内建类型定义**: `src/sksl/SkSLBuiltinTypes.h` - 所有内建类型（float, int, vec4 等）
- **编译上下文**: `src/sksl/SkSLContext.h` - 编译过程的全局上下文
- **内建函数列表**: `src/sksl/SkSLIntrinsicList.h` - 所有内建函数标识
- **代码生成器**: `src/sksl/codegen/` - 各后端代码生成器

### 外部参考
- [GLSL 语言规范](https://www.khronos.org/opengl/wiki/OpenGL_Shading_Language) - SkSL 的语法参考基础
- [SPIR-V 规范](https://www.khronos.org/registry/SPIR-V/) - SPIR-V 后端目标
- [Skia 官方文档](https://skia.org/docs/user/sksl/) - SkSL 用户文档
- [Khronos GLSL 数据类型](https://www.khronos.org/opengl/wiki/Data_Type_(GLSL)) - 不透明类型等概念的来源

### 编码惯例

1. **Convert/Make 命名约定**: `Convert()` 面向前端（带错误报告），`Make()` 面向内部（带断言）
2. **kIRNodeKind 常量**: 每个具体 IR 类都声明 `inline static constexpr Kind kIRNodeKind`，用于 `is<T>()`/`as<T>()` 类型判定
3. **description() 方法**: 每个 IR 节点都实现 `description()`，返回类似 SkSL 源码的文本表示
4. **禁止拷贝**: 所有 IR 节点的拷贝构造和赋值运算符被 `delete`，必须使用 `clone()` 进行显式深拷贝
5. **unique_ptr 所有权**: 子节点一律通过 `std::unique_ptr` 持有，保证树结构的唯一所有权
6. **Position 传播**: 每个 IR 节点携带 `Position` 记录其在源码中的位置，用于精确的错误报告
