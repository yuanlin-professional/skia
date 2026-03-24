# SkAnimatedImage

> 源文件: `include/android/SkAnimatedImage.h`, `src/android/SkAnimatedImage.cpp`

## 概述

SkAnimatedImage 是用于绘制动画图像(如 GIF、WebP、HEIF 动画)的 SkDrawable 子类。它管理多帧解码、帧时序、重复计数,并支持缩放、裁剪、方向校正和后处理效果。该类线程不安全,设计用于单线程动画播放场景。

## 架构位置

- **所属子系统**: Android 平台集成层
- **层级**: 图像解码 - 动画支持
- **作用域**: 为 Android 框架提供统一的动画图像接口

## 主要类与结构体

### SkAnimatedImage

动画图像的主类,封装解码器和帧管理逻辑。

**继承关系**: SkDrawable → SkAnimatedImage

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fCodec | std::unique_ptr<SkAndroidCodec> | 底层图像解码器 |
| fDecodeInfo | SkImageInfo | 解码目标信息 |
| fCropRect | const SkIRect | 裁剪矩形 |
| fPostProcess | const sk_sp<SkPicture> | 后处理图片 |
| fFrameCount | const int | 总帧数 |
| fMatrix | SkMatrix | 缩放/旋转/裁剪变换矩阵 |
| fSampleSize | int | 解码采样率 |
| fDisplayFrame | Frame | 当前显示帧 |
| fDecodingFrame | Frame | 解码缓冲帧 |
| fRestoreFrame | Frame | 恢复用帧(用于 RestorePrevious) |
| fRepetitionCount | int | 重复次数(-1 表示无限) |
| fRepetitionsCompleted | int | 已完成重复次数 |
| fFinished | bool | 动画是否结束 |
| fCurrentFrameDuration | int | 当前帧持续时间(毫秒) |
| fFilterMode | SkFilterMode | 绘制时的过滤模式 |

### Frame

内部帧结构,管理单帧的位图和元数据。

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fBitmap | SkBitmap | 帧的像素数据 |
| fIndex | int | 帧索引 |
| fDisposalMethod | SkCodecAnimation::DisposalMethod | 释放方法 |

**OnInit 枚举**:
| 值 | 说明 |
|----|------|
| kRestoreIfNecessary | 如需创建新 SkPixelRef,恢复旧数据 |
| kNoRestore | 不恢复数据 |

## 公共 API 函数

### `static sk_sp<SkAnimatedImage> Make(std::unique_ptr<SkAndroidCodec>, ...)`
- **功能**: 创建动画图像,完整参数版本
- **参数**:
  - `codec`: Android 解码器
  - `info`: 请求的图像信息(可包含缩放)
  - `cropRect`: 裁剪区域
  - `postProcess`: 后处理 SkPicture
- **返回值**: 动画图像智能指针,失败返回 nullptr
- **特殊行为**: 自动解码第一帧

### `static sk_sp<SkAnimatedImage> Make(std::unique_ptr<SkAndroidCodec>)`
- **功能**: 简化版本,使用默认大小,无裁剪和后处理
- **参数**: `codec` - Android 解码器
- **返回值**: 动画图像智能指针

### `void reset()`
- **功能**: 重置动画到开始状态
- **返回值**: 无
- **副作用**: 重置 fFinished 和 fRepetitionsCompleted,重新解码第 0 帧

### `bool isFinished() const`
- **功能**: 检查动画是否已完成
- **返回值**: true 表示所有重复已完成或遇到错误

### `int decodeNextFrame()`
- **功能**: 解码并显示下一帧
- **返回值**: 下一帧的持续时间(毫秒),或 kFinished (-1)
- **副作用**: 更新 fDisplayFrame 和 fCurrentFrameDuration

### `sk_sp<SkImage> getCurrentFrame()`
- **功能**: 获取当前帧的完整 SkImage(应用所有变换)
- **返回值**: SkImage 智能指针,失败返回 nullptr
- **说明**: 如果需要缩放/裁剪,会创建新位图

### `int currentFrameDuration()`
- **功能**: 获取当前帧应显示的时长
- **返回值**: 毫秒数,或 kFinished

### `void setRepetitionCount(int count)`
- **功能**: 设置重复次数
- **参数**: `count` - 新的重复次数(0 表示播放一次,kRepetitionCountInfinite 表示无限)
- **返回值**: 无

### `int getRepetitionCount() const`
- **功能**: 获取当前设置的重复次数
- **返回值**: 重复次数

### `int getFrameCount() const`
- **功能**: 获取总帧数
- **返回值**: 帧数

### `void setFilterMode(SkFilterMode filterMode)`
- **功能**: 设置绘制时的过滤模式
- **参数**: `filterMode` - 过滤模式(kNearest 或 kLinear)
- **返回值**: 无

### `SkFilterMode getFilterMode() const`
- **功能**: 获取当前过滤模式
- **返回值**: SkFilterMode

## 内部实现细节

### 帧缓冲策略

SkAnimatedImage 维护三个帧缓冲区:
1. **fDisplayFrame**: 当前正在显示的帧
2. **fDecodingFrame**: 用于解码新帧的缓冲区
3. **fRestoreFrame**: 保存需要恢复的帧(用于 RestorePrevious 释放方法)

**释放方法处理**:
- **Keep**: 保留当前帧,下一帧在其上合成
- **RestoreBackground**: 清除到背景色
- **RestorePrevious**: 恢复到前一帧(需要保存)

### 帧依赖解析

```cpp
if (frameInfo.fRequiredFrame == SkCodec::kNoFrame) {
    // 独立帧,无需前置帧
    if (is_restore_previous(frameInfo.fDisposalMethod)) {
        // 将被立即丢弃,不覆盖可能有用的帧
        使用 fRestoreFrame 作为解码缓冲
    }
} else {
    // 需要前置帧
    if (validPriorFrame(fDecodingFrame)) {
        // fDecodingFrame 可用
        options.fPriorFrame = fDecodingFrame.fIndex;
    } else if (validPriorFrame(fDisplayFrame)) {
        // 拷贝显示帧到解码缓冲
        fDisplayFrame.copyTo(&fDecodingFrame);
        options.fPriorFrame = fDecodingFrame.fIndex;
    } else if (validPriorFrame(fRestoreFrame)) {
        // 使用或拷贝恢复帧
        options.fPriorFrame = fRestoreFrame.fIndex;
    }
}
```

### 变换矩阵计算

变换顺序: `[crop] × [origin] × [scale]`

```cpp
// 1. 处理 EXIF 方向
if (origin != kDefault) {
    fMatrix = SkEncodedOriginToMatrix(origin, scaledWidth, scaledHeight);
    if (SkEncodedOriginSwapsWidthHeight(origin)) {
        // 交换宽高
        fDecodeInfo = SkPixmapUtils::SwapWidthHeight(fDecodeInfo);
    }
}

// 2. 计算采样和缩放
fSampleSize = fCodec->computeSampleSize(&decodeSize);
if (scaledSize != decodeSize) {
    float scaleX = scaledSize.width() / decodeSize.width();
    float scaleY = scaledSize.height() / decodeSize.height();
    fMatrix.preConcat(SkMatrix::Scale(scaleX, scaleY));
}

// 3. 添加裁剪偏移
fMatrix.postConcat(SkMatrix::Translate(-fCropRect.fLeft, -fCropRect.fTop));
```

### 重复计数逻辑

```cpp
int computeNextFrame(int current, bool* animationEnded) {
    int frameToDecode = current + 1;
    if (frameToDecode == fFrameCount - 1) {
        // 最后一帧
        fRepetitionsCompleted++;
        if (fRepetitionCount != kRepetitionCountInfinite &&
            fRepetitionsCompleted > fRepetitionCount) {
            *animationEnded = true;
        }
    } else if (frameToDecode == fFrameCount) {
        return 0;  // 回到第一帧
    }
    return frameToDecode;
}
```

### SkPixelRef 共享检测

```cpp
bool Frame::init(const SkImageInfo& info, OnInit onInit) {
    if (fBitmap.getPixels()) {
        if (fBitmap.pixelRef()->unique()) {
            // 我们是唯一所有者,直接重用
            return true;
        }
        // SkCanvas 持有引用,需要拷贝
        if (onInit == kRestoreIfNecessary) {
            SkBitmap tmp;
            tmp.tryAllocPixels(info);
            memcpy(tmp.getPixels(), fBitmap.getPixels(), ...);
            swap(tmp, fBitmap);
        }
    }
    return fBitmap.tryAllocPixels(info);
}
```

### HEIF 特殊处理

HEIF 格式在解码前不知道帧持续时间:
```cpp
if (fCodec->getEncodedFormat() == SkEncodedImageFormat::kHEIF) {
    // 解码后更新持续时间
    if (fCodec->codec()->getFrameInfo(frameToDecode, &frameInfo)) {
        fCurrentFrameDuration = frameInfo.fDuration;
    }
}
```

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| SkAndroidCodec | 底层图像解码 |
| SkCodec | 编解码器基础设施 |
| SkBitmap | 帧像素存储 |
| SkPicture | 后处理效果 |
| SkCanvas | 绘制接口 |
| SkImage_Raster | 位图图像创建 |
| SkPixmapUtils | 宽高交换工具 |

### 被依赖的模块
- **Android Framework**: 通过 JNI 调用播放动画
- **Skia 示例程序**: 演示动画播放
- **测试代码**: 验证动画逻辑

## 设计模式与设计决策

### 设计模式
1. **状态机模式**: 帧索引和重复计数管理
2. **策略模式**: 释放方法(Keep/RestoreBackground/RestorePrevious)
3. **双缓冲模式**: displayFrame 和 decodingFrame 交替使用
4. **RAII 模式**: 通过 unique_ptr 管理解码器生命周期

### 设计决策

**为什么不是线程安全?**
- 动画播放通常在 UI 线程
- 避免同步开销
- 简化状态管理

**为什么有三个帧缓冲?**
- displayFrame: 正在显示,不能修改
- decodingFrame: 解码目标
- restoreFrame: RestorePrevious 释放方法需要

**为什么分离 getCurrentFrame() 和 getCurrentFrameSimple()?**
- simple(): 无变换时零拷贝返回位图
- 完整版: 应用缩放/裁剪/后处理,创建新图像
- 性能优化:简单场景避免不必要的拷贝

**为什么支持后处理 SkPicture?**
- 允许 Android 框架应用颜色过滤
- 支持自定义效果(如圆角、阴影)
- 不修改源像素数据

**为什么使用 SkDrawable 而不是 SkImage?**
- SkDrawable 支持延迟绘制
- 可重写 onDraw 应用复杂变换
- 更适合动画场景的状态管理

## 性能考量

### 时间复杂度
- `decodeNextFrame()`: O(pixels) 解码时间
- `getCurrentFrame()`: O(pixels) 如需变换,否则 O(1)
- `reset()`: O(1)
- 其他方法: O(1)

### 内存使用
- **最小**: 1 个帧缓冲(简单动画)
- **典型**: 2-3 个帧缓冲
- **单帧大小**: width × height × 4 字节(RGBA)
- **解码器开销**: ~几 KB 元数据

### 优化策略
1. **采样解码**: 使用 fSampleSize 减少内存和解码时间
2. **SkPixelRef 重用**: 避免频繁分配/释放
3. **快速路径**: simple() 场景零拷贝
4. **延迟后处理**: 只在 getCurrentFrame() 时应用

### 缓存策略
- **不缓存已解码帧**: 流式解码,内存友好
- **保留必要帧**: 仅保留依赖关系需要的帧
- **暂存块**: restoreFrame 仅在需要时分配

## 相关文件
| 文件 | 关系 |
|------|------|
| include/codec/SkAndroidCodec.h | 解码器接口 |
| include/core/SkDrawable.h | 父类 |
| src/codec/SkCodecPriv.h | 编解码器私有工具 |
| src/image/SkImage_Raster.h | 位图图像实现 |

## 使用示例

### 示例 1: 基本播放
```cpp
auto codec = SkAndroidCodec::MakeFromStream(...);
auto animImage = SkAnimatedImage::Make(std::move(codec));

while (!animImage->isFinished()) {
    int duration = animImage->currentFrameDuration();
    canvas->drawDrawable(animImage.get(), 0, 0);

    // 等待 duration 毫秒
    std::this_thread::sleep_for(std::chrono::milliseconds(duration));

    animImage->decodeNextFrame();
}
```

### 示例 2: 缩放和裁剪
```cpp
auto codec = SkAndroidCodec::MakeFromStream(...);
SkImageInfo scaledInfo = codec->getInfo().makeWH(200, 200);
SkIRect cropRect = SkIRect::MakeXYWH(10, 10, 180, 180);

auto animImage = SkAnimatedImage::Make(
    std::move(codec), scaledInfo, cropRect, nullptr);
```

### 示例 3: 无限循环
```cpp
auto animImage = SkAnimatedImage::Make(std::move(codec));
animImage->setRepetitionCount(SkCodec::kRepetitionCountInfinite);

// 永远播放
```

### 示例 4: 后处理
```cpp
SkPictureRecorder recorder;
SkCanvas* canvas = recorder.beginRecording(bounds);
// ... 绘制滤镜效果 ...
sk_sp<SkPicture> postProcess = recorder.finishRecordingAsPicture();

auto animImage = SkAnimatedImage::Make(
    std::move(codec), info, cropRect, postProcess);
```

## 注意事项

1. **线程安全**: 必须在单线程使用,或外部同步
2. **内存峰值**: 最多 3 个全尺寸帧同时存在
3. **EXIF 方向**: 自动处理,无需手动旋转
4. **HEIF 限制**: 帧持续时间在解码后才知道
5. **生命周期**: SkAnimatedImage 拥有解码器,不要共享
6. **性能提示**: 使用采样减少大图像的解码时间
7. **错误处理**: decodeNextFrame() 返回 kFinished 表示错误或结束
