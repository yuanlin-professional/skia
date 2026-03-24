# SkottieTool.cpp

> 源文件: `modules/skottie/src/SkottieTool.cpp`

## 概述

`SkottieTool.cpp` 是 Skottie 模块的命令行渲染工具，用于将 Lottie/Bodymovin JSON 动画文件渲染为一系列帧图片（PNG）、Skia Picture 文件（SKP）、视频文件（MP4）或空输出（用于性能基准测试）。该工具支持 CPU 和 GPU 渲染、多线程并行处理、自定义分辨率、时间范围和帧率，是 Skottie 动画的离线批量渲染和性能测试的核心工具。它也常被用作 Skottie 功能的端到端验证工具。

## 架构位置

该文件位于 `modules/skottie/src/` 目录下，是一个独立的命令行程序。在 Skottie 的工具链中：

```
Lottie JSON -> SkottieTool (本工具)
    -> Animation::Builder::make() (解析)
    -> Animation::seekFrame() (帧跳转)
    -> Animation::render() (渲染)
    -> FrameGenerator (CPU/GPU/SKP) -> FrameSink (PNG/SKP/MP4/Null)
```

## 主要类与结构体

### `FrameSink`（抽象基类）
```cpp
class FrameSink
```
- **职责**: 帧输出的抽象接口。
- **子类**:
  - `PNGSink`: 将帧保存为 PNG 文件
  - `NullSink`: 丢弃帧数据（用于性能测试）
  - `MP4Sink`: 将帧编码为 MP4 视频（需要 `HAVE_VIDEO_ENCODER`）

### `FrameGenerator`（抽象基类）
```cpp
class FrameGenerator
```
- **职责**: 帧生成的抽象接口，负责在不同渲染后端上渲染动画帧。
- **子类**:
  - `CPUGenerator`: CPU 光栅化渲染
  - `SKPGenerator`: SkPicture 录制
  - `GPUGenerator`: GPU 渲染（需要 `SK_GANESH`）

### `Logger`
```cpp
class Logger final : public skottie::Logger
```
- **职责**: 收集动画解析过程中的错误和警告消息，并提供格式化报告。
- **内部结构**: `LogEntry { fMessage, fJSON }`

### `OutputFormat` 枚举
```cpp
enum class OutputFormat { kPNG, kSKP, kNull, kMP4 };
```

## 公共 API 函数

### `main(int argc, char** argv)`
命令行入口，支持以下参数：
- `-i` / `--input`: 输入 Lottie JSON 文件路径（必需）
- `-w` / `--writePath`: 输出目录或文件路径（必需）
- `-f` / `--format`: 输出格式（`png`, `skp`, `null`, `mp4`），默认 `png`
- `--t0`: 时间线起点 [0..1]，默认 0
- `--t1`: 时间线终点 [0..1]，默认 1
- `--fps`: 帧率（默认使用动画原生帧率）
- `--width`: 渲染宽度，默认 800
- `--height`: 渲染高度，默认 600
- `--threads`: 工作线程数（0 = CPU 核心数），默认 0
- `-g` / `--gpu`: 启用 GPU 渲染

## 内部实现细节

### 渲染流程

1. **初始化**: 解析命令行参数，注册图片解码器（PNG, JPEG, WebP），初始化字体管理器。
2. **动画加载**: 使用 `Animation::Builder` 配置字体管理器、日志器、资源提供者、预合成拦截器和文本排版工厂，从文件加载动画。
3. **缩放矩阵计算**: 通过 `SkMatrix::Rect2Rect` 将动画原始尺寸映射到目标渲染尺寸。
4. **帧计算**: 根据时间范围和帧率计算需要渲染的帧数（上限 10000 帧）。
5. **并行渲染**: 使用 `SkTaskGroup` 将帧渲染分配到多个工作线程（GPU 模式下使用单线程）。
6. **帧时间统计**: 收集每帧的渲染时间，输出最小值、中位数、平均值、最大值和总和。

### CPUGenerator 实现
- 创建 N32Premul 格式的光栅表面。
- 每帧清除画布为白色，渲染动画，然后快照为图片。

### GPUGenerator 实现（SK_GANESH 条件编译）
- 使用 GL 上下文创建 GPU 渲染表面。
- 使用异步像素读取（`asyncRescaleAndReadPixels`）避免 GPU 到 CPU 的同步等待。
- 析构时调用 `flushAndSubmit(GrSyncCpu::kYes)` 确保所有异步操作完成。

### SKPGenerator 实现
- 使用 `SkPictureRecorder` 录制渲染命令。
- 将图片序列化为 PNG 嵌入到 SKP 文件中（通过 `SkSerialProcs`）。

### MP4Sink 实现（HAVE_VIDEO_ENCODER 条件编译）
- 使用 `std::promise/future` 接收异步帧数据。
- 在 `finalize()` 中按顺序等待所有帧并编码为 MP4。
- 输出编码器"饥饿"统计信息。

### 多线程策略
- **CPU 模式**: 使用 `SkTaskGroup::batch()` 将帧分配到多个工作线程。每个线程使用 `thread_local` 的动画实例和帧生成器，避免线程间共享状态。
- **GPU 模式**: 使用单个 `GPUGenerator`（因为 GL 上下文不能跨线程共享），但仍可使用工作线程进行帧跳转。
- **LIFO 到 FIFO 转换**: `SkTaskGroup` 使用 LIFO 工作池，但工具通过 `i = frame_count - 1 - i` 反转索引，使早期帧优先开始处理。

### 资源加载链
```cpp
CachingResourceProvider
    -> DataURIResourceProviderProxy
        -> FileResourceProvider
```
- `FileResourceProvider`: 从输入文件所在目录加载外部资源文件（图片、子动画等）
- `DataURIResourceProviderProxy`: 处理 Data URI 编码的嵌入资源（`data:image/png;base64,...`），支持内联资源和字体加载
- `CachingResourceProvider`: 缓存已加载的资源，避免对相同资源的重复 I/O 和解码操作

### 帧渲染流程
```
对于每一帧 i:
    1. 获取或创建 thread_local 动画实例和帧生成器
    2. animation->seekFrame(frame0 + i * fps_scale) -- 跳转到目标帧
    3. generator->generateFrame(animation, i) -- 渲染并输出帧
       a. 清除画布 (kClearColor = 白色)
       b. animation->render(canvas) -- 渲染动画内容
       c. sink->writeFrame(image, i) -- 输出帧数据
```

## 依赖关系

### 核心依赖
- **Skia 核心**: `SkCanvas`, `SkColor`, `SkData`, `SkFontMgr`, `SkGraphics`, `SkImage`, `SkMatrix`, `SkPixmap`, `SkRect`, `SkStream`, `SkString`, `SkSurface`
- **编码器**: `SkPngEncoder`
- **解码器**: `SkCodec`, `SkJpegDecoder`, `SkWebpDecoder`, `SkPngDecoder`（条件编译）

### Skottie 依赖
- `modules/skottie/include/Skottie.h`: 核心动画 API
- `modules/skottie/include/ExternalLayer.h`: 外部图层支持
- `modules/skottie/utils/SkottieUtils.h`: `ExternalAnimationPrecompInterceptor`

### 资源依赖
- `modules/skresources/include/SkResources.h`: 资源加载框架

### GPU 依赖（条件编译）
- `include/gpu/ganesh/*`: Ganesh GPU 后端
- `tools/ganesh/GrContextFactory.h`: GPU 上下文创建

### 视频依赖（条件编译）
- `experimental/ffmpeg/SkVideoEncoder.h`: FFmpeg 视频编码

### 平台字体管理器
- macOS: `SkFontMgr_mac_ct.h`
- Android: `SkFontMgr_android.h` + FreeType
- Linux: `SkFontMgr_fontconfig.h` + FreeType
- 其他: `SkFontMgr_empty.h`

## 设计模式与设计决策

- **策略模式**: `FrameSink` 和 `FrameGenerator` 使用策略模式，允许运行时选择输出格式和渲染后端。
- **工厂方法**: `FrameSink::Make()` 和 `FrameGenerator::Make()` 根据配置创建具体实现。
- **条件编译分层**: 通过 `CPU_ONLY`, `GPU_ONLY`, `HAVE_VIDEO_ENCODER`, `SK_GANESH` 等宏控制不同构建配置下的功能可用性。
- **thread_local 模式**: 每个工作线程拥有独立的动画实例和帧生成器，避免了锁和同步。
- **Producer-Consumer（MP4）**: MP4 编码使用 `std::promise/std::future` 模式实现生产者-消费者模型。渲染线程通过 `promise::set_value()` 提交帧数据，编码线程（`finalize` 方法）通过 `future::get()` 接收帧数据。这允许渲染和编码在一定程度上并行。
- **预解码图片策略**: 使用 `ImageDecodeStrategy::kPreDecode` 确保图片在加载时即完成解码，避免在渲染热路径中触发解码操作。
- **全局实验性标志**: `gSkUseThreadLocalStrikeCaches_IAcknowledgeThisIsIncrediblyExperimental = true` 启用线程本地字体缓存（strike cache），与多线程渲染配合使用。这是一个实验性功能，变量名称本身就表达了其实验性质。
- **外部动画预合成**: 使用 `ExternalAnimationPrecompInterceptor` 支持外部动画作为预合成图层嵌入，`"__"` 作为分隔符标识外部动画引用。

## 性能考量

- **多线程并行**: 帧渲染在多个工作线程上并行执行，通过 `SkTaskGroup` 自动负载均衡。默认使用 CPU 核心数量的线程（`FLAGS_threads == 0` 时）。
- **GPU 异步读取**: `GPUGenerator` 使用 `asyncRescaleAndReadPixels` 异步像素读取，将 GPU 到 CPU 的数据传输与下一帧渲染重叠，减少 GPU 管线停顿。析构时通过 `flushAndSubmit(GrSyncCpu::kYes)` 确保所有异步操作完成。
- **thread_local 缓存**: 每个工作线程拥有独立的 `thread_local` 动画实例和帧生成器，完全避免了线程间的同步和锁竞争。这需要额外的内存（每线程一份动画副本），但换取了近乎线性的并行加速。
- **最大帧数限制**: 10000 帧上限（`kMaxFrames`）防止错误的 fps 或时间范围配置导致内存耗尽或过长的运行时间。超限时自动调整 fps。
- **PNG 编码优化**: `PNGSink` 使用最快的压缩设置（`fZLibLevel = 1`, `FilterFlag::kNone`），牺牲文件大小换取编码速度。这适合批量渲染场景，文件大小不是首要关注点。
- **帧时间统计**: 输出详细的帧时间统计信息（最小/中位/平均/最大/总和），便于性能分析和瓶颈定位。帧时间排序后的分布可以揭示是否存在长尾问题。
- **MP4 饥饿统计**: 编码器等待帧数据的时间统计（"starved stats"）揭示了渲染与编码的同步效率。理想情况下第一帧饥饿时间最长（等待渲染管线填充），后续帧接近零。
- **LIFO 工作池的处理**: `SkTaskGroup` 使用 LIFO 任务分发，但工具通过 `i = frame_count - 1 - i` 反转帧索引，确保视频的早期帧优先被渲染和编码，减少 MP4 编码的等待时间。
- **图片预解码**: 使用 `ImageDecodeStrategy::kPreDecode` 确保图片资源在加载时即完成解码，避免渲染时的解码延迟。
- **线程安全的字体缓存**: 通过设置 `gSkUseThreadLocalStrikeCaches_IAcknowledgeThisIsIncrediblyExperimental = true`，每个工作线程使用独立的字体缓存，避免全局字体缓存的锁竞争。

### 输出格式比较

| 格式 | FrameSink | FrameGenerator | 特点 |
|------|-----------|---------------|------|
| PNG | PNGSink | CPU/GPU | 逐帧独立文件，支持并行写入 |
| SKP | (内置) | SKPGenerator | Skia Picture 格式，保留绘制命令 |
| null | NullSink | CPU/GPU | 丢弃输出，仅用于性能基准测试 |
| MP4 | MP4Sink | CPU/GPU | 单一视频文件，需要 FFmpeg |

## 相关文件

- `modules/skottie/include/Skottie.h` -- 核心 Animation API（Animation, Builder）
- `modules/skottie/include/ExternalLayer.h` -- PrecompInterceptor 外部图层接口
- `modules/skottie/utils/SkottieUtils.h` -- `ExternalAnimationPrecompInterceptor` 工具实现
- `modules/skottie/utils/PreshapeTool.cpp` -- 另一个 Skottie 命令行工具（文本预排版）
- `modules/skresources/include/SkResources.h` -- 资源加载框架（FileResourceProvider 等）
- `modules/skshaper/utils/FactoryHelpers.h` -- `SkShapers::BestAvailable()` 排版引擎选择
- `src/core/SkTaskGroup.h` -- 并行任务组，支持多线程帧渲染
- `tools/flags/CommandLineFlags.h` -- 命令行参数解析框架
- `include/encode/SkPngEncoder.h` -- PNG 编码器
- `experimental/ffmpeg/SkVideoEncoder.h` -- FFmpeg 视频编码器（条件编译）
