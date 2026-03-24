# GrShaderVar

> 源文件
> - src/gpu/ganesh/GrShaderVar.h
> - src/gpu/ganesh/GrShaderVar.cpp

## 概述

`GrShaderVar` 是 Ganesh GPU 后端中用于表示着色器变量的轻量级类。它封装了着色器中变量的完整声明信息，包括变量名称、类型、类型修饰符（如 in、out、uniform）、数组维度以及 GLSL 布局限定符和额外修饰符。该类是 Skia 着色器代码生成系统的基础构建块，用于在运行时动态构建着色器代码。

在着色器生成流程中，`GrShaderVar` 提供了一个统一的抽象来表示顶点着色器和片段着色器中的各种变量，包括 uniform 变量、输入输出变量和局部变量。它支持将变量信息格式化为符合 GLSL/ESSL 语法的声明字符串，并处理不同着色器语言版本的差异。

## 架构位置

`GrShaderVar` 位于 Ganesh 着色器生成系统的核心：

```
Skia GPU 渲染流程
├── GrProcessor (处理器基类)
│   └── GrFragmentProcessor / GrGeometryProcessor
│       └── Shader 生成
│           ├── GrShaderVar (变量表示)
│           ├── GrGLSLShaderBuilder (着色器构建器)
│           └── 生成的 GLSL 代码
```

典型使用场景：
```
GrProcessor::emitCode()
  └── 创建 GrShaderVar 对象
      └── appendDecl() 生成变量声明
          └── 输出到 GrGLSLShaderBuilder
```

## 主要类与结构体

### GrShaderVar

表示着色器中的一个变量。

**继承关系：**
- 无继承关系，独立的值类型

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fType` | `SkSLType` | 变量的 SkSL 类型（float、vec2、mat4 等） |
| `fTypeModifier` | `TypeModifier` | 类型修饰符（None、In、Out、InOut、Uniform） |
| `fCount` | `int` | 数组元素个数（kNonArray 表示非数组） |
| `fName` | `SkString` | 变量名称 |
| `fLayoutQualifier` | `SkString` | 布局限定符（如 "location=0, binding=1"） |
| `fExtraModifiers` | `SkString` | 额外修饰符（如 "flat", "noperspective"） |

### 枚举类型

#### TypeModifier

```cpp
enum class TypeModifier {
    None,     // 无修饰符（局部变量）
    Out,      // 输出参数
    In,       // 输入参数
    InOut,    // 输入输出参数
    Uniform,  // Uniform 变量
};
```

### 常量

```cpp
static constexpr size_t kNonArray = 0;  // 非数组标记
```

## 公共 API 函数

### 构造函数

```cpp
GrShaderVar()  // 默认：void 类型，无修饰符

GrShaderVar(SkString name, SkSLType type, int arrayCount = kNonArray)
GrShaderVar(const char* name, SkSLType type, int arrayCount = kNonArray)

GrShaderVar(SkString name, SkSLType type, TypeModifier typeModifier)
GrShaderVar(const char* name, SkSLType type, TypeModifier typeModifier)

GrShaderVar(SkString name, SkSLType type, TypeModifier typeModifier, int arrayCount)

GrShaderVar(SkString name, SkSLType type, TypeModifier typeModifier, int arrayCount,
            SkString layoutQualifier, SkString extraModifier)
```

支持多种初始化方式，从简单的名称/类型对到完整的声明信息。

### 属性设置

```cpp
void set(SkSLType type, const char* name)  // 设置为非数组变量
void setTypeModifier(TypeModifier type)     // 设置类型修饰符
void addLayoutQualifier(const char* layoutQualifier)  // 添加布局限定符
void addModifier(const char* modifier)      // 添加额外修饰符
```

### 属性查询

```cpp
bool isArray() const              // 是否为数组
int getArrayCount() const         // 获取数组长度
const SkString& getName() const   // 获取变量名
const char* c_str() const         // 获取变量名的 C 字符串
SkSLType getType() const          // 获取类型
TypeModifier getTypeModifier() const  // 获取类型修饰符
```

### 代码生成

```cpp
void appendDecl(const GrShaderCaps* shaderCaps, SkString* out) const
```

将变量声明追加到输出字符串。

**参数：**
- `shaderCaps`: 着色器能力信息（当前实现未使用）
- `out`: 输出字符串

**生成格式：**
```glsl
[layout(...)] [额外修饰符] [类型修饰符] 类型 名称[数组大小]
```

**示例输出：**
```glsl
layout(location=0) in vec3 aPosition
uniform mat4 uViewMatrix
flat out int vInstanceID[16]
```

## 内部实现细节

### 声明生成逻辑

`appendDecl` 的实现按照 GLSL 语法顺序拼接各部分：

```cpp
void GrShaderVar::appendDecl(const GrShaderCaps* shaderCaps, SkString* out) const {
    // 1. 布局限定符
    if (!fLayoutQualifier.isEmpty()) {
        out->appendf("layout(%s) ", fLayoutQualifier.c_str());
    }

    // 2. 额外修饰符（如 flat, noperspective）
    if (!fExtraModifiers.isEmpty()) {
        out->appendf("%s ", fExtraModifiers.c_str());
    }

    // 3. 类型修饰符（in, out, uniform）
    if (this->getTypeModifier() != TypeModifier::None) {
        out->appendf("%s ", type_modifier_string(this->getTypeModifier()));
    }

    // 4. 类型和名称
    SkSLType effectiveType = this->getType();
    if (this->isArray()) {
        // 数组形式：类型 名称[大小]
        out->appendf("%s %s[%d]",
                     SkSLTypeString(effectiveType),
                     this->getName().c_str(),
                     this->getArrayCount());
    } else {
        // 非数组形式：类型 名称
        out->appendf("%s %s", SkSLTypeString(effectiveType), this->getName().c_str());
    }
}
```

### 类型修饰符字符串映射

```cpp
static const char* type_modifier_string(GrShaderVar::TypeModifier t) {
    switch (t) {
        case TypeModifier::None:    return "";
        case TypeModifier::In:      return "in";
        case TypeModifier::InOut:   return "inout";
        case TypeModifier::Out:     return "out";
        case TypeModifier::Uniform: return "uniform";
    }
    SK_ABORT("Unknown shader variable type modifier.");
}
```

### 布局限定符累加

`addLayoutQualifier` 支持多次调用，自动用逗号分隔：

```cpp
void addLayoutQualifier(const char* layoutQualifier) {
    if (!layoutQualifier || !strlen(layoutQualifier)) {
        return;
    }
    if (fLayoutQualifier.isEmpty()) {
        fLayoutQualifier = layoutQualifier;
    } else {
        fLayoutQualifier.appendf(", %s", layoutQualifier);  // 追加并用逗号分隔
    }
}
```

**示例：**
```cpp
var.addLayoutQualifier("location=0");
var.addLayoutQualifier("binding=1");
// 结果：layout(location=0, binding=1)
```

### 额外修饰符累加

`addModifier` 支持多次调用，自动用空格分隔：

```cpp
void addModifier(const char* modifier) {
    if (!modifier || !strlen(modifier)) {
        return;
    }
    if (fExtraModifiers.isEmpty()) {
        fExtraModifiers = modifier;
    } else {
        fExtraModifiers.appendf(" %s", modifier);  // 追加并用空格分隔
    }
}
```

**示例：**
```cpp
var.addModifier("flat");
var.addModifier("centroid");
// 结果：flat centroid
```

## 依赖关系

### 依赖的模块

| 模块 | 关系 | 说明 |
|------|------|------|
| `SkSLType` | 使用 | 表示 SkSL 类型系统 |
| `SkString` | 组合 | 字符串存储 |
| `GrShaderCaps` | 参数 | 着色器能力查询（当前未使用） |
| `SkSLTypeString` | 工具 | 将类型枚举转换为字符串 |

### 被依赖的模块

| 模块 | 使用方式 | 说明 |
|------|---------|------|
| `GrGLSLShaderBuilder` | 直接使用 | 着色器构建器使用 GrShaderVar 生成代码 |
| `GrProcessor` 子类 | 创建变量 | 各种处理器使用 GrShaderVar 声明变量 |
| `GrGLSLVaryingHandler` | 管理 varying | Varying 变量管理器 |
| `GrGLSLUniformHandler` | 管理 uniform | Uniform 变量管理器 |

## 设计模式与设计决策

### 值语义设计

`GrShaderVar` 采用值语义：
- 支持拷贝和移动（使用默认实现）
- 无需手动管理内存
- 适合存储在容器中（`std::vector<GrShaderVar>`）

### 构建器模式变体

虽然没有独立的 Builder 类，但提供了渐进式构建接口：
```cpp
GrShaderVar var("myVar", SkSLType::kFloat4);
var.addLayoutQualifier("location=0");
var.addModifier("flat");
var.setTypeModifier(TypeModifier::In);
```

### 字符串延迟生成

变量声明字符串不预先存储，而是按需生成：
- **优势**：节省内存，避免存储重复信息
- **劣势**：每次生成都需要字符串拼接
- **适用场景**：变量声明通常只生成一次

### 可选字段设计

布局限定符和额外修饰符为可选：
- 默认为空字符串
- 生成时自动跳过空字段
- 支持灵活的变量声明组合

### 类型安全

使用枚举类型 `SkSLType` 和 `TypeModifier`：
- 编译时类型检查
- 避免字符串拼写错误
- 便于 IDE 自动补全

## 性能考量

### 内存布局

`GrShaderVar` 的内存占用：
```
SkSLType (4 字节) + TypeModifier (4 字节) + int (4 字节) +
3 × SkString (约 24 字节/个) ≈ 84 字节
```

对于大量变量，考虑优化：
- 短字符串优化（SSO）减少堆分配
- 布局限定符和额外修饰符通常为空，不占用堆内存

### 字符串拼接

`appendDecl` 使用多次 `appendf` 调用：
- 每次调用可能触发字符串重新分配
- **优化机会**：预分配足够的缓冲区
- **实际影响**：着色器生成是一次性操作，性能影响有限

### 空字符串检查

`addLayoutQualifier` 和 `addModifier` 进行空字符串检查：
```cpp
if (!layoutQualifier || !strlen(layoutQualifier)) {
    return;
}
```

避免不必要的字符串操作和内存分配。

### 类型修饰符查找

使用简单的 switch 语句而非映射表：
- 只有 5 种类型修饰符，switch 效率高
- 编译器可以优化为跳转表
- 避免静态初始化和查找开销

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/core/SkSLTypeShared.h` | 依赖 | SkSL 类型系统定义 |
| `include/core/SkString.h` | 使用 | 字符串类 |
| `src/gpu/ganesh/GrShaderCaps.h` | 参数 | 着色器能力描述 |
| `src/gpu/ganesh/glsl/GrGLSLShaderBuilder.h` | 使用者 | 着色器代码构建器 |
| `src/gpu/ganesh/glsl/GrGLSLVaryingHandler.h` | 使用者 | Varying 变量管理 |
| `src/gpu/ganesh/glsl/GrGLSLUniformHandler.h` | 使用者 | Uniform 变量管理 |
| `src/gpu/ganesh/GrProcessor.h` | 使用者 | 处理器基类 |
