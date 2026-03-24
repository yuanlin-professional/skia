# SkSLModifiersDeclaration

> 源文件: src/sksl/ir/SkSLModifiersDeclaration.h, src/sksl/ir/SkSLModifiersDeclaration.cpp

## 概述

`ModifiersDeclaration` 类是 SkSL（Skia Shading Language）中间表示(IR)中的程序元素类型，用于表示仅包含修饰符和布局限定符的全局声明语句，例如 `layout(blend_support_all_equations) out;`。这种特殊的声明形式在 GLSL 中用于配置着色器的全局属性，如计算着色器的工作组大小（`layout(local_size_x=16) in;`）或片段着色器的混合模式。该类作为终结类（`final`）存储布局信息和修饰符标志，不关联具体的变量或类型，是纯粹的元数据声明。

## 架构位置

`ModifiersDeclaration` 位于 Skia 的 SkSL 编译器的 IR 程序元素层中：

```
skia/
  src/
    sksl/
      ir/
        SkSLIRNode.h                     # IR 节点基类
        SkSLProgramElement.h             # 程序元素基类（ModifiersDeclaration 的父类）
        SkSLModifiersDeclaration.h/cpp   # 本文件，修饰符声明
        SkSLLayout.h                     # 布局限定符
        SkSLModifierFlags.h              # 修饰符标志
        SkSLModifiers.h                  # 修饰符容器
      SkSLContext.h                      # 编译上下文
      SkSLErrorReporter.h                # 错误报告
      SkSLProgramSettings.h              # 程序配置
```

在着色器编译流程中的位置：
```
源代码解析 → 修饰符声明识别 → Convert (验证) → IR 节点 → 代码生成/属性配置
```

典型使用场景：
- 计算着色器工作组大小：`layout(local_size_x=16, local_size_y=16, local_size_z=1) in;`
- 片段着色器输出：`layout(blend_support_all_equations) out;`
- 其他全局布局配置

## 主要类与结构体

### ModifiersDeclaration 类

```cpp
class ModifiersDeclaration final : public ProgramElement {
public:
    inline static constexpr Kind kIRNodeKind = Kind::kModifiers;

    // 构造函数
    ModifiersDeclaration(Position pos, const Layout& layout, ModifierFlags flags);

    // 类型检查 + 创建（用于用户代码解析）
    static std::unique_ptr<ModifiersDeclaration> Convert(const Context& context,
                                                         const Modifiers& modifiers);

    // 直接创建（用于编译器内部）
    static std::unique_ptr<ModifiersDeclaration> Make(const Context& context,
                                                      const Modifiers& modifiers);

    // 访问器
    const Layout& layout() const;
    ModifierFlags modifierFlags() const;

    // 字符串表示
    std::string description() const override;

private:
    Layout fLayout;            // 布局限定符
    ModifierFlags fFlags;      // 修饰符标志
};
```

### 关键概念

**Layout（布局）**: 包含各种布局限定符，如：
- `local_size_x/y/z`: 计算着色器工作组维度
- `binding`, `set`: 资源绑定位置
- `location`: 输入/输出位置
- 其他特定于目标平台的布局属性

**ModifierFlags（修饰符标志）**: 位掩码，包括：
- `in`, `out`, `inout`: 参数修饰符
- `uniform`, `buffer`: 存储修饰符
- `readonly`, `writeonly`: 访问限定符

## 公共 API 函数

### 构造函数

```cpp
ModifiersDeclaration(Position pos, const Layout& layout, ModifierFlags flags)
```

**功能**: 创建修饰符声明对象。

**参数**:
- `pos`: 声明在源代码中的位置
- `layout`: 布局限定符结构体
- `flags`: 修饰符标志位掩码

### Convert (类型检查工厂)

```cpp
static std::unique_ptr<ModifiersDeclaration> Convert(const Context& context,
                                                     const Modifiers& modifiers)
```

**功能**: 从用户代码解析修饰符声明，进行语义检查和验证。

**参数**:
- `context`: 编译上下文
- `modifiers`: 修饰符容器（包含位置、布局、标志）

**检查流程**:

1. **程序类型限制**:
   ```cpp
   if (!ProgramConfig::IsFragment(kind) && !ProgramConfig::IsVertex(kind) &&
       !ProgramConfig::IsCompute(kind)) {
       context.fErrors->error(pos, "layout qualifiers are not allowed in this kind of program");
       return nullptr;
   }
   ```
   - 只允许在片段、顶点、计算着色器中使用布局限定符
   - 其他着色器类型（如几何、细分）报错

2. **local_size 验证**（计算着色器特定）:
   ```cpp
   if (modifiers.fLayout.fLocalSizeX >= 0 || ...) {
       // 检查 1: local_size 不能为零
       if (modifiers.fLayout.fLocalSizeX == 0 || ...) {
           context.fErrors->error(pos, "local size qualifiers cannot be zero");
           return nullptr;
       }

       // 检查 2: 只能用于计算着色器
       if (!ProgramConfig::IsCompute(kind)) {
           context.fErrors->error(pos, "local size layout qualifiers are only allowed in a compute program");
           return nullptr;
       }

       // 检查 3: 必须使用 'in' 修饰符
       if (modifiers.fFlags != ModifierFlag::kIn) {
           context.fErrors->error(pos, "local size layout qualifiers must be defined using an 'in' declaration");
           return nullptr;
       }
   }
   ```

   **local_size 限定符规则**:
   - 三个维度 (`X`, `Y`, `Z`) 必须全部非零
   - 仅在计算着色器中合法
   - 必须伴随 `in` 修饰符（如 `layout(...) in;`）

3. **创建声明**: 所有检查通过后，调用 `Make` 创建对象

**返回**: 成功返回 `ModifiersDeclaration`，失败返回 `nullptr` 并报告错误。

### Make (直接创建工厂)

```cpp
static std::unique_ptr<ModifiersDeclaration> Make(const Context& context,
                                                  const Modifiers& modifiers)
```

**功能**: 直接创建修饰符声明对象，假设所有检查已完成。

**断言**:
```cpp
SkASSERT(ProgramConfig::IsFragment(kind) || ProgramConfig::IsVertex(kind) ||
         ProgramConfig::IsCompute(kind));
```
验证程序类型正确性。

**用途**: 编译器内部使用，跳过重复检查以提高性能。

### 访问器方法

```cpp
const Layout& layout() const
```
返回布局限定符的常量引用。

```cpp
ModifierFlags modifierFlags() const
```
返回修饰符标志位掩码。

### description

```cpp
std::string description() const override
```

**功能**: 生成修饰符声明的字符串表示，用于调试和代码重构。

**格式**: `layout(...) modifiers;`

**实现**:
```cpp
return fLayout.paddedDescription() + fFlags.description() + ';';
```

**示例输出**:
- `layout(local_size_x=16, local_size_y=16, local_size_z=1) in;`
- `layout(blend_support_all_equations) out;`

## 内部实现细节

### local_size 三维度验证

local_size 必须同时指定或同时省略三个维度：
```cpp
if (modifiers.fLayout.fLocalSizeX >= 0 ||  // 任一维度被指定
    modifiers.fLayout.fLocalSizeY >= 0 ||
    modifiers.fLayout.fLocalSizeZ >= 0)
```

**原因**:
- 计算着色器的工作组维度是三维的
- 部分指定会导致未定义行为
- GLSL 规范要求全部指定或全部使用默认值

**默认值**（未指定时）:
- `-1` 表示未设置（在 `Layout` 结构体中）
- 代码生成器会使用平台默认值或报错

### 修饰符组合限制

`in` 修饰符与 local_size 的强制绑定：
```cpp
if (modifiers.fFlags != ModifierFlag::kIn) {
    context.fErrors->error(pos, "local size must be defined using an 'in' declaration");
    return nullptr;
}
```

**GLSL 规范要求**:
```glsl
// 正确
layout(local_size_x=16) in;

// 错误
layout(local_size_x=16) out;     // 不能用 out
layout(local_size_x=16) uniform; // 不能用 uniform
layout(local_size_x=16);         // 必须有 in
```

### 布局描述格式化

`paddedDescription()` 确保布局和修饰符之间有适当的空格：
```cpp
// fLayout.paddedDescription() 示例
"layout(location=0) "       // 末尾带空格
"layout(set=0, binding=1) " // 多个限定符，末尾带空格
""                          // 空布局，无空格
```

## 依赖关系

### 直接依赖

**头文件**:
- `SkSLProgramElement.h`: 程序元素基类
- `SkSLLayout.h`: 布局限定符
- `SkSLModifierFlags.h`: 修饰符标志
- `SkSLPosition.h`: 位置信息

**实现文件额外依赖**:
- `SkSLContext.h`: 编译上下文
- `SkSLErrorReporter.h`: 错误报告
- `SkSLProgramSettings.h`: 程序配置
- `SkSLModifiers.h`: 修饰符容器
- `SkEnumBitMask.h`: 位掩码工具

### 被依赖关系

- **解析器**: 解析 `layout(...) modifier;` 语法时创建 `ModifiersDeclaration`
- **代码生成器**: 提取布局信息生成目标代码（GLSL, SPIR-V, Metal）
- **着色器配置**: 计算着色器的工作组大小配置

## 设计模式与设计决策

### 设计模式

1. **工厂方法模式**: `Convert` 和 `Make` 提供不同的创建策略
2. **值对象模式**: `Layout` 和 `ModifierFlags` 是不可变的值类型
3. **建造者模式**: `Modifiers` 作为构建参数的容器

### 设计决策

**为什么需要独立的声明类型？**
- 修饰符声明不关联任何变量或类型
- 它是纯粹的元数据，影响全局着色器属性
- 无法表示为变量声明或函数声明

**为什么限制在特定着色器类型？**
- 不同着色器类型支持的布局限定符不同
- 简化实现和错误检查
- 符合 GLSL 规范的限制

**为什么 local_size 必须伴随 'in'？**
- GLSL 规范要求：工作组大小是"输入"配置
- 区别于 `out` 或 `uniform` 等其他存储修饰符
- 语义明确：定义计算着色器的输入工作组布局

**为什么检查 local_size 不能为零？**
- 零维度的工作组没有意义
- 会导致运行时错误或未定义行为
- 早期捕获用户错误

**为什么使用位掩码表示修饰符？**
- 高效的存储和比较（单个整数）
- 支持多个修饰符组合（如 `readonly uniform`）
- 快速的位运算操作（检查、设置、清除）

## 性能考量

### 内存占用

单个 `ModifiersDeclaration` 对象：
- `ProgramElement` 基类: ~16 字节（虚表 + 位置 + 类型标记）
- `fLayout`: ~40-60 字节（包含多个布局字段）
- `fFlags`: 4-8 字节（位掩码）
- **总计**: ~60-84 字节

### 编译时开销

- **检查成本**: O(1) - 简单的条件分支
- **创建成本**: O(1) - 直接构造对象
- **内存分配**: 单次堆分配

### 运行时影响

`ModifiersDeclaration` 不直接影响运行时性能：
- 仅用于编译期配置
- 不生成可执行代码（除了配置参数）
- 计算着色器的 local_size 会影响 GPU 性能（但这是用户配置的结果）

## 相关文件

### 核心相关文件

- **src/sksl/ir/SkSLProgramElement.h**: 程序元素基类
- **src/sksl/ir/SkSLLayout.h**: 布局限定符定义
- **src/sksl/ir/SkSLModifierFlags.h**: 修饰符标志
- **src/sksl/ir/SkSLModifiers.h**: 修饰符容器

### 代码生成相关

- **src/sksl/codegen/SkSLGLSLCodeGenerator.cpp**: GLSL 代码生成
- **src/sksl/codegen/SkSLSPIRVCodeGenerator.cpp**: SPIR-V 代码生成
- **src/sksl/codegen/SkSLMetalCodeGenerator.cpp**: Metal 代码生成

### 使用示例

```cpp
// 计算着色器工作组大小声明
Modifiers mods;
mods.fPosition = pos;
mods.fLayout.fLocalSizeX = 16;
mods.fLayout.fLocalSizeY = 16;
mods.fLayout.fLocalSizeZ = 1;
mods.fFlags = ModifierFlag::kIn;

auto decl = ModifiersDeclaration::Convert(context, mods);
// 生成代码: layout(local_size_x=16, local_size_y=16, local_size_z=1) in;
```
