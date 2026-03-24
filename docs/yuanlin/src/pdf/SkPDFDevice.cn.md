# SkPDFDevice — PDF 文档后端绘图设备

> 源文件：[src/pdf/SkPDFDevice.h](../../src/pdf/SkPDFDevice.h)、[src/pdf/SkPDFDevice.cpp](../../src/pdf/SkPDFDevice.cpp)

## 概述

`SkPDFDevice` 是 Skia 的 PDF 文档后端绘图设备，继承自 `SkClipStackDevice`。它将 Skia 的绘图操作转换为 PDF 内容流（content stream），是 Skia PDF 生成管线的核心组件。

核心功能包括：
- 将 Skia 绘图基元（路径、矩形、椭圆、圆角矩形、图像、文字）转换为 PDF 操作符
- 管理 PDF 图形状态栈（变换矩阵、裁剪、画笔属性）
- 生成 PDF 资源字典（ExtGState、Pattern、XObject、Font）
- 处理混合模式（Blend Mode）通过 Form XObject 和 SMask
- 支持 PDF 标记内容（Marked Content）用于结构化/可访问 PDF
- 遮罩滤镜支持（光栅化路径为灰度蒙版）
- 注解支持（链接、命名目标等）
- 字形渲染（原生 PDF 文字或路径回退）

## 架构位置

```
SkCanvas → SkPDFDevice (final, SkClipStackDevice)
              │
              ├── SkPDFGraphicStackState (PDF 图形状态管理)
              ├── MarkedContentManager (PDF 标记内容 / 可访问性)
              ├── SkPDFDocument (文档级资源去重和序列化)
              ├── SkPDFFont (字体子集化和嵌入)
              ├── SkPDFShader (着色器到 PDF Pattern 转换)
              ├── SkPDFGraphicState (ExtGState 管理)
              └── SkPDFBitmap (图像嵌入)
```

## 主要类与结构体

### `SkPDFDevice`

| 成员 | 类型 | 说明 |
|------|------|------|
| `fInitialTransform` | `SkMatrix` | 页面初始变换矩阵 |
| `fGraphicStateResources` | `THashSet<SkPDFIndirectReference>` | ExtGState 资源引用集 |
| `fXObjectResources` | `THashSet<SkPDFIndirectReference>` | XObject 资源引用集 |
| `fShaderResources` | `THashSet<SkPDFIndirectReference>` | Pattern/Shader 资源引用集 |
| `fFontResources` | `THashSet<SkPDFIndirectReference>` | Font 资源引用集 |
| `fContent` | `SkDynamicMemoryWStream` | 主内容流 |
| `fContentBuffer` | `SkDynamicMemoryWStream` | 临时内容缓冲区 |
| `fActiveStackState` | `SkPDFGraphicStackState` | 当前图形状态栈 |
| `fDocument` | `SkPDFDocument*` | 父文档（用于资源去重） |
| `fMarkManager` | `MarkedContentManager` | 标记内容管理器 |

### `MarkedContentManager`（内部类）

管理 PDF 标记内容序列（BMC/BDC/EMC），支持结构化 PDF（PDF/UA 可访问性）。跟踪当前活动标记的元素 ID 和 MCID，支持 Artifact 标记类型（Pagination、Layout、Page、Background）。

## 公共 API 函数

### 绘图方法

- **`drawPaint/drawRect/drawOval/drawRRect/drawPath`**：标准几何绘制，转换为 PDF 路径操作符。
- **`drawImageRect`**：图像绘制，通过 `SkPDFBitmap` 嵌入图像。
- **`drawAnnotation`**：PDF 注解（链接、目标等）。
- **`drawVertices/drawMesh`**：目前为空实现。

### PDF 特有方法

- **`makeResourceDict()`**：创建页面资源字典。破坏性操作。
- **`content()`**：返回页面内容流。
- **`initialTransform()`**：获取页面初始变换。
- **`structParentsKey()`**：获取结构树 StructParents 键。

## 内部实现细节

### 内容条目管理

通过 `ScopedContentEntry` RAII 类管理图形状态：
1. `setUpContentEntry()` 检查裁剪和画笔是否有效，设置图形状态
2. 绘图操作写入内容流
3. `finishContentEntry()` 处理非标准混合模式（通过 Form XObject + SMask 组合）

### 混合模式处理

非简单混合模式需要：
1. 将当前内容捕获为 Form XObject
2. 将新绘制捕获为另一个 Form XObject
3. 使用 SMask 和适当的混合模式组合两者

### 遮罩滤镜

`internalDrawPathWithFilter()` 将带遮罩滤镜的路径光栅化为灰度图像，再作为 opacity mask 应用。支持 JPEG 压缩遮罩（通过文档配置的 JPEG 编码器）。

### 文字渲染

`internalDrawGlyphRun()` 优先使用 PDF 原生文字操作符（Tj/TJ），通过 `SkClusterator` 处理 Unicode 集群映射。不支持的字形回退到路径渲染（`drawGlyphRunAsPath()`）。

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `SkClipStackDevice` | 基类 |
| `SkPDFDocument` | 文档级资源管理和去重 |
| `SkPDFGraphicStackState` | PDF 图形状态栈管理 |
| `SkPDFFont` | 字体子集化和嵌入 |
| `SkPDFShader` | 着色器转 PDF Pattern |
| `SkPDFGraphicState` | ExtGState 字典生成 |
| `SkPDFBitmap` | 图像嵌入 |
| `SkPDFResourceDict` | 资源字典构建 |
| `SkPDFTag` / `SkPDFStructTree` | 结构化标记和可访问性 |
| `SkPathOps` | 路径布尔运算（逆路径处理） |

## 设计模式与设计决策

1. **ScopedContentEntry**：RAII 模式管理绘图上下文的建立和清理，确保图形状态的正确匹配。

2. **文档级去重**：所有资源（图像、字体、图形状态、着色器）通过 `SkPDFDocument` 在页面间去重，减小文件大小。

3. **标记内容管理**：`MarkedContentManager` 自动管理 BMC/BDC/EMC 标记序列，支持 PDF/UA 可访问性标准。

4. **混合模式分层**：非标准混合模式通过 Form XObject 和 SMask 的组合实现，虽然增加了文件大小，但确保了 PDF 规范兼容性。

5. **坐标系翻转**：PDF 使用 y-up 坐标系，通过初始变换矩阵完成与 Skia 的 y-down 坐标系的转换。

## 性能考量

- **流式输出**：内容直接写入 `SkDynamicMemoryWStream`，避免构建中间数据结构。
- **资源去重**：跨页面的图像和字体去重显著减小文件大小。
- **JPEG 遮罩压缩**：灰度遮罩图像可选 JPEG 压缩，大幅减小遮罩数据量。
- **路径效果预处理**：路径效果在设备层应用后直接输出，避免重复计算。
- **裁剪优化**：空裁剪时跳过绘制操作。

## 相关文件

- `src/pdf/SkPDFDocumentPriv.h` — PDF 文档私有实现
- `src/pdf/SkPDFGraphicStackState.h` — 图形状态栈
- `src/pdf/SkPDFFont.h` — PDF 字体处理
- `src/pdf/SkPDFShader.h` — PDF 着色器
- `src/pdf/SkPDFBitmap.h` — PDF 图像嵌入
- `src/pdf/SkPDFResourceDict.h` — PDF 资源字典
- `src/pdf/SkPDFTag.h` — PDF 结构标记
- `src/pdf/SkPDFUtils.h` — PDF 工具函数
