# SkSVGFeBlend

> 源文件: [modules/svg/src/SkSVGFeBlend.cpp](../../../../modules/svg/src/SkSVGFeBlend.cpp)

## 概述

`SkSVGFeBlend` 实现了 SVG `<feBlend>` 滤镜效果，用于将两个输入图像按照指定的混合模式（normal、multiply、screen、darken、lighten）进行混合。该实现将 SVG 的混合模式映射为 Skia 的 `SkBlendMode`，并通过 `SkImageFilters::Blend` 生成对应的图像滤镜。

## 架构位置

```
SkSVGNode
  └── SkSVGFe (滤镜效果基类)
        └── SkSVGFeBlend  ← 本文件实现
```

位于 SVG 模块滤镜效果子系统中，负责在滤镜图构建阶段处理双输入混合操作。

## 主要类与结构体

### SkSVGFeBlend
- 继承自 `SkSVGFe`，对应 SVG `<feBlend>` 元素
- 额外属性：`in2`（第二个输入源）、`mode`（混合模式）

### SkSVGFeBlend::Mode 枚举
- `kNormal`: 正常混合（映射到 `SkBlendMode::kSrcOver`）
- `kMultiply`: 正片叠底（映射到 `SkBlendMode::kMultiply`）
- `kScreen`: 滤色（映射到 `SkBlendMode::kScreen`）
- `kDarken`: 变暗（映射到 `SkBlendMode::kDarken`）
- `kLighten`: 变亮（映射到 `SkBlendMode::kLighten`）

## 公共 API 函数

### `parseAndSetAttribute`
```cpp
bool parseAndSetAttribute(const char* name, const char* value);
```
解析 `in2` 和 `mode` 属性，同时委托基类处理通用滤镜属性（包括 `in`）。

### `onMakeImageFilter`
```cpp
sk_sp<SkImageFilter> onMakeImageFilter(const SkSVGRenderContext& ctx,
                                       const SkSVGFilterContext& fctx) const;
```
核心方法：
1. 解析滤镜子区域（crop rect）
2. 将 SVG 混合模式映射为 `SkBlendMode`
3. 解析颜色空间并获取前景/背景输入滤镜
4. 调用 `SkImageFilters::Blend` 创建混合滤镜

## 内部实现细节

### 混合模式映射

静态辅助函数 `GetBlendMode` 将 SVG 定义的混合模式映射为 Skia 的 `SkBlendMode`：
- `normal` 对应 `kSrcOver`（标准的源覆盖目标混合）
- 其他模式直接一对一映射

函数末尾使用 `SkUNREACHABLE` 宏标记不应到达的路径（当所有枚举值都已处理时）。

### 属性解析模板特化

文件末尾为 `SkSVGAttributeParser::parse<SkSVGFeBlend::Mode>` 提供模板特化，使用 `parseEnumMap` 将 SVG 字符串值映射为枚举。解析器在映射成功后还调用 `parseEOSToken()` 确保没有尾随字符。

### 双输入处理

`feBlend` 是双输入滤镜：`in`（前景，通过基类 `getIn()` 获取）和 `in2`（背景，通过 `fIn2` 成员存储）。两个输入在同一颜色空间下通过 `fctx.resolveInput` 解析。

## 依赖关系

- **Skia 核心**: `SkBlendMode`、`SkImageFilter`、`SkRect`、`SkImageFilters`
- **Skia 私有工具**: `SkAssert`
- **SVG 模块**: `SkSVGFe`（基类）、`SkSVGAttributeParser`、`SkSVGFilterContext`
- **标准库**: `<tuple>`

## 设计模式与设计决策

1. **枚举映射模式**: 使用 `constexpr` 元组数组实现字符串到枚举的编译期映射表，配合 `parseEnumMap` 通用解析器，这是 SVG 模块中属性解析的标准惯用法。

2. **前景/背景对称性**: `in` 和 `in2` 分别对应前景和背景，在 `SkImageFilters::Blend` 调用中背景在前、前景在后，与 Skia API 的参数顺序一致。

3. **不可达标记**: `SkUNREACHABLE` 在 switch 完整覆盖所有枚举值后标记，既作为代码安全保护，也帮助编译器消除「函数可能无返回值」的警告。

## 性能考量

- 混合模式映射为简单的 switch 查找，O(1) 时间复杂度。
- 实际的混合计算委托给 Skia 的 `SkImageFilters::Blend`，支持 GPU 加速。
- 属性解析使用编译期常量映射表，避免运行时字符串哈希或动态查找。

## 相关文件

- `modules/svg/include/SkSVGFeBlend.h` - 类声明与 Mode 枚举定义
- `modules/svg/include/SkSVGFe.h` - 滤镜效果基类
- `modules/svg/include/SkSVGFilterContext.h` - 滤镜上下文
- `include/core/SkBlendMode.h` - Skia 混合模式定义
- `include/effects/SkImageFilters.h` - Skia 图像滤镜工厂
