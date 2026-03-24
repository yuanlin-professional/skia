# dm/ - Dungeon Master 测试运行器

## 概述

`dm/` 目录包含 Skia 的主测试运行器 Dungeon Master（简称 DM）的实现代码。DM 是 Skia 持续集成系统的核心，负责发现、调度和执行 Skia 的所有测试类型——包括单元测试（tests/）、Golden Master 视觉测试（gm/）、SKP 文件回放、图像解码、Lottie 动画以及 SVG 渲染等。DM 的名字来源于桌游中的 Dungeon Master（地下城主），寓意其是整个测试世界的"主控者"。

DM 采用经典的 Source-Sink 架构设计。`Src`（数据源）负责产生渲染内容（如 GM 测试、SKP 文件、图像等），`Sink`（输出目标）负责渲染和输出（如 8888 光栅、GPU、PDF、SVG 等）。DM 通过笛卡尔积的方式将所有 Src 与兼容的 Sink 配对，形成完整的测试矩阵。

DM 支持丰富的命令行参数控制测试行为，包括源类型选择（`--src`）、配置选择（`--config`）、匹配过滤（`--match`）、跳过规则（`--skip`）、并行度控制（`--threads`）、结果输出路径（`--writePath`）等。测试结果以 JSON 格式输出到 `dm.json` 文件，并可以与已知的黄金哈希值进行比对。

DM 对 CPU 密集型测试和 GPU 密集型测试采用不同的调度策略：CPU 测试在线程池中并行执行，GPU 测试串行执行以避免 GPU 资源竞争。串行 CPU 测试（`kCPUSerial`）在所有并行工作启动前执行。

## 架构图

```
+------------------------------------------------------------------+
|                      DM.cpp (main 入口)                           |
|  +------------------------------------------------------------+  |
|  |  命令行参数解析                                              |  |
|  |  --src, --config, --match, --skip, --threads, --writePath   |  |
|  +------------------------------------------------------------+  |
|                              |                                    |
|  +------------------------------------------------------------+  |
|  |                 Source 发现与注册                             |  |
|  |  +------+ +-----+ +-----+ +------+ +--------+ +-----+     |  |
|  |  | GM   | | SKP | | MSKP| |Image | |Lottie  | | SVG |     |  |
|  |  | Src  | | Src | | Src | | Src  | | Src    | | Src |     |  |
|  |  +------+ +-----+ +-----+ +------+ +--------+ +-----+     |  |
|  +------------------------------------------------------------+  |
|                              |                                    |
|  +------------------------------------------------------------+  |
|  |                 Sink 配置与创建                               |  |
|  |  +--------+ +------+ +---------+ +-----+ +-----+           |  |
|  |  | Raster | | GPU  | |Graphite | | PDF | | SVG |           |  |
|  |  | Sink   | | Sink | | Sink    | | Sink| | Sink|           |  |
|  |  +--------+ +------+ +---------+ +-----+ +-----+           |  |
|  |  +------------------------------------------+               |  |
|  |  | Via (间接 Sink): ViaMatrix, ViaPicture,  |               |  |
|  |  | ViaSerialization, ViaRuntimeBlend, ViaSVG|               |  |
|  |  +------------------------------------------+               |  |
|  +------------------------------------------------------------+  |
|                              |                                    |
|  +------------------------------------------------------------+  |
|  |            Src x Sink 配对 (笛卡尔积)                       |  |
|  |  过滤: Src::veto(SinkFlags) / --skip / --match              |  |
|  +------------------------------------------------------------+  |
|                              |                                    |
|  +------------------------------------------------------------+  |
|  |              任务调度与执行                                   |  |
|  |  +------------------+  +------------------+                 |  |
|  |  | CPU 线程池       |  | GPU 串行队列     |                 |  |
|  |  | (kCPU 并行测试) |  | (kGanesh/kGraphite)|              |  |
|  |  +------------------+  +------------------+                 |  |
|  +------------------------------------------------------------+  |
|                              |                                    |
|  +------------------------------------------------------------+  |
|  |              结果输出                                        |  |
|  |  JsonWriter -> dm.json                                      |  |
|  |  Hash + Encode -> PNG/PDF/SVG 文件                          |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

## 目录结构

```
dm/
├── BUILD.bazel           # Bazel 构建配置
├── DM.cpp                # 主入口文件 (main 函数、测试发现与调度)
├── DMGpuTestProcs.cpp    # GPU 测试过程的实现
├── DMSrcSink.h           # Source 和 Sink 类层次结构定义
├── DMSrcSink.cpp         # Source 和 Sink 实现
├── DMJsonWriter.h        # JSON 结果写入器定义
└── DMJsonWriter.cpp      # JSON 结果写入器实现
```

## 关键类与函数

### Source 类层次结构（DMSrcSink.h）

| 类 | 说明 | 数据来源 |
|----|------|----------|
| `Src` | 抽象基类 | - |
| `GMSrc` | Golden Master 测试 | `gm/` 注册的 GM 工厂 |
| `CodecSrc` | 图像编解码测试 | 图像文件 |
| `AndroidCodecSrc` | Android 编解码测试 | 图像文件 |
| `BRDSrc` | 位图区域解码测试 | 图像文件 |
| `ImageGenSrc` | 图像生成器测试 | 图像文件 |
| `ColorCodecSrc` | 色彩编解码测试 | 图像文件 |
| `SKPSrc` | SKP 文件回放 | .skp 文件 |
| `BisectSrc` | SKP 路径二分查找 | .skp 文件 + 路径 |
| `SkottieSrc` | Lottie 动画测试 | .json 文件 |
| `SVGSrc` | SVG 渲染测试 | .svg 文件 |
| `MSKPSrc` | 多页 SKP 测试 | .mskp 文件 |

### Sink 类层次结构（DMSrcSink.h）

| 类 | 说明 | 输出格式 |
|----|------|----------|
| `Sink` | 抽象基类 | - |
| `NullSink` | 空输出 | 无 |
| `RasterSink` | CPU 光栅化 | PNG |
| `GPUSink` | Ganesh GPU 渲染 | PNG |
| `GPUSlugSink` | Slug 文本渲染 | PNG |
| `GPUSerializeSlugSink` | 序列化 Slug | PNG |
| `GPURemoteSlugSink` | 远程 Slug | PNG |
| `GPUPersistentCacheTestingSink` | 持久化缓存测试 | 无 |
| `GaneshPrecompileTestingSink` | Ganesh 预编译测试 | 无 |
| `GPUDDLSink` | 延迟显示列表 | PNG |
| `GraphiteSink` | Graphite GPU 渲染 | PNG |
| `GraphitePrecompileTestingSink` | Graphite 预编译测试 | 无 |
| `GraphitePipelineTrackingSink` | Pipeline 追踪 | 无 |
| `GraphitePersistentPipelineStorageTestingSink` | 持久化存储测试 | 无 |
| `PDFSink` | PDF 文档生成 | PDF |
| `XPSSink` | XPS 文档生成 | XPS |
| `SKPSink` | SKP 录制 | SKP |
| `DebugSink` | 调试 JSON 输出 | JSON |
| `SVGSink` | SVG 输出 | SVG |

### Via 类（间接 Sink）

| 类 | 说明 |
|----|------|
| `Via` | Via 抽象基类，包装另一个 Sink |
| `ViaMatrix` | 应用矩阵变换后再渲染 |
| `ViaUpright` | 应用竖直变换后再渲染 |
| `ViaSerialization` | 序列化/反序列化后再渲染 |
| `ViaPicture` | 录制为 Picture 后再渲染 |
| `ViaRuntimeBlend` | 使用运行时混合后再渲染 |
| `ViaSVG` | 转换为 SVG 后再渲染 |

### Result 类

```cpp
class Result {
    enum class Status : int { Ok, Fatal, Skip };
    static Result Ok();
    static Result Fatal(const char* fmt, ...);
    static Result Skip(const char* fmt, ...);
    bool isOk();
    bool isFatal();
    bool isSkip();
};
```

### SinkFlags 结构体

```cpp
struct SinkFlags {
    enum Type { kNull, kGPU, kVector, kRaster } type;
    enum Approach { kDirect, kIndirect } approach;
    enum Multisampled { kNotMultisampled, kMultisampled } multisampled;
};
```

### JsonWriter 类（DMJsonWriter.h）

```cpp
class JsonWriter {
    struct BitmapResult {
        SkString name;           // 如 "ninepatch-stretch"
        SkString config;         // 如 "gpu", "8888"
        SkString sourceType;     // 如 "gm", "skp", "image"
        SkString sourceOptions;  // 如 "codec", "subset"
        SkString md5;            // 32 字节 ASCII 哈希
        SkString ext;            // 如 "png", "pdf"
        SkString gamut;          // 色域
        SkString transferFn;     // 传输函数
        SkString colorType;      // 颜色类型
        SkString alphaType;      // Alpha 类型
        SkString colorDepth;     // 颜色深度
    };
    static void AddBitmapResult(const BitmapResult&);     // 线程安全
    static void DumpJson(const char* dir, ...);           // 写入 dm.json
    static bool ReadJson(const char* path, callback);     // 读取已有结果
};
```

### 核心命令行参数

| 参数 | 说明 |
|------|------|
| `--src` | 源类型列表: "tests gm skp mskp lottie rive svg image colorImage" |
| `--config` | 渲染配置: "8888 gpu gl vk mtl dawn graphite pdf svg ..." |
| `--match` / `-m` | 测试名称匹配过滤器（支持 ~、^、$ 修饰符） |
| `--skip` | 按 config/src/srcOptions/name 四元组跳过特定测试 |
| `--writePath` / `-w` | 输出文件路径 |
| `--readPath` / `-r` | 黄金结果比对路径 |
| `--threads` / `-j` | 并行线程数（默认 CPU 核心数） |
| `--key` | JSON 标识键值对 |
| `--properties` | JSON 属性键值对 |
| `--cpu` / `--gpu` / `--graphite` | 控制是否运行各类工作 |
| `--dryRun` | 仅打印将要运行的测试，不实际执行 |
| `--verbose` / `-v` | 详细输出 |

## 依赖关系

```
dm/ 依赖关系:
├── tests/Test.h                     (单元测试注册表)
├── tests/TestHarness.h              (测试线束)
├── gm/gm.h                         (GM 注册表)
├── dm/DMSrcSink.h                   (Src/Sink 类层次)
├── dm/DMJsonWriter.h                (JSON 结果输出)
├── include/core/                    (Skia 核心 API)
├── src/core/SkTaskGroup.h           (并行任务组)
├── src/core/SkMD5.h                 (MD5 哈希)
├── tools/flags/CommonFlags*.h       (命令行配置)
├── tools/HashAndEncode.h            (哈希与编码)
├── tools/Resources.h                (测试资源)
├── tools/ToolUtils.h                (工具函数)
├── tools/ganesh/GrContextFactory.h  (Ganesh 上下文工厂)
├── tools/graphite/ContextFactory.h  (Graphite 上下文工厂)
├── tools/trace/                     (追踪工具)
└── tools/ProcStats.h                (进程统计)
```

## 设计模式分析

### 1. Source-Sink 架构

DM 的核心设计是 Source-Sink 分离。Source 负责"要画什么"（内容），Sink 负责"画在哪里"（目标）。这种解耦使得新增内容类型（如新的文件格式）或新增渲染目标（如新的 GPU 后端）都很简单。

### 2. 装饰器模式（Decorator Pattern）

`Via` 类是经典的装饰器模式应用。它包装一个内部 Sink，在渲染前后插入额外的处理步骤（如矩阵变换、序列化/反序列化、Picture 录制等）。Via 可以嵌套组合使用。

### 3. 任务并行模式

DM 使用 `SkTaskGroup` 实现并行执行。CPU 测试被分发到线程池中并行执行，GPU 测试在专用线程上串行执行。测试结果的收集通过线程安全的 `JsonWriter::AddBitmapResult` 实现。

### 4. 笛卡尔积测试矩阵

DM 将所有 Source 和 Sink 进行笛卡尔积配对，然后通过 `Src::veto(SinkFlags)` 和 `--skip` 规则过滤不兼容的组合。这确保了每种内容在每种目标上都被测试到。

### 5. 哈希比对模式

测试输出不是直接进行像素级比较，而是计算 MD5 哈希。这使得结果比对既快速又节省存储空间。新的哈希值需要通过 Gold 审批服务进行人工审核。

## 数据流

```
DM 完整执行流程:

1. 启动阶段
   main() -> 解析命令行参数
          |
          v
   注册 Src: 遍历 GMRegistry, 扫描 SKP/图像目录
          |
          v
   注册 Sink: 根据 --config 创建各种 Sink
          |
          v
   配对: Src x Sink (过滤 veto/skip/match)

2. 执行阶段
   创建 SkTaskGroup (线程池)
          |
          +-- CPU Serial Tests (先执行) --+
          |                                 |
          +-- CPU Tests (并行执行) --------+
          |                                 |
          +-- GPU Tests (串行执行) --------+
          |                                 |
          v                                 v
   各 Task: Src::draw(canvas) -> Sink::draw(src, bitmap)
          |
          v
   HashAndEncode: 计算 MD5, 编码 PNG (如需输出)
          |
          v
   JsonWriter::AddBitmapResult() (线程安全)

3. 输出阶段
   JsonWriter::DumpJson() -> dm.json
          |
          v
   上传到 Gold / 与 --readPath 比对
          |
          v
   输出总结: N tests run, M failures
```

## 相关文档与参考

- `dm/DM.cpp` - DM 主入口，包含 main 函数和测试调度逻辑
- `dm/DMSrcSink.h` - Source 和 Sink 完整类层次结构定义
- `dm/DMSrcSink.cpp` - Source 和 Sink 实现细节
- `dm/DMJsonWriter.h` - JSON 结果格式定义
- `tests/Test.h` - 单元测试注册宏和框架
- `gm/gm.h` - GM 注册宏和框架
- `tools/flags/CommonFlags.h` - 通用命令行参数
- `tools/flags/CommonFlagsConfig.h` - 配置相关命令行参数
