# DMSrcSink

> 源文件: dm/DMSrcSink.h, dm/DMSrcSink.cpp

## 概述

DMSrcSink 是 Skia 的 DM (Drawing Manager) 测试框架的核心组件,提供了一个抽象的测试源(Source)和输出目标(Sink)系统。该模块定义了各种类型的渲染源(如 GM、图片、编解码器)和输出目标(如光栅化、GPU、PDF、SVG),用于自动化测试 Skia 的各种渲染路径和配置组合。

DM 框架通过组合不同的 Source 和 Sink 来生成大量的测试用例,确保 Skia 在各种场景下的正确性和性能。该架构支持多种后端(Ganesh GPU、Graphite GPU、软件光栅化)和多种图像格式的测试。

## 架构位置

```
skia/
├── dm/                          # Drawing Manager 测试框架
│   ├── DMSrcSink.h             # 核心抽象接口定义
│   ├── DMSrcSink.cpp           # 实现文件(约3594行)
│   └── DM.cpp                  # 主测试驱动程序
├── gm/                          # Golden Master 测试用例
├── tools/                       # 工具库
│   ├── ganesh/                 # Ganesh GPU 相关工具
│   ├── graphite/               # Graphite GPU 相关工具
│   └── flags/                  # 命令行标志配置
└── include/                     # 公共 API 头文件
```

该模块作为测试框架的基础设施层,连接了测试用例(GM)和各种渲染后端,是 Skia 质量保证体系的关键组件。

## 主要类与结构体

### 核心抽象类

#### Result
```cpp
class Result {
    enum class Status : int { Ok, Fatal, Skip };
    Status fStatus;
    SkString fMsg;
public:
    static Result Ok();
    static Result Fatal(const char* fmt, ...);
    static Result Skip(const char* fmt, ...);
};
```
表示测试执行结果,支持成功、致命错误和跳过三种状态。

#### Src (Source 抽象基类)
```cpp
struct Src {
    virtual Result draw(SkCanvas* canvas, GraphiteTestContext*) const = 0;
    virtual SkISize size() const = 0;
    virtual Name name() const = 0;
    virtual void modifySurfaceProps(SkSurfaceProps*) const {}
    virtual void modifyGrContextOptions(GrContextOptions*) const {}
    virtual bool veto(SinkFlags) const { return false; }
    virtual int pageCount() const { return 1; }
    virtual bool serial() const { return false; }
};
```
所有测试源的基类,定义了渲染内容的抽象接口。

#### Sink (输出目标抽象基类)
```cpp
struct Sink {
    virtual Result draw(const Src&, SkBitmap*, SkWStream*, SkString* log) const = 0;
    virtual const char* fileExtension() const = 0;
    virtual SinkFlags flags() const = 0;
    virtual void setColorSpace(sk_sp<SkColorSpace>) {}
    virtual bool serial() const { return false; }
};
```
所有输出目标的基类,定义了如何执行和输出渲染结果。

### Source 实现类

#### GMSrc
```cpp
class GMSrc : public Src {
    skiagm::GMFactory fFactory;
public:
    explicit GMSrc(skiagm::GMFactory);
};
```
Golden Master 测试源,运行标准的 GM 测试用例。

#### CodecSrc
```cpp
class CodecSrc : public Src {
    enum Mode {
        kCodec_Mode, kCodecZeroInit_Mode, kScanline_Mode,
        kStripe_Mode, kCroppedScanline_Mode, kSubset_Mode, kAnimated_Mode
    };
    Path fPath;
    Mode fMode;
    DstColorType fDstColorType;
    SkAlphaType fDstAlphaType;
    float fScale;
    bool fRunSerially;
};
```
图像编解码器测试源,支持多种解码模式(完整、扫描线、条带、子集、动画等)。

#### SKPSrc
```cpp
class SKPSrc : public Src {
    Path fPath;  // SKP 文件路径
};
```
SKP (Skia Picture) 文件测试源,用于回放录制的绘图命令。

#### BisectSrc
```cpp
class BisectSrc : public SKPSrc {
    SkString fTrail;  // 二分路径
};
```
继承自 SKPSrc,用于通过二分法定位路径绘制错误。

#### MSKPSrc (Multi-page SKP)
```cpp
class MSKPSrc : public Src {
    Path fPath;
    mutable TArray<SkDocumentPage> fPages;
public:
    int pageCount() const override;
    Result draw(int page, SkCanvas*, GraphiteTestContext*) const override;
};
```
多页 SKP 文件源,支持分页渲染。

### Sink 实现类

#### NullSink
```cpp
class NullSink : public Sink {
    // 不产生任何输出,用于性能基准测试
};
```

#### RasterSink
```cpp
class RasterSink : public Sink {
    SkColorType fColorType;
    sk_sp<SkColorSpace> fColorSpace;
};
```
软件光栅化输出,支持多种颜色类型。

#### GPUSink (Ganesh)
```cpp
class GPUSink : public Sink {
    skgpu::ContextType fContextType;
    SkCommandLineConfigGpu::SurfType fSurfType;
    int fSampleCount;
    GrContextOptions fBaseContextOptions;
    sk_gpu_test::MemoryCache fMemoryCache;
};
```
Ganesh GPU 后端输出,支持各种 GPU 配置。

#### GraphiteSink
```cpp
class GraphiteSink : public Sink {
    skiatest::graphite::TestOptions fOptions;
    skgpu::ContextType fContextType;
    SkColorType fColorType;
};
```
Graphite 新一代 GPU 后端输出。

#### PDFSink
```cpp
class PDFSink : public Sink {
    bool fPDFA;
    SkScalar fRasterDpi;
};
```
PDF 矢量格式输出。

#### SVGSink
```cpp
class SVGSink : public Sink {
    int fPageIndex;
};
```
SVG 矢量格式输出。

### Via 包装类

Via 类用于在 Sink 之前添加中间处理层:

```cpp
class Via : public Sink {
    std::unique_ptr<Sink> fSink;
};
```

派生类包括:
- **ViaMatrix**: 应用矩阵变换
- **ViaUpright**: 旋转保持直立
- **ViaSerialization**: 序列化/反序列化测试
- **ViaPicture**: 通过 SkPicture 录制和回放
- **ViaRuntimeBlend**: 使用运行时混合模式
- **ViaSVG**: 通过 SVG 转换

## 公共 API 函数

### Result 类

```cpp
// 创建成功结果
static Result Ok();

// 创建致命错误结果
static Result Fatal(const char* fmt, ...);

// 创建跳过结果
static Result Skip(const char* fmt, ...);

// 状态查询
bool isOk();
bool isFatal();
bool isSkip();
```

### Src 基类接口

```cpp
// 执行绘制
virtual Result draw(SkCanvas* canvas, GraphiteTestContext*) const = 0;

// 获取渲染尺寸
virtual SkISize size() const = 0;

// 获取源名称
virtual Name name() const = 0;

// 修改表面属性
virtual void modifySurfaceProps(SkSurfaceProps*) const;

// 修改 GPU 上下文选项
virtual void modifyGrContextOptions(GrContextOptions*) const;
virtual void modifyGraphiteContextOptions(skgpu::graphite::ContextOptions*) const;

// 否决某些 Sink 配置
virtual bool veto(SinkFlags) const;

// 是否需要串行执行
virtual bool serial() const;
```

### Sink 基类接口

```cpp
// 执行渲染并输出
virtual Result draw(const Src&, SkBitmap*, SkWStream*, SkString* log) const = 0;

// 获取文件扩展名
virtual const char* fileExtension() const = 0;

// 获取 Sink 标志
virtual SinkFlags flags() const = 0;

// 设置色彩空间
virtual void setColorSpace(sk_sp<SkColorSpace>);

// 获取颜色信息
virtual SkColorInfo colorInfo() const;

// 清理资源
virtual void done() const;
```

### CodecSrc 特有功能

```cpp
// 构造函数
CodecSrc(Path path, Mode mode, DstColorType dstColorType,
         SkAlphaType dstAlphaType, float scale);

// 解码模式枚举
enum Mode {
    kCodec_Mode,              // 标准解码
    kCodecZeroInit_Mode,      // 零初始化内存
    kScanline_Mode,           // 扫描线解码
    kStripe_Mode,             // 条带解码(测试跳过)
    kCroppedScanline_Mode,    // 裁剪扫描线
    kSubset_Mode,             // 子集解码
    kAnimated_Mode            // 动画帧解码
};
```

### GPUSink GPU 相关

```cpp
GPUSink(const SkCommandLineConfigGpu*, const GrContextOptions&);

// 创建目标表面
sk_sp<SkSurface> createDstSurface(GrDirectContext*, const Src&) const;

// 读回像素数据
bool readBack(SkSurface*, SkBitmap* dst) const;

// 获取上下文类型
skgpu::ContextType contextType() const;
```

## 内部实现细节

### 编解码器测试实现

CodecSrc 支持 7 种不同的解码模式,每种模式测试不同的 API 路径:

1. **kCodec_Mode**: 标准的 `getPixels()` 调用
2. **kCodecZeroInit_Mode**: 测试零初始化内存的处理
3. **kScanline_Mode**: 使用扫描线 API (`startIncrementalDecode/incrementalDecode`)
4. **kStripe_Mode**: 测试跳过扫描线的功能(针对 JPEG 优化)
5. **kCroppedScanline_Mode**: 测试裁剪扫描线解码
6. **kSubset_Mode**: 测试子集解码(WebP 等格式)
7. **kAnimated_Mode**: 解码动画的所有帧,网格布局显示

### 动画帧处理

```cpp
// 计算网格布局因子
const float root = sqrt((float) frameInfos.size());
const int factor = sk_float_ceil2int(root);

// 处理帧依赖关系
if (reqFrame != SkCodec::kNoFrame && reqFrame == cachedFrame) {
    memcpy(pixels.get(), priorFramePixels.get(), safeSize);
    androidOptions.fPriorFrame = reqFrame;
}
```

### GPU Sink 实现策略

GPUSink 创建 GPU 表面并处理回读:

```cpp
sk_sp<SkSurface> GPUSink::createDstSurface(GrDirectContext* ctx, const Src& src) const {
    SkImageInfo info = SkImageInfo::Make(src.size(), fColorType, fAlphaType, fColorSpace);

    if (fSurfType == SkCommandLineConfigGpu::SurfType::kDefault) {
        return SkSurfaces::RenderTarget(ctx, skgpu::Budgeted::kNo, info,
                                       fSampleCount, &surfaceProps);
    }
    // ... 其他表面类型
}
```

### DDL (Deferred Display List) 支持

GPUDDLSink 模拟 Chrome 的 DDL 使用模式:
- 在单独的录制线程上创建 DDL
- 在专用 GPU 线程上执行所有 GPU 工作
- 支持延迟着色器编译和上传

```cpp
Result GPUDDLSink::ddlDraw(const Src& src, sk_sp<SkSurface> dstSurface,
                           SkTaskGroup* recordingTaskGroup,
                           SkTaskGroup* gpuTaskGroup, ...) const {
    // 多线程 DDL 录制和回放
}
```

### Graphite 预编译测试

GraphitePrecompileTestingSink 验证预编译 API 的完整性:

1. 渲染一次并收集所有 UniqueKey
2. 清空管线缓存
3. 从 UniqueKey 重新创建管线
4. 再次渲染并验证没有创建新管线

### 色彩空间处理

```cpp
static void set_bitmap_color_space(SkImageInfo* info) {
    // 编解码器输出可能在非标准色彩空间
    // 设为 sRGB 避免绘制时再次转换
    *info = info->makeColorSpace(SkColorSpace::MakeSRGB());
}
```

### 串行执行判断

某些格式(如 RAW)在多线程解码时可能有问题:

```cpp
static bool serial_from_path_name(const SkString& path) {
    if (!FLAGS_RAW_threading) {
        static const char* const exts[] = {
            "arw", "cr2", "dng", "nef", "nrw", "orf",
            "raf", "rw2", "pef", "srw", ...
        };
        // 检查扩展名
    }
    return false;
}
```

## 依赖关系

### 核心依赖

```cpp
#include "include/core/SkCanvas.h"
#include "include/core/SkBitmap.h"
#include "include/core/SkPicture.h"
#include "include/core/SkSurface.h"
#include "include/codec/SkCodec.h"
#include "include/codec/SkAndroidCodec.h"
```

### Ganesh GPU 依赖

```cpp
#if defined(SK_GANESH)
#include "include/gpu/ganesh/GrDirectContext.h"
#include "include/gpu/ganesh/SkSurfaceGanesh.h"
#include "tools/ganesh/MemoryCache.h"
#include "tools/ganesh/DDLPromiseImageHelper.h"
#endif
```

### Graphite GPU 依赖

```cpp
#if defined(SK_GRAPHITE)
#include "include/gpu/graphite/Context.h"
#include "include/gpu/graphite/Recorder.h"
#include "include/gpu/graphite/Surface.h"
#include "tools/graphite/ContextFactory.h"
#include "tools/graphite/PipelineCallbackHandler.h"
#endif
```

### 平台特定依赖

```cpp
#if defined(SK_BUILD_FOR_ANDROID)
#include "include/ports/SkImageGeneratorNDK.h"
#include "client_utils/android/BitmapRegionDecoder.h"
#endif

#if defined(SK_BUILD_FOR_WIN)
#include "include/docs/SkXPSDocument.h"
#include "include/ports/SkImageGeneratorWIC.h"
#endif

#if defined(SK_BUILD_FOR_MAC) || defined(SK_BUILD_FOR_IOS)
#include "include/ports/SkImageGeneratorCG.h"
#endif
```

### 模块依赖

- **modules/skottie**: Lottie 动画支持
- **modules/svg**: SVG 渲染支持
- **modules/skshaper**: 文本整形
- **modules/skcms**: 色彩管理

## 设计模式与设计决策

### 1. 策略模式 (Strategy Pattern)

Src 和 Sink 是典型的策略模式实现:
- **Src 策略族**: GMSrc, CodecSrc, SKPSrc 等提供不同的测试内容
- **Sink 策略族**: RasterSink, GPUSink, PDFSink 等提供不同的输出方式
- **动态组合**: 测试框架可以任意组合 Source 和 Sink

### 2. 装饰器模式 (Decorator Pattern)

Via 类实现了装饰器模式:
```cpp
class Via : public Sink {
    std::unique_ptr<Sink> fSink;  // 包装的 Sink
};
```

Via 派生类可以链式包装,添加中间处理层(矩阵变换、序列化等)。

### 3. 模板方法模式 (Template Method)

Src 和 Sink 的基类定义了测试流程的骨架:
```cpp
// 基类定义流程
virtual Result draw(...) const = 0;  // 核心步骤由子类实现
virtual void modifySurfaceProps(...) const {}  // 可选钩子
```

### 4. 工厂模式变体

GMSrc 使用工厂函数:
```cpp
using GMFactory = skiagm::GM* (*)();
GMSrc(skiagm::GMFactory factory) : fFactory(factory) {}
```

### 设计决策

#### (1) 抽象与具体分离
- 头文件定义纯接口,实现文件包含具体逻辑
- 便于添加新的 Source 和 Sink 类型

#### (2) 条件编译
使用大量条件编译支持不同平台和配置:
```cpp
#if defined(SK_GANESH)
    // Ganesh GPU 相关代码
#endif
#if defined(SK_GRAPHITE)
    // Graphite GPU 相关代码
#endif
```

#### (3) 结果类型设计
Result 类使用三态(Ok/Fatal/Skip)而非简单的成功/失败:
- **Ok**: 测试通过
- **Fatal**: 严重错误,应停止
- **Skip**: 跳过(如配置不支持),不算失败

#### (4) Veto 机制
Source 可以否决某些 Sink 组合:
```cpp
bool CodecSrc::veto(SinkFlags flags) const {
    return flags.type != SinkFlags::kRaster || flags.approach != SinkFlags::kDirect;
}
```
这避免了无意义的测试组合(如编解码器测试不需要 GPU)。

#### (5) 串行执行控制
某些测试需要串行执行(线程不安全或资源密集):
```cpp
virtual bool serial() const { return false; }
```

## 性能考量

### 1. 内存管理

使用 SkAutoMalloc 自动管理像素缓冲区:
```cpp
SkAutoMalloc pixels(safeSize);  // 自动释放
```

对于动画帧,缓存依赖帧避免重复解码:
```cpp
SkAutoMalloc priorFramePixels;
int cachedFrame = SkCodec::kNoFrame;
if (reqFrame == cachedFrame && priorFramePixels.get()) {
    memcpy(pixels.get(), priorFramePixels.get(), safeSize);
}
```

### 2. 并行执行

通过 `serial()` 标志控制并行:
- RAW 图像默认串行(避免多线程问题)
- GPU 测试默认串行(共享上下文)
- 大多数光栅测试可以并行

### 3. GPU 资源复用

GPUSink 使用 MemoryCache 缓存着色器和管线:
```cpp
sk_gpu_test::MemoryCache fMemoryCache;
```

### 4. 条带解码优化

kStripe_Mode 测试 JPEG 跳过扫描线的优化:
```cpp
codec->skipScanlines(linesToSkip);  // 避免解码不需要的行
```

### 5. 子集解码减少内存

kSubset_Mode 只解码图像的一部分:
```cpp
subset.setXYWH(x, y, preScaleW, preScaleH);
options.fSubset = &subset;
codec->getPixels(decodeInfo, dst, rowBytes, &options);
```

### 6. 惰性初始化

某些资源(如 SVG DOM)延迟到实际绘制时创建。

## 相关文件

### 测试框架核心
- **dm/DM.cpp**: DM 主程序,驱动测试执行
- **dm/DMJsonWriter.h/cpp**: 测试结果 JSON 输出
- **tools/flags/CommonFlagsConfig.h**: 命令行配置解析

### GPU 工具
- **tools/ganesh/MemoryCache.h**: Ganesh 着色器缓存
- **tools/ganesh/DDLPromiseImageHelper.h**: DDL Promise 图像
- **tools/ganesh/DDLTileHelper.h**: DDL 分块渲染
- **tools/graphite/ContextFactory.h**: Graphite 上下文工厂
- **tools/graphite/PipelineCallbackHandler.h**: 管线回调处理

### 编解码器
- **src/codec/SkCodecImageGenerator.h**: 编解码器图像生成器
- **include/codec/SkCodec.h**: 编解码器基类
- **include/codec/SkAndroidCodec.h**: Android 编解码器

### 测试用例
- **gm/gm.h**: Golden Master 基类
- **tools/Resources.h**: 测试资源管理

### 输出格式
- **include/docs/SkPDFDocument.h**: PDF 文档生成
- **include/svg/SkSVGCanvas.h**: SVG 画布
- **modules/svg/include/SkSVGDOM.h**: SVG DOM

### 调试工具
- **tools/debugger/DebugCanvas.h**: 调试画布,用于 DebugSink

该测试框架通过灵活的 Source-Sink 组合模式,实现了对 Skia 各种渲染路径的全面测试覆盖,是 Skia 质量保证的基石。
