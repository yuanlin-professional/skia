# SkVideoEncoder

> 源文件：experimental/ffmpeg/SkVideoEncoder.h, experimental/ffmpeg/SkVideoEncoder.cpp

## 概述

`SkVideoEncoder` 是 Skia 中基于 FFmpeg 库实现的视频编码器类。该类提供了将一系列 Skia 图像或绘图操作编码为视频文件的能力，支持将帧序列转换为 MP4 格式的视频输出。它通过封装 FFmpeg 的编码 API，为 Skia 应用提供了简洁的视频创建接口，并自动处理像素格式转换（RGB/RGBA 到 YUV 420P）和视频封装。该实现特别适合从 Skia 渲染内容生成动画视频的场景。

## 架构位置

`SkVideoEncoder` 在 Skia 架构中的位置：

- 位于 `experimental/ffmpeg/` 目录，属于实验性功能
- 依赖 FFmpeg 的编码组件（libavcodec, libavformat, libswscale）
- 接受 Skia 的 `SkPixmap` 或提供 `SkCanvas` 进行绘图
- 使用 `libswscale` 进行 RGB 到 YUV 色彩空间转换
- 输出 MP4 格式的视频数据（`SkData` 对象）
- 内部使用 `SkRandomAccessWStream` 实现随机访问写入
- 与 `SkVideoDecoder` 形成编解码对

该类作为 Skia 渲染到视频的桥梁，支持动画导出和屏幕录制等应用场景。

## 主要类与结构体

### SkVideoEncoder 类

**核心成员变量**：
```cpp
// FFmpeg 编码组件
SwsContext* fSWScaleCtx;              // 像素格式转换上下文
AVIOContext* fStreamCtx;              // 自定义 IO 上下文
AVFormatContext* fFormatCtx;          // 封装格式上下文
AVCodecContext* fEncoderCtx;          // 编码器上下文
AVStream* fStream;                    // 视频流（不拥有所有权）
AVFrame* fFrame;                      // 帧缓冲
AVPacket* fPacket;                    // 编码数据包

// Skia 相关
SkImageInfo fInfo;                    // 视频帧信息
std::unique_ptr<SkRandomAccessWStream> fWStream;  // 输出流
sk_sp<SkSurface> fSurface;           // 懒加载的绘图表面

// 时间管理
int64_t fCurrentPTS;                  // 当前展示时间戳
int64_t fDeltaPTS;                    // 帧间时间增量
```

**公共方法**：
```cpp
SkVideoEncoder();
~SkVideoEncoder();

// 录制控制
bool beginRecording(SkISize dimensions, int fps);
sk_sp<SkData> endRecording();

// 添加帧 - 方式1：直接提供像素数据
bool addFrame(const SkPixmap&);

// 添加帧 - 方式2：使用 Canvas 绘制
SkCanvas* beginFrame();
bool endFrame();
```

### SkRandomAccessWStream 类

内部辅助类，实现支持随机访问的内存写入流：
```cpp
class SkRandomAccessWStream {
    SkTDArray<char> fStorage;         // 动态数组存储
    size_t fPos;                      // 当前写入位置

public:
    void write(const void* src, size_t bytes);  // 写入数据
    void seek(size_t pos);                      // 定位
    sk_sp<SkData> detachAsData();              // 分离数据
};
```

**特性**：
- 支持覆写已有数据（用于 MP4 头部回写）
- 支持随机定位
- 最终转换为 `SkData` 对象

## 公共 API 函数

### 构造与析构

**SkVideoEncoder()**
```cpp
SkVideoEncoder()
```
- **功能**：创建编码器实例
- **初始化**：设置 `fInfo` 为 `MakeUnknown()`

**~SkVideoEncoder()**
- **功能**：析构函数，清理所有 FFmpeg 资源
- **操作**：调用 `reset()` 并释放 `SwsContext`

### 录制会话管理

**beginRecording()**
```cpp
bool beginRecording(SkISize dimensions, int fps)
```
- **功能**：开始新的视频录制会话
- **参数**：
  - `dimensions`: 视频分辨率（必须为偶数，YUV 420 要求）
  - `fps`: 帧率（每秒帧数）
- **返回值**：成功返回 `true`
- **限制**：尺寸的宽高必须为偶数
- **流程**：
  1. 验证尺寸有效性
  2. 创建 N32 色彩类型的 `SkImageInfo`
  3. 初始化 FFmpeg 编码器（MP4 格式，H.264 编码）
  4. 配置色彩空间转换器（RGB/RGBA → YUV 420P）
  5. 初始化时间戳

**endRecording()**
```cpp
sk_sp<SkData> endRecording()
```
- **功能**：结束录制并返回视频数据
- **返回值**：包含完整 MP4 视频的 `SkData` 对象
- **流程**：
  1. 发送 `nullptr` 帧信号结束编码
  2. 写入 MP4 尾部信息
  3. 从流中分离数据
  4. 重置编码器状态

### 添加帧 - 像素数据方式

**addFrame()**
```cpp
bool addFrame(const SkPixmap& pixmap)
```
- **功能**：添加一帧图像到视频
- **参数**：包含像素数据的 `SkPixmap` 对象
- **返回值**：成功返回 `true`
- **要求**：
  - 尺寸必须匹配 `beginRecording()` 时设置的尺寸
  - 色彩类型必须为 `kN32_SkColorType`（RGBA 或 BGRA）
- **流程**：
  1. 验证尺寸和色彩类型
  2. 确保帧缓冲可写
  3. 设置当前帧的 PTS（展示时间戳）
  4. 使用 `libswscale` 转换为 YUV 420P
  5. 发送帧到编码器

### 添加帧 - Canvas 绘制方式

**beginFrame()**
```cpp
SkCanvas* beginFrame()
```
- **功能**：开始新帧，返回可用于绘图的 Canvas
- **返回值**：`SkCanvas` 指针，失败返回 `nullptr`
- **特性**：
  - 懒加载创建 `SkSurface`（首次调用时）
  - 自动清空 Canvas（透明色）
  - 重置 Canvas 状态

**endFrame()**
```cpp
bool endFrame()
```
- **功能**：完成当前帧的绘制并添加到视频
- **返回值**：成功返回 `true`
- **流程**：
  1. 从 Surface 提取 Pixmap
  2. 调用 `addFrame()` 添加帧

### 内部方法

**reset()**
```cpp
void reset()
```
清理所有 FFmpeg 资源并重置状态。

**init()**
```cpp
bool init(int fps)
```
初始化 FFmpeg 编码器，配置 MP4 封装和 H.264 编码。

**sendFrame()**
```cpp
bool sendFrame(AVFrame* frame)
```
将帧发送到编码器并接收编码后的数据包。

## 内部实现细节

### FFmpeg 流适配

实现两个回调函数将 `SkRandomAccessWStream` 适配到 FFmpeg 的 IO 系统：

**sk_write_packet()**
```cpp
static int sk_write_packet(void* ctx, const uint8_t* buffer, int size)
```
- 从 FFmpeg 写入数据到 `SkRandomAccessWStream`
- 返回写入的字节数

**sk_seek_packet()**
```cpp
static int64_t sk_seek_packet(void* ctx, int64_t pos, int whence)
```
- 支持 `SEEK_SET`, `SEEK_CUR`, `SEEK_END` 三种定位方式
- MP4 格式需要回到文件头更新元数据

### 编码器初始化流程

**init()** 方法的详细步骤：

1. **分配输出流**：
```cpp
fWStream.reset(new SkRandomAccessWStream);
fStreamCtx = avio_alloc_context(buffer, bufferSize, AVIO_FLAG_WRITE, ...);
```

2. **创建封装上下文**：
```cpp
avformat_alloc_output_context2(&fFormatCtx, nullptr, "mp4", nullptr);
fFormatCtx->pb = fStreamCtx;
```

3. **查找并配置编码器**：
```cpp
const auto* codec = avcodec_find_encoder(output_format->video_codec);
fEncoderCtx = avcodec_alloc_context3(codec);
fEncoderCtx->codec_id = output_format->video_codec;
fEncoderCtx->width = fInfo.width();
fEncoderCtx->height = fInfo.height();
fEncoderCtx->pix_fmt = AV_PIX_FMT_YUV420P;
```

4. **分配帧缓冲**：
```cpp
fFrame = av_frame_alloc();
fFrame->format = AV_PIX_FMT_YUV420P;
av_frame_get_buffer(fFrame, 32);  // 32 字节对齐
```

5. **写入文件头**：
```cpp
avformat_write_header(fFormatCtx, nullptr);
```

### 像素格式转换

使用 `libswscale` 进行 RGB/RGBA 到 YUV 420P 的转换：

```cpp
fSWScaleCtx = sws_getCachedContext(fSWScaleCtx,
                                   width, height, fmt,      // 源格式
                                   width, height, AV_PIX_FMT_YUV420P,  // 目标格式
                                   SWS_FAST_BILINEAR, ...);

const uint8_t* src[] = { (const uint8_t*)pm.addr() };
const int strides[] = { SkToInt(pm.rowBytes()) };
sws_scale(fSWScaleCtx, src, strides, 0, height, fFrame->data, fFrame->linesize);
```

**特点**：
- 使用 `sws_getCachedContext()` 重用或更新上下文
- 支持 `RGBA` 和 `BGRA` 两种输入格式
- 使用快速双线性插值算法

### 编码流程

**sendFrame()** 实现编码和封装：

```cpp
avcodec_send_frame(fEncoderCtx, frame);  // 发送帧到编码器

while (true) {
    ret = avcodec_receive_packet(fEncoderCtx, fPacket);  // 接收编码包
    if (ret == AVERROR(EAGAIN) || ret == AVERROR_EOF) break;

    av_packet_rescale_ts(fPacket, fEncoderCtx->time_base, fStream->time_base);
    av_interleaved_write_frame(fFormatCtx, fPacket);  // 写入封装文件
}
```

**关键点**：
- 一个帧可能产生零个或多个数据包（B 帧）
- 时间戳需要重新缩放以匹配流的时间基
- 使用交错写入保证帧顺序正确

### 时间戳管理

```cpp
fCurrentPTS = 0;
fDeltaPTS = 1;

// 每帧更新
fFrame->pts = fCurrentPTS;
fCurrentPTS += fDeltaPTS;
```

- PTS（Presentation Time Stamp）表示帧的显示时间
- 以帧为单位递增（`fDeltaPTS = 1`）
- 实际时间通过 `time_base` 转换：`time = pts × time_base`

### SkRandomAccessWStream 实现

**写入机制**：
```cpp
void write(const void* src, size_t bytes) {
    size_t overwrite = std::min(len - fPos, bytes);
    if (overwrite) {
        memcpy(&fStorage[fPos], src, overwrite);  // 覆写
    }
    if (bytes - overwrite > 0) {
        fStorage.append(bytes - overwrite, ...);  // 追加
    }
}
```

**特性**：
- 优先覆写已有数据
- 不足部分追加到末尾
- 支持 MP4 格式回写头部元数据的需求

## 依赖关系

**FFmpeg 库依赖**：
- `libavcodec` - 视频编码器（H.264）
- `libavformat` - MP4 封装格式
- `libswscale` - 像素格式转换（RGB → YUV）
- `libavutil` - 工具函数和像素格式定义

**Skia 核心依赖**：
- `include/core/SkImage.h` - 图像对象
- `include/core/SkStream.h` - 流抽象
- `include/core/SkCanvas.h` - 绘图接口
- `include/core/SkSurface.h` - 绘图表面
- `include/core/SkColorSpace.h` - 色彩空间

**内部依赖**：
- `include/private/base/SkTDArray.h` - 动态数组
- `include/private/base/SkDebug.h` - 调试宏

## 设计模式与设计决策

### 适配器模式
通过 `sk_write_packet()` 和 `sk_seek_packet()` 回调，将 Skia 的流接口适配到 FFmpeg 的 IO 系统。

### 外观模式
隐藏 FFmpeg 的复杂 API，提供简单的 `beginRecording()` / `addFrame()` / `endRecording()` 接口。

### 策略模式
提供两种添加帧的策略：
1. 直接提供像素数据（`addFrame()`）
2. 通过 Canvas 绘制（`beginFrame()` / `endFrame()`）

### 懒加载模式
`fSurface` 仅在首次调用 `beginFrame()` 时创建，节省内存。

### 关键设计决策

**1. 固定输出格式**
- 固定为 MP4 容器和 YUV 420P 像素格式
- 简化实现，覆盖大多数使用场景

**2. 内存输出**
- 将视频数据输出到内存（`SkData`）而非文件
- 提供更大的灵活性（可进一步处理或流式传输）

**3. 尺寸限制**
- 要求尺寸为偶数，满足 YUV 420 子采样要求
- 在 `beginRecording()` 时验证

**4. 自动色彩空间转换**
- 自动处理 RGB/RGBA 到 YUV 的转换
- 使用快速双线性插值平衡质量和性能

**5. Canvas 接口可选**
- 提供 Canvas 接口但不强制使用
- 支持直接传入像素数据的高性能场景

**6. 时间戳简化**
- 使用简单的递增 PTS，不支持变帧率
- 适合固定帧率的动画和屏幕录制

## 性能考量

### 像素格式转换开销

**RGB → YUV 420P 转换**：
- 使用 `libswscale` 的 `SWS_FAST_BILINEAR` 算法
- 每帧都需要转换，是主要性能瓶颈之一
- 子采样（420）减少了一半的色度数据

**优化建议**：
- 可考虑使用 `SWS_BILINEAR` 或 `SWS_BICUBIC` 提高质量
- 对于实时应用，当前的 `SWS_FAST_BILINEAR` 是合理选择

### SwsContext 缓存

```cpp
fSWScaleCtx = sws_getCachedContext(fSWScaleCtx, ...);
```
- 重用转换上下文，避免每帧重新创建
- 如果参数改变，自动释放旧上下文并创建新的

### 内存使用

**帧缓冲**：
- 单个 YUV 420P 帧缓冲：`width × height × 1.5` 字节
- 例如 1920×1080：约 3MB

**输出缓冲**：
- `SkRandomAccessWStream` 动态增长
- MP4 格式需要随机访问（回写头部）

### 编码性能

**H.264 编码速度**：
- 取决于 FFmpeg 编译选项和 CPU 性能
- 可考虑配置编码器预设（如 `ultrafast`, `fast`, `medium`）

**当前配置**：
- 使用默认编码参数
- 未显式配置比特率或质量

### I/O 性能

**内存输出的优势**：
- 避免磁盘 I/O 延迟
- 适合实时或需要后处理的场景

**潜在问题**：
- 长视频可能占用大量内存
- 可考虑添加文件输出选项

### 性能瓶颈

1. **像素格式转换**：每帧的 RGB → YUV 转换
2. **H.264 编码**：取决于视频分辨率和编码器设置
3. **内存分配**：`SkRandomAccessWStream` 的动态增长

### 优化建议

1. **并行处理**：在后台线程进行编码
2. **批量处理**：累积多帧后一次性编码
3. **编码器调优**：调整编码器参数（比特率、预设、profile）
4. **硬件加速**：使用 FFmpeg 的硬件编码器（如 NVENC、VideoToolbox）
5. **输出流选项**：添加直接写入文件的选项，避免内存累积

## 相关文件

**配套实现**：
- `experimental/ffmpeg/SkVideoDecoder.h` - 视频解码器
- `experimental/ffmpeg/SkVideoDecoder.cpp` - 解码器实现

**Skia 核心接口**：
- `include/core/SkCanvas.h` - 绘图接口
- `include/core/SkSurface.h` - 绘图表面
- `include/core/SkPixmap.h` - 像素数据封装

**工具类**：
- `include/private/base/SkTDArray.h` - 动态数组实现
- `src/utils/SkOSPath.h` - 路径工具（间接使用）

**测试文件**：
- `tests/` 目录下的视频编码相关测试
- `tools/` 目录下的视频录制示例工具

**构建配置**：
- `BUILD.gn` - GN 构建配置，链接 FFmpeg 库
- `third_party/ffmpeg/` - FFmpeg 库集成

**参考文档**：
- FFmpeg 官方文档：编码器 API 使用指南
- MP4 格式规范：ISO/IEC 14496-14
