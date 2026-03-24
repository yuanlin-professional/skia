# use_skresources.cpp - SkResources 模块外部客户端使用示例

> 源文件: `example/external_client/src/use_skresources.cpp`

## 概述

本文件是一个独立的示例程序，演示了如何作为外部客户端使用 Skia 的 `skresources` 模块。该程序通过 `FileResourceProvider` 从本地文件系统加载图片资源（PNG 和 JPEG 格式），并获取图片的基本尺寸信息。这是一个最小化的命令行工具，展示了 Skia 资源加载管线的核心用法。

## 架构位置

该文件位于 `example/external_client/` 目录下，属于 Skia 项目的外部客户端示例代码。它不是 Skia 核心库的一部分，而是面向第三方开发者的参考实现，展示了如何将 Skia 集成到外部项目中。在构建系统中，它通过 Bazel（`bazel run :use_skresources`）独立编译和运行。

## 主要类与结构体

本文件本身不定义新的类或结构体，而是使用了以下 Skia 核心类型：

- **`skresources::FileResourceProvider`**: 基于文件系统的资源提供器，通过 `Make()` 工厂方法创建，接受一个根目录路径
- **`skresources::ImageAsset`**: 图片资源的抽象表示，通过 `loadImageAsset()` 加载
- **`sk_sp<SkImage>`**: Skia 的智能指针封装的图片对象，通过 `getFrameData(0).image` 从资源中获取
- **`SkString`**: Skia 自有的字符串类型，用于传递文件路径

## 公共 API 函数

示例中演示的关键 API 调用链：

- **`SkCodecs::Register()`**: 注册图片编解码器（JPEG 和 PNG），这是解码图片前的必要步骤
- **`skresources::FileResourceProvider::Make(path)`**: 创建文件资源提供器实例
- **`FileResourceProvider::loadImageAsset(dir, name, id)`**: 从指定子目录加载指定名称的图片资源
- **`ImageAsset::getFrameData(frameIndex)`**: 获取指定帧的图片数据（静态图片使用帧索引 0）
- **`SkImage::width()` / `SkImage::height()`**: 获取解码后图片的像素尺寸

## 内部实现细节

程序的执行流程简洁明了：
1. 校验命令行参数，要求传入一个资源文件夹路径
2. 显式注册 JPEG 和 PNG 解码器（Skia 的模块化设计要求手动注册编解码器）
3. 创建 `FileResourceProvider`，指向给定的根目录
4. 依次加载 `images/baby_tux.png` 和 `images/CMYK.jpg` 两个测试图片
5. 每次加载后验证资源和解码结果的有效性，失败则输出错误信息并退出
6. 成功则打印图片尺寸

值得注意的是，程序对每一步都进行了空指针检查，展示了健壮的错误处理模式。

## 依赖关系

- **`include/codec/SkCodec.h`**: 编解码器注册基础设施
- **`include/codec/SkJpegDecoder.h`**: JPEG 解码器
- **`include/codec/SkPngDecoder.h`**: PNG 解码器
- **`include/core/SkImage.h`**: 图片核心类
- **`include/core/SkString.h`**: 字符串工具
- **`modules/skresources/include/SkResources.h`**: 资源管理模块
- **标准库**: `<cstdio>`, `<filesystem>`

## 设计模式与设计决策

- **工厂模式**: `FileResourceProvider::Make()` 和 `SkCodecs::Register()` 均采用工厂方法创建对象
- **模块化编解码器注册**: Skia 不默认启用所有编解码器，需要显式注册。这种设计减小了最终二进制体积，允许客户端仅引入需要的格式支持
- **智能指针管理**: 所有对象通过 `sk_sp` 智能指针管理生命周期，避免手动内存管理
- **帧数据抽象**: 即使是静态图片也通过 `getFrameData(frameIndex)` 接口访问，统一了静态图片和动画图片的 API

## 性能考量

- 编解码器注册是全局一次性操作，不应在性能敏感路径中反复调用
- `FileResourceProvider` 从磁盘读取文件，涉及 I/O 操作，适合离线或批处理场景
- 图片解码在 `getFrameData()` 调用时按需执行，避免了预先加载所有资源的内存开销
- 使用 `sk_sp` 智能指针自动管理引用计数，无需手动跟踪对象生命周期
- 对于生产环境，应考虑缓存已加载的 `ImageAsset` 以避免重复磁盘读取和解码
- `SkMemoryStream::MakeDirect` 可用于替代文件系统 I/O，从内存缓冲区直接创建流
- JPEG 和 PNG 解码器的注册顺序不影响功能，编解码器框架会根据文件头自动选择匹配的解码器

## 相关文件

- `modules/skresources/include/SkResources.h` - SkResources 模块的公共头文件
- `modules/skresources/src/SkResources.cpp` - SkResources 模块的实现
- `include/codec/SkCodec.h` - 编解码器注册和管理接口
- `example/external_client/BUILD.bazel` - 对应的 Bazel 构建配置
- `include/codec/SkJpegDecoder.h` - JPEG 解码器头文件
- `include/codec/SkPngDecoder.h` - PNG 解码器头文件
- `modules/skottie/` - Lottie 动画模块（也使用 SkResources）
- `include/core/SkImage.h` - SkImage 核心类型定义
