# SkSVGFeComponentTransfer

> 源文件: [modules/svg/src/SkSVGFeComponentTransfer.cpp](../../../../modules/svg/src/SkSVGFeComponentTransfer.cpp)

## 概述

`SkSVGFeComponentTransfer` 实现了 SVG `<feComponentTransfer>` 滤镜效果，用于对图像的各个颜色通道（R、G、B、A）进行独立的分量传递函数变换。该文件同时包含 `SkSVGFeFunc` 类的核心实现，后者负责根据不同的传递函数类型（identity、table、discrete、linear、gamma）生成 256 字节的查找表（LUT），最终通过 Skia 的 `SkColorFilters::TableARGB` 和 `SkImageFilters::ColorFilter` 将变换应用到图像上。

## 架构位置

该文件属于 Skia SVG 模块（`modules/svg`）中的滤镜效果子系统。在 SVG 渲染管线中，它位于滤镜图构建阶段，将 SVG DOM 节点转换为 Skia 原生的 `SkImageFilter` 对象。

```
SkSVGNode
  └── SkSVGFe (滤镜效果基类)
        └── SkSVGFeComponentTransfer  ← 本文件实现
              └── 子节点: SkSVGFeFunc (feFuncR/G/B/A)
```

## 主要类与结构体

### SkSVGFeComponentTransfer
- 继承自 `SkSVGFe`，对应 SVG `<feComponentTransfer>` 元素
- 通过遍历子节点（`feFuncA/R/G/B`）收集各通道的查找表
- 在 `onMakeImageFilter` 中将查找表组合成 `SkColorFilter` 并包装为 `SkImageFilter`

### SkSVGFeFunc
- 继承自 `SkSVGHiddenContainer`，对应 SVG `<feFuncR>`、`<feFuncG>`、`<feFuncB>`、`<feFuncA>` 元素
- 属性：`Amplitude`、`Exponent`、`Intercept`、`Offset`、`Slope`、`TableValues`、`Type`
- 核心方法 `getTable()` 根据类型生成 256 字节的颜色映射表

### SkSVGFeFuncType 枚举
- `kIdentity`: 恒等变换（返回空表）
- `kTable`: 使用 tableValues 进行线性插值
- `kDiscrete`: 使用 tableValues 进行阶梯函数映射
- `kLinear`: 线性函数 `C' = slope * C + intercept`
- `kGamma`: 伽马函数 `C' = offset + pow(C, exponent)`

## 公共 API 函数

### `SkSVGFeComponentTransfer::onMakeImageFilter`
```cpp
sk_sp<SkImageFilter> onMakeImageFilter(const SkSVGRenderContext& ctx,
                                       const SkSVGFilterContext& fctx) const;
```
- 遍历子节点，按标签类型收集 A/R/G/B 通道的查找表
- 使用 `SkColorFilters::TableARGB` 创建颜色滤镜
- 返回 `SkImageFilters::ColorFilter` 包装后的图像滤镜

### `SkSVGFeFunc::getTable`
```cpp
std::vector<uint8_t> getTable() const;
```
- 根据当前 `Type` 属性值生成 256 字节的查找表
- Identity 类型返回空向量（表示不做变换）

### `SkSVGFeFunc::parseAndSetAttribute`
```cpp
bool parseAndSetAttribute(const char* name, const char* val);
```
- 解析 SVG 属性：amplitude、exponent、intercept、offset、slope、tableValues、type

## 内部实现细节

### 查找表生成策略

1. **Linear（线性）**：遍历 0-255，计算 `intercept * 255 + i * slope`，使用 `SkTPin` 钳制到 [0, 255]。

2. **Gamma（伽马）**：遍历 0-255，计算 `offset + pow(i/255, exponent)`，再缩放到 [0, 255]。

3. **Table / Discrete**：通过 `lerp_from_table_values` 共享框架实现。将 tableValues 划分为 `n = values.size() - 1` 个插值区间，每个区间映射到对应的组件表索引范围。Table 使用线性插值 `v0 + (v1 - v0) * t`，Discrete 使用阶梯函数（始终返回 `v0`）。

4. **Identity**：直接返回空向量，下游空表意味着该通道不变换（`SkColorFilters::TableARGB` 接收 nullptr 时跳过该通道）。

### 属性解析模板特化

文件末尾提供了 `SkSVGAttributeParser::parse<SkSVGFeFuncType>` 的模板特化，使用 `parseEnumMap` 将字符串映射为枚举值。

### 断言保护

通过 `SkASSERT` 确保每个通道的查找表要么为空，要么恰好 256 字节，防止运行时越界。

## 依赖关系

- **Skia 核心**: `SkColorFilter`、`SkImageFilter`、`SkRect`、`SkImageFilters`
- **Skia 私有工具**: `SkAssert`、`SkFloatingPoint`、`SkTArray`、`SkTPin`、`SkTo`
- **SVG 模块**: `SkSVGFe`（基类）、`SkSVGAttributeParser`、`SkSVGFilterContext`、`SkSVGTypes`、`SkSVGHiddenContainer`
- **标准库**: `<cmath>`（`std::pow`）、`<cstdint>`、`<tuple>`、`<vector>`

## 设计模式与设计决策

1. **策略模式**: `getTable()` 通过 switch-case 根据 `SkSVGFeFuncType` 选择不同的表生成策略，每种策略封装为 lambda 表达式。

2. **模板方法模式（共享插值框架）**: `lerp_from_table_values` 接受一个插值函数作为参数，Table 和 Discrete 模式共享相同的区间划分与遍历逻辑，仅插值函数不同。

3. **空表语义**: Identity 类型返回空向量，`onMakeImageFilter` 中空表传递 `nullptr` 给 `SkColorFilters::TableARGB`，利用底层 API 的空指针语义跳过通道处理，避免不必要的内存分配。

4. **SVG 规范一致性**: 实现严格遵循 W3C SVG 1.1 滤镜规范中 `feComponentTransfer` 的定义（参见 https://www.w3.org/TR/SVG11/filters.html#feComponentTransferTypeAttribute）。

5. **Lambda 表达式封装**: 五种表生成策略均封装为局部 lambda 表达式，而非独立的静态函数或类方法。这种做法使得策略代码与调用代码物理上相邻，提高了代码的局部性和可读性，同时由于 lambda 的作用域限制避免了命名冲突。

6. **值钳制策略**: 所有表生成路径都使用 `SkTPin` 将输出值钳制到 [0, 255] 范围内，确保查找表不包含越界值。这是一种防御性编程实践。

### SVG 属性与 Skia 映射关系

| SVG 属性 | Skia 内部表示 | 说明 |
|----------|--------------|------|
| `type` | `SkSVGFeFuncType` 枚举 | 决定表生成算法 |
| `tableValues` | `std::vector<SkSVGNumberType>` | 仅 table/discrete 使用 |
| `slope` | `SkSVGNumberType` (float) | 仅 linear 使用 |
| `intercept` | `SkSVGNumberType` (float) | 仅 linear 使用 |
| `amplitude` | `SkSVGNumberType` (float) | 仅 gamma 使用（当前代码中未直接使用） |
| `exponent` | `SkSVGNumberType` (float) | 仅 gamma 使用 |
| `offset` | `SkSVGNumberType` (float) | 仅 gamma 使用 |

## 性能考量

- 查找表为固定 256 字节，生成后的通道映射操作为 O(1) 常量时间查找。
- Identity 类型返回空表避免分配 256 字节内存和不必要的查找操作。
- `lerp_from_table_values` 限制 `tableValues` 大小在 [2, 255] 之间，防止畸形输入导致异常开销。
- 查找表在滤镜构建时一次性生成，渲染时通过硬件加速的颜色滤镜应用，开销极低。
- 每个通道的查找表独立生成，最多 4 个通道 x 256 字节 = 1024 字节的内存分配。
- `SkTPin` 使用模板特化避免了运行时类型转换的开销。
- `sk_float_round2int` 内联函数提供了高效的浮点到整数四舍五入。
- 子节点遍历采用线性扫描，但 `feComponentTransfer` 通常仅有 1-4 个子函数节点，开销可忽略。
- `SkColorFilters::TableARGB` 在 GPU 后端可以利用纹理查找表实现硬件加速。

### 内存布局考量

每个 `SkSVGFeFunc` 节点内部通过 `SVG_ATTR` 宏存储各种属性值（amplitude、exponent 等），这些都是基本类型，内存开销很小。`tableValues` 使用 `std::vector<SkSVGNumberType>` 动态分配，但仅在 Table/Discrete 模式下使用。

### 滤镜链优化

当 `feComponentTransfer` 作为滤镜链中的一个节点时，Skia 的 `SkImageFilter` 系统可能会将连续的颜色滤镜合并优化，减少中间缓冲区的分配。

## 相关文件

- `modules/svg/include/SkSVGFeComponentTransfer.h` - 类声明与属性定义
- `modules/svg/include/SkSVGFe.h` - 滤镜效果基类
- `modules/svg/include/SkSVGHiddenContainer.h` - SkSVGFeFunc 基类
- `modules/svg/include/SkSVGFilterContext.h` - 滤镜上下文，管理滤镜输入/输出
- `modules/svg/include/SkSVGAttributeParser.h` - SVG 属性解析器
- `include/effects/SkImageFilters.h` - Skia 图像滤镜工厂方法
- `include/core/SkColorFilter.h` - 颜色滤镜基类
- `modules/svg/include/SkSVGTypes.h` - SVG 类型定义（SkSVGNumberType、SkSVGFeFuncType）
- `include/private/base/SkTPin.h` - 值钳制工具函数
- `include/private/base/SkTo.h` - 安全类型转换（SkToU8）
- `include/private/base/SkFloatingPoint.h` - 浮点数工具（sk_float_round2int）
- `modules/svg/include/SkSVGNode.h` - SVG 节点基类
- `modules/svg/include/SkSVGRenderContext.h` - 渲染上下文（前向声明使用）
