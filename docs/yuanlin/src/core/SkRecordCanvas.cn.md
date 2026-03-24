# SkRecordCanvas

> 源文件: src/core/SkRecordCanvas.h, src/core/SkRecordCanvas.cpp

## 概述

`SkRecordCanvas` 是 `SkCanvas` 的特殊实现,将所有绘图操作录制到 `SkRecord` 中,而不是立即渲染。它实现了 Canvas API 的完整接口,将每个调用转换为 `SkRecords::*` 命令并追加到记录中。该类是 Skia 延迟渲染和绘图优化的核心组件,被 `SkPictureRecorder` 用于创建可复用的绘图内容。

## 架构位置

`SkRecordCanvas` 位于 Skia 录制系统的输入端:
- 继承自 `SkNoDrawCanvas`,提供 Canvas 接口
- 将 API 调用转换为 `SkRecords::*` 命令
- 被 `SkPictureRecorder` 使用
- 管理嵌套的 `SkDrawable` 对象
- 输出的 `SkRecord` 可被 `SkRecordDraw` 回放

## 主要类与结构体

### SkDrawableList

**继承关系:**
```
SkNoncopyable
  └── SkDrawableList
```

**关键成员变量:**
- `SkTDArray<SkDrawable*> fArray`: 可绘制对象数组

**关键方法:**
- `int count() const`: 返回数量
- `void append(SkDrawable*)`: 添加 drawable(增加引用计数)
- `SkBigPicture::SnapshotArray* newDrawableSnapshot()`: 创建图片快照数组
- `~SkDrawableList()`: 析构时释放所有 drawable

### SkRecordCanvas

**继承关系:**
```
SkCanvas
  └── SkNoDrawCanvas
      └── SkCanvasVirtualEnforcer<SkNoDrawCanvas>
          └── SkRecordCanvas
```

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fApproxBytesUsedBySubPictures` | `size_t` | 嵌套图片占用的字节数 |
| `fRecord` | `SkRecord*` | 目标录制对象(非拥有) |
| `fDrawableList` | `std::unique_ptr<SkDrawableList>` | 嵌套的可绘制对象列表 |

## 公共 API 函数

### 构造函数

```cpp
SkRecordCanvas(SkRecord* record, int width, int height)  // 已弃用
SkRecordCanvas(SkRecord* record, const SkRect& bounds)
```

**参数:**
- `record`: 目标 `SkRecord`(不获取所有权)
- `bounds`: 画布边界(自动转换为安全的整数边界)

**注意:** `record` 指针必须在 `SkRecordCanvas` 生命周期内有效。

### reset

```cpp
void reset(SkRecord* record, const SkRect& bounds)
```

重置画布到新的录制对象和边界,清空之前的状态。

### forgetRecord

```cpp
void forgetRecord()
```

使 `SkRecordCanvas` 忘记其 `SkRecord`,后续调用将失败。用于提前终止录制。

### getDrawableList / detachDrawableList

```cpp
SkDrawableList* getDrawableList() const
std::unique_ptr<SkDrawableList> detachDrawableList()
```

访问或分离嵌套的 drawable 列表。

### approxBytesUsedBySubPictures

```cpp
size_t approxBytesUsedBySubPictures() const
```

返回嵌套图片占用的近似字节数。

## 内部实现细节

### append 模板方法

```cpp
template <typename T, typename... Args>
void append(Args&&... args)
```

**功能:** 向 `fRecord` 追加命令的核心方法。

**实现:**
```cpp
new (fRecord->append<T>()) T{std::forward<Args>(args)...};
```

使用 placement new 在 arena 分配的内存上构造命令对象。

### copy 模板方法

```cpp
template <typename T>
T* copy(const T* src)

template <typename T>
T* copy(const T src[], size_t count)
```

**功能:** 复制可选参数或数组到 `fRecord` 的 arena。

**特殊化:**
- `T* copy(const T*)`: 返回 `nullptr` 如果源为空
- `char* copy(const char*, size_t)`: 使用 `memcpy` 优化字符串拷贝
- `char* copy(const char*)`: 自动计算字符串长度(包括 `\0`)

### 状态管理命令实现

#### willSave / didRestore

```cpp
void willSave() override {
    this->append<SkRecords::Save>();
}

void didRestore() override {
    this->append<SkRecords::Restore>(this->getTotalMatrix());
}
```

**注意:** `Restore` 记录恢复后的矩阵,用于 `FillBounds` 的 CTM 追踪。

#### getSaveLayerStrategy

```cpp
SaveLayerStrategy getSaveLayerStrategy(const SaveLayerRec& rec) override
```

**流程:**
1. 复制 filter 数组到 arena
2. 复制 bounds 和 paint(如果存在)
3. 追加 `SkRecords::SaveLayer` 命令
4. 返回 `kNoLayer_SaveLayerStrategy`(告诉基类不创建实际图层)

#### onDoSaveBehind

```cpp
bool onDoSaveBehind(const SkRect* subset) override {
    this->append<SkRecords::SaveBehind>(this->copy(subset));
    return false;
}
```

### 变换命令实现

```cpp
void didConcat44(const SkM44& m) override {
    this->append<SkRecords::Concat44>(m);
}

void didSetM44(const SkM44& m) override {
    this->append<SkRecords::SetM44>(m);
}

void didScale(SkScalar sx, SkScalar sy) override {
    this->append<SkRecords::Scale>(sx, sy);
}

void didTranslate(SkScalar dx, SkScalar dy) override {
    this->append<SkRecords::Translate>(dx, dy);
}
```

**设计:** 监听变换而不是拦截,让基类维护实际的 CTM。

### 裁剪命令实现

```cpp
void onClipRect(const SkRect& rect, SkClipOp op, ClipEdgeStyle edgeStyle) override {
    INHERITED(onClipRect, rect, op, edgeStyle);
    SkRecords::ClipOpAndAA opAA(op, kSoft_ClipEdgeStyle == edgeStyle);
    this->append<SkRecords::ClipRect>(rect, opAA);
}
```

**关键点:**
- 先调用 `INHERITED` 宏让基类更新裁剪状态
- 然后录制命令
- 使用 `ClipOpAndAA` 紧凑存储裁剪操作和抗锯齿标志

### 绘制命令实现

#### onDrawRect

```cpp
void onDrawRect(const SkRect& rect, const SkPaint& paint) override {
    this->append<SkRecords::DrawRect>(paint, rect);
}
```

**模式:** 大多数绘制命令都是简单的追加操作。

#### onDrawImage2

```cpp
void onDrawImage2(const SkImage* image, SkScalar x, SkScalar y,
                  const SkSamplingOptions& sampling, const SkPaint* paint) override {
    this->append<SkRecords::DrawImage>(this->copy(paint), sk_ref_sp(image), x, y, sampling);
}
```

**注意:**
- 使用 `sk_ref_sp` 增加图像引用计数
- 使用 `this->copy(paint)` 处理可选 paint

#### onDrawImageLattice2

```cpp
void onDrawImageLattice2(const SkImage* image, const Lattice& lattice,
                         const SkRect& dst, SkFilterMode filter, const SkPaint* paint) override
```

**复杂度:** 需要复制多个数组:
- `fXDivs` 和 `fYDivs`(分割线)
- `fRectTypes` 和 `fColors`(九宫格类型和颜色)

#### onDrawDrawable

```cpp
void onDrawDrawable(SkDrawable* drawable, const SkMatrix* matrix) override {
    if (!fDrawableList) {
        fDrawableList = std::make_unique<SkDrawableList>();
    }
    fDrawableList->append(drawable);
    this->append<SkRecords::DrawDrawable>(
        this->copy(matrix), drawable->getBounds(), fDrawableList->count() - 1);
}
```

**存储策略:**
- `SkDrawable` 存储在独立的 `fDrawableList` 中
- 命令只记录索引和边界

#### onDrawGlyphRunList

```cpp
void onDrawGlyphRunList(const sktext::GlyphRunList& glyphRunList,
                        const SkPaint& paint) override {
    sk_sp<SkTextBlob> blob = ...;
    this->onDrawTextBlob(blob.get(), glyphRunList.origin().x(), glyphRunList.origin().y(), paint);
}
```

**转换:** 将 `GlyphRunList` 转换为 `TextBlob` 后录制。

### safe_picture_bounds 辅助函数

```cpp
static SkIRect safe_picture_bounds(const SkRect& bounds)
```

**功能:** 将浮点边界转换为安全的整数边界。

**限制:**
- 边缘限制在 `±SK_MaxS32FitsInFloat / 2 - 1`
- 防止宽高计算溢出(超过 20 亿时会导致负尺寸)
- 无重叠区域时返回空矩形

### INHERITED 宏

```cpp
#define INHERITED(method, ...) this->SkNoDrawCanvas::method(__VA_ARGS__)
```

用于调用基类方法,主要用于裁剪操作的双重处理。

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| `SkRecord` | 命令存储 |
| `SkRecords` | 命令类型 |
| `SkNoDrawCanvas` | 基类,提供状态管理 |
| `SkDrawable` | 嵌套可绘制对象 |
| `SkBigPicture` | SnapshotArray 类型 |
| `SkCanvasPriv` | 访问 Canvas 私有 API |

**被依赖的模块:**

| 模块 | 关系 |
|------|------|
| `SkPictureRecorder` | 创建并使用 SkRecordCanvas |
| 录制客户端代码 | 通过 Canvas API 录制 |

## 设计模式与设计决策

### 1. 适配器模式(Adapter Pattern)
将 `SkCanvas` API 适配为 `SkRecord` 命令序列。

### 2. 委托模式(Delegation Pattern)
继承 `SkNoDrawCanvas` 处理状态管理,专注于命令录制。

### 3. 模板方法模式(Template Method Pattern)
基类定义流程,派生类实现具体的 `on*` 方法。

### 4. Arena 分配(Arena Allocation)
所有数据通过 `fRecord->alloc()` 在 arena 中分配,简化内存管理。

### 5. 引用计数(Reference Counting)
对 `SkImage`、`SkTextBlob` 等重对象使用 `sk_sp` 共享所有权。

### 6. 延迟绑定(Lazy Binding)
`fDrawableList` 仅在需要时创建。

### 7. 完美转发(Perfect Forwarding)
`append` 使用 `std::forward` 避免不必要的拷贝。

## 性能考量

### 1. Arena 分配优势
- 批量分配减少系统调用
- 连续内存提高缓存命中率
- 一次性释放加速析构

### 2. 避免虚函数调用
录制本身很轻量,大部分操作是简单的内存拷贝。

### 3. 智能指针开销
对大对象(图像、文本)使用引用计数避免深拷贝。

### 4. 字符串优化
使用 `memcpy` 复制字符串比逐字符拷贝快约 2 倍。

### 5. 可选参数处理
使用 `Optional` 避免为 `nullptr` 分配内存。

### 6. 边界安全检查
`safe_picture_bounds` 防止整数溢出导致的崩溃。

### 7. 懒初始化
`fDrawableList` 只在需要时创建,节省大多数情况下的开销。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `src/core/SkRecord.h` | 命令存储容器 |
| `src/core/SkRecords.h` | 命令类型定义 |
| `include/utils/SkNoDrawCanvas.h` | 基类 |
| `include/core/SkPictureRecorder.h` | 创建 SkRecordCanvas |
| `include/core/SkDrawable.h` | 嵌套可绘制对象 |
| `src/core/SkBigPicture.h` | SnapshotArray 定义 |
| `src/core/SkCanvasPriv.h` | Canvas 私有 API |
| `include/core/SkImage.h` | 图像资源 |
| `include/core/SkTextBlob.h` | 文本数据 |
| `src/text/GlyphRun.h` | 字形运行列表 |
| `src/utils/SkPatchUtils.h` | Patch 工具 |
