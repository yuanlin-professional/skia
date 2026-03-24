# src/utils - Skia 通用工具函数库

## 概述

`src/utils` 目录是 Skia 图形引擎中的通用工具函数库，提供了一系列跨平台的辅助类和函数。这些工具涵盖了路径处理、画布操作、阴影渲染、数学计算、文本处理、JSON 序列化、文件系统操作等多个领域，是 Skia 核心渲染引擎的重要辅助组件。

该目录中的代码设计遵循"实用主义"原则，每个工具类或函数都针对特定的功能需求进行了精心设计。大部分代码以 `Sk` 前缀命名，保持了 Skia 一贯的命名风格。工具函数库同时包含了公开 API 的实现代码（对应 `include/utils/` 中的头文件）以及内部私有的辅助工具。

从功能角度看，这些工具可大致分为几大类别：几何与路径工具（如虚线路径、多边形操作、Bezier 曲面补丁）、画布工具（如 NWayCanvas、CanvasStack、NullCanvas、PaintFilterCanvas）、渲染辅助工具（如阴影细分、着色器工具）、数据结构与序列化工具（如 BitSet、JSONWriter、MultiPictureDocument）、以及平台相关的工具（如可执行路径获取、操作系统路径处理）。

此目录还包含两个平台特定的子目录：`mac/` 用于 macOS/iOS 平台的 Core Graphics 和 Core Text 集成，`win/` 用于 Windows 平台的 DirectWrite 和 COM 集成。这些子目录中的代码通过条件编译宏（如 `SK_BUILD_FOR_MAC`、`SK_BUILD_FOR_WIN`）实现平台隔离。

## 架构图

```
+------------------------------------------------------------------+
|                        src/utils 工具库                           |
+------------------------------------------------------------------+
|                                                                    |
|  +------------------+  +-------------------+  +-----------------+ |
|  | 画布工具         |  | 路径与几何工具     |  | 阴影渲染工具    | |
|  |                  |  |                   |  |                 | |
|  | SkNWayCanvas     |  | SkDashPath        |  | SkShadowUtils   | |
|  | SkCanvasStack    |  | SkPolyUtils       |  | SkShadow-       | |
|  | SkNullCanvas     |  | SkParsePath       |  |  Tessellator    | |
|  | SkPaintFilter-   |  | SkPatchUtils      |  |                 | |
|  |  Canvas          |  | SkClipStackUtils  |  +-----------------+ |
|  | SkCanvasState-   |  |                   |                      |
|  |  Utils           |  +-------------------+                      |
|  +------------------+                                              |
|                                                                    |
|  +------------------+  +-------------------+  +-----------------+ |
|  | 数据与序列化     |  | 数学与数值工具     |  | 文本与字体工具  | |
|  |                  |  |                   |  |                 | |
|  | SkJSONWriter     |  | SkMatrix22        |  | SkTextUtils     | |
|  | SkMultiPicture-  |  | SkFloatToDecimal  |  | SkCharToGlyph-  | |
|  |  Document        |  | SkFloatUtils      |  |  Cache          | |
|  | SkBitSet         |  | SkCamera          |  | SkCustomTypeface| |
|  |                  |  |                   |  | SkOrderedFontMgr| |
|  +------------------+  +-------------------+  +-----------------+ |
|                                                                    |
|  +------------------+  +-------------------+                      |
|  | 平台与系统工具   |  | 着色器与调试工具   |                      |
|  |                  |  |                   |                      |
|  | SkOSPath         |  | SkShaderUtils     |                      |
|  | SkGetExecutable- |  | SkEventTracer     |                      |
|  |  Path            |  | SkCallableTraits  |                      |
|  |                  |  |                   |                      |
|  +------------------+  +-------------------+                      |
|                                                                    |
|  +---------------------------+  +-----------------------------+   |
|  | mac/ (macOS/iOS 平台工具) |  | win/ (Windows 平台工具)     |   |
|  | CoreGraphics / CoreText   |  | DirectWrite / COM           |   |
|  +---------------------------+  +-----------------------------+   |
+------------------------------------------------------------------+
```

## 目录结构

```
src/utils/
├── BUILD.bazel                    # Bazel 构建配置文件
├── mac/                           # macOS/iOS 平台专用工具
│   ├── SkCGBase.h                 # CoreGraphics 基础类型转换
│   ├── SkCGGeometry.h             # CoreGraphics 几何类型辅助
│   ├── SkCreateCGImageRef.cpp     # CGImage 创建与转换
│   ├── SkCTFont.cpp / .h          # CoreText 字体平滑与权重映射
│   ├── SkCTFontCreateExactCopy.cpp / .h  # CTFont 精确复制
│   └── SkUniqueCFRef.h            # CoreFoundation 智能指针
├── win/                           # Windows 平台专用工具
│   ├── SkAutoCoInitialize.cpp / .h   # COM 自动初始化
│   ├── SkDWrite.cpp / .h             # DirectWrite 工厂与工具
│   ├── SkDWriteFontFileStream.cpp / .h  # DWrite 字体流适配器
│   ├── SkDWriteGeometrySink.cpp / .h # DWrite 几何路径转换器
│   ├── SkDWriteNTDDI_VERSION.h       # NTDDI 版本宏处理
│   ├── SkHRESULT.cpp / .h           # HRESULT 错误处理宏
│   ├── SkIStream.cpp / .h           # IStream 接口适配器
│   ├── SkObjBase.h                   # COM STDMETHOD 宏定义
│   └── SkTScopedComPtr.h            # COM 智能指针
├── SkBitSet.h                     # 高效位集合数据结构
├── SkCallableTraits.h             # 可调用对象类型萃取
├── SkCamera.cpp                   # 3D 相机变换工具
├── SkCanvasStack.cpp / .h         # 多画布堆栈管理器
├── SkCanvasStateUtils.cpp         # 画布状态序列化/反序列化
├── SkCharToGlyphCache.cpp / .h    # Unicode 到字形缓存
├── SkClipStackUtils.cpp / .h      # 裁剪栈路径工具
├── SkCustomTypeface.cpp           # 自定义字体实现
├── SkDashPath.cpp                 # 虚线路径生成
├── SkDashPathPriv.h               # 虚线路径私有接口
├── SkEventTracer.cpp              # 事件追踪器基础设施
├── SkFloatToDecimal.cpp / .h      # 浮点数到十进制字符串转换
├── SkFloatUtils.h                 # 浮点数比较工具（ULP 精度）
├── SkGetExecutablePath.h          # 获取可执行文件路径（跨平台）
├── SkGetExecutablePath_linux.cpp  # Linux 实现
├── SkGetExecutablePath_mac.cpp    # macOS 实现
├── SkGetExecutablePath_win.cpp    # Windows 实现
├── SkJSONWriter.cpp / .h          # 轻量级 JSON 写入器
├── SkMatrix22.cpp / .h            # 2x2 矩阵 Givens 旋转
├── SkMultiPictureDocument.cpp     # 多页图片文档
├── SkMultiPictureDocumentPriv.h   # 多页文档私有接口
├── SkNullCanvas.cpp               # 空操作画布实现
├── SkNWayCanvas.cpp               # N 路广播画布实现
├── SkOrderedFontMgr.cpp           # 有序字体管理器
├── SkOSPath.cpp / .h              # 操作系统文件路径工具
├── SkPaintFilterCanvas.cpp        # 绘制过滤画布
├── SkParse.cpp                    # 字符串解析工具
├── SkParseColor.cpp               # 颜色字符串解析
├── SkParsePath.cpp                # SVG 路径字符串解析
├── SkPatchUtils.cpp / .h          # Bezier 曲面补丁工具
├── SkPolyUtils.cpp / .h           # 多边形操作工具（内缩/外扩/三角剖分）
├── SkShaderUtils.cpp / .h         # 着色器调试与格式化工具
├── SkShadowTessellator.cpp / .h   # 阴影网格细分器
├── SkShadowUtils.cpp              # 阴影绘制高级工具
└── SkTextUtils.cpp                # 文本绘制辅助工具
```

## 关键类与函数

### 画布工具类

#### SkCanvasStack
```cpp
// src/utils/SkCanvasStack.h
class SkCanvasStack : public SkNWayCanvas {
public:
    SkCanvasStack(int width, int height);
    void pushCanvas(std::unique_ptr<SkCanvas>, const SkIPoint& origin);
    void removeAll() override;
};
```
`SkCanvasStack` 继承自 `SkNWayCanvas`，将画布操作广播到多个子画布上。与 `SkNWayCanvas` 的不同之处在于，它拥有子画布的所有权，并为每个子画布维护偏移原点和裁剪区域。该类在画布状态序列化（`SkCanvasStateUtils`）中被使用。

#### SkNullCanvas
```cpp
// src/utils/SkNullCanvas.cpp
std::unique_ptr<SkCanvas> SkMakeNullCanvas();
```
基于 `SkNWayCanvas` 实现的空画布，当 N=0 时所有绘制操作均为空操作。常用于测试和性能基准场景。

### 路径与几何工具

#### SkDashPath 命名空间
```cpp
// src/utils/SkDashPathPriv.h
namespace SkDashPath {
    void CalcDashParameters(SkScalar phase, SkSpan<const SkScalar> intervals,
                            SkScalar* initialDashLength, size_t* initialDashIndex,
                            SkScalar* intervalLength, SkScalar* adjustedPhase = nullptr);
    bool FilterDashPath(SkPathBuilder* dst, const SkPath& src, SkStrokeRec*, const SkRect*,
                        const SkPathEffectBase::DashInfo& info);
    bool ValidDashPath(SkScalar phase, SkSpan<const SkScalar> intervals);
}
```
虚线路径生成器，将给定路径根据间隔数组和相位参数转换为虚线效果路径。`kMaxDashCount` 限制了最大虚线段数（常规构建为 100 万，Fuzzer 构建为 1 万）。

#### SkPolyUtils 多边形工具
```cpp
// src/utils/SkPolyUtils.h
bool SkInsetConvexPolygon(...);      // 凸多边形内缩
bool SkOffsetSimplePolygon(...);     // 简单多边形偏移（内缩/外扩）
bool SkComputeRadialSteps(...);      // 计算圆弧连接的步数
int  SkGetPolygonWinding(...);       // 获取多边形绕行方向
bool SkIsConvexPolygon(...);         // 判断多边形是否为凸
bool SkIsSimplePolygon(...);         // 判断多边形是否为简单多边形
bool SkTriangulateSimplePolygon(...); // 简单多边形三角剖分
```
提供了完整的多边形几何操作集，支持凸多边形内缩、简单多边形偏移（支持正负方向）、多边形属性判断和三角剖分等功能。这些函数在阴影渲染中起到关键作用。

### 数据结构与序列化

#### SkBitSet
```cpp
// src/utils/SkBitSet.h
class SkBitSet {
public:
    explicit SkBitSet(size_t size);
    void set(size_t index);    // 设置单个位
    void set();                // 设置所有位
    void reset(size_t index);  // 清除单个位
    void reset();              // 清除所有位
    bool test(size_t index) const;
    OptionalIndex findFirst();
    OptionalIndex findFirstUnset();
    template<typename FN> void forEachSetIndex(FN f) const;
};
```
高效的位集合实现，基于 `uint32_t` 分块存储。支持快速的位操作、遍历已设置位、查找第一个已设置/未设置位等功能。在字体子系统的字形集管理中广泛使用。

#### SkJSONWriter
```cpp
// src/utils/SkJSONWriter.h
class SkJSONWriter : SkNoncopyable {
public:
    enum class Mode { kFast, kPretty };
    SkJSONWriter(SkWStream* stream, Mode mode = Mode::kFast);
    void beginObject(const char* name = nullptr, bool multiline = true);
    void endObject();
    void beginArray(const char* name = nullptr, bool multiline = true);
    void endArray();
    void appendString(...);
    void appendBool(bool value);
    void appendS32/appendU32/appendFloat/appendDouble(...);
};
```
轻量级 JSON 流式写入器，支持紧凑（kFast）和美化（kPretty）两种输出模式。使用 32KB 内部缓冲区实现高性能写入，遵循 RFC-4627 规范，内置状态机确保输出 JSON 结构正确。

### 阴影渲染工具

#### SkShadowTessellator 命名空间
```cpp
// src/utils/SkShadowTessellator.h
namespace SkShadowTessellator {
    sk_sp<SkVertices> MakeAmbient(const SkPath& path, const SkMatrix& ctm,
                                   const SkPoint3& zPlane, bool transparent);
    sk_sp<SkVertices> MakeSpot(const SkPath& path, const SkMatrix& ctm,
                                const SkPoint3& zPlane, const SkPoint3& lightPos,
                                SkScalar lightRadius, bool transparent, bool directional);
}
```
阴影网格生成器，将路径转换为可渲染的阴影顶点网格。支持两种阴影类型：环境阴影（Ambient）通过外扩路径生成半影区域；聚光阴影（Spot）根据光源位置和半径进行透视变换后生成阴影形状。

### 数学与数值工具

#### SkFloatUtils
```cpp
// src/utils/SkFloatUtils.h
template <typename RawType, unsigned int ULPs>
class SkFloatingPoint {
public:
    explicit SkFloatingPoint(const RawType& x);
    bool is_nan() const;
    bool AlmostEquals(const SkFloatingPoint& rhs) const;
};
```
基于 ULP（Units in the Last Place）的浮点数精确比较工具。通过将浮点数转换为偏置整数表示，可以精确衡量两个浮点数之间的距离。

#### SkFloatToDecimal
```cpp
// src/utils/SkFloatToDecimal.h
unsigned SkFloatToDecimal(float value, char output[kMaximumSkFloatToDecimalLength]);
```
浮点数到十进制字符串的精确转换函数，输出格式为 `[-]?([0-9]*\.)?[0-9]+`（不使用科学记数法）。处理了 INFINITY 和 NAN 等特殊值。主要用于 PDF 输出等需要精确数值表示的场景。

### 平台与系统工具

#### SkOSPath
```cpp
// src/utils/SkOSPath.h
class SkOSPath {
public:
    static constexpr char SEPARATOR = '/';  // Windows 上为 '\\'
    static SkString Join(const char* rootPath, const char* relativePath);
    static SkString Basename(const char* fullPath);
    static SkString Dirname(const char* fullPath);
};
```
跨平台的文件路径操作工具，功能类似于 Python 的 `os.path` 模块，支持路径拼接、文件名提取和目录名提取。

#### SkGetExecutablePath
```cpp
// src/utils/SkGetExecutablePath.h
std::string SkGetExecutablePath();
```
获取当前运行程序的完整路径，有 Linux（通过 `/proc/self/exe`）、macOS（通过 `_NSGetExecutablePath`）和 Windows（通过 `GetModuleFileNameA`）三个平台的独立实现。

## 依赖关系

```
src/utils/ 的依赖关系:

外部依赖（被 utils 使用）:
  include/core/         -> SkCanvas, SkPath, SkMatrix, SkBitmap, SkStream, SkString 等
  include/private/base/ -> SkTArray, SkNoncopyable, SkTemplates, SkMalloc 等
  src/core/             -> SkDevice, SkPathPriv, SkBlurMask, SkGeometry 等
  src/base/             -> SkMathPriv, SkUTF, SkRandom 等

内部依赖（utils 内部互相引用）:
  SkCanvasStack       -> SkNWayCanvas
  SkCanvasStateUtils  -> SkCanvasStack
  SkNullCanvas        -> SkNWayCanvas
  SkShadowUtils       -> SkShadowTessellator -> SkPolyUtils
  SkDashPath          -> SkPathEffectBase

被外部使用:
  src/gpu/ganesh/      -> SkShadowUtils（GPU 加速阴影渲染）
  src/ports/           -> mac/ 和 win/ 子目录的字体相关工具
  src/pdf/             -> SkFloatToDecimal（PDF 数值输出）
  tools/               -> SkJSONWriter, SkOSPath 等
```

## 设计模式分析

### 1. 代理/广播模式（Proxy/Broadcast Pattern）
`SkNWayCanvas` 和 `SkCanvasStack` 采用广播代理模式，将单个画布的操作广播到多个子画布上。这种设计允许同时向多个目标进行渲染，常用于画布状态的跨模块共享。

### 2. 空对象模式（Null Object Pattern）
`SkMakeNullCanvas()` 通过创建一个没有子画布的 `SkNWayCanvas` 来实现空画布，所有绘制操作都是空操作。这避免了代码中大量的空指针检查。

### 3. 装饰器模式（Decorator Pattern）
`SkPaintFilterCanvas` 是典型的装饰器模式，它包装了一个真实的画布，在每次绘制调用之前对 `SkPaint` 进行过滤和修改，允许在不改变原有绘制逻辑的情况下全局修改绘制属性。

### 4. RAII 模式（Resource Acquisition Is Initialization）
整个工具库广泛使用 RAII 模式管理资源。`SkBitSet` 使用 `std::unique_ptr` 配合自定义删除器管理内存；Windows 子目录中的 `SkAutoCoInitialize` 在构造时初始化 COM、析构时反初始化。

### 5. 工厂方法模式（Factory Method Pattern）
`SkShadowTessellator::MakeAmbient()` 和 `SkShadowTessellator::MakeSpot()` 是工厂方法，根据不同的参数创建不同类型的阴影顶点网格。

### 6. 策略模式（Strategy Pattern）
`SkJSONWriter` 的 `Mode` 枚举（`kFast` / `kPretty`）体现了策略模式的思想，同一个写入器可以根据构造时选择的模式采用不同的输出策略。

### 7. 模板元编程模式（Template Metaprogramming）
`SkCallableTraits` 使用高级模板元编程技术，通过宏展开和模板特化的组合，从可调用对象类型中萃取出返回类型和参数类型信息，支持普通函数、函数指针、成员函数指针及 lambda 等所有可调用类型。

## 数据流

### 阴影渲染数据流
```
SkPath (用户输入路径)
    |
    v
SkShadowUtils::DrawShadow()
    |
    +---> SkShadowTessellator::MakeAmbient()  环境阴影
    |         |
    |         v
    |     SkPolyUtils (多边形外扩/内缩)
    |         |
    |         v
    |     sk_sp<SkVertices> (环境阴影网格)
    |
    +---> SkShadowTessellator::MakeSpot()     聚光阴影
    |         |
    |         v
    |     透视变换 + SkPolyUtils
    |         |
    |         v
    |     sk_sp<SkVertices> (聚光阴影网格)
    |
    v
SkCanvas::drawVertices() (最终渲染到画布)
```

### 虚线路径处理数据流
```
SkPath (原始路径) + intervals[] (间隔数组) + phase (相位)
    |
    v
SkDashPath::ValidDashPath()  校验输入参数合法性
    |
    v
SkDashPath::CalcDashParameters()  计算初始虚线参数
    |
    v
SkDashPath::InternalFilter()  遍历路径段生成虚线
    |
    v
SkPathBuilder -> SkPath (虚线路径输出)
```

### JSON 写入数据流
```
用户调用 SkJSONWriter API
    |
    v
状态机验证 (State: kStart -> kObjectBegin -> kObjectName -> kObjectValue -> ...)
    |
    v
内部 32KB 缓冲区 (char fBlock[kBlockSize])
    |
    v (缓冲区满或调用 flush())
SkWStream (输出目标，如文件流 SkFILEWStream)
```

### 画布广播数据流
```
SkNWayCanvas / SkCanvasStack
    |
    +---> Canvas A (offset: 0,0)   ---> 渲染目标 A
    |
    +---> Canvas B (offset: x1,y1) ---> 渲染目标 B
    |
    +---> Canvas C (offset: x2,y2) ---> 渲染目标 C
    |
    v
每个 drawXxx() / clipXxx() 调用都被转发到所有子画布
(SkCanvasStack 额外为每个子画布维护偏移和必要裁剪)
```

## 相关文档与参考

| 参考项 | 路径/链接 |
|-------|----------|
| 公开 Canvas 工具头文件 | `include/utils/SkNWayCanvas.h`, `SkNullCanvas.h`, `SkPaintFilterCanvas.h` |
| 公开阴影工具头文件 | `include/utils/SkShadowUtils.h` |
| 公开解析工具头文件 | `include/utils/SkParse.h`, `SkParsePath.h` |
| 公开文本工具头文件 | `include/utils/SkTextUtils.h` |
| 公开 JSON 序列化头文件 | 内部使用，头文件在 `src/utils/SkJSONWriter.h` |
| 公开事件追踪头文件 | `include/utils/SkEventTracer.h` |
| 公开自定义字体头文件 | `include/utils/SkCustomTypeface.h` |
| 公开 Camera 头文件 | `include/utils/SkCamera.h` |
| 核心路径与矩阵类 | `include/core/SkPath.h`, `include/core/SkMatrix.h` |
| 核心画布类 | `include/core/SkCanvas.h` |
| macOS 平台工具子目录 | `src/utils/mac/` |
| Windows 平台工具子目录 | `src/utils/win/` |
| Skia 官方文档 | https://skia.org/docs/ |
| Bazel 构建配置 | `src/utils/BUILD.bazel` |
