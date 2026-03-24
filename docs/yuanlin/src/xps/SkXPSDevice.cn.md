# SkXPSDevice — XPS 文档后端绘图设备

> 源文件：[src/xps/SkXPSDevice.h](../../src/xps/SkXPSDevice.h)、[src/xps/SkXPSDevice.cpp](../../src/xps/SkXPSDevice.cpp)

## 概述

`SkXPSDevice` 是 Skia 的 XPS（XML Paper Specification）文档后端绘图设备实现。它继承自 `SkClipStackDevice`，将 Skia 的绘图操作（路径、矩形、图像、文字等）转换为 XPS 对象模型（XPS Object Model，简称 XPS OM）调用，最终生成符合 XPS 规范的文档包。

该类仅在 Windows 平台（`SK_BUILD_FOR_WIN`）下编译，依赖 Windows 的 XPS OM COM API 和字体子集化 API（`CreateFontPackage`）。

核心功能包括：
- 将 Skia 绘图基元转换为 XPS 路径（Path）、画笔（Brush）和字形（Glyphs）
- 支持纯色画笔、图像画笔、线性渐变和径向渐变
- 处理 SkPath 到 XPS 几何图形的转换（包括线段、二次贝塞尔、三次贝塞尔、圆锥曲线）
- 字体资源管理和字体子集化
- 裁剪（Clip）和遮罩滤镜（Mask Filter）的应用
- 页面生命周期管理（Portfolio -> Sheet -> Page）

## 架构位置

```
SkCanvas
    │
    └── SkXPSDevice (final, 继承自 SkClipStackDevice)
            │
            ├── XPS OM COM API (IXpsOMObjectFactory, IXpsOMPackageWriter, ...)
            │
            ├── 字体管理
            │   ├── TypefaceUse (字体资源缓存)
            │   └── CreateFontPackage (Windows 字体子集化 API)
            │
            └── 绘图转换
                ├── createXpsBrush() → 画笔创建
                ├── addXpsPathGeometry() → 路径几何转换
                ├── AddGlyphs() → 文字渲染
                └── shadePath() → 描边和填充设置
```

## 主要类与结构体

### `SkXPSDevice`

| 成员 | 类型 | 说明 |
|------|------|------|
| `fXpsFactory` | `SkTScopedComPtr<IXpsOMObjectFactory>` | XPS 对象工厂 |
| `fOutputStream` | `SkTScopedComPtr<IStream>` | 输出流 |
| `fPackageWriter` | `SkTScopedComPtr<IXpsOMPackageWriter>` | 包写入器 |
| `fCurrentPage` | `unsigned int` | 当前页码 |
| `fCurrentXpsCanvas` | `SkTScopedComPtr<IXpsOMCanvas>` | 当前页面画布 |
| `fCurrentCanvasSize` | `SkSize` | 当前画布尺寸 |
| `fCurrentUnitsPerMeter` | `SkVector` | 几何单位到物理单位转换 |
| `fCurrentPixelsPerMeter` | `SkVector` | 像素分辨率 |
| `fTypefaces` | `TArray<TypefaceUse>` | 本设备字体资源列表 |
| `fTopTypefaces` | `TArray<TypefaceUse>*` | 顶层设备字体资源指针（共享） |
| `fOpts` | `SkXPS::Options` | XPS 选项（含 PNG 编码器） |

### `SkXPSDevice::TypefaceUse`（内部类）

| 成员 | 类型 | 说明 |
|------|------|------|
| `typefaceId` | `SkTypefaceID` | 字体唯一标识 |
| `ttcIndex` | `int` | TTC 字体集合索引 |
| `fontData` | `unique_ptr<SkStream>` | 字体原始数据流 |
| `xpsFont` | `SkTScopedComPtr<IXpsOMFontResource>` | XPS 字体资源 |
| `glyphsUsed` | `SkBitSet` | 已使用的字形 ID 位集（用于子集化） |

## 公共 API 函数

### 文档生命周期

- **`beginPortfolio(SkWStream*, IXpsOMObjectFactory*)`**：初始化 XPS 文档输出，绑定输出流和工厂对象。
- **`beginSheet(unitsPerMeter, pixelsPerMeter, trimSize, ...)`**：开始新页面，设置物理单位、分辨率、裁切尺寸以及可选的 mediaBox、bleedBox、artBox、cropBox。
- **`endSheet()`**：结束当前页面。创建缩放画布将几何单位转换为 96 DPI 的物理单位，生成 XPS 页面并写入包。
- **`endPortfolio()`**：结束文档。对所有使用的字体执行子集化，关闭包写入器。

### 绘图方法（override）

- **`drawPaint(const SkPaint&)`**：用画笔填充整个画布。
- **`drawRect(const SkRect&, const SkPaint&)`**：绘制矩形。
- **`drawOval(const SkRect&, const SkPaint&)`**：绘制椭圆（转换为路径）。
- **`drawRRect(const SkRRect&, const SkPaint&)`**：绘制圆角矩形（转换为路径）。
- **`drawPath(const SkPath&, const SkPaint&)`**：绘制任意路径，支持路径效果、遮罩滤镜和各种填充规则。
- **`drawImageRect(...)`**：绘制图像矩形区域。
- **`drawPoints(...)`**、**`drawVertices(...)`**、**`drawMesh(...)`**：目前为占位实现（TODO）。
- **`drawDevice(...)`**：合并子设备画布（用于图层合成）。

### 设备创建

- **`createDevice(const CreateInfo&, const SkPaint*)`**：创建子设备用于图层操作，共享字体资源和 XPS 工厂。

## 内部实现细节

### 画笔创建策略

`createXpsBrush()` 按以下优先级选择画笔类型：
1. 无 Shader → 纯色画笔（`IXpsOMSolidColorBrush`）
2. ColorShader → 纯色画笔
3. 线性渐变 → `IXpsOMLinearGradientBrush`
4. 径向渐变 → `IXpsOMRadialGradientBrush`
5. 锥形/扫描渐变 → 目前未实现（TODO）
6. 图像着色器 → `IXpsOMImageBrush`，图像先编码为 PNG 再嵌入

### Clamp 模式的模拟

XPS 不原生支持 Clamp 平铺模式。实现通过创建一个 VisualBrush 画布来模拟：
- 中心区域使用原始图像
- 四边使用 1 像素宽的边缘条带（FlipXY 平铺）
- 四角使用边角像素的纯色填充
- 整个画布再作为 VisualBrush 使用

### 路径转换

`addXpsPathGeometry()` 遍历 SkPath 的所有动词（verb），将其映射到 XPS 线段类型：
- `kLine_Verb` → `XPS_SEGMENT_TYPE_LINE`
- `kQuad_Verb` → `XPS_SEGMENT_TYPE_QUADRATIC_BEZIER`
- `kCubic_Verb` → `XPS_SEGMENT_TYPE_BEZIER`
- `kConic_Verb` → 先用 `SkAutoConicToQuads` 转换为二次贝塞尔，再输出

### 字体管理与子集化

1. `CreateTypefaceUse()` 在字体首次使用时加载字体数据，创建 XPS 字体资源，并在 `fTopTypefaces` 数组中缓存。
2. 每个使用的字形 ID 通过 `SkBitSet` 记录。
3. `endPortfolio()` 时调用 `subset_typeface()`，使用 Windows 的 `CreateFontPackage` API 对字体进行子集化（仅保留使用的字形）。
4. 对 TTC 字体集合，子集化后重新构建 TTC 头部并修正表偏移。

### DPI 转换

XPS 固定使用 96 DPI。`endSheet()` 中计算缩放比例：`targetUnitsPerMeter = 96 * (10000/254)`，然后创建缩放画布将几何单位转换为物理单位。

### 逆填充规则处理

对于 `kInverseWinding` 和 `kInverseEvenOdd` 填充类型：
- `kInverseWinding` 先通过 `Simplify()` 转为等效路径
- 添加一个覆盖整个画布的矩形作为 EvenOdd 翻转图形

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| Windows XPS OM API | `IXpsOMObjectFactory`、`IXpsOMPackageWriter` 等 COM 接口 |
| `SkClipStackDevice` | 基类，提供裁剪栈管理 |
| `SkTScopedComPtr` | COM 指针 RAII 包装 |
| `SkIStream` / `SkWIStream` | SkStream 到 IStream 的适配 |
| `SkBitSet` | 位集合，用于跟踪使用的字形 |
| `SkSFNTHeader` / `SkTTCFHeader` | SFNT/TTC 字体头结构 |
| `CreateFontPackage` (T2EmbApi) | Windows 字体子集化 API |
| `SkPathOps` | 路径简化（Simplify） |
| `SkShaderBase` | 着色器基类（渐变信息提取） |
| `SkXPS::Options` | XPS 文档选项（PNG 编码器回调） |

## 设计模式与设计决策

1. **设备模式**：继承 `SkClipStackDevice`，实现 Skia 标准的设备虚函数接口，将绘图操作翻译到 XPS 格式。

2. **COM 资源管理**：使用 `SkTScopedComPtr` 对所有 COM 接口指针进行 RAII 管理，避免手动 `Release()` 导致的资源泄漏。

3. **字体共享**：通过 `fTopTypefaces` 指针使父子设备（图层）共享字体缓存，避免重复加载和子集化。

4. **延迟初始化**：`fPackageWriter` 在第一个页面 `endSheet()` 时创建，允许在初始化前生成缩略图。

5. **HRESULT 错误处理宏**：使用 `HRM`、`HRB`、`HRV`、`HRVM`、`HRBM` 等宏简化 COM HRESULT 检查和错误传播。

6. **GUID 资源命名**：使用 `CoCreateGuid()` 或确定性递增 ID（调试模式）为 XPS 资源生成唯一标识符。

## 性能考量

- **字体子集化延迟到 endPortfolio()**：避免重复子集化操作，一次性处理所有字体，减少开销。
- **PNG 编码开销**：图像画笔需要将位图编码为 PNG 再嵌入，对于频繁使用的图像存在显著编码开销。
- **Clamp 模拟复杂度**：Clamp 平铺模式需要创建额外的可视化画笔和路径，增加 XPS 文件大小和渲染复杂度。
- **路径到 XPS 转换**：每个路径段需要创建 COM 对象并通过 COM 调用添加，相比直接内存操作有 COM 调用开销。
- **Conic 到 Quad 转换**：圆锥曲线需要通过近似转换为二次贝塞尔曲线，引入精度/性能权衡。

## 相关文件

- `include/docs/SkXPSDocument.h` — XPS 文档创建的公共接口
- `src/utils/win/SkTScopedComPtr.h` — COM 指针 RAII 包装
- `src/utils/win/SkIStream.h` — SkStream 到 IStream 的适配
- `src/utils/win/SkHRESULT.h` — HRESULT 检查宏定义
- `src/utils/SkClipStackUtils.h` — 裁剪栈到路径的转换
- `src/sfnt/SkSFNTHeader.h` — SFNT 字体头结构
- `src/sfnt/SkTTCFHeader.h` — TTC 字体集合头结构
