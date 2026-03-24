# VariableReference

> 源文件: src/sksl/ir/SkSLVariableReference.h, src/sksl/ir/SkSLVariableReference.cpp

## 概述

`VariableReference` 是 SkSL 中间表示中用于表示变量引用的表达式节点。它表示对变量的读取或写入操作。在语句 `x = x + 1;` 中,只有一个 `Variable` 对象 'x',但有两个 `VariableReference` 分别表示读取(右侧)和写入(左侧)操作。

## 架构位置

VariableReference 位于 SkSL 编译器的中间表示层,是表达式系统的基础组件:

```
src/sksl/
  ├── ir/
  │   ├── SkSLVariableReference.h/cpp  ← 当前组件
  │   ├── SkSLExpression.h             ← 父类:表达式基类
  │   ├── SkSLVariable.h               ← 引用的变量
  │   └── SkSLIRNode.h                 ← IR 节点基类
```

在编译流程中的位置:
1. Parser 识别变量名
2. 在符号表中查找 Variable
3. 创建 VariableReference 指向该 Variable
4. 数据流分析使用引用类型(读/写/读写)

## 主要类与结构体

### VariableRefKind 枚举

```cpp
enum class VariableRefKind : int8_t {
    kRead,       // 读取变量
    kWrite,      // 写入变量
    kReadWrite,  // 读写变量(如 x++)
    kPointer     // 取地址(视为读写但不检查未赋值)
};
```

**用途:**
- 数据流分析:跟踪变量的使用模式
- 未初始化检查:区分读取和写入
- 优化:识别未使用的变量

### VariableReference 类

```cpp
class VariableReference final : public Expression {
    const Variable* fVariable;   // 引用的变量
    VariableRefKind fRefKind;    // 引用类型
};
```

**核心特性:**
- 轻量级对象,仅包含指针和枚举
- 不拥有 Variable,仅引用
- 多个 VariableReference 可引用同一 Variable
- 禁止拷贝,确保唯一性

## 公共 API 函数

### 构造函数

**函数签名:**
```cpp
VariableReference(Position pos, const Variable* variable, RefKind refKind);
```

**功能:** 创建变量引用

**参数:**
- `pos`: 引用在源码中的位置
- `variable`: 引用的变量(不能为 nullptr)
- `refKind`: 引用类型(读/写/读写/指针)

**断言:** `SkASSERT(this->variable())` 确保变量非空

### Make

**函数签名:**
```cpp
static std::unique_ptr<Expression> Make(
    Position pos,
    const Variable* variable,
    RefKind refKind = RefKind::kRead);
```

**功能:** 创建 VariableReference 的工厂方法

**默认行为:** 如果未指定,默认为读取引用

**返回值:** `unique_ptr<Expression>` 指向新创建的 VariableReference

**用途:** 推荐的创建方式,提供清晰的接口

### variable

**函数签名:**
```cpp
const Variable* variable() const;
```

**功能:** 获取引用的变量

**返回值:** 指向 Variable 对象的指针

**不变性:** Variable 指针在 VariableReference 生命周期内不变(除非显式调用 setVariable)

### refKind

**函数签名:**
```cpp
RefKind refKind() const;
```

**功能:** 获取引用类型

**返回值:** `VariableRefKind` 枚举值

**应用场景:** 数据流分析和优化

### setRefKind

**函数签名:**
```cpp
void setRefKind(RefKind refKind);
```

**功能:** 修改引用类型

**应用场景:**
- IR 变换可能改变引用语义
- 优化过程中调整引用类型

**注意:** 修改引用类型可能影响数据流分析结果

### setVariable

**函数签名:**
```cpp
void setVariable(const Variable* variable);
```

**功能:** 修改引用的变量

**应用场景:**
- 变量重命名
- IR 重写和优化

**危险性:** 应谨慎使用,可能破坏类型一致性

### description

**函数签名:**
```cpp
std::string description(OperatorPrecedence) const override;
```

**功能:** 返回变量名的字符串表示

**实现:** 直接返回 `this->variable()->name()`

**用途:** 调试、错误报告、代码生成

### clone

**函数签名:**
```cpp
std::unique_ptr<Expression> clone(Position pos) const override;
```

**功能:** 克隆 VariableReference 到新位置

**行为:** 创建新的引用,指向相同的 Variable,保持相同的 RefKind

## 内部实现细节

### 类型推导

VariableReference 的类型直接来自引用的 Variable:
```cpp
VariableReference::VariableReference(
    Position pos, const Variable* variable, RefKind refKind)
    : INHERITED(pos, kIRNodeKind, &variable->type())  // 继承变量类型
    , fVariable(variable)
    , fRefKind(refKind)
```

**优点:** 类型自动同步,无需手动维护

### 禁止拷贝

```cpp
VariableReference(const VariableReference&) = delete;
VariableReference& operator=(const VariableReference&) = delete;
```

**设计目的:**
- 每个引用都是唯一的 IR 节点
- 防止意外的浅拷贝
- 强制使用 `clone()` 显式复制

### 引用类型的语义

**kRead:** 变量值被读取
```cpp
int y = x;  // x 是 kRead
```

**kWrite:** 变量被写入(不读取旧值)
```cpp
x = 5;  // x 是 kWrite
```

**kReadWrite:** 先读后写
```cpp
x++;     // x 是 kReadWrite
x += 5;  // x 是 kReadWrite
```

**kPointer:** 取地址(视为读写但跳过未初始化检查)
```cpp
&x  // x 是 kPointer
```

## 依赖关系

### 直接依赖

- `SkSLExpression.h`: 父类,提供表达式接口
- `SkSLVariable.h`: 引用的变量定义
- `SkSLIRNode.h`: IR 节点基类

### 被依赖

- Parser: 创建变量引用
- IRGenerator: 解析标识符为变量引用
- 数据流分析: 跟踪变量使用
- 代码生成器: 生成变量访问代码
- 优化器: 死代码消除、常量传播等

### 与 Variable 的关系

- **多对一:** 多个 VariableReference 可引用同一 Variable
- **不拥有:** VariableReference 不管理 Variable 的生命周期
- **类型同步:** 类型由 Variable 决定,自动同步

## 设计模式与设计决策

### 设计模式

**1. 享元模式 (Flyweight Pattern)**
- Variable 对象被多个 VariableReference 共享
- 减少内存占用
- 保证变量身份唯一性

**2. 不可变引用模式**
- Variable 指针默认不变
- 提供 setter 但不鼓励使用
- 保证大多数情况下的引用稳定性

### 设计决策

**1. 分离 Variable 和 VariableReference**
- **问题:** 如何表示同一变量的多次使用?
- **解决:** Variable 表示变量本身,VariableReference 表示每次使用
- **优点:** 支持数据流分析,区分读写操作

**2. 引用类型枚举**
- **问题:** 如何区分变量的读取和写入?
- **解决:** `VariableRefKind` 枚举标记引用类型
- **优点:** 支持未初始化检查、优化分析

**3. kPointer 特殊语义**
- **问题:** 取地址操作既不是纯读也不是纯写
- **解决:** 专门的 kPointer 类型,跳过未初始化检查
- **优点:** 避免取地址操作的误报

**4. 禁止拷贝**
- **问题:** 拷贝 VariableReference 可能导致 IR 树结构混乱
- **解决:** 删除拷贝构造函数和赋值运算符
- **优点:** 强制使用 clone(),明确复制意图

## 性能考量

### 内存占用

**VariableReference 大小:**
- Expression 基类: ~24-32 字节
- `fVariable` 指针: 8 字节
- `fRefKind` 枚举: 1 字节(对齐后可能占4-8字节)
- **总计:** 约 32-48 字节/引用

**高频对象:** 程序中大量使用变量引用,内存占用显著

### 访问性能

**变量查找:** O(1) 直接指针访问
```cpp
const Variable* var = varRef->variable();
```

**类型查询:** O(1) 通过 Variable 间接访问
```cpp
const Type& type = varRef->type();  // 调用 variable()->type()
```

### 数据流分析

引用类型标记支持高效的数据流分析:
- 快速识别读取和写入
- O(1) 引用类型检查
- 支持单遍扫描的活跃性分析

## 相关文件

### 核心文件

- `src/sksl/ir/SkSLVariable.h`: 变量定义
- `src/sksl/ir/SkSLExpression.h`: 表达式基类
- `src/sksl/ir/SkSLIRNode.h`: IR 节点基类

### 创建相关

- `src/sksl/SkSLIRGenerator.cpp`: 创建 VariableReference
- `src/sksl/SkSLParser.cpp`: 解析标识符
- `src/sksl/ir/SkSLSymbolTable.h`: 变量查找

### 分析相关

- `src/sksl/SkSLAnalysis.h`: 数据流分析
- `src/sksl/analysis/SkSLProgramUsage.h`: 变量使用跟踪
- `src/sksl/transform/`: IR 变换使用引用类型

### 使用示例

VariableReference 的典型使用场景:
```glsl
int x = 0;          // x 的声明(Variable)
int y = x + 1;      // x 是 kRead 引用
x = 5;              // x 是 kWrite 引用
x++;                // x 是 kReadWrite 引用
int* p = &x;        // x 是 kPointer 引用
```
