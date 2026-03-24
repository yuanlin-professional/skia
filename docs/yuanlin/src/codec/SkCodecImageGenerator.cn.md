# SkCodecImageGenerator - 编解码器图像生成器

> 源文件: `src/codec/SkCodecImageGenerator.h`, `src/codec/SkCodecImageGenerator.cpp`

## 概述

`SkCodecImageGenerator` 是 `SkImageGenerator` 的子类，它将 `SkCodec` 包装为图像生成器接口。这允许编码的图像数据通过统一的 `SkImageGenerator` API 进行解码，同时自动处理 EXIF 方向校正、Alpha 类型调整和 YUVA 平面提取。该类是 Skia 中连接图像编解码和图像加载管道的关键桥梁。

## 架构位置

```
SkImageGenerator (基类, include/core/)
  └── SkCodecImageGenerator (src/codec/)
        └── SkCodec (持有的编解码器实例)
```

该类位于编解码模块和核心图像管道之间，为 `SkImage::MakeFromEncoded` 等高层 API 提供底层支持。

## 主要类与结构体

### `SkCodecImageGenerator`
- 继承自 `SkImageGenerator`
- 持有一个 `std::unique_ptr<SkCodec>` 实例
- 缓存编码数据 (`fCachedData`)
- 支持多帧动画图像的帧信息查询

## 公共 API 函数

### 工厂方法
- `MakeFromEncodedCodec(sk_sp<const SkData>, std::optional<SkAlphaType>)`: 从编码数据创建图像生成器。内部先创建 `SkCodec`，然后包装为生成器。
- `MakeFromCodec(std::unique_ptr<SkCodec>, std::optional<SkAlphaType>)`: 从已有的编解码器创建图像生成器。

### 图像操作
- `getScaledDimensions(float desiredScale)`: 获取近似支持目标缩放的尺寸，自动考虑 EXIF 方向交换宽高。
- `getPixels(const SkImageInfo&, void*, size_t, const SkCodec::Options*)`: 解码像素到指定缓冲区，自动处理 EXIF 方向旋转。

### 动画支持
- `getFrameCount()`: 返回动画帧数
- `getFrameInfo(int index, SkCodec::FrameInfo*)`: 获取指定帧信息
- `getRepetitionCount()`: 返回动画循环次数

## 内部实现细节

### Alpha 类型调整 (`adjust_info`)
构造时通过 `adjust_info` 函数调整图像信息：
1. 如果指定了 Alpha 类型，使用指定值（但不允许 `kOpaque`）
2. 否则，将 `kUnpremul` 自动转换为 `kPremul`（因为预乘在滤波时效果更好）
3. 如果 EXIF 方向交换宽高，则交换 `ImageInfo` 的宽高

### EXIF 方向处理
- `getPixels` 使用 `SkPixmapUtils::Orient` 处理方向旋转
- `getScaledDimensions` 在 EXIF 交换宽高时交换返回值的宽高
- 解码回调通过 lambda 表达式封装，容忍 `kIncompleteInput` 和 `kErrorInInput` 结果

### 编码数据缓存
`onRefEncodedData` 方法使用 `fCachedData` 延迟缓存编码数据，通过 `SkCodecPriv::GetEncodedData` 从编解码器获取。

### YUVA 支持
- `onQueryYUVAInfo`: 委托给 `fCodec->queryYUVAInfo`
- `onGetYUVAPlanes`: 委托给 `fCodec->getYUVAPlanes`，容忍不完整输入

## 依赖关系

- `SkImageGenerator`: 基类
- `SkCodec`: 底层编解码器
- `SkEncodedOrigin` / `SkPixmapUtils`: EXIF 方向处理
- `SkYUVAPixmaps`: YUVA 平面数据
- `SkData`: 编码数据管理
- `SkCodecPriv`: 私有工具函数

## 设计模式与设计决策

### 适配器模式
该类将 `SkCodec` 接口适配为 `SkImageGenerator` 接口，使编解码器可以在图像生成器框架中使用。

### 容错解码
`getPixels` 和 `onGetYUVAPlanes` 都接受 `kSuccess`、`kIncompleteInput` 和 `kErrorInInput` 三种结果为成功，确保部分损坏的图像仍能显示。

### 私有构造
构造函数为私有，强制通过工厂方法创建，确保参数验证。

## 性能考量

- 编码数据延迟缓存，仅在需要时加载
- EXIF 方向处理在像素级别进行，避免额外的中间缓冲区（使用 `Orient` 回调）
- `kPremul` 作为默认 Alpha 类型，优化后续的图像滤波操作

## 相关文件

- `include/core/SkImageGenerator.h`: 基类定义
- `include/codec/SkCodec.h`: 编解码器接口
- `include/codec/SkEncodedOrigin.h`: EXIF 方向枚举
- `include/codec/SkPixmapUtils.h`: 像素图工具（方向处理）
- `src/codec/SkCodecPriv.h`: 编解码器私有工具
- `src/codec/SkPixmapUtilsPriv.h`: 像素图私有工具
