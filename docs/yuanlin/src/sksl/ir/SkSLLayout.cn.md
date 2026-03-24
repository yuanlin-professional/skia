# SkSL Layout - 布局限定符

> 源文件:
> - `src/sksl/ir/SkSLLayout.h`
> - `src/sksl/ir/SkSLLayout.cpp`

## 概述

`Layout` 结构体表示 SkSL 中变量或接口块前的布局限定符,例如 `layout (location = 0) int x`。布局限定符提供了关于变量在 GPU 上如何存储和访问的元信息,包括绑定点、位置、偏移量、像素格式、后端类型以及计算着色器的本地调用大小等。

`LayoutFlag` 枚举以位掩码形式定义了所有可能的布局标志,涵盖了 Vulkan、Metal、WebGPU、Direct3D 等多种后端的限定符。

## 架构位置

```
SkSL 编译器
└── IR (中间表示)
    └── Layout  <-- 本文件
        ├── 被 Variable 使用(变量的布局信息)
        ├── 被 Field 使用（结构体字段的布局信息）
        └── 被 Modifiers 聚合（修饰符中的布局部分）
```

`Layout` 是一个独立的结构体,被 `Variable`、`Field`、`Modifiers` 等多种 IR 元素使用。

## 主要类与结构体

### `LayoutFlag` (枚举)

位掩码枚举,定义了所有布局限定符标志:

| 类别 | 标志 | 说明 |
|------|------|------|
| 通用标志 | `kOriginUpperLeft` | 原点在左上角 |
| | `kPushConstant` | 推送常量(Vulkan/WebGPU) |
| | `kBlendSupportAllEquations` | 混合支持所有方程 |
| | `kColor` | 颜色限定符 |
| 索引标志 | `kLocation`, `kOffset`, `kBinding` | 位置/偏移/绑定索引 |
| | `kTexture`, `kSampler`, `kIndex` | 纹理/采样器/索引 |
| | `kSet`, `kBuiltin`, `kInputAttachmentIndex` | 集合/内置/输入附件索引 |
| 后端标志 | `kVulkan`, `kMetal`, `kWebGPU`, `kDirect3D` | 后端类型(互斥) |
| 像素格式 | `kRGBA8`, `kRGBA32F`, `kR32F` | 像素格式(互斥) |
| 本地大小 | `kLocalSizeX/Y/Z` | 计算着色器的本地调用大小 |

### `Layout` (结构体)

| 成员 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fFlags` | `LayoutFlags` | `kNone` | 布局标志位掩码 |
| `fLocation` | `int` | -1 | 位置索引 |
| `fOffset` | `int` | -1 | 偏移量 |
| `fBinding` | `int` | -1 | 绑定索引 |
| `fTexture` | `int` | -1 | 纹理索引 |
| `fSampler` | `int` | -1 | 采样器索引 |
| `fIndex` | `int` | -1 | 索引值 |
| `fSet` | `int` | -1 | 描述符集合 |
| `fBuiltin` | `int` | -1 | SPIR-V 内置标识符 |
| `fInputAttachmentIndex` | `int` | -1 | Vulkan 输入附件索引 |
| `fLocalSizeX/Y/Z` | `int` | -1 | 计算着色器本地调用大小 |

## 公共 API 函数

### `Layout::description`

```cpp
std::string description() const;
```

生成布局限定符的 SkSL 文本表示,如 `layout (location = 0, binding = 1)`。末尾不含空格。

### `Layout::paddedDescription`

```cpp
std::string paddedDescription() const;
```

与 `description()` 类似,但在非空时末尾加空格,方便与其他修饰符拼接。

### `Layout::checkPermittedLayout`

```cpp
bool checkPermittedLayout(const Context& context,
                          Position pos,
                          LayoutFlags permittedLayoutFlags) const;
```

验证当前布局标志是否在允许范围内。检查规则:

1. **后端互斥**: 最多只能指定一个后端标志
2. **像素格式互斥**: 最多只能指定一个像素格式
3. **绑定冲突**: `binding` 不能与 `texture`/`sampler` 共存
4. **后端依赖**: `texture`/`sampler` 仅在 Metal/WebGPU/Direct3D 下允许; `push_constant` 仅在 Vulkan/WebGPU 下允许; `set` 在 Metal 下不允许
5. **逐项验证**: 遍历所有布局标志,报告不被允许的限定符

### `Layout::builtin` (静态方法)

```cpp
static Layout builtin(int builtin);
```

创建仅包含 `fBuiltin` 值的布局,用于 SPIR-V 内置变量。

### `Layout::operator==`

```cpp
bool operator==(const Layout& other) const;
```

比较两个布局是否完全相同,包括所有标志和索引值。

## 内部实现细节

### 描述生成

`paddedDescription()` 使用 `String::Separator()` 工具以逗号分隔的格式生成布局字符串。输出顺序为:
1. 后端标志 (vulkan/metal/webgpu/direct3d)
2. 像素格式 (rgba8/rgba32f/r32f)
3. 索引值 (location/offset/binding/...)
4. 其他标志 (origin_upper_left/push_constant/color/...)
5. 本地大小 (local_size_x/y/z)

### 权限验证的条件逻辑

`checkPermittedLayout()` 中有一些条件性的权限调整:
- 当未指定 Metal/WebGPU/Direct3D 后端时,`texture` 和 `sampler` 标志被从允许列表中移除
- 当未指定 Vulkan/WebGPU 后端时,`push_constant` 被移除
- 当显式指定 Metal 后端时,`set` 被移除

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkEnumBitMask.h` | 位掩码枚举支持 |
| `SkSLContext.h` | 编译上下文(用于权限验证) |
| `SkSLErrorReporter.h` | 错误报告 |
| `SkSLPosition.h` | 源码位置 |
| `SkSLString.h` | 字符串工具(分隔符) |
| `SkMathPriv.h` | `SkPopCount` 函数(位计数) |

## 设计模式与设计决策

1. **位掩码设计**: 使用位掩码表示布局标志,支持高效的标志组合和检查
2. **互斥组管理**: 后端标志和像素格式通过 `SkPopCount` 检查互斥性(同组最多一个)
3. **默认值约定**: 所有索引成员默认值为 -1,表示"未指定"
4. **后端感知验证**: 布局权限验证根据指定的后端类型动态调整,适应跨平台编译需求
5. **值类型语义**: `Layout` 是结构体(值类型),支持拷贝和相等比较

## 性能考量

- `LayoutFlags` 使用单个 `int` 存储所有标志,标志检查通过位运算完成,非常高效
- `checkPermittedLayout()` 使用静态常量数组遍历所有标志,但数组大小固定(约 23 项),不构成性能瓶颈
- `description()` 方法每次调用都重新生成字符串,不做缓存

## 相关文件

- `src/sksl/ir/SkSLModifiers.h` -- 修饰符,聚合 Layout 和 ModifierFlags
- `src/sksl/ir/SkSLModifierFlags.h` -- 修饰符标志(与布局标志互补)
- `src/sksl/ir/SkSLVariable.h` -- 变量,持有 Layout
- `src/sksl/ir/SkSLType.h` -- 类型系统中的 `Field` 结构体使用 Layout
- `src/sksl/spirv.h` -- SPIR-V 常量(fBuiltin 的值来源)
