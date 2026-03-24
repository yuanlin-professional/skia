# SkSL FunctionDeclaration - 函数声明

> 源文件:
> - `src/sksl/ir/SkSLFunctionDeclaration.h`
> - `src/sksl/ir/SkSLFunctionDeclaration.cpp`

## 概述

`FunctionDeclaration` 表示 SkSL IR 中的函数声明(不包含函数体)。它记录了函数的名称、参数列表、返回类型、修饰符标志以及内联属性等元数据。该类是 SkSL 函数系统的核心节点,既用于表示用户自定义函数,也用于表示内置(intrinsic)函数。

`FunctionDeclaration` 支持函数重载(通过 `nextOverload` 链表)和泛型类型解析,并包含对各种程序类型(runtime shader、color filter、blender 等)的 `main()` 函数签名的专门验证逻辑。

## 架构位置

```
SkSL 编译器
└── IR (中间表示)
    └── 符号 (Symbol)
        └── FunctionDeclaration  <-- 本文件
            ├── 被 FunctionDefinition 引用(提供函数体)
            ├── 被 FunctionCall 引用（调用目标）
            └── 通过 nextOverload 链接重载版本
```

`FunctionDeclaration` 继承自 `Symbol`,可以被添加到符号表中。

## 主要类与结构体

### `FunctionDeclaration`

| 成员 | 类型 | 说明 |
|------|------|------|
| `fDefinition` | `const FunctionDefinition*` | 指向函数定义(如果有函数体) |
| `fNextOverload` | `FunctionDeclaration*` | 指向下一个同名重载 |
| `fParameters` | `TArray<Variable*>` | 参数列表 |
| `fReturnType` | `const Type*` | 返回类型 |
| `fModifierFlags` | `ModifierFlags` | 修饰符(inline/noinline/pure 等) |
| `fIntrinsicKind` | `IntrinsicKind` | 内置函数类型标识 |
| `fModuleType` | `ModuleType` | 所属模块类型 |
| `fIsMain` | `bool` | 是否为 main 函数 |
| `fHasMainCoordsParameter` | `bool` | main 函数是否有坐标参数 |
| `fHasMainInputColorParameter` | `bool` | main 函数是否有输入颜色参数 |
| `fHasMainDestColorParameter` | `bool` | main 函数是否有目标颜色参数 |

## 公共 API 函数

### `FunctionDeclaration::Convert`

```cpp
static FunctionDeclaration* Convert(const Context& context,
                                    Position pos,
                                    const Modifiers& modifiers,
                                    std::string_view name,
                                    TArray<std::unique_ptr<Variable>> parameters,
                                    Position returnTypePos,
                                    const Type* returnType);
```

从源代码创建函数声明,执行完整的语义验证:

1. **布局检查**: 函数不允许任何布局限定符
2. **修饰符检查**: 验证 `inline`/`noinline`/`pure`/`export`/`$es3` 修饰符的合法性
3. **返回类型检查**: 函数不能返回数组类型,ES2 模式不允许返回含数组的结构体,非内置函数不能返回不透明类型
4. **参数检查**: 验证参数修饰符(const/in/out)、存储纹理的像素格式、pure 函数的 out 参数限制
5. **main 签名验证**: 根据程序类型验证 main 函数签名
6. **重复声明检查**: 在符号表中查找已有声明,处理前向声明匹配
7. **符号注册**: 将参数和函数声明添加到符号表

### `determineFinalTypes`

```cpp
bool determineFinalTypes(const ExpressionArray& arguments,
                         ParamTypes* outParameterTypes,
                         const Type** outReturnType) const;
```

为泛型函数确定具体类型。当函数参数是泛型类型(如 `$genType`)时,根据传入的实际参数类型确定最终的参数和返回类型。

### 其他重要方法

| 方法 | 说明 |
|------|------|
| `mangledName()` | 生成名称修饰后的函数名 |
| `description()` | 生成人类可读的函数描述 |
| `matches()` | 判断两个声明是否匹配(名称 + 参数类型) |
| `getMainCoordsParameter()` | 获取 main 函数的坐标参数 |
| `getMainInputColorParameter()` | 获取 main 函数的输入颜色参数 |
| `getMainDestColorParameter()` | 获取 main 函数的目标颜色参数 |

## 内部实现细节

### main 函数签名验证 (`check_main_signature`)

根据不同的程序类型强制执行不同的 main 函数签名:

| 程序类型 | 签名要求 |
|----------|----------|
| RuntimeColorFilter | `half4 main(half4)` |
| RuntimeShader | `half4 main(float2)` |
| RuntimeBlender | `half4 main(half4, half4)` |
| MeshVertex | `Varyings main(const Attributes)` |
| MeshFragment | `float2 main(const Varyings [, out half4])` |
| Vertex/Compute | `void main()` |
| Fragment | `main()` 或 `main(float2)` |

### 泛型类型解析 (`find_generic_index`)

对于内置函数的泛型参数(如 `$genType` 可匹配 `float`/`float2`/`float3`/`float4`):
1. 遍历泛型类型列表,找到与具体类型匹配的索引
2. 所有泛型参数必须解析到同一个索引
3. 泛型返回类型使用相同的索引

### 名称修饰 (`mangledName`)

- 内置函数和 main 函数使用原始名称
- 其他函数格式: `funcname_returntypeparamtypes`
- 以 `$` 开头的内置函数使用 `Q` 标记替代

### 重载链管理

函数声明通过 `fNextOverload` 指针形成单向链表。查找函数时遍历整个链表,使用参数匹配(`parameters_match`)确定正确的重载版本。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLSymbol.h` | 基类 |
| `SkSLModifierFlags.h` | 修饰符标志 |
| `SkSLIntrinsicList.h` | 内置函数类型 |
| `SkSLModule.h` | 模块类型 |
| `SkSLVariable.h` | 参数变量 |
| `SkSLType.h` | 类型系统(泛型解析) |
| `SkSLLayout.h` | 布局限定符 |
| `SkSLContext.h` | 编译上下文 |
| `SkSLErrorReporter.h` | 错误报告 |
| `SkSLProgramKind.h` | 程序类型(main 签名验证) |

## 设计模式与设计决策

1. **符号表集成**: 作为 `Symbol` 的子类,函数声明可以直接存入符号表,支持名称查找
2. **重载链表**: 同名函数通过链表连接,避免在符号表中为每个重载创建单独条目
3. **前向声明支持**: `Convert()` 中的 `find_existing_declaration` 允许函数先声明后定义
4. **程序类型感知**: main 函数的验证逻辑根据程序类型(shader/blender/filter 等)自适应
5. **泛型类型延迟解析**: 内置函数的泛型参数在调用时根据实际参数类型解析,而非声明时

## 性能考量

- 泛型类型解析通过索引查找实现,复杂度与泛型候选类型数量成正比(通常很少,最多 9 个)
- 重载解析需要遍历重载链表并对每个候选计算参数匹配,但重载数量通常很少
- `mangledName()` 在每次调用时重新生成字符串,不做缓存
- `parameters()` 返回 `SkSpan`,是零开销的视图,不涉及拷贝
- `matches()` 方法需要逐一比较参数类型,复杂度与参数数量成正比
- `description()` 方法每次调用重新生成字符串,使用 `Separator()` 工具函数高效管理逗号分隔
- `Convert()` 方法中的多阶段验证确保每种错误只报告一次,避免错误级联
- 构造函数中对 main 函数参数的分类(坐标/颜色)仅在函数名为 "main" 时执行

### 内置函数类型识别

在 `Convert()` 方法中,如果代码被标记为内置代码(`isBuiltinCode()`),会通过 `FindIntrinsicKind(name)` 查找函数是否为内置函数。这是一个哈希查找操作。对于用户代码,内置函数种类直接设为 `kNotIntrinsic`,跳过查找。

### 前向声明匹配

`find_existing_declaration()` 函数在符号表中查找同名函数时:
1. 遍历重载链表中的每个候选函数
2. 使用 `parameters_match()` 进行泛型感知的参数匹配
3. 如果参数匹配但返回类型不同,报告错误
4. 如果参数匹配但修饰符不同,报告错误
5. 如果找到完全匹配的声明,返回该声明(避免创建重复节点)

### 修饰符检查详情

`check_modifiers()` 允许的修饰符因代码上下文而异:
- **用户代码**: 仅允许 `inline` 和 `noinline`
- **内置代码**: 额外允许 `$es3`、`pure` 和 `export`
- `inline` 和 `noinline` 不能同时存在

### 参数检查详情

`check_parameters()` 对每个参数进行以下验证:
- 基本权限: `const` 和 `in` 始终允许;非不透明类型还允许 `out`
- 存储纹理参数: 额外允许 `readonly`/`writeonly` 和像素格式布局限定符
- 非内置代码的存储纹理参数必须指定像素格式(如 `layout(rgba32f)`)
- Runtime Effect 不允许使用效果子元素类型(shader/colorFilter/blender)作为参数
- `pure` 函数不允许 `out` 参数(纯函数不应修改外部状态)

### 返回类型检查详情

`check_return_type()` 验证以下规则:
- 不允许返回数组类型
- ES2 模式下不允许返回包含数组的结构体
- 非内置代码不允许返回不透明类型(sampler、texture 等)

## 相关文件

- `src/sksl/ir/SkSLFunctionDefinition.h` -- 函数定义(声明 + 函数体)
- `src/sksl/ir/SkSLFunctionCall.h` -- 函数调用表达式
- `src/sksl/ir/SkSLFunctionReference.h` -- 函数引用(未解析的调用目标)
- `src/sksl/ir/SkSLVariable.h` -- 函数参数变量
- `src/sksl/ir/SkSLModifiers.h` -- 修饰符(含布局和标志)
- `src/sksl/SkSLIntrinsicList.h` -- 内置函数枚举和查找
- `src/sksl/ir/SkSLSymbolTable.h` -- 符号表(函数注册和查找)
- `src/sksl/ir/SkSLType.h` -- 类型系统(泛型类型、返回类型)
- `src/sksl/SkSLProgramKind.h` -- 程序类型枚举(main 签名验证)
- `src/sksl/ir/SkSLLayout.h` -- 布局限定符(参数布局验证)
