# bench/ - Skia 性能基准测试目录

## 概述

`bench/` 目录是 Skia 图形库的性能基准测试（benchmark）核心目录，包含约 148 个文件，覆盖了 Skia 从 CPU 光栅化到 GPU 渲染的各个关键路径。基准测试的主要目标是持续追踪 Skia 各项操作的性能指标，及时发现性能退化。

基准测试框架以 `Benchmark` 基类为核心（定义在 `Benchmark.h` 中），所有具体的基准测试通过继承该类并实现 `onDraw()` 方法来定义被测操作。框架支持多种后端（Backend），包括非渲染（`kNonRendering`）、光栅（`kRaster`）、Ganesh GPU（`kGanesh`）、Graphite GPU（`kGraphite`）、PDF 和 HWUI。

测试的主入口是 `nanobench.cpp`，它实现了完整的基准测试运行器，包括自动循环调优（确保计时稳定）、多配置运行、JSON 格式结果输出、以及与 Skia 基础设施的集成。`nanobench` 能够自动扫描注册的基准测试，并根据命令行参数控制运行哪些测试、使用哪些配置。

`bench/graphite/` 子目录包含专门针对 Graphite 新 GPU 后端的基准测试，测试 Graphite 特有的数据结构如 `BoundsManager` 和 `IntersectionTree` 的性能。

Skia 的基准测试结果会被持续集成系统收集，并通过 Perf 仪表板展示性能趋势。每次提交都会触发基准测试运行，确保性能退化能够被及时发现和修复。

## 架构图

```
+------------------------------------------------------------------+
|                    nanobench (基准测试运行器)                      |
|  +------------------------------------------------------------+  |
|  |                  BenchRegistry (注册表)                      |  |
|  |  +------------------+  +------------------+                 |  |
|  |  | DEF_BENCH 注册   |  | GMBench 适配    |                 |  |
|  |  +------------------+  +------------------+                 |  |
|  +------------------------------------------------------------+  |
|                              |                                    |
|  +------------------------------------------------------------+  |
|  |                    Config (配置)                             |  |
|  |  +---------+ +--------+ +--------+ +----------+ +-----+    |  |
|  |  | NonRend | | Raster | | Ganesh | | Graphite | | PDF |    |  |
|  |  +---------+ +--------+ +--------+ +----------+ +-----+    |  |
|  +------------------------------------------------------------+  |
|                              |                                    |
|  +------------------------------------------------------------+  |
|  |                    Target (目标)                             |  |
|  |  setup() -> beginTiming() -> draw(loops) -> submitFrame()  |  |
|  |  -> submitWorkAndSyncCPU() -> capturePixels()              |  |
|  +------------------------------------------------------------+  |
|                              |                                    |
|  +------------------------------------------------------------+  |
|  |             NanoJSONResultsWriter (结果写入)                 |  |
|  |  beginBench() -> appendMetric() -> endBench()              |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

## 目录结构

```
bench/
├── BUILD.bazel                    # Bazel 构建配置
├── Benchmark.h                    # 基准测试基类
├── Benchmark.cpp                  # 基准测试基类实现
├── nanobench.h                    # 运行器头文件 (Config/Target 定义)
├── nanobench.cpp                  # 运行器主入口
├── ResultsWriter.h                # JSON 结果写入器
├── BenchLogger.h / .cpp           # 日志记录器
├── GpuTools.h                     # GPU 通用刷新工具
├── GMBench.h / .cpp               # GM-to-Benchmark 适配器
├── SKPBench.h / .cpp              # SKP 文件基准测试
├── SKPAnimationBench.h / .cpp     # SKP 动画基准测试
├── MSKPBench.h / .cpp             # 多页 SKP 基准测试
├── RecordingBench.h / .cpp        # 录制操作基准测试
├── SkSLBench.h / .cpp             # SkSL 编译器基准测试
├── SkGlyphCacheBench.h / .cpp     # 字形缓存基准测试
├── CodecBench.h / .cpp            # 图像编解码基准测试
├── CodecBenchPriv.h               # 编解码私有工具
├── AndroidCodecBench.h / .cpp     # Android 编解码基准测试
├── BitmapRegionDecoderBench.h/.cpp # 位图区域解码基准测试
├── BigPath.h / .cpp               # 大路径测试数据
├── gUniqueGlyphIDs.h              # 唯一字形ID数据
├── microbench.json                # 微基准测试配置
├── skpbench.json                  # SKP 基准测试配置
│
├── graphite/                      # Graphite GPU 后端基准测试
│   ├── BoundsManagerBench.cpp     # 边界管理器基准
│   └── IntersectionTreeBench.cpp  # 相交树基准
│
├── [绘制操作基准测试]
│   ├── AAClipBench.cpp            # 抗锯齿裁剪
│   ├── BlurBench.cpp              # 模糊效果
│   ├── BlurImageFilterBench.cpp   # 模糊图像滤镜
│   ├── BlurRectBench.cpp          # 矩形模糊
│   ├── DashBench.cpp              # 虚线效果
│   ├── DrawBitmapAABench.cpp      # 抗锯齿位图绘制
│   ├── GradientBench.cpp          # 渐变效果
│   ├── LineBench.cpp              # 线条绘制
│   ├── PathBench.cpp              # 路径操作
│   ├── RectBench.cpp              # 矩形绘制
│   ├── StrokeBench.cpp            # 描边操作
│   └── TextBlobBench.cpp          # 文本渲染
│
├── [图像处理基准测试]
│   ├── CodecBench.cpp             # 编解码性能
│   ├── DecodeBench.cpp            # 解码性能
│   ├── EncodeBench.cpp            # 编码性能
│   ├── FilteringBench.cpp         # 过滤操作
│   ├── ImageBench.cpp             # 图像操作
│   ├── ImageCacheBench.cpp        # 图像缓存
│   ├── MipmapBench.cpp            # Mipmap 生成
│   └── SwizzleBench.cpp           # 像素通道重排
│
├── [数据结构基准测试]
│   ├── ChecksumBench.cpp          # 校验和算法
│   ├── MathBench.cpp              # 数学运算
│   ├── MatrixBench.cpp            # 矩阵操作
│   ├── Matrix44Bench.cpp          # 4x4 矩阵操作
│   ├── SortBench.cpp              # 排序算法
│   ├── RTreeBench.cpp             # R-Tree 空间索引
│   ├── MemsetBench.cpp            # 内存填充
│   ├── RefCntBench.cpp            # 引用计数
│   └── MutexBench.cpp             # 互斥锁
│
├── [GPU 特定基准测试]
│   ├── CreateBackendTextureBench.cpp # GPU 纹理创建
│   ├── GrMemoryPoolBench.cpp      # Ganesh 内存池
│   ├── GrMipmapBench.cpp          # Ganesh Mipmap
│   ├── GrQuadBench.cpp            # Ganesh 四边形
│   ├── GrResourceCacheBench.cpp   # Ganesh 资源缓存
│   ├── TessellateBench.cpp        # 曲面细分
│   └── ClipStrategyBench.cpp      # 裁剪策略
│
└── [其他基准测试]
    ├── ParagraphBench.cpp          # 段落排版
    ├── SkSLBench.cpp               # 着色器编译
    ├── PDFBench.cpp                # PDF 生成
    ├── JSONBench.cpp               # JSON 处理
    ├── RegionBench.cpp             # 区域操作
    └── TriangulatorBench.cpp       # 三角化
```

## 关键类与函数

### Benchmark 基类（Benchmark.h）

```cpp
class Benchmark : public SkRefCnt {
public:
    enum class Backend {
        kNonRendering,  // 纯计算，无渲染
        kRaster,        // CPU 光栅化
        kGanesh,        // Ganesh GPU 后端
        kGraphite,      // Graphite GPU 后端
        kPDF,           // PDF 文档
        kHWUI,          // Android HWUI
    };

    const char* getName();               // 获取基准测试名称
    const char* getUniqueName();         // 获取唯一标识名
    SkISize getSize();                   // 获取渲染尺寸
    virtual bool isSuitableFor(Backend); // 检查是否适用于特定后端
    void draw(int loops, SkCanvas*, ...); // 执行绘制循环

protected:
    virtual const char* onGetName() = 0;          // 子类必须实现
    virtual void onDraw(int loops, SkCanvas*) = 0; // 核心绘制循环
    virtual void onDelayedSetup() {}               // 延迟初始化
    virtual void onPerCanvasPreDraw(SkCanvas*) {}  // 每个 Canvas 前置处理
    virtual void onPerCanvasPostDraw(SkCanvas*) {} // 每个 Canvas 后置处理
};
```

### Config 结构体（nanobench.h）

```cpp
struct Config {
    SkString name;                     // 配置名称 (如 "8888", "gpu")
    Benchmark::Backend backend;        // 后端类型
    SkColorType color;                 // 颜色类型
    SkAlphaType alpha;                 // Alpha 类型
    sk_sp<SkColorSpace> colorSpace;    // 色彩空间
    int samples;                       // 多采样数
    GrContextFactory::ContextType ctxType;      // GPU 上下文类型
    GrContextFactory::ContextOverrides ctxOverrides; // 上下文覆盖
    uint32_t surfaceFlags;             // Surface 标志
};
```

### Target 结构体（nanobench.h）

```cpp
struct Target {
    const Config config;               // 关联的配置
    sk_sp<SkSurface> surface;          // 渲染目标 Surface

    void setup();                      // 初始化目标
    virtual SkCanvas* beginTiming(SkCanvas*); // 计时前准备
    virtual void submitFrame();        // 提交帧
    virtual void submitWorkAndSyncCPU(); // 同步 GPU 工作
    virtual bool needsFrameTiming(int* frameLag) const; // 帧计时
    virtual bool init(SkImageInfo, Benchmark*); // 初始化
    virtual bool capturePixels(SkBitmap*);      // 捕获像素
};
```

### NanoJSONResultsWriter（ResultsWriter.h）

```cpp
class NanoJSONResultsWriter : public SkJSONWriter {
    void beginBench(const char* name, int32_t x, int32_t y);
    void endBench();
    void appendMetric(const char* name, double value); // 跳过 NaN/Inf 值
};
```

### 注册宏

```cpp
// 基本注册宏
DEF_BENCH(return new MyBenchmark(...))

// 展开为:
static BenchRegistry gBenchN([](void*) -> Benchmark* {
    return new MyBenchmark(...);
});
```

### GMBench 适配器（GMBench.h）

`GMBench` 类将 `skiagm::GM` 实例包装为 `Benchmark` 对象，允许 Golden Master 测试也能作为性能基准运行。这体现了适配器设计模式的应用。

## 依赖关系

```
bench/ 依赖关系图:

    bench/Benchmark.h
    ├── include/core/SkRefCnt.h          (引用计数基类)
    ├── include/core/SkSize.h            (尺寸类型)
    ├── include/core/SkString.h          (字符串)
    ├── include/private/base/SkTArray.h  (数组)
    ├── tools/Registry.h                 (注册表模板)
    └── include/gpu/graphite/Context.h   (Graphite 上下文)

    bench/nanobench.cpp
    ├── bench/Benchmark.h                (基准测试基类)
    ├── bench/nanobench.h                (Config/Target)
    ├── bench/ResultsWriter.h            (结果输出)
    ├── bench/GMBench.h                  (GM 适配器)
    ├── bench/SKPBench.h                 (SKP 基准)
    ├── bench/MSKPBench.h                (MSKP 基准)
    ├── bench/RecordingBench.h           (录制基准)
    ├── bench/SkSLBench.h                (SkSL 基准)
    ├── tools/flags/CommonFlags*.h       (命令行配置)
    ├── tools/Stats.h                    (统计工具)
    ├── tools/CrashHandler.h             (崩溃处理)
    └── tools/ganesh/GrContextFactory.h  (GPU 上下文工厂)

    外部交互:
    ├── gm/ (通过 GMBench 适配器运行 GM 作为基准)
    ├── tools/flags/ (命令行参数)
    └── Skia Perf (性能数据仪表板)
```

## 设计模式分析

### 1. 注册表模式（Registry Pattern）

与测试框架类似，`BenchRegistry` 使用全局链表收集所有通过 `DEF_BENCH` 宏注册的基准测试工厂函数。`nanobench` 在运行时遍历该链表，实例化并执行每个基准测试。

### 2. 模板方法模式（Template Method Pattern）

`Benchmark` 基类定义了完整的测试执行骨架：`delayedSetup()` -> `perCanvasPreDraw()` -> `preDraw()` -> `draw()` -> `postDraw()` -> `perCanvasPostDraw()`。子类通过覆写 `onDraw()`、`onDelayedSetup()` 等虚函数定制行为，而整体执行流程保持不变。

### 3. 策略模式（Strategy Pattern）

`Target` 结构体封装了不同后端的执行策略。CPU 目标直接返回 Canvas，GPU 目标需要处理帧提交和同步。通过 `Config` 配置，`nanobench` 可以在运行时选择不同的目标策略。

### 4. 适配器模式（Adapter Pattern）

`GMBench` 将 `skiagm::GM` 接口适配为 `Benchmark` 接口，`SKPBench` 将 SKP 文件回放适配为基准测试。这种设计允许不同类型的内容统一参与性能测量。

### 5. 自动调优模式

`nanobench` 会自动调整循环次数（`loops`），以确保每次测量达到足够的时间精度。测量框架先进行校准运行确定合适的循环数，再进行正式测量。

## 数据流

```
nanobench 执行流程:

1. 初始化阶段
   解析命令行参数 (--config, --match, --samples, ...)
          |
          v
   构建 Config 列表 (8888, gpu, gl, vk, mtl, ...)
          |
          v
   遍历 BenchRegistry 获取所有基准测试

2. 执行阶段 (对每个 Benchmark x Config 组合)
   创建 Target (含 SkSurface)
          |
          v
   target->setup() / bench->delayedSetup()
          |
          v
   校准循环数 (自动确定 loops)
          |
          +-- 重复 N 次采样 --+
          |                     |
          v                     v
   bench->perCanvasPreDraw()    |
          |                     |
          v                     |
   [开始计时]                   |
   for (i = 0; i < loops; i++) |
       bench->draw()           |
   [结束计时]                   |
          |                     |
          v                     |
   bench->perCanvasPostDraw()   |
          |                     |
          +---------------------+
          |
          v
   计算统计量 (min, median, mean, stddev)
          |
          v
   NanoJSONResultsWriter 写入结果

3. 输出阶段
   生成 JSON 结果文件
          |
          v
   上传到 Skia Perf 仪表板
```

## 基准测试分类详览

### 绘制基准测试

| 文件 | 测量内容 |
|------|----------|
| `AAClipBench.cpp` | 抗锯齿裁剪路径的性能 |
| `BlurBench.cpp` | 各种模糊效果的渲染速度 |
| `GradientBench.cpp` | 线性/径向/锥形渐变性能 |
| `PathBench.cpp` | 路径创建、操作和绘制性能 |
| `RectBench.cpp` | 矩形绘制吞吐量 |
| `StrokeBench.cpp` | 路径描边性能 |
| `TextBlobBench.cpp` | 文本渲染吞吐量 |
| `ShapesBench.cpp` | 批量形状绘制性能 |

### 编解码基准测试

| 文件 | 测量内容 |
|------|----------|
| `CodecBench.cpp` | 图像解码性能 (各种格式) |
| `EncodeBench.cpp` | 图像编码性能 |
| `DecodeBench.cpp` | 原始解码速度 |
| `AndroidCodecBench.cpp` | Android 编解码路径性能 |

### 算法与数据结构基准测试

| 文件 | 测量内容 |
|------|----------|
| `MathBench.cpp` | 基础数学运算 (三角函数、开方等) |
| `MatrixBench.cpp` | 矩阵乘法、求逆 |
| `ChecksumBench.cpp` | 哈希/校验和算法 |
| `SortBench.cpp` | 排序算法 |
| `RTreeBench.cpp` | R-Tree 空间查询 |
| `MemsetBench.cpp` | 内存填充性能 |

### GPU 特定基准测试

| 文件 | 测量内容 |
|------|----------|
| `CreateBackendTextureBench.cpp` | GPU 纹理创建延迟 |
| `GrResourceCacheBench.cpp` | Ganesh 资源缓存性能 |
| `GrMemoryPoolBench.cpp` | Ganesh 内存池分配性能 |
| `TessellateBench.cpp` | GPU 曲面细分 |

## 相关文档与参考

- `bench/Benchmark.h` - 基准测试基类定义
- `bench/nanobench.h` - 运行器核心类型（Config、Target）
- `bench/nanobench.cpp` - 运行器主入口和执行逻辑
- `bench/ResultsWriter.h` - JSON 结果输出格式
- `bench/GpuTools.h` - GPU 刷新工具函数
- `bench/GMBench.h` - GM-to-Benchmark 适配器
- `bench/graphite/` - Graphite 专用基准测试
- `tools/Stats.h` - 统计计算工具
- `tools/flags/CommonFlags.h` - 通用命令行参数
