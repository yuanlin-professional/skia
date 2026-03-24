# decode_png_main

> 源文件: example/external_client/src/decode_png_main.cpp

## 概述

decode_png_main 是一个专门针对 PNG 图像解码的最小化示例。程序使用 Skia 的 SkPngDecoder 模块解码 PNG 文件并输出图像尺寸。这是比 decode_everything.cpp 更简洁的示例,专注于单一格式的解码流程。

## 核心实现

```cpp
std::unique_ptr<SkFILEStream> input = SkFILEStream::Make(argv[1]);
SkCodec::Result result;
auto codec = SkPngDecoder::Decode(std::move(input), &result);
if (!codec) {
    printf("Cannot decode file %s as a PNG\n", argv[1]);
    printf("Result code: %d\n", result);
    return 1;
}
SkImageInfo info = codec->getInfo();
printf("Image is %d by %d pixels.\n", info.width(), info.height());
```

## 关键点

- **流式解码**: 直接从 SkFILEStream 解码,无需加载全文件
- **错误处理**: 检查 result 码了解解码失败原因
- **PNG 专用**: 使用 SkPngDecoder 而非通用 SkCodec
- **快速**: 仅获取元数据,不解码像素

## SkCodec::Result 码

- `kSuccess`: 解码成功
- `kIncompleteInput`: 文件截断
- `kErrorInInput`: 数据损坏
- `kInvalidConversion`: 不支持的转换
- `kInvalidScale`: 无效的缩放参数
- `kInvalidParameters`: 无效参数

## 相关文件
- decode_everything.cpp: 多格式解码
- include/codec/SkPngDecoder.h: PNG 解码器 API
- third_party/libpng/: PNG 解码库
