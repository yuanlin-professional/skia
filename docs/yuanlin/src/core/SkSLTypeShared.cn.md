# SkSLTypeShared

> 源文件: src/core/SkSLTypeShared.h, src/core/SkSLTypeShared.cpp

## 概述

`SkSLTypeShared` 定义了 Skia 着色语言(SkSL)的类型系统枚举和相关工具函数。该模块提供了 SkSL 和 C++ 代码之间的类型桥接,包括基本数据类型(布尔、整数、浮点)、向量、矩阵以及纹理采样器类型。它是 SkSL 编译器和运行时效果系统的基础组件,用于类型检查、uniform 变量管理和着色器代码生成。

## 架构位置

`SkSLTypeShared` 位于 Skia 的 `src/core` 模块,是 SkSL 类型系统的共享层:

- **上层**: `SkRuntimeEffect`、uniform 绑定系统、着色器生成器
- **中间层**: `SkSLTypeShared` 提供类型定义和工具函数
- **下层**: SkSL 编译器内部类型系统(在 `src/sksl` 中)
- **相关系统**: 与 GPU 后端(Ganesh、Graphite)的 uniform 管理系统协作

## 主要类与结构体

### SkSLType 枚举

| 属性 | 说明 |
|------|------|
| **继承关系** | 独立枚举类(enum class) |
| **关键枚举值** | `kVoid`: 空类型<br>`kBool/kBool2/kBool3/kBool4`: 布尔类型<br>`kShort/kUShort`: 短整型及向量<br>`kInt/kUInt`: 整型及向量<br>`kFloat/kHalf`: 浮点型及向量<br>`kFloat2x2/kFloat3x3/kFloat4x4`: 浮点矩阵<br>`kHalf2x2/kHalf3x3/kHalf4x4`: 半精度矩阵<br>`kTexture2DSampler`: 2D 纹理采样器<br>`kTextureExternalSampler`: 外部纹理采样器<br>`kTexture2DRectSampler`: 矩形纹理采样器<br>`kTexture2D/kSampler/kInput`: 分离的纹理和采样器对象 |

表示 SkSL 中所有可用的数据类型。

## 公共 API 函数

### 类型查询函数

```cpp
// 获取类型的 SkSL 字符串表示
const char* SkSLTypeString(SkSLType t);

// 判断是否为浮点类型(包括向量和矩阵)
static constexpr bool SkSLTypeIsFloatType(SkSLType type);

// 判断是否为整型类型(包括向量)
static constexpr bool SkSLTypeIsIntegralType(SkSLType type);

// 判断是否为全精度数值类型
bool SkSLTypeIsFullPrecisionNumericType(SkSLType type);

// 获取向量长度(非向量返回 -1)
static constexpr int SkSLTypeVecLength(SkSLType type);

// 获取矩阵尺寸(非矩阵返回 -1)
int SkSLTypeMatrixSize(SkSLType type);

// 判断是否可作为 uniform 变量
static constexpr bool SkSLTypeCanBeUniformValue(SkSLType type);

// 判断是否为组合采样器类型
bool SkSLTypeIsCombinedSamplerType(SkSLType type);
```

## 内部实现细节

### 类型字符串映射

`SkSLTypeString` 通过 switch 语句将枚举值映射到 SkSL 类型名:
- 标量: `"bool"`, `"int"`, `"float"`, `"half"` 等
- 向量: `"float2"`, `"int3"`, `"half4"` 等
- 矩阵: `"float2x2"`, `"half3x3"`, `"float4x4"` 等
- 采样器: `"sampler2D"`, `"samplerExternalOES"`, `"sampler2DRect"` 等

### 类型分类逻辑

**浮点类型判定** (`SkSLTypeIsFloatType`):
- 包括 `float` 和 `half` 系列的标量、向量和矩阵
- 排除整型、布尔和采样器类型

**整型类型判定** (`SkSLTypeIsIntegralType`):
- 包括 `short`、`ushort`、`int`、`uint` 及其向量形式
- 排除浮点型和非数值类型

**全精度判定** (`SkSLTypeIsFullPrecisionNumericType`):
- 全精度: `int`、`uint`、`float` 系列
- 半精度: `short`、`ushort`、`half` 系列
- 非数值类型返回 false

### 向量和矩阵尺寸查询

`SkSLTypeVecLength` 返回向量组件数量:
- 标量类型返回 1
- 2/3/4 分量向量返回对应长度
- 矩阵和采样器返回 -1

`SkSLTypeMatrixSize` 返回矩阵维度:
- `float2x2/half2x2` 返回 2
- `float3x3/half3x3` 返回 3
- `float4x4/half4x4` 返回 4
- 其他类型返回 -1

### Uniform 支持判定

`SkSLTypeCanBeUniformValue` 检查类型是否可作为 uniform:
- 支持: 所有浮点类型、全精度整型(`int/uint` 系列)
- 不支持: 半精度整型(`short/ushort`)、布尔、采样器、void

这与 GPU uniform 绑定 API 的限制对应。

### 组合采样器判定

`SkSLTypeIsCombinedSamplerType` 识别传统的组合采样器:
- 组合类型: `kTexture2DSampler`, `kTextureExternalSampler`, `kTexture2DRectSampler`
- 分离类型: `kTexture2D`, `kSampler`(现代 API 如 Vulkan 支持分离)

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| include/core/SkTypes.h | 基础类型定义和宏 |

### 被依赖的模块

| 模块 | 依赖方式 |
|------|----------|
| SkRuntimeEffect | 使用类型系统进行 uniform 和 child 管理 |
| SkSL 编译器 | 类型检查和代码生成 |
| GPU 后端(GrGLSLProgramDataManager) | Uniform 绑定和数据上传 |
| SkRuntimeEffectPriv | 扩展类型操作(VarAsUniform 等) |
| Graphite/Ganesh | 着色器编译和资源管理 |

## 设计模式与设计决策

### 枚举类设计

使用 `enum class` 而非普通枚举:
- 提供类型安全(防止隐式转换)
- 避免命名空间污染
- 使用 `char` 作为底层类型减少内存占用

### constexpr 优化

大量使用 `constexpr` 函数:
- 编译期计算类型属性
- 零运行时开销
- 支持在模板和编译期分支中使用

### 半精度类型支持

区分全精度和半精度类型:
- `float` vs `half`: GPU 性能优化(移动设备)
- `int` vs `short`: 内存和带宽优化
- uniform 系统仅支持全精度以匹配 GPU API

### 组合 vs 分离采样器

支持两种采样器模型:
- **组合**: 旧 API(OpenGL ES 2.0)兼容
- **分离**: 现代 API(Vulkan/Metal)支持独立纹理和采样器对象
- 通过 `SkSLTypeIsCombinedSamplerType` 区分

### 类型计数宏

`kSkSLTypeCount` 宏定义类型总数:
- 用于数组大小声明
- 自动跟随枚举变化(`kLast + 1`)
- 避免魔数

## 性能考量

### 编译期类型检查

所有 `constexpr` 函数在编译期求值:
- `SkSLTypeIsFloatType` 等直接展开为布尔常量
- 消除运行时分支和函数调用开销
- 优化器可基于类型属性进行代码特化

### 字符串查找优化

`SkSLTypeString` 使用 switch 语句:
- 编译器可优化为跳转表或二分查找
- 比哈希表或线性搜索更快
- 所有分支返回字符串字面量(无动态分配)

### 类型大小最小化

使用 `char` 作为枚举底层类型:
- 每个枚举值仅占用 1 字节
- 在包含大量 `SkSLType` 字段的结构体中节省空间
- 58 个枚举值轻松容纳在 8 位范围内

### 内联函数

所有工具函数声明为 `static constexpr` 或定义在头文件:
- 鼓励编译器内联
- 减少函数调用开销
- 跨编译单元优化

## 相关文件

| 文件 | 关系 |
|------|------|
| include/effects/SkRuntimeEffect.h | 使用类型系统管理 uniform |
| src/core/SkRuntimeEffectPriv.h | 扩展类型操作(VarAsUniform) |
| src/sksl/SkSLContext.h | SkSL 编译器内部类型系统 |
| src/gpu/ganesh/GrGLSLProgramDataManager.h | GPU uniform 绑定 |
| src/gpu/graphite/UniformManager.h | Graphite uniform 管理 |
| src/sksl/ir/SkSLType.h | SkSL 内部类型表示 |
