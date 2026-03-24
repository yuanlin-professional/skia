# decode_everything

> 源文件: example/external_client/src/decode_everything.cpp

## 概述

decode_everything 是一个演示如何使用 Skia 的多格式图像解码器的示例程序。该程序能够自动检测并解码 BMP、GIF、ICO、JPEG、JPEG XL、PNG、WBMP 和 WebP 等多种图像格式,展示了 Skia 模块化解码器架构的使用方法。程序读取图像文件,检测格式,解码并输出图像尺寸。

这是外部客户端集成 Skia 图像解码功能的参考实现,展示了如何正确使用各个独立的解码器模块。

## 架构位置

```
skia/example/external_client/src/
└── decode_everything.cpp  # 多格式解码示例(64行)
```

## 主要类与结构体

### 使用的解码器

- **SkBmpDecoder**: BMP 格式
- **SkGifDecoder**: GIF 动画
- **SkIcoDecoder**: Windows 图标
- **SkJpegDecoder**: JPEG 图像
- **SkJpegxlDecoder**: JPEG XL (新一代格式)
- **SkPngDecoder**: PNG 图像
- **SkWbmpDecoder**: 无线 Bitmap
- **SkWebpDecoder**: WebP 格式

## 公共 API 函数

### main()

```cpp
int main(int argc, char** argv);
```

**参数**: `argv[1]` - 图像文件路径

**返回值**:
- `0`: 成功解码
- `1`: 失败(无法打开/格式不支持/解码失败)

**执行流程**:
1. 读取文件到 SkData
2. 检测格式(依次尝试各解码器的 IsXxx 方法)
3. 使用对应解码器解码
4. 输出图像尺寸

## 内部实现细节

### 格式检测链

```cpp
if (SkBmpDecoder::IsBmp(data->bytes(), data->size())) {
  codec = SkBmpDecoder::Decode(data, nullptr);
} else if (SkGifDecoder::IsGif(data->bytes(), data->size())) {
  codec = SkGifDecoder::Decode(data, nullptr);
} else if (SkIcoDecoder::IsIco(data->bytes(), data->size())) {
  codec = SkIcoDecoder::Decode(data, nullptr);
} // ... 其他格式
```

**检测方法**:
- 每个解码器提供静态 `IsXxx()` 方法检查魔数
- 按顺序尝试,第一个匹配的被使用
- 高效:只检查文件头几个字节

### 解码器使用

```cpp
std::unique_ptr<SkCodec> codec = SkBmpDecoder::Decode(data, nullptr);
SkImageInfo info = codec->getInfo();
printf("Image is %d by %d pixels.\n", info.width(), info.height());
```

**步骤**:
1. `Decode()`: 创建编解码器对象
2. `getInfo()`: 获取图像元数据(无需完整解码)
3. 输出尺寸信息

## 依赖关系

```cpp
#include "include/codec/SkBmpDecoder.h"
#include "include/codec/SkGifDecoder.h"
#include "include/codec/SkIcoDecoder.h"
#include "include/codec/SkJpegDecoder.h"
#include "include/codec/SkJpegxlDecoder.h"
#include "include/codec/SkPngDecoder.h"
#include "include/codec/SkWbmpDecoder.h"
#include "include/codec/SkWebpDecoder.h"
#include "include/codec/SkCodec.h"
#include "include/core/SkData.h"
#include "include/core/SkStream.h"
```

## 设计模式与设计决策

### 1. 策略模式
每个解码器实现 SkCodec 接口,提供统一的解码 API。

### 2. 责任链模式
格式检测使用责任链:每个解码器检查是否能处理,不能则传递给下一个。

### 3. 设计决策

**(1) 为何使用独立解码器而非 SkCodec::MakeFromData()?**

```cpp
// 示例使用独立解码器
SkBmpDecoder::Decode(data, nullptr);

// 通用方法
SkCodec::MakeFromData(data);  // 内部会尝试所有注册的解码器
```

- **明确性**: 展示模块化架构
- **控制**: 可选择性链接解码器
- **学习价值**: 理解每个解码器的独立性

**(2) 为何只输出尺寸?**

- **简洁**: 演示格式检测和解码器选择
- **快速**: 无需完整解码像素数据
- **可扩展**: 用户可添加实际像素解码

## 性能考量

### 1. 格式检测开销
- **IsXxx()**: 只检查文件头(通常 <20 字节)
- **开销**: 微秒级
- **优化**: 可根据文件扩展名调整检测顺序

### 2. 延迟解码
```cpp
codec->getInfo()  // 快速:只解析头部
vs
codec->getPixels() // 慢:完整解码
```

### 3. 内存使用
```cpp
sk_sp<SkData> data = SkData::MakeFromStream(input.get(), input->getLength());
```
- 将整个文件加载到内存
- 适合小文件
- 大文件应考虑流式解码

## 相关文件

### 相关示例
- **decode_png_main.cpp**: 专门的 PNG 解码示例
- **ganesh_metal.cpp**: GPU 解码后渲染

### 解码器实现
- **src/codec/SkBmpCodec.cpp**: BMP 解码器
- **src/codec/SkPngCodec.cpp**: PNG 解码器
- **third_party/**: 第三方解码库(libjpeg、libpng 等)

该示例是学习 Skia 图像解码架构的良好起点,展示了如何灵活集成各种图像格式支持。
