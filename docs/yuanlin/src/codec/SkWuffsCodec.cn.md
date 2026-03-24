# SkWuffsCodec — 基于 Wuffs 的 GIF 解码器

> 源文件：[`src/codec/SkWuffsCodec.cpp`](../../src/codec/SkWuffsCodec.cpp)

## 概述

SkWuffsCodec 是 Skia 中用于解码 GIF 图像（包括静态和动画 GIF）的编解码器实现。它基于 Google 的 Wuffs（Wrangling Untrusted File Formats Safely）库，该库是一个内存安全的 C 语言图像解码库。SkWuffsCodec 将 Wuffs 的 GIF 解码能力封装为 Skia 的 `SkCodec` 接口，支持增量解码、动画帧管理、以及多种像素格式的输出。

该文件大约 1134 行，包含了完整的 GIF 解码流程：从流中读取数据、解码图像配置、逐帧解码、帧间合成以及动画循环控制。

## 架构位置

```
SkCodec (include/codec/SkCodec.h)
  └── SkScalingCodec (src/codec/SkScalingCodec.h)
        └── SkWuffsCodec (src/codec/SkWuffsCodec.cpp)

SkFrameHolder (src/codec/SkFrameHolder.h)
  └── SkWuffsFrameHolder

SkFrame (src/codec/SkFrameHolder.h)
  └── SkWuffsFrame

外部依赖:
  wuffs-v0.3.c — Wuffs 单文件 C 库（头文件模式引入）
```

SkWuffsCodec 在 Skia 编解码器子系统中负责 GIF 格式的解码。它通过 `SkGifDecoder` 命名空间中的工厂函数注册到 Skia 的编解码器框架中。

## 主要类与结构体

### `SkWuffsFrame`
- 继承自 `SkFrame`
- 表示 GIF 动画中的单个帧
- 存储帧的 I/O 位置（`fIOPosition`）和 alpha 类型（`fReportedAlpha`）
- 从 `wuffs_base__frame_config` 构造，转换 Wuffs 的帧配置为 Skia 的帧表示
- 设置帧的边界矩形、处置方式（disposal）、持续时间和混合模式

### `SkWuffsFrameHolder`
- 继承自 `SkFrameHolder`
- 作为 `SkWuffsCodec` 到 `SkFrameHolder` 接口的间接层
- 避免 `SkWuffsCodec` 同时继承 `SkCodec` 和 `SkFrameHolder`（Skia 风格不鼓励多重继承）
- 持有指向 `SkWuffsCodec` 的指针以转发 `onGetFrame` 调用

### `SkWuffsCodec`
- 继承自 `SkScalingCodec`
- 核心解码器类，管理 Wuffs GIF 解码器的完整生命周期
- 主要成员变量：
  - `fDecoder`：Wuffs GIF 解码器实例（使用 `sk_free` 作为自定义删除器）
  - `fPrivStream`：私有管理的输入流（不传递给基类 SkCodec）
  - `fWorkbufPtr` / `fWorkbufLen`：Wuffs 解码器的工作缓冲区
  - `fIOBuffer` / `fBuffer[4096]`：I/O 缓冲区
  - `fPixelBuffer`：Wuffs 像素缓冲区
  - `fFrames`：已解码帧的列表
  - `fTwoPassPixbufPtr`：双通道解码的中间像素缓冲区
  - `fDecoderIsSuspended`：解码器协程是否处于挂起状态

## 公共 API 函数

### 命名空间 `SkGifDecoder`

```cpp
bool IsGif(const void* buf, size_t bytesRead);
```
- 通过检查前 4 个字节是否为 `"GIF8"` 来判断数据是否为 GIF 格式
- 这是一个轻量级的格式探测函数，不需要完整解析

```cpp
std::unique_ptr<SkCodec> MakeFromStream(std::unique_ptr<SkStream> stream,
                                        SkCodec::SelectionPolicy selectionPolicy,
                                        SkCodec::Result* result);
```
- 从输入流创建 GIF 编解码器
- 如果 `selectionPolicy` 不是 `kPreferStillImage` 且流不可定位，会将流拷贝到内存中
- 分配 Wuffs 解码器（使用 `sk_malloc_canfail` 而非 C++ `new`，因为 Wuffs 类型大小在编译期不确定）
- 解码图像配置并创建 `SkWuffsCodec` 实例
- 工作缓冲区通过 `decoder->workbuf_len().max_incl` 获取所需大小

```cpp
std::unique_ptr<SkCodec> Decode(std::unique_ptr<SkStream> stream,
                                SkCodec::Result* outResult,
                                SkCodecs::DecodeContext ctx);
std::unique_ptr<SkCodec> Decode(sk_sp<const SkData> data,
                                SkCodec::Result* outResult,
                                SkCodecs::DecodeContext ctx);
```
- 便捷解码函数，从流或数据创建编解码器
- `ctx` 可用于传递 `SkCodec::SelectionPolicy`
- `Decode(SkData)` 重载内部将数据包装为 `SkMemoryStream` 后委托给流版本

### SkCodec 虚函数重写

```cpp
SkEncodedImageFormat onGetEncodedFormat() const override;
```
- 始终返回 `SkEncodedImageFormat::kGIF`

```cpp
Result onGetPixels(const SkImageInfo&, void*, size_t, const Options&, int*) override;
```
- 一次性解码整个帧，内部委托给增量解码接口

```cpp
Result onStartIncrementalDecode(const SkImageInfo&, void*, size_t, const Options&) override;
Result onIncrementalDecode(int* rowsDecoded) override;
```
- 增量解码接口，支持逐步读取和解码数据

```cpp
int onGetFrameCount() override;
bool onGetFrameInfo(int, FrameInfo*) const override;
int onGetRepetitionCount() override;
IsAnimated onIsAnimated() override;
```
- 动画信息查询接口

## 内部实现细节

### 辅助函数

- **`fill_buffer`**：从 `SkStream` 读取数据填充 `wuffs_base__io_buffer`。故意将 `closed` 硬编码为 `false`，因为 Blink 的 SkStream 子类基于异步 I/O，其 `isAtEnd()` 可能返回假阳性结果。
- **`seek_buffer`**：在 I/O 缓冲区中定位。优先通过调整 `meta.ri` 读索引来定位（更廉价），仅在必要时才在底层 SkStream 中定位。
- **`wuffs_disposal_to_skia_disposal`**：将 Wuffs 动画处置方式转换为 Skia 的 `DisposalMethod`。
- **`reset_and_decode_image_config`**：重新初始化解码器并解码图像配置，设置像素格式为 BGRA 或 RGBA（非预乘）。

### 单通道 vs 双通道解码

SkWuffsCodec 实现了两种解码路径：

**单通道解码（One Pass）**：
- 直接从 Wuffs 解码器写入目标缓冲区
- 条件：Skia 像素格式被 Wuffs 支持、无颜色配置文件、不需要缩放
- 更快且使用更少内存
- 对依赖帧使用 `SRC_OVER` 混合，对独立帧使用 `SRC` 混合

**双通道解码（Two Pass）**：
- 先写入中间缓冲区，然后合成并变换到目标缓冲区
- 用于需要颜色校正、缩放、RGB565 等 Wuffs 不直接支持的功能
- 使用 `SkDraw` 进行最终的像素合成和变换
- 中间缓冲区在最后一帧解码完成后释放以节省内存

### 协程与挂起状态管理

Wuffs 解码器使用协程模型。当 `fDecoder` 方法返回不完整状态时，解码器处于挂起状态（`fDecoderIsSuspended = true`）。在挂起状态下只能：
1. 恢复协程继续执行
2. 重置所有状态重新开始

在调用 `seekFrame` 时会检查挂起状态，必要时调用 `resetDecoder` 完全重新初始化解码器。

### 帧计数与增量解码的交互

`onGetFrameCount` 在增量解码进行中时不会推进流，以避免改变 I/O 流位置导致后续增量解码出错。这与其他可回绕流的 SkCodec 实现不同。

### 流管理

SkWuffsCodec 将 `nullptr` 传递给 SkCodec 基类构造函数的流参数，自行管理流的生命周期。这是为了避免 SkCodec 默认行为过于激进地回绕流。

## 依赖关系

### Wuffs 库
- `wuffs-v0.3.c`：以头文件模式引入（未定义 `WUFFS_IMPLEMENTATION`）
- 要求版本至少为 0.3.0-alpha.4（commit count >= 2514）
- 提供 GIF 解码、像素格式转换、动画帧管理等功能

### Skia 内部依赖
- `SkCodec` / `SkScalingCodec`：编解码器基类
- `SkFrameHolder` / `SkFrame`：动画帧管理
- `SkSampler`：像素填充
- `SkDraw` / `SkRasterClip`：双通道解码中的像素合成
- `SkStreamPriv`：流工具函数
- `skcms`：颜色管理
- `SkEncodedInfo`：编码图像信息

### 标准库
- `<climits>`, `<cstdint>`, `<cstring>`, `<memory>`, `<utility>`, `<vector>`

## 设计模式与设计决策

### 间接层模式（SkWuffsFrameHolder）
为避免多重继承，使用 `SkWuffsFrameHolder` 作为间接层将 `SkFrameHolder` 接口的调用转发到 `SkWuffsCodec`。这遵循了 Skia 代码风格中避免多重继承的约定。

### C 库的 C++ 封装
Wuffs 是纯 C 库，其类型大小可能在版本间变化。因此使用 `sk_malloc_canfail` + `std::unique_ptr<T, decltype(&sk_free)>` 替代 C++ 的 `new`/`delete`，实现 RAII 风格的内存管理。

### 防御性 I/O 设计
- `fill_buffer` 中将 `closed` 硬编码为 `false`，容忍不完整输入（针对 Blink 异步 I/O 场景）
- `seek_buffer` 优先使用缓冲区内定位，减少底层流操作
- 隐藏流不传给基类，防止 SkCodec 的默认回绕行为

### 策略模式的解码路径选择
根据运行时条件（像素格式支持、颜色配置文件、缩放需求）动态选择单通道或双通道解码路径，在兼容性与性能之间取得平衡。

### 初始化标志的编译时配置
通过 `SK_WUFFS_FAVORS_PERFORMANCE_OVER_ADDITIONAL_MEMORY_SAFETY` 宏控制 Wuffs 的初始化行为，允许跳过内部缓冲区的零初始化以提升性能（Wuffs 库本身仍保证内存安全，只是减少了编译器强制的未初始化内存读取保证）。

## 性能考量

1. **单通道解码优化**：当条件满足时直接写入目标缓冲区，避免中间缓冲区的分配和拷贝。
2. **缓冲区内定位**：`seek_buffer` 优先调整读索引而非底层流定位，减少 I/O 开销。
3. **中间缓冲区的智能释放**：双通道解码在最后一帧完成后释放中间缓冲区，减少长期内存占用（针对 Chromium 中 SkCodec 可能存活很久的场景）。
4. **O(1) 内存使用**：Wuffs 设计目标为 O(1) 内存使用（像素缓冲区分配后），不依赖 O(N) 的帧 I/O 位置存储。
5. **惰性帧缓冲区分配**：`fTwoPassPixbufPtr` 仅在需要双通道解码时才分配。
6. **`sk_bzero` 优化**：在帧矩形宽度等于步幅时，使用单次 `sk_bzero` 调用替代逐行清零。
7. **4096 字节 I/O 缓冲区**：`SK_WUFFS_CODEC_BUFFER_SIZE` 定义为 4096，在内存使用和 I/O 效率之间取得平衡。
8. **流的按需拷贝**：仅在需要定位但流不可定位时才拷贝到内存流。

## 相关文件

- `include/codec/SkCodec.h` — SkCodec 基类接口
- `include/codec/SkGifDecoder.h` — GIF 解码器公共头文件
- `include/codec/SkCodecAnimation.h` — 动画相关类型定义
- `src/codec/SkScalingCodec.h` — SkScalingCodec 基类
- `src/codec/SkFrameHolder.h` — 帧管理基类
- `src/codec/SkSampler.h` — 像素采样和填充工具
- `src/codec/SkCodecPriv.h` — 编解码器内部工具
- `src/core/SkDraw.h` — 绘制操作（双通道解码使用）
- `src/core/SkStreamPriv.h` — 流工具函数
- `wuffs-v0.3.c` — Wuffs 单文件 C 库
