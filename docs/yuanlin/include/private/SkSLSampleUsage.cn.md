# SkSLSampleUsage

> 源文件: `include/private/SkSLSampleUsage.h`

## 概述

SkSLSampleUsage 定义了片段处理器(fragment processor)被其父处理器采样的所有方式。这个类用于 SkSL(Skia Shading Language)编译器和 GPU 渲染管线,以优化着色器代码生成和坐标变换。通过跟踪子处理器的采样模式,系统可以进行重要的优化,如坐标变换合并、采样简化等。

## 架构位置

SkSLSampleUsage 位于 Skia SkSL 编译器和 GPU 后端的交互层。它是着色器编译优化的关键数据结构,用于在构建片段处理器树时传递采样信息。该类主要被 Ganesh(旧 GPU 后端)使用,也影响 SkSL 的代码生成策略。

## 主要类与结构体

### SampleUsage 类

表示片段处理器的采样使用方式。

**命名空间**: `SkSL::`

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fKind | Kind | 采样类型 |
| fHasPerspective | bool | 是否包含透视变换(仅对 kUniformMatrix 有效) |

### Kind 枚举

定义子处理器的五种采样方式。

```cpp
enum class Kind {
    kNone,           // 从不采样子处理器
    kPassThrough,    // 以相同坐标采样(透传)
    kUniformMatrix,  // 使用 uniform 矩阵变换坐标
    kFragCoord,      // 使用 sk_FragCoord.xy 采样
    kExplicit,       // 使用显式指定的坐标采样
};
```

**类型详解**:

| Kind | 含义 | 坐标来源 | 优化机会 |
|------|------|----------|----------|
| kNone | 不采样 | N/A | 可以完全跳过子处理器 |
| kPassThrough | 透传坐标 | 使用父坐标 | 可以合并坐标变换 |
| kUniformMatrix | uniform 矩阵 | 父坐标 × uniform 矩阵 | 可以合并多个矩阵 |
| kFragCoord | 片段坐标 | sk_FragCoord.xy | 忽略父坐标变换 |
| kExplicit | 显式坐标 | 着色器代码计算 | 无特殊优化 |

## 公共 API 函数

### 构造函数

#### `SampleUsage()` (默认)
- **功能**: 创建 kNone 类型的采样使用对象
- **参数**: 无
- **说明**: 表示子处理器从不被采样

#### `SampleUsage(Kind kind, bool hasPerspective)`
- **功能**: 创建指定类型的采样使用对象
- **参数**:
  - `kind`: 采样类型
  - `hasPerspective`: 是否包含透视变换
- **说明**: 如果 kind 不是 kUniformMatrix,hasPerspective 必须为 false

### 静态工厂方法

#### `static SampleUsage UniformMatrix(bool hasPerspective)`
- **功能**: 创建 uniform 矩阵采样类型
- **参数**: `hasPerspective` - 矩阵是否包含透视
- **返回值**: kUniformMatrix 类型的 SampleUsage 对象
- **说明**: uniform 矩阵名称固定为 "matrix"

#### `static SampleUsage Explicit()`
- **功能**: 创建显式坐标采样类型
- **返回值**: kExplicit 类型的 SampleUsage 对象

#### `static SampleUsage PassThrough()`
- **功能**: 创建透传采样类型
- **返回值**: kPassThrough 类型的 SampleUsage 对象

#### `static SampleUsage FragCoord()`
- **功能**: 创建片段坐标采样类型
- **返回值**: kFragCoord 类型的 SampleUsage 对象

### 查询方法

#### `Kind kind() const`
- **功能**: 获取采样类型
- **返回值**: Kind 枚举值

#### `bool hasPerspective() const`
- **功能**: 检查是否包含透视变换
- **返回值**: true 表示有透视,false 表示无透视
- **说明**: 仅对 kUniformMatrix 有意义

#### `bool isSampled() const`
- **功能**: 检查是否进行采样
- **返回值**: fKind != kNone 返回 true

#### `bool isPassThrough() const`
- **功能**: 检查是否为透传采样
- **返回值**: fKind == kPassThrough 返回 true

#### `bool isExplicit() const`
- **功能**: 检查是否为显式坐标采样
- **返回值**: fKind == kExplicit 返回 true

#### `bool isUniformMatrix() const`
- **功能**: 检查是否为 uniform 矩阵采样
- **返回值**: fKind == kUniformMatrix 返回 true

#### `bool isFragCoord() const`
- **功能**: 检查是否为片段坐标采样
- **返回值**: fKind == kFragCoord 返回 true

### 合并方法

#### `SampleUsage merge(const SampleUsage& other)`
- **功能**: 合并两个采样使用方式
- **参数**: `other` - 另一个 SampleUsage 对象
- **返回值**: 合并后的 SampleUsage 对象
- **说明**: 选择更通用(限制更少)的采样方式

### 运算符重载

#### `bool operator==(const SampleUsage& that) const`
- **功能**: 比较两个 SampleUsage 是否相等
- **参数**: `that` - 要比较的对象
- **返回值**: 相等返回 true

#### `bool operator!=(const SampleUsage& that) const`
- **功能**: 比较两个 SampleUsage 是否不等
- **参数**: `that` - 要比较的对象
- **返回值**: 不等返回 true

### Uniform 矩阵名称

#### `static const char* MatrixUniformName()`
- **功能**: 返回 uniform 矩阵的固定名称
- **返回值**: "matrix"
- **说明**: 所有 uniform 矩阵采样都使用这个名称

## 内部实现细节

### 采样类型的层次结构

采样类型按照约束强度排序(从强到弱):
1. **kNone**: 最强约束,完全不采样
2. **kPassThrough**: 只能使用父坐标
3. **kUniformMatrix**: 可以变换父坐标
4. **kFragCoord**: 忽略父坐标,使用片段坐标
5. **kExplicit**: 最弱约束,任意坐标

### merge() 的合并规则

合并两个 SampleUsage 时,选择约束更弱的类型:

```cpp
kNone + kPassThrough = kPassThrough
kPassThrough + kUniformMatrix = kUniformMatrix
kUniformMatrix + kFragCoord = kExplicit
任何 + kExplicit = kExplicit
```

对于 kUniformMatrix 类型:
- 如果任一有透视,合并结果有透视
- 两个无透视的矩阵合并仍无透视

### uniform 矩阵的特殊性

uniform 矩阵采样有特殊处理:
- **固定名称**: 所有使用矩阵的子处理器共享 "matrix" 名称
- **单一 uniform**: 避免重复的矩阵 uniform
- **透视标志**: hasPerspective 影响矩阵的维度(3x3 vs 2x3)

### 代码生成影响

不同 Kind 对着色器代码生成的影响:

**kNone**:
```glsl
// 子处理器完全不调用
```

**kPassThrough**:
```glsl
vec4 child_output = sample(child, input_coord);
```

**kUniformMatrix**:
```glsl
vec2 transformed = (matrix * vec3(input_coord, 1.0)).xy;
vec4 child_output = sample(child, transformed);
```

**kFragCoord**:
```glsl
vec4 child_output = sample(child, sk_FragCoord.xy);
```

**kExplicit**:
```glsl
vec2 custom_coord = /* 着色器代码计算 */;
vec4 child_output = sample(child, custom_coord);
```

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `include/core/SkTypes.h` | SkASSERT 宏 |

### 被依赖的模块

- **GrFragmentProcessor**: GPU 片段处理器使用此类跟踪子处理器采样
- **SkSL 编译器**: 根据 SampleUsage 生成不同的着色器代码
- **GrSkSLFP**: SkSL 运行时效果使用此类优化
- **SkRuntimeEffect**: 运行时着色器使用此类传递采样信息

## 设计模式与设计决策

### 值对象模式

SampleUsage 是一个轻量级值对象:
- **不可变性**: 创建后不能修改(除了赋值)
- **值语义**: 拷贝和比较都是值语义
- **小对象**: 只有 2 个字节,可以按值传递

### 类型安全的枚举

使用 enum class 而非普通 enum:
- **命名空间**: Kind 不会污染全局命名空间
- **类型安全**: 不能隐式转换为整数
- **强制限定**: 必须写 Kind::kNone,不能写 kNone

### 工厂方法命名

静态工厂方法使用描述性名称:
- `UniformMatrix()` 而非 `MakeUniformMatrix()`
- `PassThrough()` 而非 `MakePassThrough()`
- 简洁且清晰表达意图

### merge() 的语义

merge 选择更通用的类型:
- **保守策略**: 确保所有使用场景都能正确处理
- **优化机会**: 如果所有采样都是 PassThrough,可以优化
- **正确性优先**: 宁可放弃优化,也不能生成错误代码

## 性能考量

### 内存占用

SampleUsage 对象非常小:
- fKind: 1 字节(enum class)
- fHasPerspective: 1 字节(bool)
- 总计: 2 字节(可能有填充)

可以直接作为函数参数按值传递,无需引用或指针。

### 运行时开销

- 构造和拷贝: 零开销(2 字节拷贝)
- 比较: 一次整数比较(编译器可能优化为 16 位比较)
- merge: 简单的分支逻辑,几个时钟周期

### 编译时优化

SampleUsage 主要在着色器编译时使用:
- 运行时几乎无开销
- 编译时的额外成本可以忽略
- 换来的优化收益远大于成本

## 优化机会

### 坐标变换合并

如果父和子都是 PassThrough:
```
Parent(PassThrough) → Child(PassThrough)
可以优化为直接传递坐标,无需中间采样
```

### 矩阵合并

多个 UniformMatrix 可以合并:
```
Parent(Matrix1) → Child(Matrix2)
可以优化为单个 Matrix = Matrix2 * Matrix1
```

### 跳过未使用的处理器

如果子处理器的 SampleUsage 是 kNone:
- 可以完全跳过子处理器的代码生成
- 节省 uniform 空间和着色器指令

### 透视优化

如果所有采样都无透视:
- 使用 2x3 矩阵而非 3x3 矩阵
- 节省一个 vec3 uniform
- 减少矩阵乘法指令

## 典型使用场景

### 片段处理器树构建

```cpp
class MyFragmentProcessor : public GrFragmentProcessor {
    SampleUsage childUsage() const override {
        // 使用 uniform 矩阵采样子处理器
        return SampleUsage::UniformMatrix(false);
    }
};
```

### SkSL 运行时效果

```cpp
// SkSL 代码
uniform shader child;
vec4 main(vec2 coord) {
    // PassThrough 采样
    return sample(child, coord);
}
```

编译器会分析并设置 SampleUsage::PassThrough()。

### 合并多个采样方式

```cpp
SampleUsage total = SampleUsage::PassThrough();
for (const auto& child : children) {
    total = total.merge(child->sampleUsage());
}
// total 现在是最通用的采样方式
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `src/gpu/ganesh/GrFragmentProcessor.h` | 片段处理器使用此类 |
| `src/sksl/SkSLCompiler.cpp` | SkSL 编译器分析采样使用 |
| `src/sksl/ir/SkSLFunctionCall.cpp` | sample() 函数调用处理 |
| `src/gpu/ganesh/GrSkSLFP.cpp` | SkSL 片段处理器使用此类 |
| `include/effects/SkRuntimeEffect.h` | 运行时效果使用此类 |
| `tests/SkSLTest.cpp` | 单元测试 |
