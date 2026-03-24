# tools/viewer/ - Skia 交互式查看器应用程序

## 概述

`tools/viewer/` 目录实现了 Skia 项目中最重要的可视化工具——Skia Viewer。它是一个功能丰富的跨平台交互式应用程序，用于实时预览、调试和分析 Skia 的各种渲染效果。Viewer 是 Skia 开发者日常工作中不可或缺的工具，既用于开发新功能时的实时验证，也用于性能分析和问题排查。

Viewer 的核心架构基于"幻灯片"（Slide）模型。每个 Slide 是一个独立的渲染演示，封装了特定的绘制逻辑。Viewer 管理着一个 Slide 集合，用户可以通过键盘快捷键或触控手势在不同 Slide 之间切换。当前版本包含超过 70 种不同的幻灯片实现，涵盖了从基础几何图形、路径操作、文本渲染到高级效果（如阴影、着色器、Lottie 动画）的方方面面。

技术实现上，Viewer 类同时继承了 `sk_app::Application`（应用生命周期管理）和 `sk_app::Window::Layer`（窗口图层事件处理）。它通过 Layer 系统将自身的渲染和事件处理逻辑插入窗口的事件处理链中，同时集成了 ImGui 调试界面层（ImGuiLayer）和性能统计层（StatsLayer）来提供丰富的运行时信息。

Viewer 支持多种 GPU 后端的动态切换（OpenGL、Vulkan、Metal、Dawn、软件光栅化等），支持多种色彩空间模式（Legacy、ColorManaged8888、F16、F16Norm），并提供了透视变换、平铺渲染、缩放窗口等高级调试功能。所有这些功能都可以通过 ImGui 界面或键盘快捷键进行控制。

Viewer 的设计是高度可扩展的。开发者可以通过 `DEF_SLIDE` 宏在任意源文件中注册新的幻灯片，无需修改 Viewer 的核心代码。这种自注册机制极大地简化了新功能演示的添加流程。

## 架构图

```
+------------------------------------------------------------------+
|                        Viewer 应用                                |
|                                                                   |
|  +------------------------------------------------------------+  |
|  |                    Viewer 类                                 |  |
|  |  继承: sk_app::Application + sk_app::Window::Layer          |  |
|  |                                                              |  |
|  |  +------------------+  +------------------+  +------------+  |  |
|  |  |  Slide 管理      |  |  渲染控制        |  |  输入处理   |  |  |
|  |  |  fSlides[]       |  |  ColorMode       |  |  onKey()   |  |  |
|  |  |  fCurrentSlide   |  |  BackendType     |  |  onMouse() |  |  |
|  |  |  initSlides()    |  |  PerspectiveMode |  |  onTouch() |  |  |
|  |  +------------------+  +------------------+  +------------+  |  |
|  +------------------------------------------------------------+  |
|                            |                                      |
|          +-----------------+------------------+                   |
|          |                 |                  |                    |
|  +-------v-------+ +------v--------+ +-------v-------+           |
|  |  ImGuiLayer   | |  StatsLayer   | |  TouchGesture |           |
|  |  (调试界面)    | |  (性能统计)    | |  (手势处理)    |           |
|  |  drawImGui()  | |  Timer 管理    | |  缩放/平移     |           |
|  +---------------+ +---------------+ +---------------+           |
|                                                                   |
|  +------------------------------------------------------------+  |
|  |                    Slide 体系                                |  |
|  |                                                              |  |
|  |  Slide (抽象基类)                                            |  |
|  |    |-- GMSlide          (GM 测试用例包装)                      |  |
|  |    |-- SKPSlide         (SKP 文件渲染)                        |  |
|  |    |-- ImageSlide       (图片显示)                            |  |
|  |    |-- SkSLSlide        (SkSL 着色器编辑)                     |  |
|  |    |-- SkottieSlide     (Lottie 动画)                         |  |
|  |    |-- SvgSlide         (SVG 渲染)                            |  |
|  |    |-- PathSlide        (路径操作演示)                         |  |
|  |    |-- ShadowUtilsSlide (阴影效果)                            |  |
|  |    |-- AnimatedImageSlide (动画图片)                           |  |
|  |    |-- MSKPSlide        (多页 SKP)                            |  |
|  |    |-- BisectSlide      (二分调试)                            |  |
|  |    |-- CaptureSlide     (命令捕获)                            |  |
|  |    +-- ... (70+ 种实现)                                       |  |
|  +------------------------------------------------------------+  |
|                                                                   |
|  +------------------------------------------------------------+  |
|  |  支撑系统                                                    |  |
|  |  sk_app::Window  -->  skwindow::WindowContext               |  |
|  |  sk_app::CommandSet  (快捷键系统)                            |  |
|  |  CommandLineFlags    (命令行参数)                            |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

## 目录结构

```
tools/viewer/
|-- Viewer.h                  # Viewer 主类头文件
|-- Viewer.cpp                # Viewer 主类实现（~2700 行）
|-- Slide.h                   # Slide 抽象基类定义
|-- SlideDir.h/cpp            # 幻灯片目录（组织多个子 Slide）
|-- BUILD.bazel               # Bazel 构建定义
|
|-- # UI 层
|-- ImGuiLayer.h/cpp          # ImGui 集成层，处理 ImGui 输入/渲染
|-- StatsLayer.h/cpp          # 性能统计层，显示帧时间图表
|-- TouchGesture.h/cpp        # 触摸手势识别（平移、缩放、惯性滑动）
|-- AnimTimer.h               # 动画计时器
|
|-- # GM 与文件 Slide
|-- GMSlide.h/cpp             # 将 GM 测试用例包装为 Slide
|-- SKPSlide.h/cpp            # SKP (Skia Picture) 文件 Slide
|-- MSKPSlide.h/cpp           # 多页 SKP 文件 Slide
|-- ImageSlide.h/cpp          # 图片文件 Slide
|-- AnimatedImageSlide.h/cpp  # 动画图片（GIF、WebP 动画）Slide
|-- SvgSlide.h/cpp            # SVG 文件 Slide
|-- SVGFileSlide.cpp          # SVG 文件加载 Slide
|
|-- # SkSL 相关 Slide
|-- SkSLSlide.h/cpp           # SkSL 着色器实时编辑器
|-- SkSLDebuggerSlide.h/cpp   # SkSL 调试器界面
|
|-- # 调试工具 Slide
|-- BisectSlide.h/cpp         # 二分法调试 Slide
|-- CaptureSlide.h/cpp        # 命令捕获 Slide
|
|-- # 动画与特效 Slide
|-- SkottieSlide.h/cpp        # Lottie/Skottie 动画渲染
|-- FlutterAnimateSlide.cpp   # Flutter 动画模拟
|-- MotionMarkSlide.cpp       # MotionMark 基准测试
|-- AnimatedRectsSlide.cpp    # 动画矩形
|-- AnimatedTextSlide.cpp     # 动画文本
|-- AnimBlurSlide.cpp         # 动画模糊效果
|
|-- # 路径与几何 Slide
|-- PathSlide.cpp             # 路径操作
|-- PathEffectsSlide.cpp      # 路径效果
|-- PathTextSlide.cpp         # 路径文本
|-- ArcSlide.cpp              # 弧形绘制
|-- ClipSlide.cpp             # 裁剪操作
|-- PatchSlide.cpp            # 补丁网格
|-- QuadStrokerSlide.cpp      # 二次曲线描边
|-- StrokeVerbSlide.cpp       # 描边动词
|-- SimpleStrokerSlide.cpp    # 简单描边
|-- VariableWidthStrokerSlide.cpp  # 可变宽度描边
|-- DegenerateQuadsSlide.cpp  # 退化四边形
|
|-- # 渲染效果 Slide
|-- ShadowUtilsSlide.cpp      # 阴影工具
|-- ShadowColorSlide.cpp      # 阴影颜色
|-- ShadowReferenceSlide.cpp  # 阴影参考
|-- MaterialShadowsSlide.cpp  # Material Design 阴影
|-- AndroidShadowsSlide.cpp   # Android 风格阴影
|-- GradientsSlide.cpp        # 渐变
|-- MeshSlide.cpp             # 网格渲染
|-- MeshGradientSlide.cpp     # 网格渐变
|-- ShipSlide.cpp             # 船形渲染
|-- XferSlide.cpp             # 传输模式
|
|-- # 文本与字体 Slide
|-- ChineseFlingSlide.cpp     # 中文快速滚动
|-- TextBoxSlide.cpp          # 文本框
|-- TypefaceSlide.cpp         # 字体展示
|-- SBIXSlide.cpp             # SBIX 字体
|-- GlyphTransformSlide.cpp   # 字形变换
|
|-- # 性能与压力测试 Slide
|-- ManyRectsSlide.cpp        # 大量矩形渲染
|-- TextureUploadSlide.cpp    # 纹理上传性能
|-- TimingSlide.cpp           # 时序测试
|-- ChartSlide.cpp            # 图表绘制
|
|-- # 高级功能 Slide
|-- 3DSlide.cpp               # 3D 渲染
|-- CameraSlide.cpp           # 相机变换
|-- GraphitePrimitivesSlide.cpp  # Graphite 图元
|-- RasterPipelineVizSlide.cpp   # 光栅管线可视化
|-- EdgeBuilderVizSlide.cpp   # 边构建器可视化
|-- FatBitsSlide.cpp          # 像素放大镜
|-- ZoomInSlide.h/cpp         # 缩放查看
|-- FilterBoundsSlide.cpp     # 滤镜边界可视化
|-- ImageFilterDAGSlide.cpp   # 图像滤镜 DAG 可视化
|
|-- # 其他 Slide
|-- AtlasSlide.cpp            # 图集绘制
|-- AudioSlide.cpp            # 音频可视化
|-- ClockSlide.cpp            # 时钟绘制
|-- CowboySlide.cpp           # 牛仔绘制
|-- LayersSlide.cpp           # 图层
|-- MixerSlide.cpp            # 混合器
|-- RepeatTileSlide.cpp       # 重复平铺
|-- SGSlide.cpp               # 场景图
|-- ClickHandlerSlide.h/cpp   # 点击处理
|-- FitCubicToCircleSlide.cpp # 三次贝塞尔拟合圆
|-- PathLerpSlide.cpp         # 路径插值
|-- PathOverstrokeSlide.cpp   # 路径过度描边
|-- PathTessellatorsSlide.cpp # 路径细分器
|-- RectanizerSlide.cpp       # 矩形装箱
|-- StringArtSlide.cpp        # 字符串艺术
|-- ThinAASlide.cpp           # 薄抗锯齿
|-- ProtectedSlide.cpp        # 受保护内容渲染
|-- SlidesSlide.cpp           # Slide 内嵌 Slide
+-- PathClipSlide.cpp         # 路径裁剪
```

## 关键类与函数

### Viewer 类

```cpp
// tools/viewer/Viewer.h
class Viewer : public sk_app::Application, sk_app::Window::Layer {
public:
    Viewer(int argc, char** argv, void* platformData);

    // Application 接口
    void onIdle() override;

    // Window::Layer 接口
    void onBackendCreated() override;
    void onPaint(SkSurface*) override;
    void onResize(int width, int height) override;
    bool onTouch(intptr_t owner, skui::InputState state, float x, float y) override;
    bool onMouse(int x, int y, skui::InputState state, skui::ModifierKey modifiers) override;
    bool onKey(skui::Key key, skui::InputState state, skui::ModifierKey modifiers) override;
    bool onChar(SkUnichar c, skui::ModifierKey modifiers) override;

private:
    // 幻灯片管理
    void initSlides();           // 初始化所有幻灯片
    void setCurrentSlide(int);   // 切换当前幻灯片
    void drawSlide(SkSurface*);  // 绘制当前幻灯片
    void drawImGui();            // 绘制 ImGui 界面

    // 渲染控制
    void setBackend(BackendType);     // 切换 GPU 后端
    void setColorMode(ColorMode);     // 切换色彩模式

    // 变换计算
    SkMatrix computeMatrix();         // 计算最终变换矩阵
    SkMatrix computePerspectiveMatrix(); // 计算透视矩阵

    // 成员变量
    sk_app::Window*          fWindow;
    StatsLayer               fStatsLayer;
    ImGuiLayer               fImGuiLayer;
    TouchGesture             fGesture;
    sk_app::CommandSet       fCommands;
    TArray<sk_sp<Slide>>     fSlides;
    int                      fCurrentSlide;
    ColorMode                fColorMode;
    BackendType              fBackendType;
};
```

### Slide 抽象基类

```cpp
// tools/viewer/Slide.h
class Slide : public SkRefCnt {
public:
    virtual SkISize getDimensions() const;    // 获取内容尺寸
    virtual void draw(SkCanvas* canvas) = 0;  // 核心绘制方法（纯虚）
    virtual bool animate(double nanos);       // 动画更新
    virtual void load(SkScalar w, SkScalar h); // 加载资源
    virtual void unload();                     // 卸载资源
    virtual void resize(SkScalar w, SkScalar h); // 窗口大小变化
    virtual bool onChar(SkUnichar c);          // 字符输入
    virtual bool onMouse(SkScalar x, SkScalar y, skui::InputState, skui::ModifierKey);
    const SkString& getName();

protected:
    SkString fName;  // Slide 名称，用于 UI 显示
};
```

### StatsLayer 性能统计

```cpp
// tools/viewer/StatsLayer.h
class StatsLayer : public sk_app::Window::Layer {
public:
    typedef int Timer;
    Timer addTimer(const char* label, SkColor color, SkColor labelColor = 0);
    void beginTiming(Timer);
    void endTiming(Timer);
    void enableGpuTimer(SkColor color);
    void onPaint(SkSurface*) override;  // 绘制性能图表
};
```

### TouchGesture 手势处理

```cpp
// tools/viewer/TouchGesture.h
class TouchGesture {
public:
    void touchBegin(void* owner, float x, float y);
    void touchMoved(void* owner, float x, float y);
    void touchEnd(void* owner);
    void startZoom();
    void updateZoom(float scale, float startX, float startY, float lastX, float lastY);
    const SkMatrix& localM();  // 获取局部变换矩阵
    const SkMatrix& globalM() const;  // 获取全局变换矩阵
    void setTransLimit(const SkRect& contentRect, const SkRect& windowRect, const SkMatrix&);
};
```

## 依赖关系

```
Viewer
  |
  +---> sk_app::Application       (应用生命周期)
  +---> sk_app::Window             (窗口管理)
  +---> sk_app::Window::Layer      (事件处理层)
  +---> sk_app::CommandSet         (快捷键管理)
  +---> skwindow::DisplayParams    (显示参数)
  |
  +---> ImGuiLayer                 (ImGui 调试界面)
  |       +---> imgui 库
  +---> StatsLayer                 (性能统计)
  +---> TouchGesture               (手势处理)
  +---> AnimTimer                  (动画计时)
  |
  +---> Slide 子类                 (幻灯片实现)
  |       +---> SlideRegistry      (自注册)
  +---> CommandLineFlags           (命令行参数)
  +---> CommonFlags                (通用标志)
  |
  +---> Skia Core
  |       +---> SkCanvas, SkSurface, SkPaint, SkFont
  |       +---> SkImage, SkPicture, SkData
  |       +---> SkSL::Compiler     (着色器编译)
  |
  +---> GPU 后端 (条件编译)
          +---> GrDirectContext     (SK_GANESH)
          +---> graphite::Context   (SK_GRAPHITE)
          +---> MemoryCache         (着色器缓存)
```

## 设计模式分析

### 1. 组合模式 (Composite) - Slide 体系

`SlideDir` 类将多个 Slide 组合成一个可浏览的目录结构，允许嵌套组织。每个 Slide 既可以是叶子节点（具体绘制），也可以是容器节点（包含子 Slide）。

### 2. 观察者模式 (Observer) - Layer 系统

Viewer 通过 Layer 机制监听窗口事件。ImGuiLayer、StatsLayer 和 Viewer 自身都是 Window 的 Layer，各自独立响应事件。Layer 的添加顺序决定了绘制和事件处理的优先级。

### 3. 注册表模式 (Registry) - Slide 自注册

```cpp
// DEF_SLIDE 宏实现自注册
#define DEF_SLIDE(code) \
    static Slide* SK_MACRO_APPEND_LINE(F_)() { code } \
    static SlideRegistry SK_MACRO_APPEND_LINE(R_)(SK_MACRO_APPEND_LINE(F_));
```

任意源文件中使用 `DEF_SLIDE` 即可注册新的 Slide，Viewer 在 `initSlides()` 中遍历注册表加载所有已注册的 Slide。

### 4. 状态模式 (State) - ColorMode 与 PerspectiveMode

Viewer 通过枚举管理渲染状态的切换：
- `ColorMode`: kLegacy / kColorManaged8888 / kColorManagedF16 / kColorManagedF16Norm
- `PerspectiveMode`: kPerspective_Off / kPerspective_Real / kPerspective_Fake
- `GestureDevice`: kNone / kTouch / kMouse

### 5. 命令模式 (Command) - CommandSet

通过 `CommandSet` 将键盘按键映射为命令对象，每个命令包含分组、描述和回调函数。支持分组显示帮助信息和字母序显示帮助信息两种模式。

### 6. 覆盖模式 (Override Fields)

Viewer 独特的 `SkPaintFields`、`SkFontFields`、`DisplayFields` 结构体实现了细粒度的属性覆盖机制。每个字段都有一个 bool 标志控制是否应用覆盖，使开发者可以精确控制哪些渲染属性被修改。

## 相关文档与参考

- **Skia Viewer 官方文档**: https://skia.org/docs/dev/tools/viewer/
- **Slide 开发指南**: 参考已有 Slide 实现，如 `PathSlide.cpp` 或 `GradientsSlide.cpp`
- **ImGui 文档**: https://github.com/ocornut/imgui
- **GM 测试框架**: `gm/gm.h` - GMSlide 将 GM 包装为 Slide
- **SkSL 着色器语言**: `src/sksl/` - SkSLSlide 提供实时 SkSL 编辑
- **Skottie 动画**: `modules/skottie/` - SkottieSlide 渲染 Lottie 动画
- **sk_app 框架**: `tools/sk_app/README.md` - 应用框架文档
- **window 上下文**: `tools/window/README.md` - 窗口管理文档
