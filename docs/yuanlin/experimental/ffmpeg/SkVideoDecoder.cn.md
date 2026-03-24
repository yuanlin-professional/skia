# SkVideoDecoder

> 源文件：experimental/ffmpeg/SkVideoDecoder.h, experimental/ffmpeg/SkVideoDecoder.cpp

## 概述

`SkVideoDecoder` 是 Skia 中基于 FFmpeg 库实现的视频解码器类。该类提供了从视频流中逐帧提取图像的能力，支持多种视频格式和编码方式。它通过封装 FFmpeg 的复杂 API，为 Skia 应用提供了简洁的视频解码接口，并能够将解码后的视频帧转换为 Skia 的 `SkImage` 对象。该实现支持 YUV 420 格式的硬件加速渲染（通过 Ganesh GPU 后端），并能够正确处理视频的色彩空间信息。

## 架构位置

`SkVideoDecoder` 在 Skia 架构中的位置：

- 位于 `experimental/ffmpeg/` 目录，属于实验性功能
- 依赖 FFmpeg 库的核心组件（libavcodec, libavformat, libavutil, libswscale）
- 与 Skia 的图像系统集成，生成 `SkImage` 对象
- 可选支持 Ganesh GPU 加速（通过 `GrRecordingContext`）
- 处理 YUV 色彩空间到 RGB 的转换
- 支持从 `SkStream` 流式读取视频数据
- 管理色彩空间转换和 ICC 配置文件

该类作为 Skia 与 FFmpeg 之间的桥梁，将视频解码能力引入 Skia 生态系统。

## 主要类与结构体

### SkVideoDecoder 类

**核心成员变量**：
```cpp
GrRecordingContext* fRecordingContext;    // GPU 上下文（不拥有所有权）
std::unique_ptr<SkStream> fStream;        // 输入流

// FFmpeg 核心对象
AVIOContext* fStreamCtx;                  // 自定义 IO 上下文
AVFormatContext* fFormatCtx;              // 封装格式上下文
AVCodecContext* fDecoderCtx;              // 解码器上下文
int fStreamIndex;                         // 视频流索引

// 解码缓冲
AVPacket fPacket;                         // 压缩数据包
AVFrame* fFrame;                          // 解码后的帧
ConvertedColorSpace fCSCache;             // 色彩空间缓存

// 解码状态机
Mode fMode;  // kProcessing_Mode | kDraining_Mode | kDone_Mode
```

**公共方法**：
```cpp
explicit SkVideoDecoder(GrRecordingContext* = nullptr);
~SkVideoDecoder();

void reset();                                   // 重置解码器
void setGrContext(GrRecordingContext*);        // 设置 GPU 上下文

bool loadStream(std::unique_ptr<SkStream>);   // 加载视频流
bool rewind();                                 // 重置到开始

SkISize dimensions() const;                    // 获取视频尺寸
double duration() const;                       // 获取时长（秒）

sk_sp<SkImage> nextImage(double* timeStamp = nullptr);  // 获取下一帧
```

### ConvertedColorSpace 结构体

色彩空间缓存，避免重复转换：
```cpp
struct ConvertedColorSpace {
    AVColorPrimaries fPrimaries;               // 色域原色
    AVColorTransferCharacteristic fTransfer;   // 传输特性（gamma）
    sk_sp<SkColorSpace> fCS;                  // 转换后的 Skia 色彩空间

    ConvertedColorSpace();
    void update(AVColorPrimaries, AVColorTransferCharacteristic);
};
```

### Mode 枚举

解码状态机的三个阶段：
```cpp
enum Mode {
    kProcessing_Mode,  // 正常处理数据包
    kDraining_Mode,    // 排空解码器缓冲
    kDone_Mode,        // 解码完成
};
```

## 公共 API 函数

### 构造与析构

**SkVideoDecoder()**
```cpp
explicit SkVideoDecoder(GrRecordingContext* rContext = nullptr)
```
- **功能**：创建解码器实例
- **参数**：可选的 GPU 上下文，用于硬件加速渲染
- **说明**：传入 GPU 上下文可启用 YUV 纹理的硬件加速

**~SkVideoDecoder()**
- **功能**：析构函数，自动调用 `reset()` 清理资源

### 流加载与控制

**loadStream()**
```cpp
bool loadStream(std::unique_ptr<SkStream> stream)
```
- **功能**：加载视频流并初始化解码器
- **参数**：包含视频数据的流对象
- **返回值**：成功返回 `true`，失败返回 `false`
- **流程**：
  1. 重置现有状态
  2. 分配自定义 IO 缓冲区
  3. 创建 FFmpeg IO 上下文
  4. 打开并分析视频格式
  5. 查找最佳视频流
  6. 初始化解码器

**rewind()**
```cpp
bool rewind()
```
- **功能**：重置解码器到视频开始位置
- **返回值**：成功返回 `true`
- **实现**：保存流对象，重置解码器，重新加载流

**reset()**
```cpp
void reset()
```
- **功能**：清理所有 FFmpeg 资源并重置状态
- **说明**：释放帧、解码器上下文、格式上下文、IO 上下文等

### 元数据查询

**dimensions()**
```cpp
SkISize dimensions() const
```
- **功能**：获取视频分辨率
- **返回值**：`SkISize` 包含宽度和高度

**duration()**
```cpp
double duration() const
```
- **功能**：获取视频总时长
- **返回值**：时长（单位：秒）

### 解码操作

**nextImage()**
```cpp
sk_sp<SkImage> nextImage(double* timeStamp = nullptr)
```
- **功能**：获取下一个视频帧
- **参数**：可选的时间戳输出参数
- **返回值**：`SkImage` 智能指针，到达结尾返回 `nullptr`
- **说明**：自动管理解码状态机，处理数据包读取和帧解码

### 上下文设置

**setGrContext()**
```cpp
void setGrContext(GrRecordingContext* rContext)
```
- **功能**：设置或更新 GPU 上下文
- **参数**：GPU 记录上下文指针

## 内部实现细节

### FFmpeg 流适配

实现两个回调函数将 `SkStream` 适配到 FFmpeg 的 IO 系统：

**skstream_read_packet()**
```cpp
static int skstream_read_packet(void* ctx, uint8_t* dstBuffer, int dstSize)
```
- 从 `SkStream` 读取数据到 FFmpeg 缓冲区
- 返回 `AVERROR_EOF` 表示流结束

**skstream_seek_packet()**
```cpp
static int64_t skstream_seek_packet(void* ctx, int64_t pos, int whence)
```
- 支持 `SEEK_SET`, `SEEK_CUR`, `SEEK_END` 三种定位方式
- 将 FFmpeg 的 seek 请求转换为 `SkStream::seek()` 调用

### 色彩空间转换系统

**YUV 色彩空间映射**
```cpp
static SkYUVColorSpace get_yuvspace(AVColorSpace space)
```
将 FFmpeg 的 `AVColorSpace` 映射到 Skia 的 `SkYUVColorSpace`：
- `AVCOL_SPC_RGB` → `kIdentity_SkYUVColorSpace`
- `AVCOL_SPC_BT709` → `kRec709_SkYUVColorSpace`
- `AVCOL_SPC_SMPTE170M/240M/BT470BG` → `kRec601_SkYUVColorSpace`

**传输特性转换**
```cpp
static skcms_TransferFunction compute_transfer(AVColorTransferCharacteristic t)
```
- 使用预定义的传输特性参数表 `gTransfer[]`
- 支持 BT.709, Gamma 2.2/2.8, SMPTE, IEC61966, BT.2020 等标准
- 计算 gamma 曲线的逆函数（编码空间到线性空间）

**色彩原色映射**
```cpp
sk_sp<SkColorSpace> make_colorspace(AVColorPrimaries primaries,
                                    AVColorTransferCharacteristic transfer)
```
- 使用预定义的色彩原色坐标表 `gPrimaries[]`
- 支持 BT.709, BT.470M/BG, SMPTE 系列, BT.2020 等标准
- 转换为 XYZ D50 矩阵并创建 `SkColorSpace`

### 帧转换机制

**convertFrame()**
```cpp
sk_sp<SkImage> convertFrame(const AVFrame* frame)
```
实现两种转换路径：

**1. YUV 420 硬件加速路径**：
```cpp
case AV_PIX_FMT_YUV420P:
    return make_yuv_420(fRecordingContext, frame->width, frame->height,
                        frame->data, frame->linesize, yuv_space, fCSCache.fCS);
```
- 创建 `SkYUVAPixmaps` 封装 Y/U/V 三个平面
- 通过 `SkImages::TextureFromYUVAPixmaps()` 创建 GPU 纹理
- 仅在提供 GPU 上下文时可用

**2. N32 通用软件路径**：
```cpp
default:
    // 使用 libswscale 转换为 RGBA/BGRA
    auto* ctx = sws_getContext(...);
    sws_scale(ctx, frame->data, frame->linesize, 0, frame->height, dst, dst_stride);
    return SkImages::RasterFromBitmap(bm);
```
- 对于不支持的像素格式，使用 FFmpeg 的 `libswscale` 转换
- 转换为 Skia 的原生 N32 格式（RGBA 或 BGRA）
- 创建栅格图像

### 解码状态机

**nextImage()** 实现三阶段解码流程：

**阶段 1：Processing Mode（处理模式）**
```cpp
while (!av_read_frame(fFormatCtx, &fPacket)) {
    if (fPacket.stream_index != fStreamIndex) continue;

    avcodec_send_packet(fDecoderCtx, &fPacket);
    if (!avcodec_receive_frame(fDecoderCtx, fFrame)) {
        return this->convertFrame(fFrame);
    }
}
fMode = kDraining_Mode;
```
- 循环读取数据包并发送给解码器
- 尝试接收解码后的帧
- 如果没有更多数据包，进入排空模式

**阶段 2：Draining Mode（排空模式）**
```cpp
avcodec_send_packet(fDecoderCtx, nullptr);  // 信号：开始排空
if (avcodec_receive_frame(fDecoderCtx, fFrame) >= 0) {
    return this->convertFrame(fFrame);
}
fMode = kDone_Mode;
```
- 发送 `nullptr` 数据包信号开始排空
- 从解码器缓冲区取出剩余的帧
- 完成后进入完成模式

**阶段 3：Done Mode（完成模式）**
- 返回 `nullptr`，表示解码结束

### 时间戳计算

```cpp
double SkVideoDecoder::computeTimeStamp(const AVFrame* frame) const {
    AVRational base = fFormatCtx->streams[fStreamIndex]->time_base;
    return 1.0 * frame->pts * base.num / base.den;
}
```
将 FFmpeg 的 PTS（Presentation Time Stamp）转换为秒：
- 使用流的 `time_base` 作为时间单位
- 计算公式：`timestamp = pts × (num / den)`

## 依赖关系

**FFmpeg 库依赖**：
- `libavcodec` - 视频编解码器
- `libavformat` - 封装格式处理
- `libavutil` - 工具函数和像素格式描述
- `libswscale` - 图像缩放和像素格式转换

**Skia 核心依赖**：
- `include/core/SkImage.h` - 图像对象
- `include/core/SkBitmap.h` - 位图对象
- `include/core/SkStream.h` - 流抽象
- `include/core/SkColorSpace.h` - 色彩空间
- `include/core/SkYUVAPixmaps.h` - YUV 平面数据

**Ganesh GPU 依赖**：
- `include/gpu/ganesh/SkImageGanesh.h` - GPU 图像创建
- `GrRecordingContext` - GPU 上下文

**色彩管理依赖**：
- `skcms` - Skia 色彩管理系统

## 设计模式与设计决策

### 适配器模式
通过 `skstream_read_packet()` 和 `skstream_seek_packet()` 回调函数，将 Skia 的 `SkStream` 适配到 FFmpeg 的 IO 系统。

### 状态模式
使用 `Mode` 枚举实现解码状态机，清晰地管理处理、排空、完成三个阶段。

### 缓存策略
`ConvertedColorSpace` 缓存上一帧的色彩空间转换结果，避免重复计算。

### 策略模式
根据像素格式选择不同的转换策略（YUV 硬件加速 vs 软件转换）。

### 关键设计决策

**1. 流式 IO 抽象**
通过 FFmpeg 的自定义 IO 机制集成 `SkStream`，而非要求文件路径，提高了灵活性。

**2. GPU 加速可选**
YUV 420 格式支持 GPU 纹理创建，但不强制要求 GPU 上下文，保持了兼容性。

**3. 懒加载与流式处理**
逐帧解码而非一次性加载整个视频，适合内存受限场景和长视频处理。

**4. 色彩空间完整支持**
正确处理视频的色彩原色、传输特性和 YUV 色彩空间，确保色彩准确性。

**5. 错误处理**
使用 `check_err()` 辅助函数记录 FFmpeg 错误，但尽可能继续处理，提高健壮性。

**6. 资源 RAII 管理**
通过 `reset()` 集中管理 FFmpeg 资源的释放，确保无内存泄漏。

## 性能考量

### YUV 硬件加速

**优势**：
- 直接创建 GPU YUV 纹理，避免 CPU 端的 YUV 到 RGB 转换
- 利用 GPU 的 YUV 采样器在着色器中完成转换
- 减少内存带宽消耗

**限制**：
- 仅支持 `AV_PIX_FMT_YUV420P` 格式
- 需要 `GrRecordingContext` 可用
- 依赖 GPU 的 YUV 采样器支持

### libswscale 回退路径

对于不支持的像素格式，使用 `libswscale` 进行软件转换：
- 灵活性高，支持几乎所有像素格式
- CPU 密集型操作，性能较低
- 考虑缓存 `SwsContext` 以减少创建开销（当前每帧创建）

### 色彩空间缓存

```cpp
fCSCache.update(frame->color_primaries, frame->color_trc);
```
- 避免每帧重新计算色彩空间矩阵和传输函数
- 对于整个视频通常使用相同的色彩空间，缓存命中率高

### IO 性能

**缓冲区大小**：
```cpp
int bufferSize = 4 * 1024;  // 4KB
```
- 较小的缓冲区可能导致频繁的 IO 调用
- 可考虑增大缓冲区（如 64KB）以提高流式读取性能

### 内存使用

**单帧缓冲**：
- 仅保持一个 `AVFrame` 对象，内存占用小
- 不适合需要帧间比较或缓存的场景

### 性能瓶颈

1. **软件 YUV 转换**：非 420P 格式的转换是主要瓶颈
2. **IO 读取**：网络流或慢速存储的读取速度
3. **解码器性能**：取决于视频编码格式和分辨率

### 优化建议

1. **缓存 SwsContext**：避免每帧创建销毁
2. **增大 IO 缓冲**：从 4KB 增加到 64KB 或更大
3. **多线程解码**：FFmpeg 支持多线程解码，可在初始化时启用
4. **预取机制**：在后台线程预解码下一帧
5. **格式协商**：如果可能，要求 FFmpeg 输出 YUV 420P 格式

## 相关文件

**相关实现**：
- `experimental/ffmpeg/SkVideoEncoder.h` - 配套的视频编码器
- `experimental/ffmpeg/SkVideoEncoder.cpp` - 编码器实现

**Skia 图像系统**：
- `include/core/SkImage.h` - 图像接口定义
- `include/core/SkYUVAPixmaps.h` - YUV 平面数据封装
- `include/gpu/ganesh/SkImageGanesh.h` - GPU 图像创建

**色彩管理**：
- `include/core/SkColorSpace.h` - 色彩空间定义
- `modules/skcms/skcms.h` - 色彩管理系统

**测试文件**：
- `tests/` 目录下的视频解码相关测试
- `tools/` 目录下的视频播放示例工具

**构建配置**：
- `BUILD.gn` - GN 构建配置，链接 FFmpeg 库
- `third_party/ffmpeg/` - FFmpeg 库的集成配置

**参考文档**：
- FFmpeg 官方文档：解码器 API 使用指南
- Skia 文档：YUV 图像处理和 GPU 纹理创建
