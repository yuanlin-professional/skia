# SkSLFinalizationChecks

> 源文件: src/sksl/analysis/SkSLFinalizationChecks.cpp

## 概述

`SkSLFinalizationChecks` 模块实现了 SkSL 编译器的最终语义验证阶段。在程序的 IR 树完全构建之后、代码生成之前,该模块执行一系列完整性检查,确保程序符合 SkSL 和目标平台(如 OpenGL ES、Vulkan、Metal)的各种语义约束。

该模块检查的内容包括:全局变量大小限制、绑定索引唯一性、函数输出参数赋值、计算着色器工作组大小定义,以及函数声明的完整性。这些检查在 IR 构建阶段可能因为前向引用或跨模块依赖而无法完成,因此放在最终化阶段统一处理。

## 架构位置

该模块位于编译流程的最后验证阶段:

```
SkSL 编译流程:
  词法分析 → 语法分析 → IR 构建 → 中间优化
                                    ↓
                            ┌───────────────┐
                            │ 最终化检查     │ ← 本模块
                            │ (Finalization) │
                            └───────────────┘
                                    ↓
                            代码生成 (GLSL/SPIR-V/Metal)
```

`DoFinalizationChecks` 是编译器在代码生成前调用的最后一个分析步骤,确保没有语义错误逃逸到后端。

## 主要类与结构体

### FinalizationVisitor

继承自 `ProgramVisitor`,实现完整性检查的核心逻辑。

**成员变量:**

```cpp
size_t fGlobalSlotsUsed = 0;           // 已使用的全局变量槽位数
const Context& fContext;               // 编译上下文
const ProgramUsage& fUsage;            // 符号使用统计
THashSet<uint64_t> fBindings;          // 已使用的 set/binding 组合
int fLocalSizeX = -1;                  // 计算着色器工作组 X 维度
int fLocalSizeY = -1;                  // 工作组 Y 维度
int fLocalSizeZ = -1;                  // 工作组 Z 维度
```

**核心方法:**

```cpp
bool visitProgramElement(const ProgramElement& pe) override;
bool visitExpression(const Expression& expr) override;
void checkGlobalVariableSizeLimit(const GlobalVarDeclaration& globalDecl);
void checkBindUniqueness(const InterfaceBlock& block);
void checkOutParamsAreAssigned(const FunctionDefinition& funcDef);
void checkWorkgroupLocalSize(const ModifiersDeclaration& d);
bool definesLocalSize() const;
```

## 公共 API 函数

### Analysis::DoFinalizationChecks

```cpp
void Analysis::DoFinalizationChecks(const Program& program)
```

**功能:** 对完整程序执行最终化检查

**参数:**
- `program`: 已构建完成的 SkSL 程序

**检查项目:**
1. 全局变量大小限制(针对 RuntimeEffect)
2. 接口块的 binding 唯一性
3. 函数 `out` 参数的赋值验证
4. 计算着色器的 `local_size` 声明
5. 函数调用的有效性(函数必须已定义)
6. 表达式类型有效性

**实现细节:**
```cpp
FinalizationVisitor visitor{*program.fContext, *program.usage()};
for (const std::unique_ptr<ProgramElement>& element : program.fOwnedElements) {
    visitor.visitProgramElement(*element);
}
if (ProgramConfig::IsCompute(program.fConfig->fKind) && !visitor.definesLocalSize()) {
    program.fContext->fErrors->error(Position(),
                                     "compute programs must specify a workgroup size");
}
```

只检查程序拥有的元素(`fOwnedElements`),内置元素假定已经过验证。

## 内部实现细节

### 全局变量大小限制检查

```cpp
void checkGlobalVariableSizeLimit(const GlobalVarDeclaration& globalDecl)
```

**适用范围:** 仅对 RuntimeEffect 类型的程序生效

**限制:** 全局变量总槽位数不得超过 `kVariableSlotLimit`

**槽位计算:**
- `float`: 1 个槽位
- `vec4`: 4 个槽位
- `mat4`: 16 个槽位
- 数组和结构体累加所有成员的槽位

**实现策略:**
```cpp
size_t prevSlotsUsed = fGlobalSlotsUsed;
fGlobalSlotsUsed = SkSafeMath::Add(fGlobalSlotsUsed, decl.var()->type().slotCount());
if (prevSlotsUsed < kVariableSlotLimit && fGlobalSlotsUsed >= kVariableSlotLimit) {
    fContext.fErrors->error(decl.fPosition,
                            "global variable '" + std::string(decl.var()->name()) +
                            "' exceeds the size limit");
}
```

只在第一次超限时报告错误,避免重复错误消息。

### 绑定唯一性检查

```cpp
void checkBindUniqueness(const InterfaceBlock& block)
```

**目标:** 确保 `layout(set=X, binding=Y)` 组合不重复

**实现:**
```cpp
uint64_t key = ((uint64_t)set << 32) + binding;
if (!fBindings.contains(key)) {
    fBindings.add(key);
} else {
    // 报告错误...
}
```

将 `set` 和 `binding` 打包为 64 位整数作为唯一键,使用哈希集合快速查重。

**限制:** 当前实现不处理 `set=-1` 的默认值,TODO 注释指出这可能导致与隐式默认值的冲突。

### 输出参数赋值检查

```cpp
void checkOutParamsAreAssigned(const FunctionDefinition& funcDef)
```

**规则:** GLSL 规范要求 `out` 参数必须被赋值,否则其值未定义

**检查逻辑:**
```cpp
for (const Variable* param : funcDecl.parameters()) {
    const ModifierFlags paramInout = param->modifierFlags() & (ModifierFlag::kIn |
                                                               ModifierFlag::kOut);
    if (paramInout == ModifierFlag::kOut) {  // 纯 out,不包含 in
        ProgramUsage::VariableCounts counts = fUsage.get(*param);
        if (counts.fWrite <= 0) {
            fContext.fErrors->error(param->fPosition,
                                    "function '" + std::string(funcDecl.name()) +
                                    "' never assigns a value to out parameter '" +
                                    std::string(param->name()) + "'");
        }
    }
}
```

利用 `ProgramUsage` 统计的写入次数进行验证。`inout` 参数不需要检查,因为输入值可作为默认输出。

### 工作组大小检查

```cpp
void checkWorkgroupLocalSize(const ModifiersDeclaration& d)
```

**适用范围:** 计算着色器(Compute Shader)

**要求:** 必须至少指定 `local_size_x`,其他维度默认为 1

**检查点:**
```cpp
if (d.layout().fLocalSizeX >= 0) {
    if (fLocalSizeX >= 0) {
        fContext.fErrors->error(d.fPosition, "'local_size_x' was specified more than once");
    } else {
        fLocalSizeX = d.layout().fLocalSizeX;
    }
}
```

防止重复声明,记录每个维度的值。在 `DoFinalizationChecks` 末尾验证计算着色器是否定义了至少 X 维度。

### 表达式有效性检查

```cpp
bool visitExpression(const Expression& expr) override
```

**检查内容:**

1. **函数调用验证:**
```cpp
case Expression::Kind::kFunctionCall:
    const FunctionDeclaration& decl = expr.as<FunctionCall>().function();
    if (!decl.isBuiltin() && !decl.definition()) {
        fContext.fErrors->error(expr.fPosition, "function '" + decl.description() +
                                                "' is not defined");
    }
```

确保非内置函数有定义(函数体)。

2. **无效引用检测:**
```cpp
case Expression::Kind::kFunctionReference:
case Expression::Kind::kMethodReference:
case Expression::Kind::kTypeReference:
    SkDEBUGFAIL("invalid reference-expr, should have been reported by coerce()");
    fContext.fErrors->error(expr.fPosition, "invalid expression");
```

这些引用类型应在类型强制转换阶段被处理,如果残留则是编译器 bug。

3. **类型有效性:**
```cpp
if (expr.type().matches(*fContext.fTypes.fInvalid)) {
    fContext.fErrors->error(expr.fPosition, "invalid expression");
}
```

捕获类型推导失败的表达式。

## 依赖关系

**核心依赖:**
- `src/sksl/SkSLContext.h`: 编译上下文
- `src/sksl/SkSLErrorReporter.h`: 错误报告机制
- `src/sksl/analysis/SkSLProgramUsage.h`: 符号使用统计
- `src/sksl/analysis/SkSLProgramVisitor.h`: 访问者基类

**IR 节点:**
- `SkSLProgram.h`: 程序表示
- `SkSLFunctionDefinition.h`, `SkSLFunctionDeclaration.h`: 函数
- `SkSLInterfaceBlock.h`: 接口块(Uniform/Storage Block)
- `SkSLModifiersDeclaration.h`: 修饰符声明
- `SkSLVarDeclarations.h`, `SkSLVariable.h`: 变量

**配置与设置:**
- `SkSLProgramSettings.h`: 程序类型判断
- `SkSLBuiltinTypes.h`: 内置类型

**工具:**
- `src/core/SkTHash.h`: 哈希集合
- `src/base/SkSafeMath.h`: 安全算术运算

## 设计模式与设计决策

### 延迟验证策略

许多检查放在最终化阶段的原因:
1. **前向引用:** 函数可能在声明前被调用
2. **模块化编译:** 不同模块的符号可能相互依赖
3. **优化影响:** 某些优化可能改变符号使用情况

在 IR 完全构建后统一验证,避免复杂的增量更新逻辑。

### 单次遍历多重检查

`FinalizationVisitor` 在一次遍历中完成多个检查,避免重复遍历 IR 树:
```cpp
switch (pe.kind()) {
    case ProgramElement::Kind::kGlobalVar:
        this->checkGlobalVariableSizeLimit(...);
        break;
    case ProgramElement::Kind::kInterfaceBlock:
        this->checkBindUniqueness(...);
        break;
    // ...
}
```

### 选择性检查

某些检查仅在特定程序类型下执行:
```cpp
if (!ProgramConfig::IsRuntimeEffect(fContext.fConfig->fKind)) {
    return;  // 跳过全局变量大小检查
}
```

这避免了对不需要限制的程序类型施加不必要的约束。

### 错误聚合

收集所有错误而不是遇到第一个错误就停止:
- 访问者返回 `false` 继续遍历
- 错误通过 `ErrorReporter` 累积
- 用户可以一次性修复多个问题

### 使用 ProgramUsage 加速

利用预先计算的符号使用统计:
```cpp
ProgramUsage::VariableCounts counts = fUsage.get(*param);
if (counts.fWrite <= 0) { /* ... */ }
```

避免重新遍历函数体来统计变量写入。

## 性能考量

### 单次遍历

所有检查在一次 IR 遍历中完成,时间复杂度 O(n),n 为 IR 节点数。

### 哈希集合查重

使用 `THashSet<uint64_t>` 存储绑定,插入和查询均为 O(1) 平均时间。

### 槽位计数缓存

类型的 `slotCount()` 方法结果通常被缓存,避免重复计算。

### 跳过内置元素

不检查 `program.fSharedElements`(内置符号),假定它们已验证,减少工作量。

### 早期退出

某些检查发现问题后不影响后续检查,继续执行以收集更多错误。

## 相关文件

**同模块分析:**
- `SkSLProgramUsage.cpp`: 符号使用统计
- `SkSLIsConstantExpression.cpp`: 常量表达式验证
- `SkSLProgramVisitor.h`: 访问者基类

**IR 构建:**
- `src/sksl/SkSLCompiler.cpp`: 调用 `DoFinalizationChecks` 的位置

**类型系统:**
- `src/sksl/ir/SkSLType.cpp`: `slotCount()` 实现

**配置:**
- `src/sksl/SkSLProgramSettings.h`: 程序类型定义

**错误报告:**
- `src/sksl/SkSLErrorReporter.h`: 错误接口
- `src/sksl/SkSLPosition.h`: 源位置信息

**测试:**
- `tests/sksl/errors/`: 各种语义错误的测试用例
