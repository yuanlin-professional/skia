# BitmapRegionDecoder - Android 位图区域解码器

> 源文件:
> - `client_utils/android/BitmapRegionDecoder.h`
> - `client_utils/android/BitmapRegionDecoder.cpp`

## 概述

BitmapRegionDecoder 是 Skia 为 Android 平台提供的客户端工具类，用于从编码图像中解码指定矩形区域的像素数据。它封装了 `SkAndroidCodec`，支持子集解码和降采样，是 Android 系统中 `android.graphics.BitmapRegionDecoder` 的底层实现。该类支持 JPEG、PNG、WebP、HEIF 和 AVIF 格式。

## 架构位置

```
Android Framework (Java/Kotlin)
    ↓ (JNI 调用)
client_utils/android/BitmapRegionDecoder  <── 本模块
    ↓ (委托)
SkAndroidCodec
    ↓ (委托)
SkCodec (具体格式解码器)
```

位于 Skia 的客户端工具层（`client_utils/android`），为 Android 系统提供定制化的图像解码接口。

## 主要类与结构体

### `BitmapRegionDecoder`

- **命名空间**: `android::skia`
- **标记**: `final`（不可继承）
- **成员变量**:
  - `fCodec` (`std::unique_ptr<SkAndroidCodec>`): 底层 Android 编解码器

## 公共 API 函数

| 函数 | 描述 |
|------|------|
| `Make(sk_sp<SkData>)` | 静态工厂方法，从编码数据创建解码器 |
| `decodeRegion(...)` | 解码图像的指定矩形区域 |
| `getEncodedFormat()` | 获取编码图像格式 |
| `computeOutputColorType(SkColorType)` | 计算输出颜色类型 |
| `computeOutputColorSpace(SkColorType, SkColorSpace)` | 计算输出颜色空间 |
| `width()` | 获取图像宽度 |
| `height()` | 获取图像高度 |
| `getAndroidGainmap(...)` | 获取 Android Gainmap 数据 |
| `getGainmapBitmapRegionDecoder(...)` | 获取 Gainmap 的区域解码器 |

## 内部实现细节

### 格式支持验证

`Make()` 方法在创建 `SkAndroidCodec` 后检查编码格式，仅支持以下五种格式：
- JPEG、PNG、WebP、HEIF、AVIF

其他格式直接返回 `nullptr`。

### 区域解码流程（decodeRegion）

1. **采样率校正**: 确保 `sampleSize >= 1`
2. **子集调整**: 通过 `adjust_subset_rect` 处理超出图像边界的子集请求：
   - `kOutside_SubsetType`: 完全在图像外部，返回 false
   - `kPartiallyInside_SubsetType`: 部分在图像外部，计算偏移量
3. **获取支持的子集**: 调用 `getSupportedSubset` 确保编解码器支持所请求的子集
4. **计算缩放尺寸**: 使用 `getSampledSubsetDimensions` 获取降采样后的尺寸
5. **配置输出位图**:
   - 计算 alpha 类型（是否要求非预乘）
   - 对灰度图做特殊处理：使用 `kAlpha_8_SkColorType` 替代 `kGray_8_SkColorType`（保持与旧版 BitmapFactory 的行为兼容）
   - 处理部分在图像内部的情况，计算缩放后的偏移
6. **分配像素**: 通过 `BRDAllocator` 分配目标位图的像素缓冲区
7. **零初始化**: 对部分在图像内部的情况，将整个缓冲区清零
8. **执行解码**: 调用 `getAndroidPixels` 进行实际解码

### 灰度图兼容性处理

```cpp
if (kGray_8_SkColorType == dstColorType) {
    outInfo = outInfo.makeColorType(kAlpha_8_SkColorType)
                     .makeAlphaType(kPremul_SkAlphaType);
}
```

这是为了保持与 Android 旧版 `BitmapFactory` 的行为一致——在 `kGray_8` 出现之前，灰度图使用 `kAlpha_8` 表示。

### 结果处理

解码结果中，`kSuccess`、`kIncompleteInput` 和 `kErrorInInput` 都视为成功返回 `true`，仅在其他错误时返回 `false`。

## 依赖关系

- **编解码器**: `SkAndroidCodec`（核心解码器）、`SkCodecPriv`（内部工具）
- **Skia 核心**: `SkBitmap`、`SkData`、`SkImageInfo`、`SkColorSpace`
- **Android 适配**: `BRDAllocator`（位图区域解码分配器）
- **内部工具**: `BitmapRegionDecoderPriv.h`（`adjust_subset_rect` 等内部辅助函数）

## 设计模式与设计决策

- **工厂方法模式**: `Make()` 封装格式验证逻辑，失败时返回 `nullptr`
- **私有构造函数**: 确保只能通过 `Make()` 创建实例
- **Gainmap 支持**: 提供两种 Gainmap 接口——流式读取和区域解码器创建
- **向后兼容**: 灰度图的 `kAlpha_8` 兼容处理体现了对 Android 生态系统的向后兼容承诺
- **宽容的错误处理**: `kIncompleteInput` 和 `kErrorInInput` 不视为致命错误，允许部分解码结果

## 性能考量

- 子集解码避免了解码整幅图像的开销，对大图像尤其重要
- `sampleSize` 参数支持硬件级别的降采样，在解码阶段就减少像素处理量
- 部分越界子集仅对未覆盖区域进行零初始化，但注释中提到可优化为仅清零非解码区域
- `BRDAllocator` 允许 Android 使用自定义的内存分配策略（如共享内存）
- 零初始化检查 `allocator->zeroInit()` 避免了对已零初始化缓冲区的重复清零

## 相关文件

- `client_utils/android/BRDAllocator.h` - 位图区域解码分配器接口
- `client_utils/android/BitmapRegionDecoderPriv.h` - 内部辅助函数
- `include/codec/SkAndroidCodec.h` - Android 编解码器接口
- `include/codec/SkCodec.h` - Skia 编解码器基类
- `client_utils/android/FrontBufferedStream.h` - 前置缓冲流（常配合使用）
