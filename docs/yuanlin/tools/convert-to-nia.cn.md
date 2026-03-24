# convert-to-nia - NIA/NIE 图像格式转换工具

> 源文件: `tools/convert-to-nia.cpp`

## 概述

`convert-to-nia` 将 stdin 输入的编码图像(JPEG、PNG 等)转换为 NIA(动画)或 NIE(静态)格式输出到 stdout。NIA/NIE 是 Google Wuffs 项目定义的极简图像格式,用于跨解码器实现的像素级输出对比。

## 架构位置

属于 Skia 工具链中的解码器验证工具,用于与 Chromium 和 Wuffs 的解码器输出进行对比。

## 公共 API 函数

- **`main()`**: 读取 stdin 图像,输出 NIA/NIE 格式到 stdout
- **`write_nix_header()`**: 写入 NIE/NIA 文件头
- **`write_nie_pixels()`**: 写入 BGRA 像素数据
- **`write_nia_duration()`**: 写入动画帧的时间戳(Flicks 单位)
- **`write_nia_footer()`**: 写入 NIA 尾部(循环计数)

## 内部实现细节

- NIA 使用 Flicks 时间单位(1/705,600,000 秒)
- 像素格式: 4 字节非预乘 BGRA
- 支持多帧动画和帧间依赖缓存
- `-1` 或 `-first-frame-only` 标志输出 NIE(仅首帧)

## 依赖关系

- `include/codec/SkCodec.h` - 图像解码
- `src/base/SkAutoMalloc.h` - 内存管理

## 设计模式与设计决策

- **管道模式**: stdin 输入 stdout 输出,可与其他工具组合
- **帧缓存**: 缓存被后续帧依赖的帧数据避免重复解码

## 性能考量

使用 4KB 缓冲区减少 fwrite 调用次数。帧缓存避免冗余解码。

## 相关文件

- Wuffs 项目的 `convert-to-nia.c` - 等效的 Wuffs 实现
- Chromium 的等效实现 (crrev.com/c/2210331)
