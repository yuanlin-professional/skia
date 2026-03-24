# SkGifDecoder

> 源文件: `include/codec/SkGifDecoder.h`

## 概述

SkGifDecoder 提供 GIF(Graphics Interchange Format)图像格式的解码能力。GIF 是互联网上使用最广泛的动画图像格式,支持透明度、多帧动画和调色板压缩。该模块是 Skia 动画图像处理的核心组件,广泛用于表情包、加载动画、UI 装饰等场景。

## 架构位置

SkGifDecoder 位于 Skia Codec 子系统,实现 SkCodec 抽象接口。它依赖底层的 GIF 解析库(如 wuffs 或 giflib)处理 LZW 压缩和帧管理,为上层提供统一的动画图像访问接口,是 Skia 多帧图像支持的典型代表。

## 命名空间 API

### `IsGif`

检测数据是否为 GIF 格式。

```cpp
SK_API bool IsGif(const void* data, size_t length)
```

**功能**: 通过检查 GIF 文件头识别格式。

**参数**:
- `data`: 待检测数据的指针
- `length`: 数据长度(字节)

**返回值**:
- `true`: 数据以 GIF 魔数开头
- `false`: 非 GIF 格式

**检测逻辑**:
- GIF87a: `47 49 46 38 37 61` ("GIF87a")
- GIF89a: `47 49 46 38 39 61` ("GIF89a")
- 最少需要 6 字节进行检测

**版本区别**:
- **GIF87a**(1987): 基础版本,支持透明色索引
- **GIF89a**(1989): 增加动画、图形控制扩展等功能

### `Decode` (SkStream 版本)

从输入流解码 GIF 图像。

```cpp
SK_API std::unique_ptr<SkCodec> Decode(
    std::unique_ptr<SkStream> stream,
    SkCodec::Result* result,
    SkCodecs::DecodeContext context = nullptr
)
```

**参数**:
- `stream`: 输入数据流,解码器获取所有权
- `result`: 输出参数,返回解码结果状态
- `context`: 解码上下文(当前版本忽略)

**返回值**:
- 成功: 返回 SkCodec 智能指针,支持多帧访问
- 失败: 返回 `nullptr`,`result` 设为错误码

**支持的 GIF 特性**:
- 多帧动画(通过 `getFrameCount()` 和 `getFrameInfo()` 访问)
- 透明色索引
- 帧延迟时间(Delay Time)
- 帧处置方法(Disposal Method)
- 循环次数(Loop Count)
- 局部和全局调色板

### `Decode` (SkData 版本)

从内存数据块解码 GIF 图像。

```cpp
SK_API std::unique_ptr<SkCodec> Decode(
    sk_sp<const SkData> data,
    SkCodec::Result* result,
    SkCodecs::DecodeContext context = nullptr
)
```

**参数**:
- `data`: 包含完整 GIF 数据的智能指针
- `result`: 输出参数,返回解码状态
- `context`: 解码上下文(当前忽略)

**适用场景**:
- 从网络下载的 GIF 表情包
- 内存中生成的 GIF 动画
- 应用资源文件中的 GIF

### `Decoder`

返回解码器描述符,用于注册到解码器工厂。

```cpp
inline constexpr SkCodecs::Decoder Decoder()
```

**返回值**: 包含以下信息的结构体:
- `name`: 字符串 "gif"
- `isFormat`: 函数指针 `IsGif`
- `makeCodec`: 函数指针 `Decode`

## 内部实现细节

### GIF 文件结构
```
Header (6 字节)
    Signature: "GIF"
    Version: "87a" 或 "89a"

Logical Screen Descriptor (7 字节)
    Width, Height
    Global Color Table Flag
    Color Resolution
    Sort Flag
    Global Color Table Size
    Background Color Index
    Pixel Aspect Ratio

Global Color Table (可选)
    256 色 * 3 字节(RGB)

Graphic Control Extension (可选,用于动画)
    Disposal Method
    User Input Flag
    Transparent Color Flag
    Delay Time
    Transparent Color Index

Image Descriptor
    Left, Top, Width, Height
    Local Color Table Flag
    Interlace Flag
    Sort Flag
    Local Color Table Size

Local Color Table (可选)

Image Data (LZW 压缩)
    LZW Minimum Code Size
    Data Sub-blocks

Trailer (1 字节)
    0x3B
```

### LZW 压缩
GIF 使用 Lempel-Ziv-Welch(LZW)无损压缩算法:
- **动态字典**: 边解码边构建码表
- **可变码长**: 初始 9-bit,最大 12-bit
- **压缩率**: 索引色图像可达 2-5 倍

### 帧处置方法
| 方法 | 枚举值 | 行为 |
|------|--------|------|
| None | 0 或 1 | 保留当前帧,下一帧覆盖在上面 |
| Background | 2 | 清除当前帧区域为背景色 |
| Previous | 3 | 恢复到前一帧状态 |

### 透明色处理
- GIF 使用索引透明(单一颜色索引为透明)
- 不支持 Alpha 通道(全透明或全不透明)
- 透明索引在图形控制扩展中指定

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| include/codec/SkCodec.h | SkCodec 基类定义 |
| include/core/SkRefCnt.h | 智能指针支持 |
| include/private/base/SkAPI.h | 导出宏 SK_API |
| wuffs 或 giflib | 底层 GIF 解析和 LZW 解压缩 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| SkCodec | 通过工厂方法创建 GIF 解码器 |
| SkAnimatedImage | 播放 GIF 动画 |
| SkImage | 从 GIF 帧创建图像 |
| Web 应用 | 显示 GIF 表情包和加载动画 |

## 设计模式与设计决策

### 多帧接口设计
GIF 解码器通过 SkCodec 的多帧 API 暴露动画能力:
```cpp
int frameCount = codec->getFrameCount();
std::vector<SkCodec::FrameInfo> frameInfos(frameCount);
codec->getFrameInfo(0, frameCount, frameInfos.data());

// 解码第 n 帧
SkCodec::Options options;
options.fFrameIndex = n;
codec->getPixels(info, pixels, rowBytes, &options);
```

### 增量解码支持
GIF 支持流式解码,适合网络场景:
- 边下载边解析帧信息
- 可先显示第一帧,后续帧逐步加载
- 适用于渐进式加载用户体验

### 后端抽象
Skia 支持多种 GIF 解析后端:
- **wuffs**(默认): 安全的 C 库,内存安全性强
- **giflib**: 传统实现,兼容性好但可能有安全问题

## 性能考量

### 解码速度
GIF 解码速度取决于多个因素:
- **LZW 解压缩**: CPU 密集型操作(~20-50ms for 500x500 单帧)
- **调色板转换**: 索引色转 RGBA(~5-10ms)
- **帧数**: 多帧 GIF 解码总时间 = 单帧 * 帧数

### 内存占用
- 解码器对象: ~500 字节
- 调色板缓存: 256 色 * 4 字节 = 1024 字节
- LZW 字典: ~4-8 KB
- 帧缓冲区: width * height * 4 字节(每帧)
- 多帧缓存: 对于 Previous 处置方法,需要额外帧缓冲

### 文件大小
- 单帧 GIF(500x500): ~50-200 KB
- 动画 GIF(10 帧): ~500 KB - 2 MB
- 高帧率动画可能超过 10 MB

## 典型使用场景

### 场景 1: 显示静态 GIF
```cpp
// 许多 GIF 实际只有一帧(作为静态图使用)
auto codec = SkGifDecoder::Decode(stream, &result);
if (codec->getFrameCount() == 1) {
    // 按静态图处理
    codec->getPixels(info, pixels, rowBytes);
}
```

### 场景 2: 播放 GIF 动画
```cpp
auto codec = SkGifDecoder::Decode(data, &result);
int frameCount = codec->getFrameCount();
std::vector<SkCodec::FrameInfo> frameInfos(frameCount);
codec->getFrameInfo(0, frameCount, frameInfos.data());

for (int i = 0; i < frameCount; ++i) {
    SkCodec::Options options;
    options.fFrameIndex = i;
    codec->getPixels(info, pixels, rowBytes, &options);

    // 显示当前帧
    display(pixels);

    // 延迟到下一帧
    sleep(frameInfos[i].fDuration);
}
```

### 场景 3: 提取第一帧作为缩略图
```cpp
// 快速提取 GIF 的第一帧作为预览
auto codec = SkGifDecoder::Decode(data, &result);
codec->getPixels(info, thumbnailPixels, rowBytes);
// 无需解码所有帧,节省时间
```

## 动画控制

### 循环次数
```cpp
// 获取动画循环次数
int repetitionCount = codec->getRepetitionCount();
// -1: 无限循环
// 0: 播放一次(不循环)
// N: 循环 N 次
```

### 帧时长
```cpp
SkCodec::FrameInfo info = frameInfos[i];
int durationMs = info.fDuration; // 毫秒
// GIF 规范最小单位是 10ms(0.01 秒)
```

### 帧间依赖
```cpp
// 某些帧依赖前一帧(当 DisposalMethod 为 Previous 时)
if (frameInfos[i].fRequiredFrame != SkCodec::kNoFrame) {
    // 需要先解码 requiredFrame
    int requiredFrame = frameInfos[i].fRequiredFrame;
}
```

## 边界情况处理

### 损坏的 GIF 文件
- LZW 数据损坏: 返回 `kIncompleteInput`,已解码的帧仍可用
- 截断的 GIF: 可能只能解码部分帧
- 非法帧尺寸: 返回 `kInvalidInput`

### 超大 GIF
- 单帧超大(如 5000x5000): 可能内存不足,建议限制最大尺寸
- 帧数过多(如 1000+ 帧): 解析时间长,考虑懒加载

### 无限循环 GIF
- 某些 GIF 没有结束标记,解析时设置超时
- 使用流式解码可提前终止

## 平台相关说明

### Web 浏览器
- 浏览器原生支持 GIF,可能使用系统解码器
- Skia 用于 Chrome/Edge 的 Canvas API
- WASM 构建使用 Skia 的 GIF 解码器

### Android
- Android 9+ 原生支持 AnimatedImageDrawable(GIF)
- Skia 提供统一接口,无论是否使用系统 API
- 可选使用硬件加速(通过 MediaCodec)

### iOS/macOS
- 系统通过 ImageIO 支持 GIF
- Skia 可选使用系统解码器或自带实现

## 限制与注意事项

### 颜色限制
- GIF 每帧最多 256 色(8-bit 调色板)
- 不适合照片或渐变丰富的图像
- 现代替代: WebP 动画(支持真彩色)

### 透明度限制
- 仅支持二值透明(全透明或全不透明)
- 无 Alpha 渐变或半透明效果
- 边缘可能出现锯齿

### 文件大小
- 动画 GIF 文件通常很大
- 建议转换为 WebP(压缩率更高)或 MP4(视频格式)

## 优化技巧

### 减少内存占用
```cpp
// 使用单帧缓冲区,逐帧解码
for (int i = 0; i < frameCount; ++i) {
    options.fFrameIndex = i;
    codec->getPixels(info, reuseBuffer, rowBytes, &options);
    display(reuseBuffer);
}
// 而非预解码所有帧到内存
```

### 跳帧播放
```cpp
// 对于高帧率 GIF,可跳过部分帧
for (int i = 0; i < frameCount; i += 2) { // 每隔一帧
    options.fFrameIndex = i;
    codec->getPixels(...);
}
```

### 缩放解码
```cpp
// 解码为较小尺寸,减少内存和 CPU 开销
SkImageInfo scaledInfo = info.makeWH(width / 2, height / 2);
codec->getPixels(scaledInfo, pixels, rowBytes);
```

## 相关文件

| 文件 | 关系 |
|------|------|
| src/codec/SkGifCodec.cpp | GIF 解码器实现 |
| src/codec/SkWuffsCodec.cpp | wuffs 后端实现 |
| include/codec/SkCodecAnimation.h | 定义 DisposalMethod 和 Blend 枚举 |
| include/codec/SkCodec.h | 解码器基类,定义多帧 API |
| src/android/SkAnimatedImage.cpp | Android 动画图像播放 |

## 扩展阅读

### GIF 格式规范
- GIF87a 规范
- GIF89a 规范(What's New in GIF89a)
- CompuServe GIF 标准文档

### 替代格式
- **WebP 动画**: 更好的压缩率,支持真彩色
- **APNG**: PNG 的动画扩展,无损
- **AVIF**: 次世代格式,压缩率最高

## 最佳实践

### 格式选择
- **简单动画**: GIF(兼容性最好)
- **高质量动画**: WebP 或 APNG
- **视频内容**: 使用 MP4/WebM 而非 GIF

### 性能优化
- 限制 GIF 尺寸(建议 ≤ 500x500)
- 减少帧数(10-30 帧为佳)
- 使用 WebP 转换工具压缩

### 用户体验
- 提供播放控制(暂停/播放)
- 自动循环次数限制(避免分散注意力)
- 低电量或弱网环境禁用自动播放
