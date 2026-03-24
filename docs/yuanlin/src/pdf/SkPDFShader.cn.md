# SkPDFShader — PDF 着色器（Pattern）生成

> 源文件：[src/pdf/SkPDFShader.h](../../src/pdf/SkPDFShader.h)、[src/pdf/SkPDFShader.cpp](../../src/pdf/SkPDFShader.cpp)

## 概述

`SkPDFShader` 模块负责将 Skia 的 `SkShader` 对象转换为 PDF Pattern 资源。在 PDF 规范中，Pattern 用于替代颜色实现图案填充和着色器效果。

该模块处理三类着色器：
- **渐变着色器**：委托给 `SkPDFGradientShader` 处理（线性、径向、扫描、锥形渐变）
- **图像着色器**：将图像绘制到 PDF 设备中，生成 Tiling Pattern
- **回退着色器**：对不支持的着色器类型（如混合着色器等），光栅化到位图后作为图像着色器处理

## 架构位置

```
SkPDFDevice::drawPath/drawRect/...
    │
    └── SkPDFMakeShader()
            │
            ├── SkPDFGradientShader::Make() (渐变)
            ├── make_image_shader() (图像 Tiling Pattern)
            └── make_fallback_shader() (光栅化回退)
```

## 主要类与结构体

### `SkPDFImageShaderKey`

用于图像着色器缓存的键结构体，使用 `SK_BEGIN_REQUIRE_DENSE` 确保内存布局紧凑以支持直接哈希。

| 字段 | 类型 | 说明 |
|------|------|------|
| `fTransform` | `SkMatrix` | 最终变换矩阵 |
| `fBBox` | `SkIRect` | 表面边界框 |
| `fBitmapKey` | `SkBitmapKey` | 图像标识键 |
| `fImageTileModes[2]` | `SkTileMode` | X/Y 方向平铺模式 |
| `fPaintColor` | `SkColor4f` | 画笔颜色 |

## 公共 API 函数

### `SkPDFMakeShader(doc, shader, ctm, surfaceBBox, paintColor) -> SkPDFIndirectReference`

将 SkShader 转换为 PDF 间接引用。处理逻辑：
1. 渐变着色器 → 委托 `SkPDFGradientShader::Make()`
2. 图像着色器 → 查缓存，命中则返回缓存引用；未命中则调用 `make_image_shader()` 创建并缓存
3. 其他着色器 → `make_fallback_shader()` 光栅化处理

## 内部实现细节

### 图像着色器（make_image_shader）

1. 在 Pattern 单元空间创建 `SkPDFDevice`
2. 将图像绘制到设备上
3. **Mirror 模式**：绘制水平翻转、垂直翻转和对角翻转的镜像副本，使 Pattern 单元为 2x 宽和/或 2x 高
4. **Clamp 模式**：
   - 四角填充角像素颜色
   - 四边使用 1 像素宽的边缘条带拉伸填充
   - Mirror+Clamp 混合模式也正确处理
5. **Decal 模式**：扩展 PatternBBox 但不填充
6. 使用 `SkPDFUtils::PopulateTilingPatternDict()` 生成 Pattern 字典
7. 输出为 PDF 流对象

### 回退着色器（make_fallback_shader）

对于不直接支持的着色器类型：
1. 创建临时 raster Surface（最大 1M 像素）
2. 用 SkPaint+SkShader 绘制整个区域
3. 将结果截图为 SkImage
4. 以 Clamp 模式调用 `make_image_shader()`

### 颜色调整

`adjust_color()` 对非 alpha-only 图像将颜色设为黑色（仅保留 alpha），因为图像着色器的颜色信息来自图像本身。

### 缓存机制

图像着色器通过 `SkPDFImageShaderKey` 在文档的 `fImageShaderMap` 中缓存。回退着色器不缓存（每次唯一）。

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `SkPDFGradientShader` | 渐变着色器生成 |
| `SkPDFDevice` | Pattern 设备（绘制 Pattern 单元内容） |
| `SkPDFDocumentPriv` | 文档级缓存（fImageShaderMap） |
| `SkPDFUtils` | PDF 工具（Tiling Pattern 字典、坐标变换） |
| `SkKeyedImage` | 图像键标识 |
| `SkShaderBase` | 着色器类型判断和属性提取 |
| `SkSurface` / `SkCanvas` | 回退着色器的光栅化 |

## 设计模式与设计决策

1. **缓存去重**：图像着色器通过包含变换、边界框、图像 ID、平铺模式和颜色的复合键进行缓存，避免重复生成相同的 Pattern。

2. **渐变/图像/回退三层策略**：渐变有专用的高效 PDF 表示；图像着色器通过 Tiling Pattern 实现；其他着色器通过光栅化兜底。

3. **Clamp 模拟**：PDF Tiling Pattern 不支持 Clamp，通过绘制边缘像素拉伸来模拟，这与 XPS 后端的策略类似。

4. **Dense 结构体键**：`SkPDFImageShaderKey` 使用 `REQUIRE_DENSE` 确保无填充字节，支持直接按内存内容哈希。

## 性能考量

- **缓存命中**：相同参数的着色器复用已生成的 PDF 对象，避免重复处理。
- **回退光栅化面积限制**：限制为 1M 像素，防止大表面导致内存爆炸。
- **Pattern 设备复用**：使用 SkPDFDevice 绘制 Pattern 内容，直接生成 PDF 流，无需中间光栅化。
- **颜色优化**：非 alpha-only 图像的着色器颜色简化为黑色+alpha，减少不必要的颜色处理。

## 相关文件

- `src/pdf/SkPDFGradientShader.h` / `.cpp` — 渐变着色器生成
- `src/pdf/SkPDFDevice.h` — PDF 设备（用于 Pattern 绘制）
- `src/pdf/SkPDFDocumentPriv.h` — 文档私有实现（缓存）
- `src/pdf/SkPDFUtils.h` — PDF 工具函数
- `src/pdf/SkBitmapKey.h` — 位图唯一标识
- `src/pdf/SkKeyedImage.h` — 键控图像
