# gm/ - Skia Golden Master 测试目录

## 概述

`gm/` 目录是 Skia 图形库的 Golden Master（简称 GM）测试目录，包含约 439 个测试文件。GM 测试是 Skia 最重要的视觉回归测试机制，每个 GM 测试生成一张确定性的渲染图像，与预先审批的"黄金"参考图像进行比对，以检测渲染结果的变化。

GM 框架的核心是 `skiagm::GM` 基类（定义在 `gm/gm.h` 中），每个 GM 测试继承该类或使用 `DEF_SIMPLE_GM` 等便捷宏定义。GM 测试指定画布尺寸和背景色，然后在 `onDraw()` 方法中执行绘制操作。DM 运行器会将 GM 测试在多种配置下运行（8888 光栅、GPU、PDF 等），并将输出的像素数据计算哈希值，与已知的"黄金"哈希值进行比对。

每个 GM 测试本质上是一个独立的渲染场景，通常聚焦于测试一个特定的 Skia 功能或 API。例如 `blurs.cpp` 测试各种模糊效果，`gradients.cpp` 测试渐变渲染，`rrects.cpp` 测试圆角矩形。这些测试既可以作为回归测试使用，也可以作为 API 使用示例参考。

GM 测试在 Skia 的持续集成系统中扮演核心角色。所有 GM 的渲染结果会被上传到 Gold（Skia 的图像审批服务），开发者可以在 Gold 仪表板上审查新的渲染结果、比较不同平台的输出差异、以及追踪渲染变化的历史。当 GM 输出发生变化时，需要人工审批确认变更是预期的。

GM 测试还可以通过 `GMBench` 适配器作为性能基准测试运行（在 `bench/GMBench.h` 中定义），这使得同一组渲染场景既能验证正确性又能监控性能。

## 架构图

```
+------------------------------------------------------------------+
|                    DM (测试运行器)                                 |
|  +------------------------------------------------------------+  |
|  |                  GMRegistry (注册表)                         |  |
|  |  +----------+ +-------------+ +------------------+          |  |
|  |  | DEF_GM   | | DEF_SIMPLE_ | | DEF_SIMPLE_GPU_  |          |  |
|  |  | (完整GM) | | GM (简单GM) | | GM (GPU GM)      |          |  |
|  |  +----------+ +-------------+ +------------------+          |  |
|  +------------------------------------------------------------+  |
|                              |                                    |
|  +------------------------------------------------------------+  |
|  |                  Sink (渲染目标)                             |  |
|  |  +--------+ +-------+ +-----+ +------+ +---------+         |  |
|  |  | Raster | | GPU   | | PDF | | SVG  | |Graphite |         |  |
|  |  | (8888) | |(GL/VK)| |     | |      | |         |         |  |
|  |  +--------+ +-------+ +-----+ +------+ +---------+         |  |
|  +------------------------------------------------------------+  |
|                              |                                    |
|  +------------------------------------------------------------+  |
|  |              渲染结果处理                                    |  |
|  |  Hash计算 -> Gold上传 -> 人工审批 -> 黄金图像更新            |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

## 目录结构

```
gm/
├── BUILD.bazel                    # Bazel 构建配置
├── gm.h                           # GM 基类定义（核心头文件）
│
├── [基础图元测试]
│   ├── rrects.cpp                 # 圆角矩形
│   ├── roundrects.cpp             # 圆角矩形变体
│   ├── rects.cpp                  # 矩形
│   ├── circles.cpp                # (由 circle_sizes.cpp 等覆盖)
│   ├── circle_sizes.cpp           # 不同尺寸的圆
│   ├── circulararcs.cpp           # 圆弧
│   ├── lines.cpp                  # (由 strokedlines.cpp 等覆盖)
│   ├── strokedlines.cpp           # 描边线条
│   ├── strokes.cpp                # 描边效果
│   ├── shapes.cpp                 # 通用形状
│   └── vertices.cpp               # 顶点绘制
│
├── [路径测试]
│   ├── beziers.cpp                # 贝塞尔曲线
│   ├── arcto.cpp                  # 弧线绘制
│   ├── addarc.cpp                 # 添加弧线
│   ├── clippedbitmapshaders.cpp   # 裁剪的位图着色器
│   ├── collapsepaths.cpp          # 退化路径
│   ├── convexpaths.cpp            # (由 batchedconvexpaths.cpp 覆盖)
│   ├── batchedconvexpaths.cpp     # 批量凸路径
│   ├── thinconcavepaths.cpp       # 薄凹路径
│   ├── trickycubicstrokes.cpp     # 复杂三次曲线描边
│   └── smallpaths.cpp             # 小尺寸路径
│
├── [文本渲染测试]
│   ├── textblob.cpp               # 文本块
│   ├── texteffects.cpp            # 文本效果
│   ├── stroketext.cpp             # 描边文本
│   ├── textblobmixedsizes.cpp     # 混合尺寸文本
│   ├── textblobrandomfont.cpp     # 随机字体文本
│   ├── textblobshader.cpp         # 文本着色器
│   ├── variedtext.cpp             # 变化文本
│   ├── slug.cpp                   # Slug 文本渲染
│   ├── scaledemoji.cpp            # 缩放的 emoji
│   └── scaledemoji_rendering.cpp  # emoji 渲染
│
├── [图像处理测试]
│   ├── bitmapimage.cpp            # 位图图像
│   ├── bitmapfilters.cpp          # 位图过滤器
│   ├── bitmapshader.cpp           # 位图着色器
│   ├── bitmaptiled.cpp            # 平铺位图
│   ├── bitmapcopy.cpp             # 位图复制
│   ├── wacky_yuv_formats.cpp      # YUV 格式测试
│   ├── ycbcrimage.cpp             # YCbCr 图像
│   ├── yuv420_odd_dim.cpp         # 奇数尺寸 YUV420
│   └── tilemodes.cpp              # 平铺模式
│
├── [滤镜与效果测试]
│   ├── blurs.cpp                  # 模糊效果
│   ├── blurrect.cpp               # 矩形模糊
│   ├── blurroundrect.cpp          # 圆角矩形模糊
│   ├── blurcircles.cpp            # 圆形模糊
│   ├── blurimagevmask.cpp         # 图像遮罩模糊
│   ├── shadowutils.cpp            # 阴影工具
│   ├── xfermodes.cpp              # 混合模式 (传输模式)
│   ├── xfermodes2.cpp             # 混合模式变体
│   ├── xfermodes3.cpp             # 混合模式变体
│   ├── xfermodeimagefilter.cpp    # 混合模式图像滤镜
│   ├── tablecolorfilter.cpp       # 查找表颜色滤镜
│   ├── runtimecolorfilter.cpp     # 运行时颜色滤镜
│   ├── runtimeimagefilter.cpp     # 运行时图像滤镜
│   ├── runtimeshader.cpp          # 运行时着色器
│   ├── runtimefunctions.cpp       # 运行时函数
│   └── runtimeintrinsics.cpp      # 运行时内置函数
│
├── [渐变测试]
│   ├── gradients.cpp              # (由多个渐变文件覆盖)
│   ├── alphagradients.cpp         # Alpha 渐变
│   ├── analytic_gradients.cpp     # 解析渐变
│   ├── shallowgradient.cpp        # 浅渐变
│   └── testgradient.cpp           # 渐变测试
│
├── [裁剪测试]
│   ├── aaclip.cpp                 # 抗锯齿裁剪
│   ├── circularclips.cpp          # 圆形裁剪
│   ├── clipshader.cpp             # 着色器裁剪
│   ├── clip_error.cpp             # 裁剪错误场景
│   ├── clip_sierpinski_region.cpp # Sierpinski 区域裁剪
│   └── windowrectangles.cpp       # 窗口矩形裁剪
│
├── [GPU 特定测试]
│   ├── beziereffects.cpp          # 贝塞尔 GPU 效果
│   ├── clockwise.cpp              # 顺时针方向判定
│   ├── bigrrectaaeffect.cpp       # 大圆角矩形抗锯齿
│   └── clear_swizzle.cpp          # 清除通道重排
│
├── [Bug 修复验证]
│   ├── bug12866.cpp               # 已修复 bug 的回归测试
│   ├── bug5252.cpp
│   ├── bug530095.cpp
│   ├── bug6643.cpp
│   ├── bug6783.cpp
│   ├── bug9331.cpp
│   ├── skbug_257.cpp
│   ├── skbug_4868.cpp
│   ├── skbug_5321.cpp
│   ├── skbug_8664.cpp
│   ├── skbug_8955.cpp
│   ├── skbug_9319.cpp
│   ├── skbug_9819.cpp
│   ├── skbug_12212.cpp
│   └── skbug1719.cpp
│
├── [3D 与高级功能]
│   ├── 3d.cpp                     # 3D 透视效果
│   ├── savelayer.cpp              # SaveLayer 操作
│   ├── surface.cpp                # Surface 操作
│   └── animated_gif.cpp           # 动画 GIF
│
└── [颜色与色彩空间]
    ├── color4f.cpp                # 高精度颜色
    ├── srgb.cpp                   # sRGB 色彩空间
    └── workingspace.cpp           # 工作色彩空间
```

## 关键类与函数

### GM 基类（gm.h）

```cpp
namespace skiagm {

enum class DrawResult { kOk, kFail, kSkip };

class GM {
public:
    enum Mode { kGM_Mode, kSample_Mode, kBench_Mode };

    explicit GM(SkColor backgroundColor = SK_ColorWHITE);

    // 生命周期方法
    DrawResult gpuSetup(SkCanvas*, SkString* errorMsg, GraphiteTestContext*);
    void gpuTeardown();
    void onceBeforeDraw();
    DrawResult draw(SkCanvas*, SkString* errorMsg);

    // 属性
    virtual SkISize getISize() = 0;        // 画布尺寸
    virtual SkString getName() const = 0;   // GM 名称
    virtual bool runAsBench() const;        // 是否可作为基准测试

    // 可选覆写
    virtual void modifySurfaceProps(SkSurfaceProps*) const {}
    virtual void modifyGrContextOptions(GrContextOptions*) {}
    virtual void modifyGraphiteContextOptions(skgpu::graphite::ContextOptions*) const {}
    virtual std::map<std::string, std::string> getGoldKeys() const;

protected:
    virtual DrawResult onGpuSetup(SkCanvas*, SkString*, GraphiteTestContext*);
    virtual void onGpuTeardown() {}
    virtual void onOnceBeforeDraw();
    virtual DrawResult onDraw(SkCanvas*, SkString* errorMsg);
    virtual void onDraw(SkCanvas*);
    virtual bool onAnimate(double nanos);
};
```

### 注册宏

| 宏 | 用途 | 示例 |
|----|------|------|
| `DEF_GM(CODE)` | 注册完整 GM 类 | `DEF_GM(return new MyGM();)` |
| `DEF_SIMPLE_GM(NAME, CANVAS, W, H)` | 注册简单 GM（单函数） | `DEF_SIMPLE_GM(test, c, 200, 200) { c->drawRect(...); }` |
| `DEF_SIMPLE_GM_BG(NAME, CANVAS, W, H, BG)` | 带自定义背景色 | |
| `DEF_SIMPLE_GM_CAN_FAIL(NAME, CANVAS, ERR, W, H)` | 可返回失败/跳过 | |
| `DEF_SIMPLE_GPU_GM(NAME, CTX, CANVAS, W, H)` | GPU 专用 GM | |
| `DEF_SIMPLE_GPU_GM_CAN_FAIL(...)` | 可失败的 GPU GM | |

### 辅助类

| 类 | 说明 |
|----|------|
| `SimpleGM` | 基于函数指针的简单 GM 实现 |
| `GpuGM` | 需要 GPU 上下文的 GM 基类（Ganesh） |
| `SimpleGpuGM` | 基于函数指针的简单 GPU GM |
| `GMFactory` | `std::function<std::unique_ptr<GM>()>` 工厂类型 |
| `GMRegistry` | `sk_tools::Registry<GMFactory>` 注册表 |

### 辅助函数

```cpp
void MarkGMGood(SkCanvas*, SkScalar x, SkScalar y);  // 在画布上标记测试通过
void MarkGMBad(SkCanvas*, SkScalar x, SkScalar y);   // 在画布上标记测试失败
```

## 依赖关系

```
gm/ 依赖关系图:

    gm/gm.h
    ├── include/core/SkColor.h           (颜色定义)
    ├── include/core/SkScalar.h          (标量类型)
    ├── include/core/SkSize.h            (尺寸类型)
    ├── include/core/SkString.h          (字符串)
    ├── include/core/SkSurfaceProps.h    (Surface 属性)
    ├── tools/Registry.h                 (注册表模板)
    └── struct GrContextOptions           (GPU 上下文选项)

    gm/*.cpp (具体 GM 测试)
    ├── gm/gm.h                          (GM 基类)
    ├── include/core/SkCanvas.h          (Canvas API)
    ├── include/core/SkPaint.h           (画笔)
    ├── include/core/SkPath.h            (路径)
    ├── include/core/SkFont.h            (字体)
    ├── include/effects/Sk*Effect.h      (各种效果)
    ├── include/core/SkImage.h           (图像)
    └── tools/ToolUtils.h               (工具函数)

    运行时依赖:
    ├── dm/ (测试运行器，通过 GMSrc 适配器加载 GM)
    ├── bench/GMBench.h (性能基准适配器)
    └── Gold (图像审批服务)
```

## 设计模式分析

### 1. 注册表模式（Registry Pattern）

每个 GM 通过 `DEF_GM` 或 `DEF_SIMPLE_GM` 宏注册到全局 `GMRegistry`。DM 运行器在启动时遍历注册表，创建所有 GM 实例并在各种配置下运行。

### 2. 模板方法模式（Template Method Pattern）

`GM` 基类定义了固定的执行流程：`gpuSetup()` -> `onceBeforeDraw()` -> `drawBackground()` -> `drawContent()`。子类通过覆写 `onDraw()`、`onGpuSetup()` 等方法注入自定义绘制逻辑。

### 3. 工厂模式（Factory Pattern）

`GMFactory` 是一个 `std::function<std::unique_ptr<GM>()>` 类型，每次执行时会创建全新的 GM 实例，确保测试之间没有状态泄漏。

### 4. 简化接口模式（Facade Pattern）

`DEF_SIMPLE_GM` 系列宏为最常见的 GM 测试提供了极简的声明方式。开发者只需要写一个绘制函数，宏会自动处理 GM 类的创建、注册和生命周期管理。

### 5. 双重调度模式

GM 测试通过 `DrawResult` 枚举（`kOk`、`kFail`、`kSkip`）支持三种结果状态。GPU GM 在非 GPU 配置下自动返回 `kSkip`，而不是硬性失败，这实现了优雅的跨平台兼容性。

## 数据流

```
GM 测试执行流程:

1. 注册阶段 (编译/链接时)
   DEF_SIMPLE_GM(blurs, canvas, 700, 500) { ... }
          |
          v
   GMRegistry 链表添加 GMFactory

2. 发现阶段 (DM 启动时)
   遍历 GMRegistry
          |
          v
   创建 GMSrc 对象 (包装 GMFactory)
          |
          v
   与 Sink 配对 (8888, gpu, pdf, ...)

3. 执行阶段 (每个 GMSrc x Sink 组合)
   GMFactory 创建 GM 实例
          |
          v
   GM::gpuSetup() -- 初始化 GPU 资源
          |
          v
   GM::onceBeforeDraw() -- 一次性设置
          |
          v
   GM::drawBackground() -- 绘制背景色
          |
          v
   GM::drawContent() -> GM::onDraw(canvas) -- 核心绘制
          |
          v
   Sink 捕获输出 (像素/矢量)

4. 验证阶段
   计算输出的 MD5 哈希
          |
          v
   与已知黄金哈希比对
          |
          +-- 匹配 --> 通过
          |
          +-- 不匹配 --> 上传到 Gold 待审批
          |
          +-- Gold 审批 --> 更新黄金哈希
```

## 编写新 GM 测试指南

### 简单 GM（推荐）

```cpp
#include "gm/gm.h"
#include "include/core/SkCanvas.h"

DEF_SIMPLE_GM(my_test_name, canvas, 200, 200) {
    SkPaint paint;
    paint.setColor(SK_ColorRED);
    canvas->drawRect(SkRect::MakeWH(100, 100), paint);
}
```

### 完整 GM 类

```cpp
class MyGM : public skiagm::GM {
    SkString getName() const override { return SkString("my_gm"); }
    SkISize getISize() override { return {300, 300}; }
    void onDraw(SkCanvas* canvas) override {
        // 绘制逻辑
    }
};
DEF_GM(return new MyGM();)
```

### GPU 专用 GM

```cpp
DEF_SIMPLE_GPU_GM(my_gpu_test, ctx, canvas, 256, 256) {
    // ctx 是 GrRecordingContext*
    // 可以进行 GPU 特定操作
}
```

## 相关文档与参考

- `gm/gm.h` - GM 基类完整定义，包含所有宏和类
- `dm/DMSrcSink.h` - `GMSrc` 适配器，将 GM 包装为 DM 数据源
- `bench/GMBench.h` - `GMBench` 适配器，将 GM 包装为性能基准
- `tools/Registry.h` - 注册表模板基类
- Gold 服务 - Skia 图像审批与追踪系统
- `dm/DM.cpp` - DM 测试运行器主入口
