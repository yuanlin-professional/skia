# SkPDFUtils (PDF 工具函数)

> 源文件:
> - `src/pdf/SkPDFUtils.h`
> - `src/pdf/SkPDFUtils.cpp`

## 概述

`SkPDFUtils` 命名空间提供了 Skia PDF 生成器中广泛使用的工具函数集。这些函数覆盖了 PDF 内容流操作（路径绘制命令、图形状态应用）、数值格式化（颜色分量、浮点数）、矩阵和矩形的 PDF 数组转换、混合模式映射、以及图像处理等功能。源文件超过 560 行，是 PDF 模块的基础工具库。

## 架构位置

```
SkPDFDevice (绘制操作)
  |-- 使用 SkPDFUtils 写入 PDF 内容流
  |     |-- MoveTo, AppendLine, EmitPath (路径命令)
  |     |-- PaintPath, StrokePath (绘制命令)
  |     |-- ApplyGraphicState, ApplyPattern (状态切换)
  |
  |-- 使用 SkPDFUtils 进行格式转换
        |-- ColorToDecimal, AppendScalar (数值格式化)
        |-- RectToArray, MatrixToArray (类型转换)
        |-- BlendModeName (混合模式映射)
```

## 主要类与结构体

本模块不定义类，所有功能通过命名空间函数和内联工具提供。

### 辅助枚举

- **`EmptyPath`** -- 空路径处理方式：`Discard`（丢弃）或 `Preserve`（保留为零矩形）
- **`EmptyVerb`** -- 空动词处理方式：`Discard`（丢弃）或 `Preserve`（保留）

## 公共 API 函数

### 混合模式

- **`BlendModeName(SkBlendMode)`** -- 将 Skia 混合模式映射为 PDF 混合模式名称。不支持的模式返回 `nullptr`。

### 类型转换

- **`RectToArray(rect)`** -- 将 `SkRect` 转换为 PDF 数组 `[left, top, right, bottom]`。
- **`MatrixToArray(matrix)`** -- 将 `SkMatrix` 的仿射分量转换为 PDF 数组 `[a, b, c, d, e, f]`。

### PDF 内容流路径命令

- **`MoveTo(x, y, content)`** -- 输出 `x y m` 移动命令。
- **`AppendLine(x, y, content)`** -- 输出 `x y l` 直线命令。
- **`AppendRectangle(rect, content)`** -- 输出 `x y w h re` 矩形命令。处理 Skia 与 PDF 的 Y 轴方向差异。
- **`ClosePath(content)`** -- 输出 `h` 闭合路径命令。
- **`EmitPath(path, style, emptyPath, emptyVerb, content, tolerance)`** -- 将 SkPath 转换为 PDF 路径命令序列。处理矩形优化、二次曲线到三次曲线转换、空路径等。
- **`PaintPath(style, fill, content)`** -- 输出路径绘制命令（填充、描边或两者）。
- **`StrokePath(content)`** -- 输出 `S` 描边命令。

### 图形状态

- **`ApplyGraphicState(objectIndex, content)`** -- 输出 `gs` 图形状态应用命令。
- **`ApplyPattern(objectIndex, content)`** -- 输出 `scn` 图案应用命令。
- **`AppendTransform(matrix, stream)`** -- 输出 `cm` 坐标变换命令。

### 数值格式化

- **`ColorToDecimal(value, result)`** -- 将 `uint8_t` 颜色值转换为三位精度的十进制字符串（如 `0.502`）。
- **`ColorToDecimalF(value, result)`** -- 将 `float` 颜色值转换为四位精度的十进制字符串。
- **`AppendScalar(value, stream)`** -- 将 `SkScalar` 写为 PDF 数值格式。
- **`AppendColorComponent(value, wStream)`** -- 内联函数，写入 uint8 颜色分量。
- **`AppendColorComponentF(value, wStream)`** -- 内联函数，写入 float 颜色分量。

### 十六进制写入

- **`WriteUInt16BE(wStream, value)`** -- 写入大端序 16 位十六进制值。
- **`WriteUInt8(wStream, value)`** -- 写入 8 位十六进制值。
- **`WriteUTF16beHex(wStream, utf32)`** -- 将 UTF-32 码点转换为 UTF-16BE 并写入十六进制。

### 着色器与图像

- **`GetShaderLocalMatrix(shader)`** -- 获取着色器的局部矩阵。
- **`InverseTransformBBox(matrix, bbox)`** -- 对包围框应用逆变换。
- **`PopulateTilingPatternDict(pattern, bbox, ...)`** -- 填充平铺图案字典。
- **`ToBitmap(img, dst)`** -- 将 SkImage 转换为 SkBitmap。
- **`GetDateTime(dateTime)`** -- 获取当前时间并填充 PDF 日期时间结构。

### 辅助模板

- **`SkPackedArrayEqual(u, v, n)`** -- 比较两个紧凑数组是否相等。

## 内部实现细节

### 路径输出优化

`EmitPath()` 包含多项优化：
1. **矩形检测**：如果路径是闭合矩形（顺时针或偶奇填充），直接使用 `re` 命令。
2. **空路径处理**：根据 `EmptyPath` 参数决定丢弃或保留。
3. **单线条检测**：填充模式下的单线条路径（无面积）被跳过。
4. **二次到三次转换**：PDF 不支持二次贝塞尔，使用 `SkConvertQuadToCubic` 转换。
5. **三次曲线优化**：当第二控制点与终点重合时使用 `y` 命令而非 `c` 命令。

### 混合模式映射

PDF 只支持有限的混合模式子集。不支持的 Skia 混合模式（如 `kXor`、`kPlus`）回退到 `Normal`。其他复杂模式由 `SkPDFDevice` 通过分层合成处理。

### 数值格式化

颜色值使用三到四位有效数字，在保持视觉无损的同时最小化 PDF 文件大小。`ColorToDecimal` 将 `[0, 255]` 映射为 `[0.000, 1.000]`。

`AppendScalar` 使用 `SkFloatToDecimal` 进行高效的浮点到十进制转换，输出最少的必要位数，确保往返转换的精确性。

### 路径 Verb 处理

`EmitPath` 对每种路径 verb 有不同处理：
- `kMove` -- 使用 `m` 命令移动画笔
- `kLine` -- 使用 `l` 命令绘制直线
- `kQuad` -- 转换为三次贝塞尔（`SkConvertQuadToCubic`）后使用 `c` 命令
- `kConic` -- 将圆锥曲线转换为多段三次贝塞尔
- `kCubic` -- 直接使用 `c` 或 `y` 命令（优化：当第二控制点与终点重合时）
- `kClose` -- 使用 `h` 命令闭合路径

### 日期时间处理

`GetDateTime()` 使用平台特定的时间获取方式：
- Windows 上使用 `GetSystemTime` 获取 UTC 时间
- 其他平台使用 `gmtime` 获取 UTC 时间
- 结果填入 `SkPDF::DateTime` 结构，用于 PDF 文档的 `/CreationDate` 和 `/ModDate`

## 依赖关系

**内部依赖：**
- `SkPDFTypes` -- PDF 对象类型（Array, Dict）
- `SkPDFResourceDict` -- 资源字典
- `SkFloatToDecimal` -- 浮点数到十进制转换
- `SkGeometry` -- 几何工具（曲线转换）
- `SkPathPriv` -- 路径内部工具

**外部依赖：**
- `SkMatrix`, `SkPath`, `SkRect`, `SkPaint` -- Skia 基础类型
- `SkStream` -- 输出流
- `SkUTF` -- Unicode 工具
- `SkShaderBase` -- 着色器内部接口

## 设计模式与设计决策

1. **内联优先**：频繁调用的小函数（如 `AppendScalar`、`WriteUInt16BE`）在头文件中内联定义，减少函数调用开销。

2. **流式输出**：所有命令直接写入 `SkWStream`，不构建中间字符串，最小化内存使用。

3. **PDF 命令忠实性**：路径命令直接对应 PDF 操作符（`m`, `l`, `c`, `y`, `h`, `re`），确保生成的 PDF 内容流符合规范。

4. **Y 轴处理**：在 `AppendRectangle` 中处理 Skia（Y 轴向下）和 PDF（Y 轴向上）的差异。

## 性能考量

- **矩形快速路径**：检测矩形路径并使用 `re` 命令，避免逐顶点输出。
- **精度控制**：`SkFloatToDecimal` 输出最少的有效数字，减小 PDF 文件大小。
- **内联函数**：高频调用函数内联，消除函数调用开销。
- **空路径跳过**：根据配置跳过空路径和空动词，避免无意义的 PDF 命令输出。

## 相关文件

- `src/pdf/SkPDFTypes.h` -- PDF 基础类型
- `src/pdf/SkPDFDevice.h` -- PDF 绘制设备（主要调用者）
- `src/pdf/SkPDFResourceDict.h` -- 资源字典
- `src/utils/SkFloatToDecimal.h` -- 浮点格式化
- `include/docs/SkPDFDocument.h` -- 文档公共接口
