# CodecUtils - 编解码器批量注册工具

> 源文件: `tools/CodecUtils.h`

## 概述

`CodecUtils.h` 提供 `RegisterAllAvailable()` 函数,根据编译时的宏定义自动注册所有可用的图像编解码器。这是一个便利函数,避免工具和测试代码重复编写条件编译的注册逻辑。

## 架构位置

属于 Skia 工具层,是模块化编解码器系统和工具代码之间的桥梁。不能放在 `src/` 中因为不希望 Skia 核心依赖编解码器。

## 公共 API 函数

- **`CodecUtils::RegisterAllAvailable()`**: 注册所有编译进来的编解码器(幂等)

## 内部实现细节

支持的编解码器(条件编译):
- AVIF, BMP (C++/Rust), GIF, ICO, JPEG, JPEGXL, PNG (libpng/Rust), RAW, WBMP, WEBP

每个编解码器通过对应的 `SK_CODEC_DECODES_*` 宏控制是否编译和注册。

## 依赖关系

- `include/codec/SkCodec.h` - 编解码器注册接口
- 各编解码器的头文件(条件包含)

## 设计模式与设计决策

- **条件编译注册**: 通过宏控制可用编解码器,保持模块化
- **幂等调用**: 多次调用安全,SkCodecs::Register 内部去重

## 性能考量

注册操作本身开销极小。调用一次即可。

## 相关文件

- `include/codec/` 目录下的各编解码器头文件
