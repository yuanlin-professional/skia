# VarDeclarations

> 源文件: src/sksl/ir/SkSLVarDeclarations.h, src/sksl/ir/SkSLVarDeclarations.cpp

## 概述

`VarDeclarations` 模块包含两个核心 IR 节点类:`VarDeclaration` 和 `GlobalVarDeclaration`,用于表示 SkSL 中的变量声明。`VarDeclaration` 表示单个变量的声明语句,而 `GlobalVarDeclaration` 将全局变量声明包装为程序元素。该模块负责变量声明的验证、类型强制转换和符号表管理,是 SkSL 语义分析的关键组件。

## 架构位置

VarDeclarations 位于 SkSL 编译器的中间表示层,连接语法分析和语义分析:

```
src/sksl/
  ├── ir/
  │   ├── SkSLVarDeclarations.h/cpp    ← 当前组件
  │   ├── SkSLVariable.h               ← 变量符号定义
  │   ├── SkSLStatement.h              ← Statement 基类
  │   ├── SkSLProgramElement.h         ← ProgramElement 基类
  │   ├── SkSLExpression.h             ← 初始化表达式
  │   └── SkSLModifiers.h              ← 修饰符定义
```

在编译流程中的位置:
1. Parser 识别变量声明语法
2. VarDeclaration::Convert() 创建 IR 节点并执行语义检查
3. 将 Variable 添加到符号表
4. 代码生成器遍历 VarDeclaration 生成目标代码

## 主要类与结构体

### VarDeclaration 类

表示单个变量声明语句:

```cpp
class VarDeclaration final : public Statement {
    Variable* fVar;                      // 关联的变量符号
    const Type& fBaseType;               // 基础类型(数组时为元素类型)
    int fArraySize;                      // 数组大小(0表示非数组)
    std::unique_ptr<Expression> fValue;  // 初始化表达式
};
```

**关键特性:**
- 继承自 `Statement`,可以出现在函数体中
- 与 `Variable` 符号双向关联
- 支持数组声明和初始化表达式
- 析构时自动断开与 Variable 的连接

### GlobalVarDeclaration 类

全局作用域的变量声明包装器:

```cpp
class GlobalVarDeclaration final : public ProgramElement {
    std::unique_ptr<Statement> fDeclaration;  // 内部的 VarDeclaration
};
```

**设计目的:**
- 将语句级别的 VarDeclaration 提升为程序元素
- 全局变量必须包装为 ProgramElement 才能添加到程序中
- 提供统一的全局声明接口

## 公共 API 函数

### VarDeclaration::ErrorCheck

**函数签名:**
```cpp
static void ErrorCheck(
    const Context& context, Position pos,
    Position modifiersPosition, const Layout& layout,
    ModifierFlags modifierFlags, const Type* type,
    const Type* baseType, Variable::Storage storage);
```

**功能:** 验证变量声明的合法性(不涉及初始化表达式)

**验证规则:**
1. **不透明类型限制:** opaque 类型(除 atomic 外)必须为全局变量
2. **矩阵类型限制:** `in` 变量不能是矩阵类型
3. **无大小数组限制:** `in`/`out` 变量不能是无大小数组
4. **修饰符冲突检查:**
   - `in uniform` 非法
   - `readonly` 和 `writeonly` 不能同时存在
   - `uniform buffer` 非法
   - `workgroup` 不能与 `in`/`out` 同时使用
5. **uniform 类型检查:** 调用 `check_valid_uniform_type()`
6. **effect child 类型:** 必须是 uniform
7. **atomic 类型限制:** 必须是 workgroup 或可写存储缓冲区成员
8. **布局标志验证:** `layout(color)` 仅用于 runtime effect 的 uniform 变量
9. **接口块特殊规则:** 无大小数组仅能作为 buffer 块的最后一个成员

**应用场景:** 被 Convert() 调用,也被接口块字段处理代码显式调用

### VarDeclaration::Convert (无 Variable 版本)

**函数签名:**
```cpp
static std::unique_ptr<VarDeclaration> Convert(
    const Context& context, Position overallPos,
    const Modifiers& modifiers, const Type& type,
    Position namePos, std::string_view name,
    VariableStorage storage,
    std::unique_ptr<Expression> value);
```

**功能:** 从零创建变量声明,执行完整的语义分析

**流程:**
1. 调用 `Variable::Convert()` 创建 Variable 符号
2. 调用 `VarDeclaration::Convert()` 的 Variable 版本

**注意:** 不支持参数存储类型(参数声明不是语句)

### VarDeclaration::Convert (有 Variable 版本)

**函数签名:**
```cpp
static std::unique_ptr<VarDeclaration> Convert(
    const Context& context,
    std::unique_ptr<Variable> var,
    std::unique_ptr<Expression> value);
```

**功能:** 从已有 Variable 创建声明,验证并强制转换初始化表达式

**语义检查:**
1. 调用 `ErrorCheckAndCoerce()` 验证类型和修饰符
2. 检查全局作用域的名称冲突
3. 特殊变量检查(如 `sk_RTAdjust` 必须是 float4)
4. 将 Variable 添加到当前符号表

**返回值:** 成功返回 VarDeclaration,失败返回 nullptr

### VarDeclaration::Make

**函数签名:**
```cpp
static std::unique_ptr<VarDeclaration> Make(
    const Context& context, Variable* var,
    const Type* baseType, int arraySize,
    std::unique_ptr<Expression> value);
```

**功能:** 直接创建 VarDeclaration,不执行验证(仅 ASSERT)

**前提条件:**
- 所有语义检查已完成
- 类型已正确设置
- const 变量必须有初始化表达式
- 初始化表达式必须是常量(如果是 const 或全局变量)

**应用场景:** IR 变换和优化阶段使用,避免重复验证

### ErrorCheckAndCoerce

**函数签名:**
```cpp
static bool ErrorCheckAndCoerce(
    const Context& context, const Variable& var,
    const Type* baseType,
    std::unique_ptr<Expression>& value);
```

**功能:** 验证变量和初始化表达式的兼容性,执行类型强制转换

**检查项:**
1. **类型验证:** 拒绝 invalid 和 void 类型
2. **调用 ErrorCheck()** 验证修饰符和类型组合
3. **初始化表达式限制:**
   - opaque/atomic 类型不能有初始化表达式
   - `in` 变量不能初始化
   - `uniform` 变量不能初始化
   - 接口块字段不能初始化
   - strict-ES2 模式下数组不能初始化
4. **const 变量要求:** 必须有常量初始化表达式
5. **全局变量要求:** 初始化表达式必须是常量
6. **类型强制转换:** 调用 `type.coerceExpression()` 转换初始化表达式

**返回值:** 成功返回 true,失败返回 false

### 访问器方法

**baseType():** 返回基础类型(数组时返回元素类型)

**var():** 返回关联的 Variable 符号

**arraySize():** 返回数组大小(0 表示非数组)

**value():** 返回初始化表达式的引用

**description():** 生成声明的字符串表示

### 生命周期管理

**detachDeadVariable():** 断开与已删除 Variable 的连接

**析构函数:** 自动调用 `var->detachDeadVarDeclaration()`

## 内部实现细节

### 数组类型处理

变量类型可能是数组类型 `Type::isArray()`:
- **fBaseType:** 存储元素类型
- **fArraySize:** 存储数组大小
- **分离存储的原因:** 简化类型系统,避免为每个数组大小创建新类型

**示例:**
```cpp
int[5] myArray;
// fBaseType = int
// fArraySize = 5
// var->type() = int[5]
```

### uniform 类型验证

`check_valid_uniform_type()` 函数验证 uniform 变量的类型:

**Runtime Effect 限制:**
- 允许: shader, blender, colorFilter
- 允许: int, int2, int3, int4
- 允许: float/half 及其向量和方阵
- 拒绝: 其他所有类型

**通用规则:**
- 调用 `Type::isAllowedInUniform()` 检查
- 递归验证结构体和数组成员
- 报告具体不合法的嵌套类型位置

### const 变量初始化

const 变量的特殊要求:
```cpp
if (var.modifierFlags().isConst()) {
    if (!value) {
        context.fErrors->error(var.fPosition,
            "'const' variables must be initialized");
    }
    if (!Analysis::IsConstantExpression(*value)) {
        context.fErrors->error(value->fPosition,
            "'const' variable initializer must be a constant expression");
    }
}
```

### 全局变量初始化

全局变量初始化表达式必须是编译期常量:
```cpp
if (var.storage() == Variable::Storage::kGlobal) {
    if (value && !Analysis::IsConstantExpression(*value)) {
        context.fErrors->error(value->fPosition,
            "global variable initializer must be a constant expression");
    }
}
```

### 符号表管理

变量声明创建后自动添加到符号表:
```cpp
// 检查名称冲突
if (context.fSymbolTable->find(var->name())) {
    context.fErrors->error(var->fPosition,
        "symbol '" + std::string(var->name()) + "' was already defined");
}

// 添加到符号表
context.fSymbolTable->add(context, std::move(var));
```

### 特殊变量处理

**sk_RTAdjust:**
- 用于位置修正表达式
- 必须是 `float4` 类型
- 在 IR 生成器中触发特殊逻辑

## 依赖关系

### 直接依赖

- `SkSLVariable.h`: 变量符号定义
- `SkSLStatement.h` / `SkSLProgramElement.h`: 基类
- `SkSLExpression.h`: 初始化表达式
- `SkSLType.h`: 类型系统
- `SkSLAnalysis.h`: 常量表达式分析
- `SkSLModifiers.h`: 修饰符定义

### 被依赖

- Parser: 创建变量声明节点
- IRGenerator: 管理变量声明的上下文
- 代码生成器: 遍历变量声明生成代码
- IR 变换: 创建临时变量声明

### 循环依赖

Variable ↔ VarDeclaration 相互引用:
- 使用前向声明打破编译依赖
- 使用指针避免值类型循环
- 双向关联需要谨慎的生命周期管理

## 设计模式与设计决策

### 设计模式

**1. 包装器模式 (Wrapper Pattern)**
- GlobalVarDeclaration 包装 VarDeclaration
- 将 Statement 提升为 ProgramElement
- 保持接口统一性

**2. 工厂方法模式 (Factory Method Pattern)**
- Convert() 方法创建并验证对象
- Make() 方法直接创建对象
- 分离验证逻辑和构造逻辑

**3. 双向关联模式**
- VarDeclaration ↔ Variable 双向引用
- 支持从任意方向快速访问
- 析构时自动清理关联

### 设计决策

**1. Statement vs ProgramElement 分离**
- **问题:** 全局变量和局部变量需要不同的节点类型
- **解决:** VarDeclaration 作为 Statement,GlobalVarDeclaration 作为包装
- **优点:** 代码复用,避免重复实现

**2. 数组类型分离存储**
- **问题:** 数组类型会导致类型爆炸
- **解决:** 分别存储 baseType 和 arraySize
- **优点:** 简化类型系统,减少类型对象数量

**3. 多阶段验证**
- **ErrorCheck:** 验证类型和修饰符(不涉及初始化表达式)
- **ErrorCheckAndCoerce:** 验证初始化表达式并强制转换
- **优点:** 支持接口块字段验证(无初始化表达式)

**4. 符号表自动管理**
- Convert() 自动将变量添加到符号表
- 检查名称冲突
- 简化调用者代码

## 性能考量

### 验证成本

**类型检查:** O(1) 基础检查 + O(n) 嵌套类型遍历
- 结构体: 递归检查所有字段
- 数组: 递归检查元素类型
- uniform 验证: 可能遍历深层嵌套结构

**常量分析:** `Analysis::IsConstantExpression()` 遍历表达式树
- const 变量和全局变量都需要常量初始化
- 成本取决于初始化表达式复杂度

### 内存布局

**VarDeclaration 大小:**
- 指针成员: 8-16 字节(Variable*, Expression*)
- 引用成员: 8 字节(fBaseType)
- int: 4 字节(fArraySize)
- 基类开销: ~16-24 字节
- **总计:** 约 40-60 字节/声明

**GlobalVarDeclaration 开销:**
- unique_ptr: 8 字节
- 基类: ~16-24 字节
- **总计:** 约 24-32 字节额外开销

### 符号表性能

- 查找: O(1) 哈希表查找
- 插入: O(1) 平均情况
- 名称冲突检查: O(1)

## 相关文件

### 核心文件

- `src/sksl/ir/SkSLVariable.h`: 变量符号定义
- `src/sksl/ir/SkSLExpression.h`: 初始化表达式基类
- `src/sksl/ir/SkSLType.h`: 类型系统

### 语义分析

- `src/sksl/SkSLAnalysis.h`: 常量表达式分析
- `src/sksl/ir/SkSLModifiers.h`: 修饰符定义
- `src/sksl/ir/SkSLSymbolTable.h`: 符号表管理

### 使用示例

- `src/sksl/SkSLIRGenerator.cpp`: 创建变量声明
- `src/sksl/transform/`: IR 变换使用 Make() 创建声明
- `src/sksl/codegen/`: 代码生成器遍历声明
