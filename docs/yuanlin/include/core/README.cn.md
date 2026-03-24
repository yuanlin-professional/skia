# include/core - Skia 核心公共 API

## 概述

`include/core` 是 Skia 2D 图形库最核心的公共头文件目录，包含约 95 个头文件，定义了 Skia 所有基础绘图能力的公共接口。这些头文件构成了 Skia 的"骨架"，无论底层渲染后端是 CPU 光栅化、GPU（Vulkan/OpenGL/Metal/Direct3D）还是文档输出（PDF/SVG），上层应用都通过此目录中的类和函数与 Skia 交互。

此目录的设计遵循"接口与实现分离"的原则：所有公共 API 集中在 `include/core` 中，而具体的实现代码分布在 `src/core`、`src/gpu`、`src/pdf` 等目录中。开发者只需引用 `include/core` 中的头文件即可使用 Skia 的全部核心功能，无需关心底层渲染细节。

核心 API 围绕几个关键抽象展开：**SkCanvas** 作为绘图操作的统一入口，**SkPaint** 控制绘图样式与效果，**SkPath** 描述矢量几何形状，**SkImage** 和 **SkSurface** 管理像素数据的读取与写入，**SkMatrix/SkM44** 处理二维与三维变换。这些类通过引用计数（`SkRefCnt`/`sk_sp`）和不可变对象模式实现高效的内存管理和线程安全共享。

该目录还包含完整的颜色管理系统（`SkColorSpace`、`SkColorType`、`SkAlphaType`）、文本排版系统（`SkFont`、`SkTypeface`、`SkTextBlob`）、流式 I/O 抽象（`SkStream`、`SkData`）以及滤镜管线（`SkShader`、`SkColorFilter`、`SkImageFilter`、`SkMaskFilter`、`SkPathEffect`）。所有这些子系统通过 `SkPaint` 汇聚到 `SkCanvas` 的绘制调用中，形成一个完整而灵活的 2D 图形管线。

## 架构图

```
+=========================================================================+
|                         应用层 (Application)                              |
+=========================================================================+
                                    |
                                    v
+=========================================================================+
|                     SkCanvas (绘图操作统一入口)                             |
|  +---------------------------------------------------------------+      |
|  | drawRect / drawPath / drawImage / drawTextBlob / drawVertices |      |
|  | drawArc / drawRRect / drawPicture / drawDrawable / drawMesh   |      |
|  +---------------------------------------------------------------+      |
|  |       save / restore / saveLayer (状态栈管理)                   |      |
|  |       clipRect / clipPath / clipRegion (裁剪)                  |      |
|  |       concat / setMatrix / translate / scale / rotate (变换)   |      |
|  +---------------------------------------------------------------+      |
+=========================================================================+
          |                    |                      |
          v                    v                      v
+------------------+  +------------------+  +--------------------+
|    SkPaint       |  |   SkMatrix/SkM44 |  | SkRegion/SkClipOp  |
| (绘图样式与效果)  |  | (2D/3D 几何变换)  |  | (裁剪区域)          |
+------------------+  +------------------+  +--------------------+
    |    |    |    |
    v    v    v    v
+------+ +--------+ +-----------+ +-------------+ +----------+
|Shader| |ColorFlt| |ImageFilter| |MaskFilter   | |PathEffect|
|着色器 | |颜色滤镜 | |图像滤镜    | |遮罩滤镜     | |路径效果   |
+------+ +--------+ +-----------+ +-------------+ +----------+
          |                              |
          v                              v
+------------------+          +--------------------+
|  SkColorSpace    |          |    SkBlendMode     |
|  (色彩空间管理)   |          |   (混合模式)        |
+------------------+          +--------------------+

+=========================================================================+
|                       几何与图像数据层                                     |
|  +----------+ +--------+ +--------+ +----------+ +---------+ +--------+ |
|  | SkPath   | |SkImage | |SkBitmap| | SkPixmap | |SkPicture| |SkVertices|
|  | 矢量路径  | |不可变图 | |可变像素| | 像素视图  | |绘制录制  | |顶点数据 | |
|  +----------+ +--------+ +--------+ +----------+ +---------+ +--------+ |
|  +----------+ +-----------+ +----------+ +-----------+ +--------+       |
|  |SkPathBld | |SkTextBlob  | |SkDrawable| |SkMesh     | |SkRRect |       |
|  |路径构建器 | |文本块       | |可绘制对象 | |自定义网格  | |圆角矩形 |       |
|  +----------+ +-----------+ +----------+ +-----------+ +--------+       |
+=========================================================================+
                                    |
                                    v
+=========================================================================+
|                      SkSurface (渲染目标)                                 |
|         SkSurfaces::Raster (CPU)  |  GPU Surface (Vulkan/GL/Metal)       |
+=========================================================================+
```

## 目录结构

按功能模块对 95 个头文件进行分类：

### 核心绘图引擎
| 文件 | 说明 |
|------|------|
| `SkCanvas.h` | 绘图操作核心接口，管理变换矩阵栈和裁剪栈，提供所有 draw 方法 |
| `SkPaint.h` | 绘图样式控制：颜色、描边/填充模式、抗锯齿及各类滤镜效果聚合器 |
| `SkSurface.h` | 渲染目标抽象，通过 `SkSurfaces` 命名空间创建 CPU 或 GPU 画布 |
| `SkSurfaceProps.h` | 渲染目标属性：LCD 亚像素方向、设备无关字体设置 |
| `SkOverdrawCanvas.h` | 调试用画布，统计每个像素的过度绘制次数 |
| `SkCanvasVirtualEnforcer.h` | 画布虚函数强制实现基类，确保子类实现所有绘图方法 |
| `SkRecorder.h` | 录制画布，用于记录绘制操作 |
| `SkCapabilities.h` | 查询后端渲染能力（如支持的 SkSL 版本） |

### 几何与路径
| 文件 | 说明 |
|------|------|
| `SkPath.h` | 矢量路径：包含移动、直线、二次/三次贝塞尔曲线、圆锥曲线等指令 |
| `SkPathBuilder.h` | 路径构建器：通过 Builder 模式逐步构造 SkPath |
| `SkPathTypes.h` | 路径相关枚举：FillType（奇偶/非零缠绕）、Direction、Verb 等 |
| `SkPathIter.h` | 路径迭代器接口，用于遍历路径中的各段几何指令 |
| `SkPathEffect.h` | 路径效果基类：虚线、圆角等变换在绘制前应用于路径几何 |
| `SkPathMeasure.h` | 路径测量：计算路径长度、沿路径取点和切线 |
| `SkPathUtils.h` | 路径工具函数 |
| `SkContourMeasure.h` | 轮廓测量：对单条轮廓进行长度、位置、切线计算 |
| `SkStrokeRec.h` | 描边记录：存储描边宽度、连接方式、端点样式等信息 |
| `SkRect.h` | 矩形：SkRect（浮点）和 SkIRect（整数），Skia 最基础的几何图元 |
| `SkRRect.h` | 圆角矩形：支持四角独立圆角半径 |
| `SkPoint.h` | 二维点/向量：SkPoint（浮点）和 SkIPoint（整数） |
| `SkPoint3.h` | 三维点 SkPoint3 |
| `SkSize.h` | 尺寸：SkSize（浮点）和 SkISize（整数） |
| `SkArc.h` | 弧形定义：椭圆弧的参数化表示 |
| `SkRegion.h` | 整数区域：用游程编码表示的矩形并集，用于裁剪 |
| `SkRSXform.h` | 旋转+缩放+平移变换（用于 drawAtlas） |

### 变换矩阵
| 文件 | 说明 |
|------|------|
| `SkMatrix.h` | 3x3 变换矩阵：平移、缩放、旋转、倾斜、透视 |
| `SkM44.h` | 4x4 矩阵及 SkV2/SkV3/SkV4 向量类型，支持三维变换 |
| `SkScalar.h` | 标量类型定义（`float`）及相关数学工具宏 |

### 图像与像素
| 文件 | 说明 |
|------|------|
| `SkImage.h` | 不可变图像：CPU 或 GPU 纹理支持，延迟解码，通过 `SkImages` 命名空间创建 |
| `SkBitmap.h` | 可变像素容器：包装 SkPixelRef，可作为绘制源和绘制目标 |
| `SkPixmap.h` | 轻量像素视图：将 SkImageInfo 与像素指针和行字节数配对 |
| `SkPixelRef.h` | 像素引用：管理像素内存生命周期，线程安全 |
| `SkMallocPixelRef.h` | 基于 malloc 的 SkPixelRef 实现 |
| `SkImageGenerator.h` | 图像生成器：延迟产生像素数据的抽象接口 |
| `SkImageInfo.h` | 图像描述信息：宽高 + SkColorType + SkAlphaType + SkColorSpace |
| `SkTiledImageUtils.h` | 分块图像绘制工具 |
| `SkSamplingOptions.h` | 图像采样选项：最近邻、双线性、双三次、各向异性过滤 |
| `SkSwizzle.h` | 像素分量交换工具函数 |
| `SkUnPreMultiply.h` | 预乘 Alpha 逆变换工具 |
| `SkYUVAInfo.h` | YUV 平面布局信息 |
| `SkYUVAPixmaps.h` | YUV 多平面像素容器 |
| `SkTextureCompressionType.h` | 纹理压缩格式枚举（ETC1、BC1 等） |

### 颜色与色彩管理
| 文件 | 说明 |
|------|------|
| `SkColor.h` | 颜色类型：SkColor（32 位 ARGB）、SkColor4f（浮点 RGBA）、SkPMColor |
| `SkColorType.h` | 像素颜色格式枚举：RGBA_8888、BGRA_8888、RGB_565、RGBA_F16 等 |
| `SkAlphaType.h` | Alpha 类型枚举：Opaque、Premul、Unpremul |
| `SkColorSpace.h` | 色彩空间：sRGB、Display P3、BT.2020 等，基于 ICC 色彩配置 |
| `SkColorTable.h` | 颜色查找表 |
| `SkColorFilter.h` | 颜色滤镜基类：颜色矩阵、混合模式颜色等逐像素颜色变换 |
| `SkBlendMode.h` | 29 种混合模式枚举：Porter-Duff 合成和高级混合（叠加、正片叠底等） |
| `SkBlender.h` | 自定义混合器基类，支持 SkSL 运行时混合 |
| `SkCoverageMode.h` | 覆盖率合并模式 |

### 着色器与滤镜管线
| 文件 | 说明 |
|------|------|
| `SkShader.h` | 着色器基类：定义绘制时的源颜色，支持图像平铺、渐变等 |
| `SkImageFilter.h` | 图像滤镜基类：模糊、阴影、位移等在离屏缓冲上操作的后处理效果 |
| `SkMaskFilter.h` | 遮罩滤镜基类：在 Alpha 遮罩上操作（如高斯模糊） |
| `SkBlurTypes.h` | 模糊样式枚举：Normal、Solid、Outer、Inner |
| `SkTileMode.h` | 平铺模式枚举：Clamp（钳制）、Repeat（重复）、Mirror（镜像）、Decal（贴花） |

### 文本排版
| 文件 | 说明 |
|------|------|
| `SkFont.h` | 字体控制：字号、字体微调（hinting）、抗锯齿模式、缩放/倾斜等 |
| `SkTypeface.h` | 字体面：描述字体文件和内在样式（粗细、斜体），不可变且线程安全 |
| `SkFontStyle.h` | 字体样式：权重（weight）、宽度（width）、斜度（slant） |
| `SkFontMgr.h` | 字体管理器：枚举和匹配系统字体 |
| `SkFontMetrics.h` | 字体度量信息：上升线、下降线、行距等 |
| `SkFontArguments.h` | 字体实例化参数：可变字体轴、调色板等 |
| `SkFontParameters.h` | 字体参数定义 |
| `SkFontScanner.h` | 字体扫描器接口 |
| `SkFontTypes.h` | 文本编码枚举（UTF-8、UTF-16、UTF-32、GlyphID） |
| `SkTextBlob.h` | 不可变文本块：组合多个文本运行（run），每个 run 包含字形、位置和字体 |

### 录制与回放
| 文件 | 说明 |
|------|------|
| `SkPicture.h` | 绘制命令录制：记录 SkCanvas 的全部绘制操作，可回放或序列化 |
| `SkPictureRecorder.h` | 录制控制器：开始录制返回 SkCanvas，结束后生成 SkPicture |
| `SkDrawable.h` | 可绘制对象基类：支持 generation ID 的自定义绘制内容 |
| `SkDocument.h` | 多页文档基类：PDF 和 XPS 文档输出的统一接口 |

### 数据与 I/O
| 文件 | 说明 |
|------|------|
| `SkData.h` | 不可变数据容器：引用计数的字节缓冲区 |
| `SkDataTable.h` | 数据表：按行索引的异构数据集合 |
| `SkStream.h` | 流式 I/O 抽象：SkStream（读）和 SkWStream（写），支持内存/文件后端 |
| `SkString.h` | 字符串类：轻量级 UTF-8 字符串 |
| `SkSpan.h` | 非拥有的连续内存视图（类似 std::span） |

### 序列化
| 文件 | 说明 |
|------|------|
| `SkFlattenable.h` | 可序列化基类：所有可写入数据流的对象的基类 |
| `SkSerialProcs.h` | 自定义序列化/反序列化钩子 |
| `SkAnnotation.h` | 注解：为绘制内容添加元数据（如 PDF 链接） |

### 引用计数与内存
| 文件 | 说明 |
|------|------|
| `SkRefCnt.h` | 引用计数基类 `SkRefCntBase` 和智能指针 `sk_sp<T>` |

### 高级与网格
| 文件 | 说明 |
|------|------|
| `SkVertices.h` | 顶点数据：三角形/三角扇/三角带网格 |
| `SkMesh.h` | 自定义网格：支持 SkSL 顶点/片段程序的可编程网格绘制 |
| `SkCubicMap.h` | 三次贝塞尔映射函数 |

### 后端上下文
| 文件 | 说明 |
|------|------|
| `SkCPUContext.h` | CPU 渲染上下文 |
| `SkCPURecorder.h` | CPU 录制器 |
| `SkRasterHandleAllocator.h` | 光栅句柄分配器 |

### 全局与杂项
| 文件 | 说明 |
|------|------|
| `SkTypes.h` | 全局基础类型与宏定义（SK_API、SkASSERT 等） |
| `SkGraphics.h` | Skia 全局初始化与资源控制（字体缓存大小等） |
| `SkMilestone.h` | Skia 版本号里程碑 |
| `SkClipOp.h` | 裁剪操作枚举：Intersect（交集）和 Difference（差集） |
| `SkFourByteTag.h` | 四字节标签（如 OpenType 表标签） |
| `SkExecutor.h` | 线程执行器接口 |
| `SkTraceMemoryDump.h` | 内存跟踪转储接口 |
| `SkBBHFactory.h` | 边界框层次结构工厂（加速 SkPicture 回放） |
| `SkOpenTypeSVGDecoder.h` | OpenType SVG 字形解码器 |

## 关键类与函数

### SkCanvas - 绘图操作核心

```cpp
// 文件: include/core/SkCanvas.h
class SK_API SkCanvas {
public:
    // === 创建方式 ===
    static std::unique_ptr<SkCanvas> MakeRasterDirect(
        const SkImageInfo& info, void* pixels, size_t rowBytes,
        const SkSurfaceProps* props = nullptr);
    explicit SkCanvas(const SkBitmap& bitmap);

    // === 绘制基本图元 ===
    void drawColor(SkColor color, SkBlendMode mode = SkBlendMode::kSrcOver);
    void drawPaint(const SkPaint& paint);
    void drawRect(const SkRect& rect, const SkPaint& paint);
    void drawRRect(const SkRRect& rrect, const SkPaint& paint);
    void drawOval(const SkRect& oval, const SkPaint& paint);
    void drawCircle(SkScalar cx, SkScalar cy, SkScalar radius, const SkPaint& paint);
    void drawArc(const SkArc& arc, const SkPaint& paint);
    void drawPath(const SkPath& path, const SkPaint& paint);
    void drawLine(SkScalar x0, SkScalar y0, SkScalar x1, SkScalar y1, const SkPaint& paint);
    void drawPoints(PointMode mode, size_t count, const SkPoint pts[], const SkPaint& paint);

    // === 图像绘制 ===
    void drawImage(const SkImage* image, SkScalar left, SkScalar top,
                   const SkSamplingOptions&, const SkPaint* paint = nullptr);
    void drawImageRect(const SkImage*, const SkRect& src, const SkRect& dst,
                       const SkSamplingOptions&, const SkPaint*, SrcRectConstraint);

    // === 文本绘制 ===
    void drawTextBlob(const SkTextBlob* blob, SkScalar x, SkScalar y, const SkPaint& paint);

    // === 高级绘制 ===
    void drawVertices(const sk_sp<SkVertices>& vertices, SkBlendMode mode, const SkPaint& paint);
    void drawMesh(const SkMesh& mesh, sk_sp<SkBlender> blender, const SkPaint& paint);
    void drawPicture(const SkPicture* picture);
    void drawDrawable(SkDrawable* drawable, const SkMatrix* matrix = nullptr);

    // === 状态管理（栈式） ===
    int save();
    int saveLayer(const SkRect* bounds, const SkPaint* paint);
    void restore();

    // === 变换 ===
    void translate(SkScalar dx, SkScalar dy);
    void scale(SkScalar sx, SkScalar sy);
    void rotate(SkScalar degrees);
    void concat(const SkMatrix& matrix);
    void concat(const SkM44& matrix);

    // === 裁剪 ===
    void clipRect(const SkRect& rect, SkClipOp op, bool doAntiAlias);
    void clipPath(const SkPath& path, SkClipOp op, bool doAntiAlias);
    void clipRegion(const SkRegion& deviceRgn, SkClipOp op = SkClipOp::kIntersect);
};
```

`SkCanvas` 是 Skia 的"绘图入口"。它管理一个变换矩阵和裁剪区域的栈。每次调用 `save()` 会将当前状态压栈，`restore()` 弹栈恢复。所有绘制操作都会经过当前矩阵变换和裁剪区域裁剪后再传递给底层设备。

### SkPaint - 绘图样式聚合

```cpp
// 文件: include/core/SkPaint.h
class SK_API SkPaint {
public:
    SkPaint();
    explicit SkPaint(const SkColor4f& color, SkColorSpace* colorSpace = nullptr);

    // 样式
    enum Style { kFill_Style, kStroke_Style, kStrokeAndFill_Style };
    Style getStyle() const;
    void setStyle(Style style);

    // 颜色
    void setColor(SkColor color);
    void setColor4f(const SkColor4f& color, SkColorSpace* colorSpace = nullptr);
    void setAlphaf(float alpha);

    // 描边属性
    void setStrokeWidth(SkScalar width);
    void setStrokeCap(SkPaint::Cap cap);
    void setStrokeJoin(SkPaint::Join join);
    void setStrokeMiter(SkScalar miter);

    // 抗锯齿
    void setAntiAlias(bool aa);
    void setDither(bool dither);

    // 滤镜管线
    void setShader(sk_sp<SkShader> shader);
    void setColorFilter(sk_sp<SkColorFilter> colorFilter);
    void setImageFilter(sk_sp<SkImageFilter> imageFilter);
    void setMaskFilter(sk_sp<SkMaskFilter> maskFilter);
    void setPathEffect(sk_sp<SkPathEffect> pathEffect);
    void setBlender(sk_sp<SkBlender> blender);
    void setBlendMode(SkBlendMode mode);
};
```

`SkPaint` 集中管理了所有影响绘制外观的属性。它不直接实现效果，而是持有各种效果对象的智能指针引用。通过 `sk_sp` 的引用计数，多个 `SkPaint` 实例可以安全地共享相同的着色器、滤镜等对象。

### SkPath - 矢量路径

```cpp
// 文件: include/core/SkPath.h
class SK_API SkPath {
public:
    // 快捷工厂方法
    static SkPath Rect(const SkRect&, SkPathDirection = SkPathDirection::kDefault);
    static SkPath Oval(const SkRect&, SkPathDirection = SkPathDirection::kDefault);
    static SkPath Circle(SkScalar cx, SkScalar cy, SkScalar radius, SkPathDirection dir);
    static SkPath RRect(const SkRRect&, SkPathDirection dir = SkPathDirection::kDefault);
    static SkPath Line(SkPoint a, SkPoint b);
    static SkPath Polygon(SkSpan<const SkPoint> pts, bool isClosed, SkPathFillType fillType);

    // 填充规则
    SkPathFillType getFillType() const;  // kWinding, kEvenOdd, kInverseWinding, kInverseEvenOdd
    void setFillType(SkPathFillType ft);

    // 几何查询
    const SkRect& getBounds() const;
    bool isEmpty() const;
    bool isConvex() const;
    bool contains(SkScalar x, SkScalar y) const;

    // 变换
    SkPath makeTransform(const SkMatrix& m) const;
    void transform(const SkMatrix& matrix);
};
```

`SkPath` 采用"写时复制"（Copy-on-Write）语义和惰性计算策略。边界框和凸性在首次查询时才计算并缓存。通过 `SkPathBuilder` 可以更高效地分步构造路径。

### SkImage 与 SkSurface - 图像读写

```cpp
// 文件: include/core/SkImage.h
namespace SkImages {
    // 从位图创建（共享或复制像素）
    sk_sp<SkImage> RasterFromBitmap(const SkBitmap& bitmap);
    // 从编码数据延迟解码
    sk_sp<SkImage> DeferredFromEncodedData(sk_sp<const SkData> encoded);
    // 从像素数据创建
    sk_sp<SkImage> RasterFromData(const SkImageInfo&, sk_sp<SkData>, size_t rowBytes);
    // 从图像生成器延迟创建
    sk_sp<SkImage> DeferredFromGenerator(std::unique_ptr<SkImageGenerator>);
}

// 文件: include/core/SkSurface.h
namespace SkSurfaces {
    // CPU 光栅化表面
    sk_sp<SkSurface> Raster(const SkImageInfo& imageInfo, size_t rowBytes,
                            const SkSurfaceProps* surfaceProps);
    // 包装已有像素
    sk_sp<SkSurface> WrapPixels(const SkImageInfo&, void* pixels, size_t rowBytes,
                                const SkSurfaceProps* = nullptr);
    // 空画布（无像素）
    sk_sp<SkSurface> Null(int width, int height);
}
```

`SkImage` 代表不可变图像（适合读取、缓存），`SkSurface` 代表可绘制目标（适合写入）。通过 `SkSurface::getCanvas()` 获取画布进行绘制，通过 `SkSurface::makeImageSnapshot()` 获取绘制结果的 SkImage 快照。

### sk_sp 与 SkRefCnt - 引用计数内存管理

```cpp
// 文件: include/core/SkRefCnt.h
class SK_API SkRefCntBase {
public:
    SkRefCntBase() : fRefCnt(1) {}
    bool unique() const;
    void ref() const;    // 原子增加引用计数
    void unref() const;  // 原子减少引用计数，计数归零时删除对象
};

// 智能指针 sk_sp<T> 类似 std::shared_ptr，但更轻量
template <typename T> class sk_sp {
public:
    sk_sp(T* obj);         // 接管所有权（不增加引用计数）
    sk_sp(const sk_sp&);   // 复制（增加引用计数）
    sk_sp(sk_sp&&);        // 移动（不改变引用计数）
    ~sk_sp();              // 释放时 unref
    T* get() const;
    T* operator->() const;
};
```

## 依赖关系

### 内部依赖层次

```
SkTypes.h, SkScalar.h, SkPoint.h, SkRect.h       (第0层: 基础类型)
    |
    v
SkRefCnt.h, SkSpan.h, SkColor.h, SkSize.h        (第1层: 基础设施)
    |
    v
SkMatrix.h, SkColorType.h, SkAlphaType.h          (第2层: 几何与颜色类型)
    |
    v
SkColorSpace.h, SkImageInfo.h                      (第3层: 色彩空间与图像描述)
    |
    v
SkFlattenable.h, SkData.h, SkPixmap.h             (第4层: 序列化与像素容器)
    |
    v
SkShader.h, SkColorFilter.h, SkPathEffect.h       (第5层: 效果对象)
SkMaskFilter.h, SkImageFilter.h, SkBlender.h
    |
    v
SkPaint.h, SkPath.h, SkFont.h, SkImage.h          (第6层: 绘制参数与数据)
    |
    v
SkCanvas.h, SkSurface.h, SkPicture.h              (第7层: 绘制入口与目标)
```

### 外部依赖

- **C++ 标准库**: `<cstdint>`, `<cstddef>`, `<memory>`, `<atomic>`, `<optional>`, `<vector>` 等
- **skcms**: 色彩管理模块（`modules/skcms/skcms.h`），被 `SkColorSpace.h` 使用
- **include/private/base**: 内部基础设施（`SkDebug.h`, `SkFloatingPoint.h`, `SkTArray.h`, `SkOnce.h` 等）
- **include/effects/SkRuntimeEffect.h**: 被 `SkMesh.h` 使用，提供 SkSL 运行时效果支持

## 设计模式分析

### 1. 工厂方法模式（Factory Method）

Skia 大量使用命名空间级别的工厂函数替代传统构造函数：

```cpp
// SkImages 命名空间工厂方法
sk_sp<SkImage> SkImages::RasterFromBitmap(const SkBitmap&);
sk_sp<SkImage> SkImages::DeferredFromEncodedData(sk_sp<const SkData>);

// SkSurfaces 命名空间工厂方法
sk_sp<SkSurface> SkSurfaces::Raster(const SkImageInfo&, ...);
sk_sp<SkSurface> SkSurfaces::WrapPixels(const SkImageInfo&, void*, ...);

// SkPath 静态工厂方法
SkPath SkPath::Rect(const SkRect&, ...);
SkPath SkPath::Circle(SkScalar cx, SkScalar cy, SkScalar radius, ...);
```

这种模式使得创建过程语义明确，同时支持返回 `nullptr` 表示创建失败。

### 2. 策略模式（Strategy）

`SkPaint` 通过组合多种策略对象来定义绘制行为：

```cpp
paint.setShader(shader);           // 着色策略
paint.setColorFilter(colorFilter); // 颜色变换策略
paint.setImageFilter(imageFilter); // 后处理策略
paint.setMaskFilter(maskFilter);   // 遮罩变换策略
paint.setPathEffect(pathEffect);   // 几何变换策略
paint.setBlender(blender);         // 混合策略
```

每种策略都有多种具体实现，可自由组合。

### 3. 不可变对象模式（Immutable Object）

多个核心类型在创建后不可修改，确保线程安全：

- **SkImage**: 一旦创建，像素数据不可更改
- **SkPicture**: 录制完成后命令流不可修改
- **SkTextBlob**: 文本运行序列不可变
- **SkTypeface**: 字体面属性不可变
- **SkData**: 字节缓冲区不可变
- **SkVertices**: 顶点数据不可变

### 4. Builder 模式

复杂对象通过专用 Builder 分步构造：

```cpp
// SkPathBuilder 分步构造路径
SkPathBuilder builder;
builder.moveTo(0, 0).lineTo(100, 0).lineTo(100, 100).close();
SkPath path = builder.detach();

// SkTextBlobBuilder 分步构造文本块
SkTextBlobBuilder blobBuilder;
auto run = blobBuilder.allocRun(font, glyphCount, x, y);
// ... 填充 run 数据
sk_sp<SkTextBlob> blob = blobBuilder.make();

// SkVertices::Builder 构造网格数据
SkVertices::Builder vBuilder(SkVertices::kTriangles_VertexMode, vertexCount, indexCount, flags);
```

### 5. 装饰器模式（Decorator）

滤镜对象支持链式组合：

```cpp
// 颜色滤镜组合
auto composed = outerFilter->makeComposed(innerFilter);
// 等价于: result = outer(inner(color))

// 路径效果组合
auto composed = SkPathEffect::MakeCompose(outer, inner);
// 等价于: result = outer(inner(path))

// 着色器添加颜色滤镜
auto newShader = shader->makeWithColorFilter(filter);
```

### 6. 命令模式（Command）

`SkPicture` 和 `SkPictureRecorder` 实现了经典的命令录制与回放：

```cpp
SkPictureRecorder recorder;
SkCanvas* canvas = recorder.beginRecording(bounds);
canvas->drawRect(rect, paint);     // 命令被录制而非立即执行
canvas->drawPath(path, paint);
sk_sp<SkPicture> picture = recorder.finishRecordingAsPicture();

// 在任意画布上回放
anyCanvas->drawPicture(picture);
```

### 7. 写时复制（Copy-on-Write）

`SkPath` 和 `SkBitmap` 等值类型使用写时复制优化：

```cpp
SkPath path1 = SkPath::Circle(0, 0, 100);
SkPath path2 = path1;  // 共享内部数据，不复制
path2.setFillType(SkPathFillType::kEvenOdd);  // 此时才真正复制数据
```

## 数据流

### 典型绘制流程

```
1. 准备阶段
   SkImageInfo ──> SkSurfaces::Raster() ──> sk_sp<SkSurface>
                                                    |
                                            surface->getCanvas()
                                                    |
                                                    v
2. 绘制阶段                                     SkCanvas
   SkPaint.setShader(gradient)                     |
   SkPaint.setAntiAlias(true)        canvas->drawPath(path, paint)
   SkPaint.setStrokeWidth(2.0f)                    |
                                                   v
3. 管线处理
   几何数据(SkPath) ──> PathEffect变换 ──> Matrix变换 ──> Clip裁剪
                                                          |
   颜色数据(SkShader) ──> ColorFilter ──> BlendMode/Blender ──> 像素输出
                                                          |
   Alpha(SkMaskFilter) ──> ImageFilter(离屏处理) ─────────┘
                                                          |
                                                          v
4. 输出阶段
   SkSurface ──> makeImageSnapshot() ──> sk_sp<SkImage> (不可变结果)
              ──> readPixels() ──> SkPixmap/SkBitmap (像素访问)
```

### 图像创建与消费流程

```
编码数据 (PNG/JPEG/WebP)
    |
    v
SkImages::DeferredFromEncodedData()  ──> sk_sp<SkImage> (延迟解码)
                                              |
                                    canvas->drawImage(image, ...)
                                              |
                                              v
                                    首次绘制时触发解码 ──> 像素缓存
                                              |
                                              v
                                    GPU: 上传为纹理  /  CPU: 光栅化

SkBitmap (可变像素)
    |
    v
SkImages::RasterFromBitmap()  ──> sk_sp<SkImage> (若 immutable 则共享像素)
```

### 文本绘制流程

```
字体文件 ──> SkFontMgr::matchFamily() ──> sk_sp<SkTypeface>
                                               |
                                          SkFont(typeface, size)
                                               |
                                    SkTextBlobBuilder.allocRun(font, ...)
                                               |
                                          sk_sp<SkTextBlob>
                                               |
                                    canvas->drawTextBlob(blob, x, y, paint)
                                               |
                                               v
                                    字形光栅化 + 缓存 ──> 像素输出
```

## 相关文档与参考

### 官方资源
- **Skia 官网**: https://skia.org
- **API 参考**: https://skia.org/docs/user/api/
- **Fiddle 在线沙盒**: https://fiddle.skia.org - 可在线运行 Skia 代码片段
- **源码浏览**: https://source.chromium.org/chromium/chromium/src/+/main:third_party/skia/

### 相关源码目录
| 目录 | 说明 |
|------|------|
| `src/core/` | `include/core` 中各类的具体实现 |
| `include/effects/` | 具体的着色器、颜色滤镜、图像滤镜实现（渐变、模糊等） |
| `include/gpu/` | GPU 后端相关 API（GrDirectContext、Vulkan/GL/Metal 等） |
| `include/codec/` | 图像编解码器（PNG、JPEG、WebP 等） |
| `include/encode/` | 图像编码器 |
| `include/pathops/` | 路径布尔运算（并、交、差等） |
| `include/svg/` | SVG 渲染 |
| `include/docs/` | 文档输出（PDF） |
| `modules/skshaper/` | 高级文本整形（HarfBuzz 集成） |
| `modules/skcms/` | 色彩管理系统 |

### 核心类之间的关系总结

```
SkSurface ──拥有──> SkCanvas ──使用──> SkPaint ──引用──> SkShader
    |                  |                   |              SkColorFilter
    |                  |                   |              SkImageFilter
    |              绘制目标              绘制源            SkMaskFilter
    |                  |                   |              SkPathEffect
    v                  v                   |              SkBlender
SkImage <──快照── SkCanvas               |
    |                  |            SkPath ──构建自── SkPathBuilder
    |              变换栈               |
    |                  |            SkFont ──引用──> SkTypeface
    v                  v               |
SkPixmap         SkMatrix/SkM44    SkTextBlob ──构建自── SkTextBlobBuilder
SkBitmap         SkRegion
```

### 线程安全说明

- **线程安全的不可变类型**: `SkImage`, `SkPicture`, `SkTextBlob`, `SkTypeface`, `SkData`, `SkVertices`
- **引用计数线程安全**: `SkRefCntBase` 的 `ref()`/`unref()` 使用原子操作
- **非线程安全**: `SkCanvas`, `SkBitmap`, `SkPath`, `SkPaint` - 每个线程应拥有独立实例
- **条件线程安全**: `SkMatrix` 在调用 `getType()` 后可安全跨线程读取
