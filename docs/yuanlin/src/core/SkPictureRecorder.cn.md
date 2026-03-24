# SkPictureRecorder

> 源文件
> - include/core/SkPictureRecorder.h
> - src/core/SkPictureRecorder.cpp

## 概述

`SkPictureRecorder` 是 Skia Picture 子系统的高层录制接口，提供简单易用的 API 来记录绘图命令并生成 `SkPicture` 或 `SkDrawable` 对象。它封装了底层的 `SkRecord` 和 `SkRecordCanvas` 机制，管理录制的生命周期，并支持边界框层次结构（BBH）加速。

该类是用户与 Picture 录制功能交互的主要入口点，通过 `beginRecording()` 开始录制，通过 `finishRecordingAsPicture()` 或 `finishRecordingAsDrawable()` 结束录制并获取结果。

## 架构位置

`SkPictureRecorder` 位于 Skia Picture 子系统的用户接口层：

- 提供公共 API 用于 Picture 录制
- 内部使用 `SkRecordCanvas` 记录命令
- 使用 `SkRecord` 存储命令流
- 支持 `SkBBoxHierarchy` 进行空间加速
- 生成 `SkBigPicture` 或 `SkRecordedDrawable`

## 主要类与结构体

### SkPictureRecorder

Picture 录制器类。

**关键成员变量**

| 成员变量 | 类型 | 描述 |
|---------|------|------|
| fBBH | sk_sp<SkBBoxHierarchy> | 边界框层次结构（可选） |
| fRecorder | unique_ptr<SkRecordCanvas> | 录制画布 |
| fRecord | sk_sp<SkRecord> | 命令记录 |
| fCullRect | SkRect | 裁剪矩形 |
| fActivelyRecording | bool | 是否正在录制 |

**不可移动/拷贝**
- 删除移动构造函数和移动赋值
- 确保唯一所有权

## 公共 API 函数

### 构造与析构

```cpp
// 构造函数
SkPictureRecorder();

// 析构函数
~SkPictureRecorder();
```

### 开始录制

```cpp
// 使用边界框层次结构开始录制
SkCanvas* beginRecording(const SkRect& bounds,
                         sk_sp<SkBBoxHierarchy> bbh);

// 使用工厂创建 BBH
SkCanvas* beginRecording(const SkRect& bounds,
                         SkBBHFactory* bbhFactory = nullptr);

// 使用宽高开始录制
SkCanvas* beginRecording(SkScalar width, SkScalar height,
                         SkBBHFactory* bbhFactory = nullptr);
```

### 获取录制画布

```cpp
// 获取当前录制画布（如果正在录制）
SkCanvas* getRecordingCanvas();
```

### 完成录制

```cpp
// 完成录制并返回 Picture
sk_sp<SkPicture> finishRecordingAsPicture();

// 完成录制并返回 Picture（更新裁剪矩形）
sk_sp<SkPicture> finishRecordingAsPictureWithCull(const SkRect& cullRect);

// 完成录制并返回 Drawable
sk_sp<SkDrawable> finishRecordingAsDrawable();
```

### 私有方法

```cpp
// Android Framework 使用
void partialReplay(SkCanvas* canvas) const;
```

## 内部实现细节

### 构造函数

```cpp
SkPictureRecorder::SkPictureRecorder() {
    fActivelyRecording = false;
    // 预创建空的 RecordCanvas
    fRecorder = std::make_unique<SkRecordCanvas>(nullptr, SkRect::MakeEmpty());
}
```

预创建 Canvas 避免空指针检查。

### 开始录制

```cpp
SkCanvas* SkPictureRecorder::beginRecording(const SkRect& userCullRect,
                                            sk_sp<SkBBoxHierarchy> bbh)
{
    // 处理空矩形
    const SkRect cullRect = userCullRect.isEmpty() ?
                            SkRect::MakeEmpty() : userCullRect;

    fCullRect = cullRect;
    fBBH = std::move(bbh);

    // 创建或重用 SkRecord
    if (!fRecord) {
        fRecord.reset(new SkRecord);
    }

    // 重置录制画布
    fRecorder->reset(fRecord.get(), cullRect);
    fActivelyRecording = true;

    return this->getRecordingCanvas();
}

SkCanvas* SkPictureRecorder::beginRecording(const SkRect& bounds,
                                            SkBBHFactory* factory)
{
    return this->beginRecording(bounds, factory ? (*factory)() : nullptr);
}
```

**关键点**：
- 重用 `fRecord` 对象以减少分配
- 支持空边界（表示无限大）
- BBH 可选，用于空间加速

### 完成录制为 Picture

```cpp
sk_sp<SkPicture> SkPictureRecorder::finishRecordingAsPicture() {
    fActivelyRecording = false;

    // 补齐缺失的 restore
    fRecorder->restoreToCount(1);

    // 空 Picture 优化
    if (fRecord->count() == 0) {
        return sk_make_sp<SkEmptyPicture>();
    }

    // 优化记录
    SkRecordOptimize(fRecord.get());

    // 获取可绘制对象列表
    SkDrawableList* drawableList = fRecorder->getDrawableList();
    std::unique_ptr<SkBigPicture::SnapshotArray> pictList{
        drawableList ? drawableList->newDrawableSnapshot() : nullptr
    };

    // 构建 BBH
    if (fBBH) {
        AutoTArray<SkRect> bounds(fRecord->count());
        AutoTMalloc<SkBBoxHierarchy::Metadata> meta(fRecord->count());

        // 计算每个操作的边界
        SkRecordFillBounds(fCullRect, *fRecord, bounds.data(), meta);

        // 插入 BBH
        fBBH->insert(bounds.data(), meta, fRecord->count());

        // 根据实际边界收缩裁剪矩形
        SkRect bbhBound = SkRect::MakeEmpty();
        for (int i = 0; i < fRecord->count(); i++) {
            bbhBound.join(bounds[i]);
        }
        fCullRect = bbhBound;
    }

    // 计算子 Picture 字节数
    size_t subPictureBytes = fRecorder->approxBytesUsedBySubPictures();
    for (int i = 0; pictList && i < pictList->count(); i++) {
        subPictureBytes += pictList->begin()[i]->approximateBytesUsed();
    }

    // 创建 SkBigPicture
    return sk_make_sp<SkBigPicture>(fCullRect,
                                    std::move(fRecord),
                                    std::move(pictList),
                                    std::move(fBBH),
                                    subPictureBytes);
}
```

### 空 Picture 实现

```cpp
class SkEmptyPicture final : public SkPicture {
public:
    void playback(SkCanvas*, AbortCallback*) const override { }

    size_t approximateBytesUsed() const override {
        return sizeof(*this);
    }

    int approximateOpCount(bool nested) const override {
        return 0;
    }

    SkRect cullRect() const override {
        return SkRect::MakeEmpty();
    }
};
```

空 Picture 优化，避免分配无用的数据结构。

### 更新裁剪矩形

```cpp
sk_sp<SkPicture> SkPictureRecorder::finishRecordingAsPictureWithCull(
    const SkRect& cullRect)
{
    fCullRect = cullRect;
    return this->finishRecordingAsPicture();
}
```

允许在录制后调整裁剪矩形（影响 BBH 生成）。

### 完成录制为 Drawable

```cpp
sk_sp<SkDrawable> SkPictureRecorder::finishRecordingAsDrawable() {
    fActivelyRecording = false;

    // 补齐缺失的 restore
    fRecorder->restoreToCount(1);

    // 优化记录
    SkRecordOptimize(fRecord.get());

    // 构建 BBH
    if (fBBH) {
        AutoTArray<SkRect> bounds(fRecord->count());
        AutoTMalloc<SkBBoxHierarchy::Metadata> meta(fRecord->count());
        SkRecordFillBounds(fCullRect, *fRecord, bounds.data(), meta);
        fBBH->insert(bounds.data(), meta, fRecord->count());
    }

    // 创建 SkRecordedDrawable
    sk_sp<SkDrawable> drawable =
        sk_make_sp<SkRecordedDrawable>(std::move(fRecord),
                                       std::move(fBBH),
                                       fRecorder->detachDrawableList(),
                                       fCullRect);

    return drawable;
}
```

**与 Picture 的区别**：
- Drawable 保留对嵌套 Drawable 的实时引用
- Picture 快照嵌套 Drawable 的状态
- Drawable 反映嵌套对象的当前状态

### 部分重播

```cpp
void SkPictureRecorder::partialReplay(SkCanvas* canvas) const {
    if (nullptr == canvas) {
        return;
    }

    // 获取 Drawable 列表
    int drawableCount = 0;
    SkDrawable* const* drawables = nullptr;
    SkDrawableList* drawableList = fRecorder->getDrawableList();
    if (drawableList) {
        drawableCount = drawableList->count();
        drawables = drawableList->begin();
    }

    // 重播记录
    SkRecordDraw(*fRecord, canvas, nullptr, drawables, drawableCount,
                 nullptr/*bbh*/, nullptr/*callback*/);
}
```

Android Framework 使用此方法在录制期间预览绘制结果。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| SkRecordCanvas | 执行实际录制 |
| SkRecord | 存储命令流 |
| SkBBoxHierarchy | 空间加速结构 |
| SkBigPicture | 生成的 Picture 实现 |
| SkRecordedDrawable | 生成的 Drawable 实现 |
| SkRecordOpts | 优化命令流 |
| SkRecordDraw | 重播命令 |

### 被依赖的模块

| 模块 | 关系 |
|-----|------|
| 用户代码 | 调用 SkPictureRecorder API |
| Android Framework | 使用 partialReplay |
| 测试代码 | 使用录制功能 |

## 设计模式与设计决策

### 建造者模式

`SkPictureRecorder` 实现建造者模式：
- `beginRecording()` 开始构建
- 通过 Canvas 添加操作
- `finishRecording*()` 完成并返回产品

### RAII 资源管理

录制状态通过对象生命周期管理：
- 构造函数初始化状态
- 析构函数清理资源
- 明确的开始/结束方法

### 延迟优化

优化推迟到完成录制时：
- 录制期间快速记录
- 完成时执行 `SkRecordOptimize`
- 平衡录制和回放性能

### 可选 BBH

边界框层次结构为可选功能：
- 不需要加速时省略
- 支持多种 BBH 实现
- 使用工厂模式创建

## 性能考量

### 对象重用

重用 `fRecord` 对象：
- 避免重复分配
- 减少内存碎片
- 提高连续录制性能

### 空 Picture 优化

检测空录制并返回轻量级对象：
- 避免分配完整 Picture
- 减少内存占用
- 快速返回

### BBH 构建

延迟构建 BBH：
- 录制时不计算边界
- 完成时一次性计算
- 减少录制开销

### 裁剪矩形优化

根据实际内容收缩裁剪矩形：
- 提高 BBH 效率
- 减少回放时的裁剪测试
- 更精确的边界信息

## 相关文件

| 文件路径 | 描述 |
|---------|------|
| src/core/SkRecordCanvas.h/cpp | 录制画布实现 |
| src/core/SkRecord.h | 命令存储 |
| src/core/SkBigPicture.h/cpp | Picture 实现 |
| src/core/SkRecordedDrawable.h/cpp | Drawable 实现 |
| src/core/SkRecordOpts.h/cpp | 命令优化 |
| src/core/SkRecordDraw.h/cpp | 命令重播 |
| include/core/SkBBHFactory.h | BBH 工厂接口 |
| include/core/SkPicture.h | Picture 接口 |
| include/core/SkDrawable.h | Drawable 接口 |
