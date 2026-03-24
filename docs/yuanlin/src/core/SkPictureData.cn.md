# SkPictureData

> 源文件
> - src/core/SkPictureData.h
> - src/core/SkPictureData.cpp

## 概述

`SkPictureData` 是 Skia Picture 子系统的核心存储类，负责管理已记录的绘图操作数据及其关联的资源。它将 `SkPictureRecord` 记录的命令流和资源（画笔、路径、图像、子图片等）组织成可序列化的格式，支持将 Picture 写入文件流或从文件流读取。

该类不仅存储操作码流，还管理所有引用的资源，包括字体（typefaces）、工厂（factories）、以及各种绘图对象。它实现了 Picture 的序列化和反序列化逻辑，支持版本兼容和增量序列化。

## 架构位置

`SkPictureData` 在 Picture 架构中扮演数据管理和持久化的角色：

- 从 `SkPictureRecord` 接收记录的数据
- 为 `SkPicturePlayback` 提供回放所需的数据
- 被 `SkBigPicture` 持有，作为 Picture 的数据载体
- 与 `SkStream`/`SkWStream` 交互完成序列化

## 主要类与结构体

### SkPictInfo

Picture 元信息结构体。

**关键成员变量**

| 成员变量 | 类型 | 描述 |
|---------|------|------|
| fMagic | char[8] | 魔数标识 |
| fVersion | uint32_t | 版本号（私有） |
| fCullRect | SkRect | 裁剪矩形 |

**主要方法**

```cpp
uint32_t getVersion() const;
void setVersion(uint32_t version);
```

### SkPictureData

Picture 数据管理类。

**关键成员变量**

| 成员变量 | 类型 | 描述 |
|---------|------|------|
| fOpData | sk_sp<SkData> | 操作码和参数数据 |
| fPaints | TArray<SkPaint> | 画笔数组 |
| fPaths | TArray<SkPath> | 路径数组 |
| fPictures | TArray<sk_sp<const SkPicture>> | 子图片数组 |
| fDrawables | TArray<sk_sp<SkDrawable>> | 可绘制对象数组 |
| fTextBlobs | TArray<sk_sp<const SkTextBlob>> | 文本块数组 |
| fSlugs | TArray<sk_sp<const sktext::gpu::Slug>> | GPU文本块数组 |
| fVertices | TArray<sk_sp<const SkVertices>> | 顶点数组 |
| fImages | TArray<sk_sp<const SkImage>> | 图像数组 |
| fTFPlayback | SkTypefacePlayback | 字体回放辅助对象 |
| fFactoryPlayback | unique_ptr<SkFactoryPlayback> | 工厂回放辅助对象 |
| fInfo | const SkPictInfo | Picture 元信息 |
| fEmptyPath | const SkPath | 空路径（默认值） |
| fEmptyBitmap | const SkBitmap | 空位图（默认值） |

## 公共 API 函数

### 构造与创建

```cpp
// 从记录创建
SkPictureData(const SkPictureRecord& record, const SkPictInfo& info);

// 从流创建
static SkPictureData* CreateFromStream(
    SkStream* stream,
    const SkPictInfo& info,
    const SkDeserialProcs& procs,
    SkTypefacePlayback* topLevelTFPlayback,
    int recursionLimit);

// 从缓冲区创建
static SkPictureData* CreateFromBuffer(
    SkReadBuffer& buffer,
    const SkPictInfo& info);
```

### 序列化

```cpp
// 序列化到流
void serialize(
    SkWStream* stream,
    const SkSerialProcs& procs,
    SkRefCntSet* topLevelTypeFaceSet,
    bool textBlobsOnly = false) const;

// 扁平化到缓冲区
void flatten(SkWriteBuffer& buffer) const;
```

### 数据访问

```cpp
// 获取元信息
const SkPictInfo& info() const;

// 获取操作数据
const sk_sp<SkData>& opData() const;

// 获取资源（带验证）
const SkImage* getImage(SkReadBuffer* reader) const;
const SkPath& getPath(SkReadBuffer* reader) const;
const SkPicture* getPicture(SkReadBuffer* reader) const;
SkDrawable* getDrawable(SkReadBuffer* reader) const;
const SkTextBlob* getTextBlob(SkReadBuffer* reader) const;
const sktext::gpu::Slug* getSlug(SkReadBuffer* reader) const;
const SkVertices* getVertices(SkReadBuffer* reader) const;

// 获取画笔
const SkPaint* optionalPaint(SkReadBuffer* reader) const;
const SkPaint& requiredPaint(SkReadBuffer* reader) const;
```

## 内部实现细节

### 从记录创建

构造函数从 `SkPictureRecord` 复制数据：

```cpp
SkPictureData::SkPictureData(const SkPictureRecord& record,
                             const SkPictInfo& info)
    : fPictures(record.getPictures())
    , fDrawables(record.getDrawables())
    , fTextBlobs(record.getTextBlobs())
    , fVertices(record.getVertices())
    , fImages(record.getImages())
    , fSlugs(record.getSlugs())
    , fInfo(info)
{
    fOpData = record.opData();
    fPaints = record.fPaints;

    // 转换路径映射为数组
    fPaths.reset(record.fPaths.count());
    record.fPaths.foreach([this](const SkPath& path, int n) {
        fPaths[n-1] = path;  // 转换为0-based索引
    });

    this->initForPlayback();
}
```

### 序列化格式

Picture 序列化为带标签的数据块：

```cpp
// 标签定义
#define SK_PICT_READER_TAG     SkSetFourByteTag('r', 'e', 'a', 'd')
#define SK_PICT_FACTORY_TAG    SkSetFourByteTag('f', 'a', 'c', 't')
#define SK_PICT_TYPEFACE_TAG   SkSetFourByteTag('t', 'p', 'f', 'c')
#define SK_PICT_PICTURE_TAG    SkSetFourByteTag('p', 'c', 't', 'r')
#define SK_PICT_DRAWABLE_TAG   SkSetFourByteTag('d', 'r', 'a', 'w')
#define SK_PICT_BUFFER_SIZE_TAG SkSetFourByteTag('a', 'r', 'a', 'y')
#define SK_PICT_PAINT_BUFFER_TAG SkSetFourByteTag('p', 'n', 't', ' ')
#define SK_PICT_PATH_BUFFER_TAG  SkSetFourByteTag('p', 't', 'h', ' ')
// ... 更多标签
#define SK_PICT_EOF_TAG         SkSetFourByteTag('e', 'o', 'f', ' ')
```

每个数据块格式：
```
[4字节标签] [4字节大小] [数据内容]
```

### 序列化过程

```cpp
void SkPictureData::serialize(SkWStream* stream,
                              const SkSerialProcs& procs,
                              SkRefCntSet* topLevelTypeFaceSet,
                              bool textBlobsOnly) const
{
    // 1. 写入操作数据
    write_tag_size(stream, SK_PICT_READER_TAG, fOpData->size());
    stream->write(fOpData->bytes(), fOpData->size());

    // 2. 收集字体
    SkRefCntSet localTypefaceSet;
    SkRefCntSet* typefaceSet = topLevelTypeFaceSet ?
                                topLevelTypeFaceSet : &localTypefaceSet;

    // 3. 扁平化到内存缓冲区
    SkBinaryWriteBuffer buffer(...);
    this->flattenToBuffer(buffer, textBlobsOnly);

    // 4. 写入工厂和字体
    WriteFactories(stream, factSet);
    WriteTypefaces(stream, *typefaceSet, procs);

    // 5. 写入缓冲区数据
    write_tag_size(stream, SK_PICT_BUFFER_SIZE_TAG, buffer.bytesWritten());
    buffer.writeToStream(stream);

    // 6. 递归写入子图片
    if (!fPictures.empty()) {
        write_tag_size(stream, SK_PICT_PICTURE_TAG, fPictures.size());
        for (const auto& pic : fPictures) {
            pic->serialize(stream, &procs, typefaceSet, false);
        }
    }

    // 7. 写入结束标记
    stream->write32(SK_PICT_EOF_TAG);
}
```

### 反序列化过程

```cpp
bool SkPictureData::parseStream(SkStream* stream,
                                const SkDeserialProcs& procs,
                                SkTypefacePlayback* topLevelTFPlayback,
                                int recursionLimit)
{
    for (;;) {
        uint32_t tag;
        if (!stream->readU32(&tag)) { return false; }
        if (SK_PICT_EOF_TAG == tag) {
            break;  // 读取完成
        }

        uint32_t size;
        if (!stream->readU32(&size)) { return false; }

        // 解析标签
        if (!this->parseStreamTag(stream, tag, size, procs,
                                   topLevelTFPlayback, recursionLimit)) {
            return false;
        }
    }
    return true;
}
```

### 资源索引访问

资源使用1-based索引（0表示空/无效）：

```cpp
const SkPicture* SkPictureData::getPicture(SkReadBuffer* reader) const {
    return read_index_base_1_or_null(reader, fPictures);
}

template <typename T>
T* read_index_base_1_or_null(SkReadBuffer* reader,
                             const TArray<sk_sp<T>>& array) {
    int index = reader->readInt();
    return reader->validate(index > 0 && index <= array.size()) ?
           array[index - 1].get() : nullptr;
}
```

图像使用0-based索引：

```cpp
const SkImage* SkPictureData::getImage(SkReadBuffer* reader) const {
    const int index = reader->readInt();
    return reader->validateIndex(index, fImages.size()) ?
           fImages[index].get() : nullptr;
}
```

### 画笔访问

```cpp
const SkPaint* SkPictureData::optionalPaint(SkReadBuffer* reader) const {
    int index = reader->readInt();
    if (index == 0) {
        return nullptr;  // 无画笔
    }
    return reader->validate(index > 0 && index <= fPaints.size()) ?
        &fPaints[index - 1] : nullptr;
}

const SkPaint& SkPictureData::requiredPaint(SkReadBuffer* reader) const {
    const SkPaint* paint = this->optionalPaint(reader);
    if (reader->validate(paint != nullptr)) {
        return *paint;
    }
    static const SkPaint& stub = *(new SkPaint);  // 错误情况的占位符
    return stub;
}
```

### 字体去重

序列化时收集所有唯一字体：

```cpp
// 跳过自定义字体处理器，避免重复调用
static SkSerialProcs skip_typeface_proc(const SkSerialProcs& procs) {
    SkSerialProcs newProcs = procs;
    newProcs.fTypefaceProc = nullptr;
    newProcs.fTypefaceCtx = nullptr;
    return newProcs;
}

// 序列化画笔时跳过字体处理，最后统一处理
SkBinaryWriteBuffer buffer(skip_typeface_proc(procs));
buffer.setTypefaceRecorder(sk_ref_sp(typefaceSet));
// ... 扁平化数据
WriteTypefaces(stream, *typefaceSet, procs);  // 统一写入字体
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| SkPictureRecord | 数据来源 |
| SkPictureFlat | 操作码和辅助类定义 |
| SkReadBuffer/SkWriteBuffer | 序列化缓冲区 |
| SkStream/SkWStream | 流式I/O |
| SkSerialProcs/SkDeserialProcs | 序列化回调 |
| SkRefCntSet | 引用计数集合（字体去重） |
| SkFactorySet | 工厂集合 |

### 被依赖的模块

| 模块 | 关系 |
|-----|------|
| SkBigPicture | 持有 SkPictureData 实例 |
| SkPicturePlayback | 从 SkPictureData 读取数据进行回放 |
| SkPicture | 间接使用 SkPictureData |

## 设计模式与设计决策

### 标签化序列化

使用标签化格式便于扩展和向后兼容：
- 可以跳过不识别的标签
- 便于添加新数据类型
- 明确的数据边界

### 两阶段序列化

先内存缓冲，再流式输出：
- 便于计算数据大小
- 支持字体去重等预处理
- 优化递归子图片处理

### 延迟初始化

`initForPlayback()` 延迟计算路径边界：

```cpp
void SkPictureData::initForPlayback() const {
    for (int i = 0; i < fPaths.size(); i++) {
        fPaths[i].updateBoundsCache();
    }
}
```

### 安全访问

所有资源访问都包含验证：
- 索引范围检查
- 空指针保护
- 错误时返回默认值

## 性能考量

### 内存布局

- 连续数组存储，缓存友好
- 避免指针追踪，提高局部性
- 共享资源引用计数

### 字体去重

- 全局字体集合避免重复序列化
- 递归子图片共享字体集合
- 减少文件大小和内存占用

### 流式处理

- 支持增量读写
- 递归限制防止栈溢出
- 标签化格式支持跳过不需要的数据

### 两次遍历优化

序列化分两次遍历：
1. `textBlobsOnly=true`：仅收集字体
2. `textBlobsOnly=false`：完整序列化

减少字体重复处理开销。

## 相关文件

| 文件路径 | 描述 |
|---------|------|
| src/core/SkPictureRecord.h/cpp | 提供记录的数据 |
| src/core/SkPicturePlayback.h/cpp | 使用数据进行回放 |
| src/core/SkPictureFlat.h/cpp | 标签和辅助类定义 |
| src/core/SkBigPicture.h/cpp | 持有 SkPictureData |
| src/core/SkReadBuffer.h | 反序列化缓冲区 |
| src/core/SkWriteBuffer.h | 序列化缓冲区 |
| src/core/SkPtrRecorder.h | 指针记录器 |
| include/core/SkStream.h | 流式I/O接口 |
| include/core/SkSerialProcs.h | 序列化回调定义 |
