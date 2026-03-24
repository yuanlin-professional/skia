# SkSVGFeFlood

> 源文件: [modules/svg/src/SkSVGFeFlood.cpp](../../../../modules/svg/src/SkSVGFeFlood.cpp)

## 概述

`SkSVGFeFlood` 实现了 SVG `<feFlood>` 滤镜基元，用于生成一个纯色填充的矩形区域。该滤镜基元通过 `flood-color` 和 `flood-opacity` 展示属性确定填充颜色和透明度，常与其他滤镜组合使用，例如作为合成操作的背景层。

## 架构位置

```
SkSVGNode
  └── SkSVGFe                    （滤镜基元基类）
        └── SkSVGFeFlood          ← 本文件
```

## 主要类与结构体

### `SkSVGFeFlood`

该类不定义额外的属性，使用从 `SkSVGNode` 继承的 `flood-color` 和 `flood-opacity` 展示属性。

## 公共 API 函数

该类没有额外的公共 API，所有功能通过基类 `SkSVGFe` 的接口暴露。

## 内部实现细节

### 洪水颜色解析 (`resolveFloodColor`)

将 `flood-color` 和 `flood-opacity` 展示属性解析为 `SkColor`：
1. 获取 `flood-color` 属性值（通过 `getFloodColor()`）
2. 获取 `flood-opacity` 属性值（通过 `getFloodOpacity()`）
3. 验证两个属性都有具体值（非继承未解析的不确定状态）
4. 通过 `ctx.resolveSvgColor()` 解析颜色（处理 `currentColor` 等特殊值）
5. 将 `flood-opacity` 应用到 Alpha 通道：`SkColorSetA(color, floodOpacity * 255)`

### 图像滤镜生成 (`onMakeImageFilter`)

创建一个纯色着色器图像滤镜：
1. 调用 `resolveFloodColor()` 获取解析后的颜色
2. 使用 `SkShaders::Color()` 创建纯色着色器
3. 通过 `SkImageFilters::Shader()` 包装为图像滤镜
4. 限定在 `resolveFilterSubregion()` 返回的子区域内

### 展示属性的特殊性

`flood-color` 和 `flood-opacity` 是不可继承的展示属性（在 `SkSVGNode` 中标记为 `false`），但它们仍然可以通过 CSS 或 `style` 属性设置。在节点构造时默认值为黑色和 1.0。

## 依赖关系

- **Skia Core**: `SkScalar`, `SkShader`
- **Skia Effects**: `SkImageFilters`
- **SVG 模块**: `SkSVGRenderContext`, `SkSVGFilterContext`

## 设计模式与设计决策

1. **展示属性复用**: 不定义自己的 `flood-color`/`flood-opacity` 属性，而是复用 `SkSVGNode` 基类中定义的展示属性，保持了 SVG 属性系统的一致性。

2. **安全降级**: 当展示属性缺少值时，回退到黑色（`SK_ColorBLACK`），并输出调试信息。

3. **简洁实现**: 整个实现只有 36 行，体现了 feFlood 作为最简单滤镜基元之一的本质。没有输入图像依赖，没有额外属性，只生成纯色输出。

4. **透明度处理**: `flood-opacity` 通过 `SkScalarRoundToInt(*floodOpacity * 255)` 映射到 8 位 alpha 通道，使用四舍五入确保值的精确性。

## 性能考量

- 纯色着色器是最轻量的着色器类型，GPU 渲染时仅需单次颜色填充
- `resolveFloodColor` 仅涉及颜色值查找和简单的整数运算（`SkScalarRoundToInt`）
- 滤镜子区域限定确保着色器仅在必要区域内求值
- `SkColorSetA` 是一个位操作，将 opacity 乘以 255 后设置到颜色的 alpha 通道
- 整个滤镜基元不接受输入图像，是纯生成式滤镜，不涉及像素数据读取

## 相关文件

- `modules/svg/include/SkSVGFeFlood.h` - 头文件定义
- `modules/svg/include/SkSVGFe.h` - 滤镜基元基类，提供 `resolveFilterSubregion()` 方法
- `modules/svg/src/SkSVGFilter.cpp` - 滤镜容器，遍历 fe 子节点并构建 DAG
- `modules/svg/src/SkSVGNode.cpp` - flood-color/flood-opacity 默认值初始化
- `modules/svg/include/SkSVGRenderContext.h` - 渲染上下文，提供 `resolveSvgColor()` 方法
