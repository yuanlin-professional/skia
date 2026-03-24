# SkAnimCodecPlayer

> 源文件: modules/skresources/src/SkAnimCodecPlayer.h, modules/skresources/src/SkAnimCodecPlayer.cpp

## 概述

`SkAnimCodecPlayer` 是一个动画播放器类,用于播放由 `SkCodec` 解码的多帧图像动画,如 GIF、APNG、WebP 动画等。该类封装了复杂的帧管理逻辑,包括帧缓存、依赖帧处理、时间码定位、图像方向转换等,为上层提供简单的时间码查找和帧获取接口。

该播放器支持帧级别的缓存优化,依赖帧(required frame)的正确处理,以及 EXIF 方向信息的自动应用。

## 架构位置

`SkAnimCodecPlayer` 位于 `skresources` 资源管理模块中,作为动画资源的播放器:

```
skia/modules/
├── skresources/
│   └── src/
│       └── SkAnimCodecPlayer.h/.cpp    # 动画播放器
└── codec/
    └── include/
        └── SkCodec.h                    # 编解码器接口
```

**使用场景:**
- Skottie 动画中的图像动画
- Lottie 中的动画图片资源
- 各种需要动画图像播放的场景

## 主要类与结构体

### SkAnimCodecPlayer
```cpp
class SkAnimCodecPlayer
```
动画播放器类,管理多帧图像的解码和缓存。

**核心成员:**
- `fCodec`: `SkCodec` 解码器对象(静态图像时为 null)
- `fImageInfo`: 图像信息(颜色类型、透明度等)
- `fFrameInfos`: 每帧的元数据数组(修改后的持续时间为累积时间)
- `fImages`: 帧图像缓存数组
- `fCurrIndex`: 当前帧索引
- `fTotalDuration`: 动画总持续时间(毫秒)

## 公共 API 函数

### 构造与析构
```cpp
explicit SkAnimCodecPlayer(std::unique_ptr<SkCodec> codec)
```
从 `SkCodec` 对象构造播放器。

**初始化逻辑:**
- 获取图像信息和所有帧的元数据
- 将帧持续时间转换为累积结束时间(优化二分查找)
- 为静态图像创建延迟加载的图像
- 为动画图像预分配帧缓存数组

```cpp
~SkAnimCodecPlayer()
```
析构函数,清理资源。

### 帧访问
```cpp
sk_sp<SkImage> getFrame()
```
获取当前帧的图像。

**行为:**
- 默认返回第一帧(时间码 0)
- 多次调用返回相同的图像对象(直到 `seek()` 改变当前帧)
- 失败时返回 `nullptr`

### 时间码定位
```cpp
bool seek(uint32_t msec)
```
根据时间码(毫秒)定位到最接近的帧。

**参数:**
- `msec`: 时间码(毫秒),自动对总持续时间取模(支持循环播放)

**返回:**
- `true`: 当前帧改变了
- `false`: 当前帧未改变(仍然是同一帧)

**实现:**
使用二分查找在累积时间数组中查找对应帧。

### 查询接口
```cpp
SkISize dimensions() const
```
返回图像尺寸,考虑 EXIF 方向信息(可能交换宽高)。

```cpp
uint32_t duration() const
```
返回动画总持续时间(毫秒),静态图像返回 0。

## 内部实现细节

### 构造函数初始化
构造函数执行关键的初始化:

```cpp
SkAnimCodecPlayer::SkAnimCodecPlayer(std::unique_ptr<SkCodec> codec) : fCodec(std::move(codec)) {
    fImageInfo = fCodec->getInfo();
    fFrameInfos = fCodec->getFrameInfo();
    fImages.resize(fFrameInfos.size());

    // 将帧持续时间转换为累积结束时间
    size_t dur = 0;
    for (auto& f : fFrameInfos) {
        dur += f.fDuration;
        f.fDuration = dur;  // 现在存储的是累积时间
    }
    fTotalDuration = dur;

    if (!fTotalDuration) {
        // 静态图像 - 使用延迟加载
        fFrameInfos.clear();
        fImages.clear();
        fImages.push_back(SkImages::DeferredFromGenerator(
                SkCodecImageGenerator::MakeFromCodec(std::move(fCodec))));
    }
}
```

**关键优化:**
- 累积时间转换使 `seek()` 可以使用二分查找
- 静态图像使用延迟生成器,避免立即解码

### 帧解码与缓存
`getFrameAt()` 实现帧的按需解码和缓存:

```cpp
sk_sp<SkImage> SkAnimCodecPlayer::getFrameAt(int index) {
    // 1. 检查缓存
    if (fImages[index]) {
        return fImages[index];
    }

    // 2. 分配像素内存
    size_t rb = fImageInfo.minRowBytes();
    size_t size = fImageInfo.computeByteSize(rb);
    auto data = SkData::MakeUninitialized(size);

    // 3. 配置解码选项
    SkCodec::Options opts;
    opts.fFrameIndex = index;

    // 4. 处理图像方向
    const auto origin = fCodec->getOrigin();
    const auto orientedDims = this->dimensions();
    const auto originMatrix = SkEncodedOriginToMatrix(origin, ...);

    // 5. 处理依赖帧
    const int requiredFrame = fFrameInfos[index].fRequiredFrame;
    if (requiredFrame != SkCodec::kNoFrame && fImages[requiredFrame]) {
        auto requiredImage = fImages[requiredFrame];
        auto canvas = SkCanvas::MakeRasterDirect(imageInfo, data->writable_data(), rb);
        if (origin != kDefault_SkEncodedOrigin) {
            // 撤销方向变换,因为解码在应用方向之前
            canvas->concat(*originMatrix.invert());
        }
        canvas->drawImage(requiredImage, 0, 0, SkSamplingOptions(), &paint);
        opts.fPriorFrame = requiredFrame;
    }

    // 6. 解码帧
    if (SkCodec::kSuccess != fCodec->getPixels(imageInfo, data->writable_data(), rb, &opts)) {
        return nullptr;
    }

    // 7. 应用图像方向
    auto image = SkImages::RasterFromData(imageInfo, std::move(data), rb);
    if (origin != kDefault_SkEncodedOrigin) {
        // 创建新图像并应用方向变换
        imageInfo = imageInfo.makeDimensions(orientedDims);
        rb = imageInfo.minRowBytes();
        data = SkData::MakeUninitialized(size);
        auto canvas = SkCanvas::MakeRasterDirect(imageInfo, data->writable_data(), rb);
        canvas->concat(originMatrix);
        canvas->drawImage(image, 0, 0, SkSamplingOptions(), &paint);
        image = SkImages::RasterFromData(imageInfo, std::move(data), rb);
    }

    // 8. 缓存并返回
    return fImages[index] = image;
}
```

### 依赖帧处理
GIF 和 APNG 等格式使用"依赖帧"优化:
- 某些帧仅存储相对于前一帧的差异
- `fRequiredFrame` 指定需要先解码哪一帧
- 播放器先绘制依赖帧,再在其上解码当前帧

**处理流程:**
1. 检查是否有依赖帧且该帧已缓存
2. 将依赖帧绘制到当前帧的像素缓冲区
3. 告诉解码器前置帧索引(`opts.fPriorFrame`)
4. 解码器仅解码增量部分

### EXIF 方向处理
图像可能包含 EXIF 方向信息(旋转、镜像):

```cpp
SkISize SkAnimCodecPlayer::dimensions() const {
    if (SkEncodedOriginSwapsWidthHeight(fCodec->getOrigin())) {
        return { fImageInfo.height(), fImageInfo.width() };  // 交换宽高
    }
    return { fImageInfo.width(), fImageInfo.height() };
}
```

解码时需要两步变换:
1. 解码依赖帧时**撤销**方向变换(因为依赖帧已应用方向)
2. 解码完成后**应用**方向变换到最终图像

### 时间码查找
`seek()` 使用二分查找高效定位帧:

```cpp
bool SkAnimCodecPlayer::seek(uint32_t msec) {
    if (!fTotalDuration) {
        return false;  // 静态图像
    }

    msec %= fTotalDuration;  // 支持循环播放

    auto lower = std::lower_bound(fFrameInfos.begin(), fFrameInfos.end(), msec,
                                  [](const SkCodec::FrameInfo& info, uint32_t msec) {
                                      return (uint32_t)info.fDuration <= msec;
                                  });
    int prevIndex = fCurrIndex;
    fCurrIndex = lower - fFrameInfos.begin();
    return fCurrIndex != prevIndex;
}
```

**时间复杂度:** O(log n),其中 n 是帧数

### 透明度类型调整
处理不透明帧信息与不透明图像信息的冲突:

```cpp
auto imageInfo = fImageInfo;
if (fFrameInfos[index].fAlphaType != kOpaque_SkAlphaType && imageInfo.isOpaque()) {
    imageInfo = imageInfo.makeAlphaType(kPremul_SkAlphaType);
}
```

确保图像缓冲区能正确存储带透明度的帧。

## 依赖关系

### 核心依赖
- **SkCodec**: 图像解码器,支持多帧解码
- **SkImage**: 解码后的图像表示
- **SkCanvas**: 用于绘制依赖帧和应用方向变换
- **SkData**: 像素数据存储

### 使用者
- **Skottie**: Lottie 动画播放器
- **资源管理器**: 动画资源加载和管理

### 依赖图
```
SkAnimCodecPlayer
    ↓ (uses)
SkCodec (解码器)
    ↓ (produces)
SkImage (帧图像)
    ↓ (used by)
动画播放系统
```

## 设计模式与设计决策

### 懒加载与缓存
- **按需解码**: 仅在首次访问时解码帧
- **帧缓存**: 解码后的帧缓存在 `fImages` 数组中
- **静态图像延迟加载**: 使用 `SkCodecImageGenerator` 延迟解码

### 累积时间优化
将帧持续时间转换为累积结束时间:
- 优化时间码查找(O(log n) 而非 O(n))
- 简化二分查找逻辑
- 轻微的内存开销(修改元数据,但总大小不变)

### 透明处理
使用 `SkBlendMode::kSrc` 绘制依赖帧:
- 完全替换像素,不进行混合
- 正确处理透明区域
- 符合 GIF 和 APNG 的语义

### 方向变换分离
将方向变换与解码分离:
- 解码器输出未变换的像素
- 播放器应用方向变换
- 简化解码器实现,提升复用性

## 性能考量

### 内存使用
- **帧缓存**: 每个已访问帧占用一张完整图像的内存
- **静态图像优化**: 使用延迟生成器,仅在访问时解码
- **增量解码**: 依赖帧机制减少存储冗余

**内存权衡:**
- 优势: 重复访问无需重新解码
- 劣势: 长动画可能占用大量内存
- 改进方向: 实现 LRU 缓存淘汰策略

### 时间复杂度
- **seek()**: O(log n),二分查找
- **getFrame()**: O(1),直接数组访问
- **getFrameAt()**: 首次 O(decode),后续 O(1)

### 解码优化
- **依赖帧复用**: 避免重新解码前置帧
- **缓存已解码帧**: 重复播放时无需重新解码
- **方向变换**: 仅在需要时应用,静态图像可能更高效

### 循环播放支持
`msec %= fTotalDuration` 支持循环播放:
- 自动处理时间码超出范围的情况
- 无需上层额外逻辑
- 适合无限循环动画

## 相关文件

### 编解码器
- `include/codec/SkCodec.h`: 图像解码器接口
- `src/codec/SkCodecImageGenerator.h`: 延迟解码图像生成器

### 图像处理
- `include/core/SkImage.h`: 图像对象
- `include/core/SkCanvas.h`: 画布(用于合成和变换)
- `include/core/SkData.h`: 像素数据存储

### 资源管理
- `modules/skresources/include/SkResources.h`: 资源管理接口

### 使用方
- Skottie 动画引擎
- Lottie 播放器
