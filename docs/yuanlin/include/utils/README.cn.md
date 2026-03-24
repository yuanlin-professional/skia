# utils - 实用工具 API

## 概述

`include/utils` 目录提供了一系列实用工具类和函数，作为 Skia 核心 API 的补充和扩展。
这些工具覆盖了画布包装、文本处理、路径解析、阴影绘制、事件追踪、自定义字体等多个
方面，为应用开发者和 Skia 内部使用提供便利。

画布工具是该目录中最丰富的部分。`SkNoDrawCanvas` 是一个不执行实际光栅化的画布实现，
适用于绘制分析（如计算边界、提取操作信息）场景。`SkNWayCanvas` 将绘制操作同时转发
到多个目标画布。`SkPaintFilterCanvas` 提供了一个代理画布模式，允许在绘制操作执行前
拦截和修改 SkPaint 属性。`SkMakeNullCanvas()` 创建一个完全丢弃所有绘制操作的画布，
用于性能基准测试。`SkCanvasStateUtils` 支持跨动态库边界传递画布状态。

`SkShadowUtils` 提供了高质量的3D阴影绘制功能，支持环境光阴影和聚光阴影两种效果，
可以模拟 Material Design 风格的阴影效果。阴影基于路径和3D平面参数计算，支持
方向光和点光源两种模式。

文本和路径工具方面，`SkTextUtils` 提供了带对齐方式的文本绘制便捷函数，`SkParsePath`
支持 SVG 路径字符串的解析和生成，`SkParse` 提供了通用的字符串解析功能。

`SkCustomTypefaceBuilder` 允许开发者以编程方式创建自定义字体，通过逐个设置字形
的路径或 Drawable 来构建 SkTypeface。`SkOrderedFontMgr` 提供了将多个字体管理器
串联查找的功能。

事件追踪工具（`SkEventTracer`、`SkTraceEventPhase`）为 Skia 的性能分析和调试
提供了基础设施，兼容 Chrome 的 trace event 格式。

该目录还包含一个 `mac/` 子目录，提供了 Apple 平台（macOS/iOS）特有的工具函数。

## 架构图

```
+------------------------------------------------------------------+
|                       应用层                                       |
+------------------------------------------------------------------+
         |
    +----+--------+----------+----------+---------+
    |             |          |          |         |
    v             v          v          v         v
+---------+ +----------+ +--------+ +-------+ +----------+
| 画布工具 | | 阴影工具  | | 文本/  | | 字体  | | 事件追踪  |
|         | |          | | 路径   | | 工具  | |          |
+---------+ +----------+ +--------+ +-------+ +----------+
| NoDrawC | | Shadow   | | TextU  | |Custom | | Event    |
| NWayC   | | Utils    | | ParseP | |Typefa | | Tracer   |
| PaintFC | |          | | Parse  | |Ordere | | Trace    |
| NullC   | +----------+ +--------+ |dFontM | | Phase    |
| Canvas  |                          +-------+ +----------+
| State   |
+---------+
         |
         v
+-------------------+
|  mac/ 子目录       |
|  Apple 平台工具    |
|  SkCGUtils        |
+-------------------+
```

## 目录结构

```
include/utils/
  BUILD.bazel              # Bazel 构建配置
  mac/                     # macOS/iOS 平台工具（见子目录文档）
  SkCamera.h               # 3D 相机变换工具（已弃用，使用 SkM44）
  SkCanvasStateUtils.h     # 跨动态库边界传递画布状态
  SkCustomTypeface.h       # 自定义字体构建器
  SkEventTracer.h          # 事件追踪基类
  SkNoDrawCanvas.h         # 不执行光栅化的分析画布
  SkNullCanvas.h           # 丢弃所有操作的空画布
  SkNWayCanvas.h           # 多路转发画布
  SkOrderedFontMgr.h       # 有序字体管理器（串联多个 FontMgr）
  SkPaintFilterCanvas.h    # 绘制属性拦截代理画布
  SkParse.h                # 通用字符串解析工具
  SkParsePath.h            # SVG 路径字符串解析/生成
  SkShadowUtils.h          # 3D 阴影绘制工具
  SkTextUtils.h            # 文本绘制便捷工具
  SkTraceEventPhase.h      # 追踪事件阶段枚举
```

## 关键类与函数

### SkNoDrawCanvas - 不绘制的画布

```cpp
class SkNoDrawCanvas : public SkCanvasVirtualEnforcer<SkCanvas> {
    SkNoDrawCanvas(int width, int height);
    explicit SkNoDrawCanvas(const SkIRect&);
    void resetCanvas(int w, int h);
};
```
不执行实际光栅化的画布子类，所有绘制操作为空操作。使用保守裁剪（仅矩形裁剪）。
适用于绘制操作分析、提取信息等场景。

### SkNWayCanvas - 多路转发画布

```cpp
class SkNWayCanvas : public SkCanvasVirtualEnforcer<SkNoDrawCanvas> {
    void addCanvas(SkCanvas*);
    void removeCanvas(SkCanvas*);
    void removeAll();
};
```
将所有绘制操作同时转发到多个注册的目标画布。

### SkPaintFilterCanvas - 绘制属性拦截画布

```cpp
class SkPaintFilterCanvas : public SkCanvasVirtualEnforcer<SkNWayCanvas> {
    explicit SkPaintFilterCanvas(SkCanvas* canvas);
protected:
    virtual bool onFilter(SkPaint& paint) const = 0;
};
```
抽象代理画布，在执行绘制操作前调用 `onFilter()` 回调修改 SkPaint。
返回 `false` 可以跳过该绘制操作。

### SkShadowUtils - 阴影绘制

```cpp
class SkShadowUtils {
    static void DrawShadow(SkCanvas*, const SkPath&,
                           const SkPoint3& zPlaneParams,
                           const SkPoint3& lightPos, SkScalar lightRadius,
                           SkColor ambientColor, SkColor spotColor,
                           uint32_t flags = kNone_ShadowFlag);

    static bool GetLocalBounds(const SkMatrix& ctm, const SkPath& path,
                               const SkPoint3& zPlaneParams,
                               const SkPoint3& lightPos, SkScalar lightRadius,
                               uint32_t flags, SkRect* bounds);

    static void ComputeTonalColors(SkColor inAmbient, SkColor inSpot,
                                   SkColor* outAmbient, SkColor* outSpot);
};
```

`SkShadowFlags` 控制选项：
- `kTransparentOccluder_ShadowFlag` - 遮挡物非不透明
- `kGeometricOnly_ShadowFlag` - 仅使用几何阴影
- `kDirectionalLight_ShadowFlag` - 使用方向光而非点光源
- `kConcaveBlurOnly_ShadowFlag` - 凹路径仅使用模糊

### SkTextUtils - 文本绘制

```cpp
class SkTextUtils {
    enum Align { kLeft_Align, kCenter_Align, kRight_Align };
    static void DrawString(SkCanvas*, const char text[], SkScalar x, SkScalar y,
                           const SkFont&, const SkPaint&, Align = kLeft_Align);
    static void GetPath(const void* text, size_t length, SkTextEncoding,
                        SkScalar x, SkScalar y, const SkFont&, SkPath*);
};
```

### SkParsePath - SVG 路径解析

```cpp
class SkParsePath {
    static std::optional<SkPath> FromSVGString(const char str[]);
    static SkString ToSVGString(const SkPath&, PathEncoding = PathEncoding::Absolute);
};
```

### SkCustomTypefaceBuilder - 自定义字体

```cpp
class SkCustomTypefaceBuilder {
    void setGlyph(SkGlyphID, float advance, const SkPath&);
    void setGlyph(SkGlyphID, float advance, sk_sp<SkDrawable>, const SkRect& bounds);
    void setMetrics(const SkFontMetrics& fm, float scale = 1);
    void setFontStyle(SkFontStyle);
    sk_sp<SkTypeface> detach();
};
```

### SkMakeNullCanvas - 空画布

```cpp
std::unique_ptr<SkCanvas> SkMakeNullCanvas();
```
创建一个丢弃所有绘制操作的画布，用于性能基准测试。

## 依赖关系

- **内部依赖**：`include/core`（SkCanvas、SkPaint、SkPath、SkFont、SkTypeface 等）
- **内部依赖**：`include/utils/mac`（Apple 平台工具子目录）
- **被依赖**：应用层、测试框架、SVG 模块

## 相关文档与参考

- SVG 路径规范（用于 SkParsePath）
- Material Design 阴影指南（SkShadowUtils 的设计灵感）
- Chrome Trace Event 格式（SkEventTracer 兼容）
- 源码实现位于 `src/utils/` 目录
