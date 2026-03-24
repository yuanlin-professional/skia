# SkPathUtils

> 源文件
> - include/core/SkPathUtils.h
> - src/core/SkPathUtils.cpp

## 概述

`SkPathUtils` 是 Skia 中提供路径实用工具函数的命名空间 `skpathutils`。它主要提供将描边路径转换为填充路径的功能，即 `FillPathWithPaint` 系列函数。这些函数处理路径效果（path effects）和描边参数（stroke parameters），生成可以用填充方式渲染的等效路径，是路径渲染管线的重要组成部分。

## 架构位置

`SkPathUtils` 位于 Skia 核心路径工具层：

- 头文件位于 `include/core`，是公开 API 的一部分
- 实现位于 `src/core`，属于核心路径处理模块
- 处于路径表示（`SkPath`）和渲染（`SkCanvas`）之间的转换层
- 与 `SkPaint`、`SkPathEffect`、`SkStrokeRec` 协同工作
- 为路径描边和效果应用提供底层支持

## 主要类与结构体

该模块主要提供函数而非类，位于 `skpathutils` 命名空间中。

## 公共 API 函数

### FillPathWithPaint (基础版本)

```cpp
SK_API bool FillPathWithPaint(const SkPath& src, const SkPaint& paint, SkPathBuilder* dst);
```

将描边路径转换为填充路径的简化版本：

- **参数**
  - `src`: 源路径
  - `paint`: 包含描边和路径效果设置的画笔
  - `dst`: 输出路径构建器
- **返回值**: 如果结果可以填充返回 `true`，如果是细线（hairline）需要描边则返回 `false`

使用默认的裁剪矩形（`nullptr`）和单位矩阵（`SkMatrix::I()`）。

### FillPathWithPaint (完整版本)

```cpp
SK_API bool FillPathWithPaint(const SkPath& src, const SkPaint& paint, SkPathBuilder* dst,
                              const SkRect* cullRect, const SkMatrix& ctm);
```

完整版本，支持裁剪矩形和变换矩阵：

- **参数**
  - `src`: 源路径
  - `paint`: 包含描边和路径效果设置的画笔
  - `dst`: 输出路径构建器
  - `cullRect`: 可选的裁剪矩形，传递给路径效果
  - `ctm`: 当前变换矩阵（Current Transform Matrix），用于提高精度（在缩放时）
- **返回值**: 如果结果可以填充返回 `true`，如果是细线需要描边则返回 `false`

### FillPathWithPaint (返回 SkPath)

```cpp
SK_API SkPath FillPathWithPaint(const SkPath& src, const SkPaint& paint, bool* isFill = nullptr);
```

便利函数，直接返回转换后的路径：

- **参数**
  - `src`: 源路径
  - `paint`: 包含描边和路径效果设置的画笔
  - `isFill`: 可选的输出参数，指示结果是否为填充路径
- **返回值**: 转换后的路径对象

## 内部实现细节

### 路径效果处理

函数首先检查并应用路径效果：

```cpp
const SkPath* srcPtr = &origSrc;
SkPath pathStorage;
SkPathEffect* pe = paint.getPathEffect();
if (pe && pe->filterPath(builder, origSrc, &rec, cullRect, ctm)) {
    pathStorage = builder->detach();
    srcPtr = &pathStorage;
}
```

如果画笔包含路径效果（如虚线、圆角等），先应用效果，然后使用效果后的路径进行后续处理。

### 描边转换

使用 `SkStrokeRec` 处理描边参数：

```cpp
SkStrokeRec rec(paint, resScale);
if (!rec.applyToPath(builder, *srcPtr)) {
    *builder = *srcPtr;
}
```

`SkStrokeRec` 封装了描边的所有参数（宽度、端点样式、连接样式、斜接限制等），并负责将描边路径转换为填充路径。

### 分辨率缩放

使用 `SkMatrixPriv::ComputeResScaleForStroking` 计算分辨率缩放因子：

```cpp
const SkScalar resScale = SkMatrixPriv::ComputeResScaleForStroking(ctm);
SkStrokeRec rec(paint, resScale);
```

当变换矩阵包含缩放时，提高路径精度，确保描边在变换后仍然正确。

### 有效性检查

函数在开始和结束时检查路径的有效性：

```cpp
if (!origSrc.isFinite()) {
    builder->reset();
    return false;
}

if (!builder->isFinite()) {
    builder->reset();
}
```

确保输入和输出路径都不包含无穷大或 NaN 值。

### 细线检测

函数返回值指示是否为细线：

```cpp
return !rec.isHairlineStyle();
```

细线（hairline）是特殊的描边样式，宽度始终为1像素，无论变换矩阵如何缩放。细线不能转换为填充路径，必须通过描边方式渲染。

### 模糊测试保护

针对模糊测试添加了特殊保护：

```cpp
#if defined(SK_BUILD_FOR_FUZZER)
    // Prevent lines with small widths from timing out.
    if (rec.getStyle() == SkStrokeRec::Style::kStroke_Style && rec.getWidth() < 0.001) {
        return false;
    }
#endif
```

极小的描边宽度可能导致大量计算，在模糊测试环境中提前返回。

## 依赖关系

**依赖的模块**

| 模块 | 用途 |
|------|------|
| `SkPath` | 源路径和结果路径 |
| `SkPathBuilder` | 构建输出路径 |
| `SkPaint` | 获取描边和效果参数 |
| `SkPathEffect` | 应用路径效果（虚线、圆角等） |
| `SkStrokeRec` | 描边参数记录和应用 |
| `SkMatrix` | 变换矩阵，用于分辨率计算 |
| `SkMatrixPriv` | 矩阵私有辅助函数 |
| `SkRect` | 裁剪矩形 |

**被依赖的模块**

| 模块 | 关系 |
|------|------|
| 路径渲染管线 | 在实际渲染前进行路径转换 |
| `SkCanvas` | 可能在内部调用进行路径描边 |
| 导出工具 | 将描边路径转换为填充路径以便导出 |

## 设计模式与设计决策

### 策略模式

通过 `SkPaint` 和 `SkPathEffect` 实现策略模式：

- 不同的路径效果（虚线、圆角、自定义效果）作为可插拔的策略
- 函数通过统一接口处理各种效果
- 扩展性好，易于添加新的路径效果

### 两阶段转换

路径转换分为两个阶段：

1. **路径效果阶段**：应用 `SkPathEffect`（如虚线效果）
2. **描边阶段**：使用 `SkStrokeRec` 将描边转换为填充

这种分离确保了效果和描边的正确组合。

### 重载设计

提供三个重载版本满足不同需求：

- **简化版本**：快速使用，默认参数
- **完整版本**：提供所有控制选项
- **返回路径版本**：便利接口，避免手动创建 `SkPathBuilder`

### 精度控制

通过 `resScale` 参数控制精度：

- 考虑变换矩阵的缩放
- 在高分辨率或放大场景中提高质量
- 避免在变换后出现锯齿或不准确的描边

### 防御式编程

多处进行有效性检查：

- 输入路径有效性检查
- 输出路径有效性检查
- 模糊测试保护
- 确保函数健壮性

## 性能考量

### 路径重用

使用临时路径 `pathStorage` 存储中间结果：

- 避免不必要的路径拷贝
- 使用指针切换（`srcPtr`）降低开销

### 提前返回

在多处进行提前返回：

- 无效路径立即返回
- 模糊测试场景提前返回
- 避免不必要的计算

### 路径构建器

使用 `SkPathBuilder` 而非直接修改 `SkPath`：

- 更高效的路径构建
- 批量操作优化
- 最后一次性生成最终路径

### 分辨率优化

`resScale` 参数平衡了质量和性能：

- 仅在必要时提高精度
- 避免过度细分路径
- 适应不同的渲染场景

### 适用场景

最佳使用场景：

- 需要将描边路径转换为填充路径的场景
- 应用路径效果后需要进一步处理
- 路径导出工具（描边路径通常需要转换为填充）
- 预处理路径以提高渲染性能

### 性能权衡

- **优势**：将描边转换为填充后可以使用更高效的填充渲染器
- **劣势**：转换过程本身有开销，生成的路径可能更复杂
- **权衡**：对于重复渲染的路径，转换成本可以分摊

## 相关文件

| 文件路径 | 说明 |
|----------|------|
| `include/core/SkPath.h` | 路径定义 |
| `include/core/SkPathBuilder.h` | 路径构建器 |
| `include/core/SkPaint.h` | 画笔定义（包含描边参数） |
| `include/core/SkPathEffect.h` | 路径效果基类 |
| `include/core/SkStrokeRec.h` | 描边参数记录 |
| `src/core/SkMatrixPriv.h` | 矩阵私有辅助函数 |
| `include/core/SkMatrix.h` | 变换矩阵 |
