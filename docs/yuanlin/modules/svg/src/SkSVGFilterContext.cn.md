# SkSVGFilterContext

> 源文件: [modules/svg/src/SkSVGFilterContext.cpp](../../../../modules/svg/src/SkSVGFilterContext.cpp)

## 概述

`SkSVGFilterContext` 是 SVG 滤镜系统的运行时上下文管理器，在构建滤镜效果 DAG（有向无环图）过程中负责管理滤镜基元之间的输入/输出关系。它追踪每个滤镜基元的结果、色彩空间以及滤镜子区域，并提供输入解析功能——将 SVG 中定义的各种输入类型（`SourceGraphic`、`SourceAlpha`、`FillPaint`、`StrokePaint`、具名结果等）解析为对应的 `SkImageFilter` 对象。

该类是 `SkSVGFilter` 和 `SkSVGFe*` 之间的桥梁，在滤镜 DAG 构建过程中维护完整的状态。

## 架构位置

```
SkSVGFilter
  └── 使用 SkSVGFilterContext 构建 DAG
        ├── 注册结果 (registerResult)
        ├── 解析输入 (resolveInput)
        └── 管理上一结果 (setPreviousResult)

SkSVGFe* (各种滤镜基元)
  └── 通过 SkSVGFilterContext 获取输入和子区域
```

`SkSVGFilterContext` 在 `SkSVGFilter::buildFilterDAG()` 中被创建，然后在遍历每个 fe 子节点时作为参数传递。

## 主要类与结构体

### `SkSVGFilterContext`

| 成员 | 类型 | 说明 |
|------|------|------|
| `fFilterEffectsRegion` | `SkRect` | 整体滤镜效果区域 |
| `fPrimitiveUnits` | `SkSVGObjectBoundingBoxUnits` | 滤镜基元坐标单位 |
| `fResults` | `THashMap<SkSVGStringType, Result>` | 具名滤镜结果映射表 |
| `fPreviousResult` | `Result` | 前一个滤镜基元的输出结果 |

### `Result` 结构体

| 字段 | 类型 | 说明 |
|------|------|------|
| `fImageFilter` | `sk_sp<SkImageFilter>` | 滤镜结果的图像滤镜 |
| `fFilterSubregion` | `SkRect` | 滤镜基元子区域 |
| `fColorspace` | `SkSVGColorspace` | 结果的色彩空间 |

## 公共 API 函数

### `filterEffectsRegion() const`
返回整体滤镜效果区域。

### `filterPrimitiveSubregion(const SkSVGFeInputType& input) const`
根据输入类型查找对应的滤镜基元子区域。对于具名引用返回该结果的子区域，对于未指定输入返回前一结果的子区域，其他情况返回整体滤镜效果区域。

### `registerResult(id, result, subregion, colorspace)`
将具有 `result` 属性的滤镜基元输出注册到映射表中，供后续滤镜基元通过 `in` 属性引用。

### `setPreviousResult(result, subregion, colorspace)`
设置当前滤镜基元的输出为"前一结果"，供未指定 `in` 属性的下一个滤镜基元隐式引用。

### `previousResultIsSourceGraphic() const`
检查前一结果是否为原始源图形（即 `fImageFilter == nullptr`）。

### `resolveInputColorspace(ctx, inputType) const`
解析输入类型对应的色彩空间。

### `resolveInput(ctx, inputType) const`
解析输入类型为 `SkImageFilter`，不进行色彩空间转换。

### `resolveInput(ctx, inputType, colorspace) const`
解析输入类型为 `SkImageFilter`，并执行色彩空间转换到目标色彩空间。

## 内部实现细节

### 输入类型解析 (`getInput`)

实现了 SVG 1.1 规范中 `FilterPrimitiveIn` 属性的完整语义，支持六种输入类型：

| 输入类型 | 行为 |
|----------|------|
| `SourceAlpha` | 创建一个仅保留 alpha 通道的颜色矩阵滤镜（RGB 置零） |
| `SourceGraphic` | 返回 nullptr（表示原始源图形，null 在 Skia 中等同于源输入） |
| `FillPaint` | 将填充画笔转换为着色器，然后包装为图像滤镜 |
| `StrokePaint` | 将描边画笔转换为着色器，然后包装为图像滤镜 |
| `FilterPrimitiveReference` | 从结果映射表中查找具名结果 |
| `Unspecified` | 使用前一结果（隐式链式引用） |

### 色彩空间转换 (`ConvertFilterColorspace`)

匿名命名空间中的辅助函数，支持三种转换情况：
- 相同色彩空间：直接返回（无操作）
- sRGB -> linearRGB：应用 `SRGBToLinearGamma` 颜色滤镜
- linearRGB -> sRGB：应用 `LinearToSRGBGamma` 颜色滤镜

### 画笔到着色器转换 (`paint_as_shader`)

辅助函数，将 `SkPaint` 转换为 `SkShader`：
1. 如果画笔有着色器且 alpha < 1，通过 `DstIn` 混合模式应用透明度
2. 如果画笔无着色器，创建纯色着色器
3. 如果画笔有颜色滤镜，叠加应用

## 依赖关系

- **Skia Core**: `SkBlendMode`, `SkColor`, `SkColorFilter`, `SkColorSpace`, `SkPaint`, `SkShader`
- **Skia Effects**: `SkColorMatrix`, `SkImageFilters`
- **Skia Internal**: `SkTHash`（哈希映射）
- **SVG 模块**: `SkSVGRenderContext`, `SkSVGTypes`

## 设计模式与设计决策

1. **注册表模式**: 通过 `fResults` 哈希映射实现具名结果的注册和查找，允许滤镜基元间的任意引用关系。

2. **隐式链式引用**: `fPreviousResult` 实现了 SVG 规范中"未指定输入时使用前一结果"的语义，简化了常见的线性滤镜链场景。

3. **色彩空间感知**: 每个结果都携带色彩空间信息，在输入解析时自动执行必要的色彩空间转换，确保滤镜计算的色彩正确性。

4. **null 约定**: `SkImageFilter` 为 nullptr 表示"源图形"，这是 Skia 图像滤镜 API 的约定，简化了 SourceGraphic 输入的处理。

## 性能考量

- 哈希映射查找的时间复杂度为 O(1)，高效支持大量具名结果
- 色彩空间转换会在滤镜链中插入额外的 `SkColorFilter` 节点，增加渲染开销
- `paint_as_shader` 中的着色器包装会创建新对象，但在滤镜 DAG 构建中只执行一次
- 整体上下文为栈分配（在 `buildFilterDAG` 的作用域内），无堆分配开销
- SourceAlpha 输入创建颜色矩阵滤镜以清零 RGB 通道，这比直接提取 alpha 更通用但开销稍大
- FillPaint 和 StrokePaint 输入需要将 SkPaint 转换为 SkShader，涉及对象创建但仅在首次使用时执行
- `resolveInput` 的三参数版本在需要色彩空间转换时才添加额外滤镜节点，避免了不必要的处理
- 滤镜基元子区域的查找对于未指定输入使用 O(1) 直接访问 `fPreviousResult`
- `ConvertFilterColorspace` 使用快速路径检查（`src == dst`）避免在色彩空间相同时创建不必要的颜色滤镜

## 相关文件

- `modules/svg/include/SkSVGFilterContext.h` - 头文件，定义类接口和 Result 结构体
- `modules/svg/src/SkSVGFilter.cpp` - 创建和使用 FilterContext 的入口点
- `modules/svg/include/SkSVGFe.h` - 滤镜基元基类，使用 FilterContext 获取输入
- `modules/svg/include/SkSVGRenderContext.h` - 渲染上下文，提供画笔信息和颜色解析
- `modules/svg/include/SkSVGTypes.h` - SVG 类型定义，包括 SkSVGFeInputType、SkSVGColorspace 等
- `include/effects/SkImageFilters.h` - Skia 图像滤镜工厂方法
- `include/effects/SkColorMatrix.h` - Skia 颜色矩阵，用于 SourceAlpha 输入
- `include/core/SkColorFilter.h` - Skia 颜色滤镜，用于色彩空间转换
- `src/core/SkTHash.h` - Skia 内部哈希映射实现，用于存储具名滤镜结果

### 使用示例

在 `SkSVGFilter::buildFilterDAG` 中，`SkSVGFilterContext` 的典型使用流程为：

```
1. 创建 SkSVGFilterContext（传入滤镜效果区域和基元单位）
2. 对每个 fe 子节点:
   a. 调用 feNode.resolveFilterSubregion(ctx, fctx) 解析子区域
   b. 调用 feNode.resolveColorspace(ctx, fctx) 解析色彩空间
   c. 调用 feNode.makeImageFilter(ctx, fctx) 生成滤镜
   d. 调用 fctx.registerResult() 注册具名结果
   e. 调用 fctx.setPreviousResult() 设置前一结果
```
