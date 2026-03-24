# SkSLInterfaceBlock

> 源文件: src/sksl/ir/SkSLInterfaceBlock.h, src/sksl/ir/SkSLInterfaceBlock.cpp

## 概述

`InterfaceBlock` 类是 SkSL（Skia Shading Language）中间表示(IR)中的程序元素类型，用于表示 GLSL 风格的接口块（Interface Block）声明。接口块是着色器之间传递数据的高级机制，类似于结构体但具有特殊的存储和链接语义，常用于顶点着色器输出（如 `out sk_PerVertex`）和片段着色器输入。在 IR 层面，接口块被表示为单个结构体类型的变量，该变量可以是命名的（实例化接口块）或匿名的（字段直接导出到全局作用域）。该类管理接口块与其关联变量之间的双向关系，并在对象销毁时自动解除绑定。

## 架构位置

`InterfaceBlock` 位于 Skia 的 SkSL 编译器的 IR 程序元素层中：

```
skia/
  src/
    sksl/
      ir/
        SkSLIRNode.h              # IR 节点基类
        SkSLProgramElement.h      # 程序元素基类（InterfaceBlock 的父类）
        SkSLInterfaceBlock.h/cpp  # 本文件，接口块声明
        SkSLVariable.h            # 变量定义
        SkSLFieldSymbol.h         # 字段符号（匿名接口块）
        SkSLType.h                # 类型系统
        SkSLVarDeclarations.h     # 变量声明
      SkSLContext.h               # 编译上下文
      SkSLCompiler.h              # 编译器（RTADJUST_NAME 定义）
      SkSLSymbolTable.h           # 符号表管理
```

在着色器管线中的位置：
```
顶点着色器          片段着色器
    ↓                  ↓
out InterfaceBlock → in InterfaceBlock
    ↓                  ↓
  字段传递           字段接收
```

典型使用场景：
- `sk_PerVertex`：顶点着色器内置输出块
- `sk_PerFragment`：片段着色器内置输入块
- 用户自定义接口块：跨着色器阶段的数据传递

## 主要类与结构体

### InterfaceBlock 类

```cpp
class InterfaceBlock final : public ProgramElement {
public:
    inline static constexpr Kind kIRNodeKind = Kind::kInterfaceBlock;

    // 构造函数：关联变量并设置双向引用
    InterfaceBlock(Position pos, Variable* var);

    // 析构函数：解除与变量的关联
    ~InterfaceBlock() override;

    // 类型检查 + 创建（用于用户代码解析）
    static std::unique_ptr<InterfaceBlock> Convert(const Context& context,
                                                   Position pos,
                                                   const Modifiers& modifiers,
                                                   std::string_view typeName,
                                                   skia_private::TArray<Field> fields,
                                                   std::string_view varName,
                                                   int arraySize);

    // 直接创建（用于编译器内部）
    static std::unique_ptr<InterfaceBlock> Make(const Context& context,
                                                Position pos,
                                                Variable* variable);

    // 访问器
    Variable* var() const;
    void detachDeadVariable();
    std::string_view typeName() const;
    std::string_view instanceName() const;
    int arraySize() const;

    // 字符串表示
    std::string description() const override;

private:
    Variable* fVariable;  // 关联的接口块变量（可为 nullptr）
};
```

### 接口块的两种形式

**命名接口块（实例化）**:
```glsl
out sk_PerVertex {
    vec4 sk_Position;
    float sk_PointSize;
} myVertex;  // 实例名
```
- 通过实例名访问：`myVertex.sk_Position`
- 变量存储在符号表中

**匿名接口块（字段导出）**:
```glsl
out sk_PerVertex {
    vec4 sk_Position;
    float sk_PointSize;
};  // 无实例名
```
- 字段直接可见：`sk_Position`（无需限定符）
- 每个字段作为 `FieldSymbol` 存储在符号表中

## 公共 API 函数

### 构造函数

```cpp
InterfaceBlock(Position pos, Variable* var)
```

**功能**: 创建接口块对象并建立与变量的双向关联。

**参数**:
- `pos`: 接口块在源代码中的位置
- `var`: 关联的变量（必须是接口块类型或接口块数组类型）

**副作用**:
- 断言验证变量的组件类型是接口块（`var->type().componentType().isInterfaceBlock()`）
- 调用 `var->setInterfaceBlock(this)` 建立反向引用

### 析构函数

```cpp
~InterfaceBlock() override
```

**功能**: 销毁接口块时解除与变量的关联。

**逻辑**:
```cpp
if (fVariable) {
    fVariable->detachDeadInterfaceBlock();
}
```

防止悬空指针：变量可能在接口块之后仍然存在。

### Convert (类型检查工厂)

```cpp
static std::unique_ptr<InterfaceBlock> Convert(const Context& context,
                                               Position pos,
                                               const Modifiers& modifiers,
                                               std::string_view typeName,
                                               TArray<Field> fields,
                                               std::string_view varName,
                                               int arraySize)
```

**功能**: 从用户代码解析接口块声明，进行完整的语义检查和类型构建。

**参数**:
- `context`: 编译上下文
- `pos`: 声明位置
- `modifiers`: 修饰符（`in`, `out`, `uniform`, `buffer` 等）
- `typeName`: 接口块类型名称
- `fields`: 字段列表（字段名、类型、位置、布局）
- `varName`: 实例名称（空字符串表示匿名块）
- `arraySize`: 数组大小（0 表示非数组）

**检查流程**:

1. **程序类型限制**:
   - 只允许在顶点、片段、计算着色器中使用接口块
   - 其他着色器类型（如几何、细分）报错

2. **sk_RTAdjust 验证**:
   - 查找名为 `sk_RTAdjust` 的特殊字段
   - 如果存在，必须是 `float4` 类型
   - `sk_RTAdjust` 用于运行时坐标系调整（Y 轴翻转等）

3. **结构体类型构建**:
   - 调用 `Type::MakeStructType` 创建接口块结构体类型
   - 标记 `interfaceBlock=true` 以区分普通结构体
   - 将类型添加到符号表

4. **数组处理**:
   - 如果 `arraySize > 0`，创建数组类型
   - 调用 `convertArraySize` 验证数组大小合法性
   - 使用 `addArrayDimension` 构建数组类型

5. **全局变量错误检查**:
   - 调用 `VarDeclaration::ErrorCheck` 验证接口块作为全局变量的合法性
   - 检查修饰符冲突、存储类别等

6. **变量创建**:
   - 调用 `Variable::Convert` 创建全局变量
   - 将变量所有权转移到符号表

7. **接口块创建**:
   - 调用 `Make` 完成最终创建

**返回**: 成功返回 `InterfaceBlock`，失败返回 `nullptr` 并报告错误。

### Make (直接创建工厂)

```cpp
static std::unique_ptr<InterfaceBlock> Make(const Context& context,
                                            Position pos,
                                            Variable* variable)
```

**功能**: 直接创建接口块对象，假设变量已正确构建。

**断言**:
- 程序类型是顶点、片段或计算着色器
- 变量的组件类型是接口块

**符号表处理**:

**匿名接口块（`varName` 为空）**:
```cpp
if (variable->name().empty()) {
    // 将每个字段作为 FieldSymbol 添加到符号表
    for (size_t i = 0; i < fields.size(); ++i) {
        context.fSymbolTable->add(
            context, std::make_unique<FieldSymbol>(fields[i].fPosition, variable, i));
    }
}
```
- 创建 `FieldSymbol` 对象包装字段
- 字段可以直接在全局作用域访问

**命名接口块**:
```cpp
else {
    // 将接口块变量添加到符号表（不获取所有权）
    context.fSymbolTable->addWithoutOwnership(context, variable);
}
```
- 变量所有权已在 `Convert` 中转移
- 仅添加符号引用

### 访问器方法

```cpp
Variable* var() const
```
返回关联的接口块变量。

```cpp
void detachDeadVariable()
```
解除与变量的关联，设置 `fVariable` 为 `nullptr`。用于变量先于接口块销毁的情况。

```cpp
std::string_view typeName() const
```
返回接口块的类型名称（如 `sk_PerVertex`）。

```cpp
std::string_view instanceName() const
```
返回实例名称（命名接口块）或空字符串（匿名接口块）。

```cpp
int arraySize() const
```
返回数组大小，非数组返回 0。

### description

```cpp
std::string description() const override
```

**功能**: 生成接口块的字符串表示，用于调试和代码重构。

**格式**:
```glsl
layout(...) modifier typeName {
    field1;
    field2;
} instanceName[arraySize];
```

**逻辑**:
1. 输出布局和修饰符
2. 输出类型名称和开括号
3. 遍历字段输出字段描述
4. 输出闭括号
5. 如果有实例名称，输出实例名称和数组大小

## 内部实现细节

### 双向引用管理

接口块和变量之间维护双向引用：
```
InterfaceBlock ←→ Variable
  fVariable         fInterfaceBlock
```

**创建时建立关联**:
```cpp
InterfaceBlock::InterfaceBlock(Position pos, Variable* var)
    : fVariable(var) {
    fVariable->setInterfaceBlock(this);  // 建立反向引用
}
```

**销毁时解除关联**:
```cpp
InterfaceBlock::~InterfaceBlock() {
    if (fVariable) {
        fVariable->detachDeadInterfaceBlock();  // 清除反向引用
    }
}
```

**提前销毁变量**:
```cpp
Variable::~Variable() {
    if (fInterfaceBlock) {
        fInterfaceBlock->detachDeadVariable();  // 清除正向引用
    }
}
```

防止悬空指针和双重释放。

### sk_RTAdjust 特殊处理

`sk_RTAdjust` 是 Skia 的内置字段，用于运行时坐标系调整：
```cpp
static std::optional<int> find_rt_adjust_index(SkSpan<const Field> fields) {
    for (size_t index = 0; index < fields.size(); ++index) {
        if (fields[index].fName == Compiler::RTADJUST_NAME) {
            return index;
        }
    }
    return std::nullopt;
}
```

**检查逻辑**:
```cpp
if (rtAdjustIndex.has_value()) {
    const Field& rtAdjustField = fields[*rtAdjustIndex];
    if (!rtAdjustField.fType->matches(*context.fTypes.fFloat4)) {
        context.fErrors->error(pos, "sk_RTAdjust must have type 'float4'");
        return nullptr;
    }
}
```

**用途**: 将 Vulkan/Metal 的 Y 轴向下坐标系转换为 OpenGL 的 Y 轴向上坐标系。

### 符号表处理策略

**匿名接口块的字段导出**:
```cpp
// 源代码
out InterfaceBlock {
    vec4 position;
    float size;
};

// 符号表添加
FieldSymbol("position", variable, 0)
FieldSymbol("size", variable, 1)

// 访问方式
position = vec4(0);  // 直接访问
```

**命名接口块的实例访问**:
```cpp
// 源代码
out InterfaceBlock {
    vec4 position;
    float size;
} instance;

// 符号表添加
Variable("instance", InterfaceBlockType)

// 访问方式
instance.position = vec4(0);  // 限定访问
```

## 依赖关系

### 直接依赖

**头文件**:
- `SkSLProgramElement.h`: 程序元素基类
- `SkSLVariable.h`: 变量类型
- `SkSLType.h`: 类型系统
- `SkSLPosition.h`: 位置信息

**实现文件额外依赖**:
- `SkSLContext.h`: 编译上下文
- `SkSLCompiler.h`: 编译器（`RTADJUST_NAME` 常量）
- `SkSLErrorReporter.h`: 错误报告
- `SkSLSymbolTable.h`: 符号表管理
- `SkSLFieldSymbol.h`: 字段符号
- `SkSLVarDeclarations.h`: 变量声明检查
- `SkSLLayout.h`: 布局修饰符
- `SkSLModifiers.h`: 修饰符系统

### 被依赖关系

- **着色器解析器**: 解析接口块声明时创建 `InterfaceBlock`
- **代码生成器**: 将接口块转换为目标语言（GLSL, SPIR-V, Metal）
- **链接器**: 验证着色器阶段之间的接口块匹配

## 设计模式与设计决策

### 设计模式

1. **工厂方法模式**: `Convert` 和 `Make` 提供不同的创建策略
2. **双向关联模式**: 接口块和变量相互引用，需要生命周期管理
3. **策略模式**: 匿名和命名接口块采用不同的符号表处理策略

### 设计决策

**为什么在 IR 层面表示为单个变量？**
- 简化类型系统：接口块是特殊的结构体类型
- 统一变量管理：可以复用 `Variable` 的所有基础设施
- 代码生成简单：直接映射到 GLSL 接口块语法

**为什么需要双向引用？**
- 从接口块访问变量：获取修饰符、类型、名称
- 从变量访问接口块：用于代码生成时识别变量属于接口块
- 生命周期管理：确保对象销毁时正确清理引用

**为什么区分匿名和命名接口块？**
- 匿名块：GLSL 标准特性，字段提升到全局作用域
- 命名块：支持数组实例和显式访问路径
- 符合 OpenGL/Vulkan 规范

**为什么限制在特定着色器类型？**
- 接口块的语义在几何、细分着色器中更复杂
- 当前 Skia 的目标场景主要是顶点和片段着色器
- 简化实现和测试负担

**为什么 sk_RTAdjust 必须是 float4？**
- 包含四个分量：`[scaleX, scaleY, offsetX, offsetY]`
- 用于坐标变换：`adjustedPos = pos * scale + offset`
- 固定格式便于运行时处理

## 性能考量

### 内存占用

单个 `InterfaceBlock` 对象：
- `ProgramElement` 基类: ~16 字节（虚表 + 位置 + 类型标记）
- `fVariable`: 8 字节（指针）
- **总计**: ~24 字节

关联的开销：
- 匿名块：N × sizeof(FieldSymbol) （N 为字段数）
- 命名块：无额外开销（变量已存在）

### 符号表开销

**匿名接口块的字段导出**:
- 每个字段创建一个 `FieldSymbol` 对象（~32 字节）
- 符号表查找多个符号（O(log N)）
- 大量字段的接口块可能影响符号表性能

**优化**: Skia 的接口块通常字段较少（<10），开销可控。

### 潜在瓶颈

- **大型匿名接口块**: 字段导出导致符号表膨胀
- **频繁接口块创建**: 双向关联的建立和解除有开销
- **sk_RTAdjust 查找**: 线性搜索字段列表（实际字段数少，影响小）

## 相关文件

### 核心相关文件

- **src/sksl/ir/SkSLProgramElement.h**: 程序元素基类
- **src/sksl/ir/SkSLVariable.h**: 变量定义
- **src/sksl/ir/SkSLFieldSymbol.h**: 字段符号
- **src/sksl/ir/SkSLType.h**: 类型系统
- **src/sksl/SkSLSymbolTable.h**: 符号表管理

### 代码生成相关

- **src/sksl/codegen/SkSLGLSLCodeGenerator.cpp**: GLSL 代码生成
- **src/sksl/codegen/SkSLSPIRVCodeGenerator.cpp**: SPIR-V 代码生成
- **src/sksl/codegen/SkSLMetalCodeGenerator.cpp**: Metal 代码生成

### 使用示例

```cpp
// 解析接口块声明
TArray<Field> fields;
fields.push_back({pos, layout, "sk_Position", float4Type});
fields.push_back({pos, layout, "sk_PointSize", floatType});

auto block = InterfaceBlock::Convert(
    context,
    pos,
    Modifiers(ModifierFlags::kOut),
    "sk_PerVertex",
    std::move(fields),
    "",  // 匿名块
    0    // 非数组
);
```
