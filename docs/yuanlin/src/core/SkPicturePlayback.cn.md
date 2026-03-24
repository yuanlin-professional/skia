# SkPicturePlayback

> 源文件
> - src/core/SkPicturePlayback.h
> - src/core/SkPicturePlayback.cpp

## 概述

`SkPicturePlayback` 是 Skia Picture 子系统的回放引擎，负责将 `SkPictureData` 中存储的操作码流解析并执行到 `SkCanvas` 上。它实现了完整的操作码解释器，支持所有绘图、变换、裁剪和状态管理操作。

该类是无状态的回放器，每次调用 `draw()` 时遍历操作码流，逐条解析并调用 Canvas 相应的方法。它处理复杂的操作码格式解析、资源引用解析、以及版本兼容性问题。

## 架构位置

`SkPicturePlayback` 在 Picture 架构中扮演执行器的角色：

- 从 `SkPictureData` 读取操作码和资源
- 将操作重播到任意 `SkCanvas` 上
- 被 `SkBigPicture` 的 `playback()` 方法调用
- 支持中断回放（通过 `AbortCallback`）

## 主要类与结构体

### SkPicturePlayback

回放引擎类。

**继承关系**
- 继承自：`SkNoncopyable`（不可拷贝）

**关键成员变量**

| 成员变量 | 类型 | 描述 |
|---------|------|------|
| fPictureData | const SkPictureData* | Picture 数据指针 |
| fCurOffset | size_t | 当前操作偏移量（用于调试） |

**嵌套类**

```cpp
class AutoResetOpID {
public:
    AutoResetOpID(SkPicturePlayback* playback);
    ~AutoResetOpID();  // 自动重置操作ID
private:
    SkPicturePlayback* fPlayback;
};
```

## 公共 API 函数

### 构造与回放

```cpp
// 构造函数
explicit SkPicturePlayback(const SkPictureData* data);

// 主回放函数
void draw(SkCanvas* canvas,
          SkPicture::AbortCallback* callback,
          SkReadBuffer* buffer);

// 调试接口
size_t curOpID() const;      // 当前操作ID
void resetOpID();             // 重置操作ID
```

## 内部实现细节

### 回放主循环

```cpp
void SkPicturePlayback::draw(SkCanvas* canvas,
                             SkPicture::AbortCallback* callback,
                             SkReadBuffer* buffer)
{
    AutoResetOpID aroi(this);
    SkASSERT(0 == fCurOffset);

    // 创建读取器
    SkReadBuffer reader(fPictureData->opData()->bytes(),
                        fPictureData->opData()->size());
    reader.setVersion(fPictureData->info().getVersion());

    // 记录初始矩阵（用于SET_MATRIX）
    SkM44 initialMatrix = canvas->getLocalToDevice();

    SkAutoCanvasRestore acr(canvas, false);

    // 主循环
    while (!reader.eof() && reader.isValid()) {
        // 检查中断
        if (callback && callback->abort()) {
            return;
        }

        fCurOffset = reader.offset();

        // 读取操作码和大小
        uint32_t bits = reader.readInt();
        uint32_t op   = bits >> 24;
        uint32_t size = bits & 0xffffff;
        if (size == 0xffffff) {
            size = reader.readInt();  // 扩展大小
        }

        // 验证操作码
        if (!reader.validate(size > 0 && op > UNUSED &&
                            op <= LAST_DRAWTYPE_ENUM)) {
            return;
        }

        // 处理操作
        this->handleOp(&reader, (DrawType)op, size, canvas, initialMatrix);
    }

    // 传播错误状态
    if (buffer) {
        buffer->validate(reader.isValid());
    }
}
```

### 操作码解析

`handleOp()` 使用大型 switch 语句处理所有操作：

```cpp
void SkPicturePlayback::handleOp(SkReadBuffer* reader,
                                 DrawType op,
                                 uint32_t size,
                                 SkCanvas* canvas,
                                 const SkM44& initialMatrix)
{
    switch (op) {
        case SAVE:
            canvas->save();
            break;

        case RESTORE:
            canvas->restore();
            break;

        case TRANSLATE: {
            SkScalar dx = reader->readScalar();
            SkScalar dy = reader->readScalar();
            BREAK_ON_READ_ERROR(reader);
            canvas->translate(dx, dy);
            break;
        }

        case DRAW_RECT: {
            const SkPaint& paint = fPictureData->requiredPaint(reader);
            SkRect rect;
            reader->readRect(&rect);
            BREAK_ON_READ_ERROR(reader);
            canvas->drawRect(rect, paint);
            break;
        }

        // ... 处理所有操作码
    }
}
```

### 裁剪操作处理

裁剪操作需要处理版本兼容性：

```cpp
static bool do_clip_op(SkReadBuffer* reader, SkCanvas* canvas,
                       SkRegion::Op op, SkClipOp* clipOpToUse)
{
    switch(op) {
        case SkRegion::kDifference_Op:
        case SkRegion::kIntersect_Op:
            // 完全支持，直接映射
            *clipOpToUse = static_cast<SkClipOp>(op);
            return true;

        case SkRegion::kReplace_Op:
            // 模拟替换操作：重置 + 相交
            SkASSERT(reader->isVersionLT(SkPicturePriv::kNoExpandingClipOps));
            SkCanvasPriv::ResetClip(canvas);
            *clipOpToUse = SkClipOp::kIntersect;
            return true;

        default:
            // 扩展裁剪操作（旧版本）：忽略
            SkASSERT(reader->isVersionLT(SkPicturePriv::kNoExpandingClipOps));
            return false;
    }
}

// 使用示例
case CLIP_RECT: {
    SkRect rect;
    reader->readRect(&rect);
    uint32_t packed = reader->readInt();
    SkRegion::Op rgnOp = ClipParams_unpackRegionOp(reader, packed);
    bool doAA = ClipParams_unpackDoAA(packed);
    size_t offsetToRestore = reader->readInt();
    validate_offsetToRestore(reader, offsetToRestore);
    BREAK_ON_READ_ERROR(reader);

    SkClipOp clipOp;
    if (do_clip_op(reader, canvas, rgnOp, &clipOp)) {
        canvas->clipRect(rect, clipOp, doAA);
    }

    // 优化：空裁剪跳过
    if (canvas->isClipEmpty() && offsetToRestore) {
        reader->skip(offsetToRestore - reader->offset());
    }
    break;
}
```

### 裁剪跳转优化

空裁剪区域可以跳过后续操作直到恢复点：

```cpp
static void validate_offsetToRestore(SkReadBuffer* reader,
                                     size_t offsetToRestore)
{
    if (offsetToRestore) {
        reader->validate(SkIsAlign4(offsetToRestore) &&
                        offsetToRestore >= reader->offset());
    }
}

// 如果裁剪为空，跳到恢复点
if (canvas->isClipEmpty() && offsetToRestore) {
    reader->skip(offsetToRestore - reader->offset());
}
```

### SaveLayer 处理

SaveLayer 支持复杂的参数组合：

```cpp
case SAVE_LAYER_SAVELAYERREC: {
    SkCanvas::SaveLayerRec rec(nullptr, nullptr, nullptr, 0);
    const uint32_t flatFlags = reader->readInt();
    SkRect bounds;
    AutoSTArray<2, sk_sp<SkImageFilter>> filters;

    // 解析可选参数
    if (flatFlags & SAVELAYERREC_HAS_BOUNDS) {
        reader->readRect(&bounds);
        rec.fBounds = &bounds;
    }
    if (flatFlags & SAVELAYERREC_HAS_PAINT) {
        rec.fPaint = &fPictureData->requiredPaint(reader);
    }
    if (flatFlags & SAVELAYERREC_HAS_BACKDROP) {
        const SkPaint& paint = fPictureData->requiredPaint(reader);
        rec.fBackdrop = paint.getImageFilter();
    }
    if (flatFlags & SAVELAYERREC_HAS_FLAGS) {
        rec.fSaveLayerFlags = reader->readInt();
    }
    if (flatFlags & SAVELAYERREC_HAS_BACKDROP_SCALE) {
        SkCanvasPriv::SetBackdropScaleFactor(&rec, reader->readScalar());
    }
    if (flatFlags & SAVELAYERREC_HAS_MULTIPLE_FILTERS) {
        int filterCount = reader->readUInt();
        reader->validate(filterCount > 0 &&
                        filterCount <= SkCanvas::kMaxFiltersPerLayer);
        BREAK_ON_READ_ERROR(reader);

        filters.reset(filterCount);
        for (int i = 0; i < filterCount; ++i) {
            const SkPaint& paint = fPictureData->requiredPaint(reader);
            filters[i] = paint.refImageFilter();
        }
        rec.fFilters = filters;
    }
    if (flatFlags & SAVELAYERREC_HAS_BACKDROP_TILEMODE) {
        rec.fBackdropTileMode = reader->read32LE(SkTileMode::kLastTileMode);
    }
    BREAK_ON_READ_ERROR(reader);

    canvas->saveLayer(rec);
    break;
}
```

### 图像集合绘制

EdgeAA 图像集合是最复杂的操作之一：

```cpp
case DRAW_EDGEAA_IMAGE_SET2: {
    int cnt = reader->readInt();
    if (!reader->validate(cnt >= 0)) break;

    const SkPaint* paint = fPictureData->optionalPaint(reader);
    SkSamplingOptions sampling = reader->readSampling();
    SkCanvas::SrcRectConstraint constraint =
        reader->checkRange(SkCanvas::kStrict_SrcRectConstraint,
                          SkCanvas::kFast_SrcRectConstraint);

    // 预先验证数据量
    if (!reader->validate(SkSafeMath::Mul(cnt, kEntryReadSize) <=
                         reader->available())) {
        break;
    }

    // 读取条目
    int expectedClipPointCount = 0;
    int maxMatrixIndex = -1;
    AutoTArray<SkCanvas::ImageSetEntry> set(cnt);

    for (int i = 0; i < cnt && reader->isValid(); ++i) {
        set[i].fImage = sk_ref_sp(fPictureData->getImage(reader));
        reader->readRect(&set[i].fSrcRect);
        reader->readRect(&set[i].fDstRect);
        set[i].fMatrixIndex = reader->readInt();
        set[i].fAlpha = reader->readScalar();
        set[i].fAAFlags = reader->readUInt();
        set[i].fHasClip = reader->readInt();

        expectedClipPointCount += set[i].fHasClip ? 4 : 0;
        if (set[i].fMatrixIndex > maxMatrixIndex) {
            maxMatrixIndex = set[i].fMatrixIndex;
        }
    }

    // 读取裁剪点
    int dstClipPointCount = reader->readInt();
    const SkPoint* dstClips = nullptr;
    if (reader->validate(dstClipPointCount == expectedClipPointCount)) {
        if (dstClipPointCount > 0) {
            dstClips = (const SkPoint*)reader->skip(
                dstClipPointCount, sizeof(SkPoint));
        }
    }

    // 读取矩阵
    int matrixCount = reader->readInt();
    if (!reader->validate(maxMatrixIndex == (matrixCount - 1))) break;

    TArray<SkMatrix> matrices(matrixCount);
    for (int i = 0; i < matrixCount && reader->isValid(); ++i) {
        reader->readMatrix(&matrices.push_back());
    }
    BREAK_ON_READ_ERROR(reader);

    // 绘制
    canvas->experimental_DrawEdgeAAImageSet(
        set.get(), cnt, dstClips, matrices.begin(),
        sampling, paint, constraint);
    break;
}
```

### 矩阵设置处理

SET_MATRIX 和 SET_M44 需要与初始矩阵组合：

```cpp
case SET_M44: {
    SkM44 m;
    reader->read(&m);
    canvas->setMatrix(initialMatrix * m);  // 组合初始矩阵
    break;
}

case SET_MATRIX: {
    SkMatrix matrix;
    reader->readMatrix(&matrix);
    canvas->setMatrix(initialMatrix * SkM44(matrix));  // 组合
    break;
}
```

这确保 Picture 相对于当前 Canvas 状态正确绘制。

### 错误处理

使用宏简化错误检查：

```cpp
#define BREAK_ON_READ_ERROR(r)  if (!r->isValid()) break

// 使用示例
SkScalar dx = reader->readScalar();
SkScalar dy = reader->readScalar();
BREAK_ON_READ_ERROR(reader);
canvas->translate(dx, dy);
```

读取错误时中断操作解析，但不崩溃。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| SkPictureData | 提供操作数据和资源 |
| SkPictureFlat | 操作码定义 |
| SkReadBuffer | 读取操作流 |
| SkCanvas | 执行绘图操作 |
| SkCanvasPriv | 访问私有 Canvas 功能 |
| SkPicturePriv | 版本检查 |

### 被依赖的模块

| 模块 | 关系 |
|-----|------|
| SkBigPicture | 调用 SkPicturePlayback::draw() |
| SkPicture | 间接通过 SkBigPicture 使用 |

## 设计模式与设计决策

### 解释器模式

`SkPicturePlayback` 是操作码解释器：
- 操作码是"指令"
- Canvas 是"执行上下文"
- 数据流是"程序"

### 无状态设计

回放器本身不维护绘图状态：
- 所有状态由 Canvas 管理
- 可以重复回放到不同 Canvas
- 线程安全（如果 Canvas 线程安全）

### 版本兼容性

通过 `reader->isVersionLT()` 处理旧版本：
- 支持读取旧格式 Picture
- 模拟废弃的操作（如 kReplace_Op）
- 跳过不识别的数据

### 优化中断

支持回放中断：
- 定期检查 `AbortCallback`
- 长时间操作可及时终止
- 用于 UI 响应性

## 性能考量

### 裁剪跳转

空裁剪区域跳转优化：
- 避免处理不可见操作
- 减少 Canvas 调用
- 显著提升复杂场景性能

### 直接指针访问

使用 `reader->skip()` 直接访问数据：

```cpp
const SkPoint* pts = (const SkPoint*)reader->skip(count, sizeof(SkPoint));
```

避免逐个读取，提高性能。

### 缓存初始矩阵

记录初始矩阵避免重复查询：

```cpp
SkM44 initialMatrix = canvas->getLocalToDevice();
// 在整个回放过程中重用
```

### 验证成本

安全验证有性能开销：
- 索引范围检查
- 数据可用性检查
- 操作码有效性检查

权衡安全性和性能。

## 相关文件

| 文件路径 | 描述 |
|---------|------|
| src/core/SkPictureData.h/cpp | 提供数据和资源 |
| src/core/SkPictureFlat.h/cpp | 操作码和标志定义 |
| src/core/SkBigPicture.h/cpp | 调用回放器 |
| src/core/SkReadBuffer.h | 读取缓冲区 |
| src/core/SkCanvasPriv.h | 私有 Canvas API |
| src/core/SkPicturePriv.h | 版本信息 |
| include/core/SkCanvas.h | Canvas 接口 |
| include/core/SkPicture.h | Picture 接口 |
