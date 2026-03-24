# SkWriteBuffer

> 源文件: src/core/SkWriteBuffer.h, src/core/SkWriteBuffer.cpp

## 概述

`SkWriteBuffer` 是 Skia 序列化框架的高级抽象接口，提供了类型安全的序列化 API，用于将 Skia 对象（如 `SkPaint`、`SkPath`、`SkFlattenable` 等）序列化为二进制格式。它定义了序列化操作的标准接口，而 `SkBinaryWriteBuffer` 是其具体实现，负责将数据写入扁平的二进制流。

该模块是 Skia 对象持久化和 IPC（进程间通信）的核心，广泛应用于 SkPicture 录制、着色器/滤镜序列化、字体数据传输等场景。它与 `SkReadBuffer` 配对使用，形成完整的序列化/反序列化体系。

## 架构位置

`SkWriteBuffer` 在 Skia 序列化架构中处于关键位置：

```
应用层对象 (SkPaint, SkImageFilter, SkShader)
         ↓
  SkFlattenable::flatten()
         ↓
  SkWriteBuffer (抽象接口) ← 本模块
         ↓
  SkBinaryWriteBuffer (具体实现)
         ↓
  SkWriter32 (低级二进制写入)
         ↓
  输出流 / 内存缓冲区
```

它作为"语义层"存在，理解 Skia 对象的类型和结构，而将底层的对齐和内存管理委托给 `SkWriter32`。

## 主要类与结构体

### SkWriteBuffer（抽象基类）

定义序列化操作的纯虚接口。

**继承关系**
- 无基类（根类）

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fProcs` | `SkSerialProcs` | 自定义序列化回调集合（图像、字体等） |

### SkBinaryWriteBuffer（具体实现）

将数据序列化为扁平二进制格式的实现类。

**继承关系**
- 继承自 `SkWriteBuffer`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fWriter` | `SkWriter32` | 底层二进制写入器 |
| `fFactorySet` | `sk_sp<SkFactorySet>` | 工厂函数记录器（用于 SkPicture） |
| `fTFSet` | `sk_sp<SkRefCntSet>` | 字体记录器 |
| `fFlattenableDict` | `THashMap<const char*, uint32_t>` | Flattenable 类型名字典（压缩重复名称） |

## 公共 API 函数

### SkWriteBuffer 抽象接口

#### 基本类型写入

```cpp
virtual void writeBool(bool value) = 0;
virtual void writeInt(int32_t value) = 0;
virtual void writeUInt(uint32_t value) = 0;
virtual void writeScalar(SkScalar value) = 0;
virtual void writeString(std::string_view value) = 0;
```

#### 数组写入

```cpp
virtual void writeScalarArray(SkSpan<const SkScalar>) = 0;
virtual void writeIntArray(SkSpan<const int32_t>) = 0;
virtual void writeColorArray(SkSpan<const SkColor>) = 0;
virtual void writeColor4fArray(SkSpan<const SkColor4f>) = 0;
virtual void writePointArray(SkSpan<const SkPoint>) = 0;
```

#### 几何类型写入

```cpp
virtual void writePoint(const SkPoint& point) = 0;
virtual void writePoint3(const SkPoint3& point) = 0;
virtual void writeMatrix(const SkMatrix& matrix) = 0;
virtual void write(const SkM44&) = 0;
virtual void writeIRect(const SkIRect& rect) = 0;
virtual void writeRect(const SkRect& rect) = 0;
virtual void writeRegion(const SkRegion& region) = 0;
virtual void writePath(const SkPath& path) = 0;
```

#### 复杂对象写入

```cpp
virtual void writeFlattenable(const SkFlattenable* flattenable) = 0;
virtual void writeImage(const SkImage*) = 0;
virtual void writeTypeface(SkTypeface* typeface) = 0;
virtual void writePaint(const SkPaint& paint) = 0;
virtual void writeSampling(const SkSamplingOptions&) = 0;
```

#### 原始数据写入

```cpp
virtual void writeByteArray(const void* data, size_t size) = 0;
virtual void writePad32(const void* buffer, size_t bytes) = 0;
virtual size_t writeStream(SkStream* stream, size_t length) = 0;
```

### SkBinaryWriteBuffer 特有方法

#### 构造与重置

```cpp
explicit SkBinaryWriteBuffer(const SkSerialProcs&);
SkBinaryWriteBuffer(void* initialStorage, size_t storageSize, const SkSerialProcs&);

void reset(void* storage = nullptr, size_t storageSize = 0);
```

#### 查询与导出

```cpp
size_t bytesWritten() const;
bool usingInitialStorage() const;

bool writeToStream(SkWStream*) const;
void writeToMemory(void* dst) const;
sk_sp<SkData> snapshotAsData() const;
```

#### 配置方法

```cpp
void setFactoryRecorder(sk_sp<SkFactorySet>);
void setTypefaceRecorder(sk_sp<SkRefCntSet>);
```

## 内部实现细节

### Flattenable 序列化机制

`writeFlattenable()` 实现了 Skia 最核心的多态序列化机制：

```cpp
void SkBinaryWriteBuffer::writeFlattenable(const SkFlattenable* flattenable) {
    if (nullptr == flattenable) {
        this->write32(0);
        return;
    }

    // 两种编码方式：
    // 1. 工厂索引（SkPicture 使用，配合 SkFactorySet）
    // 2. 类型名称字符串或名称字典索引

    if (SkFlattenable::Factory factory = flattenable->getFactory(); factory && fFactorySet) {
        this->write32(fFactorySet->add(factory));
    } else {
        const char* name = flattenable->getTypeName();

        if (uint32_t* indexPtr = fFlattenableDict.find(name)) {
            // 已见过的类型：写入索引（左移 8 位，首字节为 0 作为标记）
            this->write32(*indexPtr << 8);
        } else {
            // 新类型：写入完整名称字符串
            this->writeString(name);
            fFlattenableDict.set(name, fFlattenableDict.count() + 1);
        }
    }

    // 预留 4 字节用于回填对象大小
    (void)fWriter.reserve(sizeof(uint32_t));
    size_t offset = fWriter.bytesWritten();

    // 调用对象的 flatten() 方法
    flattenable->flatten(*this);

    // 回填对象大小
    size_t objSize = fWriter.bytesWritten() - offset;
    fWriter.overwriteTAt(offset - sizeof(uint32_t), SkToU32(objSize));
}
```

**序列化格式**
```
[类型标识: 索引/字符串]
[对象大小: 4 字节]
[对象数据...]
```

**类型名字典压缩**
- 首次出现的类型名：写入完整字符串
- 重复类型：写入索引（左移 8 位，首字节为 0 标识索引）
- 索引限制：24 位（0-16777215）

### 图像序列化

`writeImage()` 实现了灵活的图像序列化策略：

```cpp
void SkBinaryWriteBuffer::writeImage(const SkImage* image) {
    uint32_t flags = 0;
    const SkMipmap* mips = as_IB(image)->onPeekMips();
    if (mips) {
        flags |= kHasMipmap;
    }
    if (image->alphaType() == kUnpremul_SkAlphaType) {
        flags |= kUnpremul;
    }

    this->write32(flags);

    // 1. 尝试使用自定义序列化回调
    // 2. 否则使用图像的编码数据（如来自 PNG/JPEG）
    sk_sp<const SkData> data = serialize_image(image, fProcs);
    this->writeDataAsByteArray(data.get());

    // 可选：序列化 mipmap 层级
    if (flags & kHasMipmap) {
        sk_sp<SkData> mipData = serialize_mipmap(mips, fProcs);
        this->writeDataAsByteArray(mipData.get());
    }
}
```

**图像序列化格式**
```
[标志位: 4 字节]
[编码数据长度: 4 字节]
[编码数据: 变长，带填充]
[可选 mipmap 数据...]
```

**标志位定义**
- `kHasMipmap` (1 << 9)：包含 mipmap 数据
- `kUnpremul` (1 << 10)：Alpha 未预乘

### 字体序列化

`writeTypeface()` 支持三种模式：

```cpp
void SkBinaryWriteBuffer::writeTypeface(SkTypeface* obj) {
    if (obj == nullptr) {
        fWriter.write32(0);  // 空字体
    } else if (fProcs.fTypefaceProc) {
        // 使用自定义序列化回调
        auto data = fProcs.fTypefaceProc(obj, fProcs.fTypefaceCtx);
        if (data) {
            int32_t ssize = SkToS32(data->size());
            fWriter.write32(-ssize);  // 负数标识自定义数据
            this->writePad32(data->data(), size);
            return;
        }
    }
    // 使用字体记录器索引
    fWriter.write32(fTFSet ? fTFSet->add(obj) : 0);
}
```

**编码方案**
- `0`：空字体（默认字体）
- `正数`：字体记录器中的索引
- `负数`：自定义序列化数据长度（取反后为实际长度）

### 采样选项序列化

采样选项使用条件序列化节省空间：

```cpp
// SkWriter32::writeSampling() 被 SkBinaryWriteBuffer 调用
void writeSampling(const SkSamplingOptions& sampling) {
    this->write32(sampling.maxAniso);
    if (!sampling.isAniso()) {
        this->writeBool(sampling.useCubic);
        if (sampling.useCubic) {
            this->writeScalar(sampling.cubic.B);
            this->writeScalar(sampling.cubic.C);
        } else {
            this->write32((unsigned)sampling.filter);
            this->write32((unsigned)sampling.mipmap);
        }
    }
}
```

根据采样模式动态决定写入的字段数量。

## 依赖关系

**依赖的模块**

| 模块 | 用途 |
|------|------|
| `SkWriter32` | 底层二进制写入 |
| `SkFlattenable` | 多态对象序列化基类 |
| `SkImage` | 图像对象 |
| `SkTypeface` | 字体对象 |
| `SkPaint` | 绘制样式（通过 SkPaintPriv） |
| `SkPath` | 路径对象 |
| `SkMatrix` | 矩阵对象 |
| `SkSerialProcs` | 自定义序列化回调 |
| `SkFactorySet` | 工厂函数记录器 |
| `SkRefCntSet` | 引用计数对象集合 |
| `SkMipmap` | Mipmap 数据 |

**被依赖的模块**

| 模块 | 依赖原因 |
|------|----------|
| `SkFlattenable` 子类 | 调用 `flatten(*this)` |
| `SkPicture` | 录制绘制命令 |
| `SkImageFilter` | 滤镜序列化 |
| `SkShader` | 着色器序列化 |
| `SkColorFilter` | 颜色滤镜序列化 |
| `SkPathEffect` | 路径效果序列化 |
| `SkDrawable` | 可绘制对象序列化 |

## 设计模式与设计决策

### 设计模式

1. **抽象工厂模式**
   - `SkWriteBuffer` 作为抽象接口
   - `SkBinaryWriteBuffer` 作为具体工厂
   - 可扩展支持其他格式（如 JSON、Protobuf）

2. **策略模式**
   - `SkSerialProcs` 允许注入自定义序列化策略
   - 图像、字体可使用应用层提供的回调

3. **访问者模式**
   - `SkFlattenable::flatten()` 接受 `SkWriteBuffer&` 参数
   - 对象将自己序列化到缓冲区

4. **享元模式**
   - `fFlattenableDict` 压缩重复的类型名称
   - `SkFactorySet` 和 `SkRefCntSet` 去重工厂和字体

5. **模板方法模式**
   - 基类定义序列化流程
   - 子类实现具体写入逻辑

### 设计决策

#### 1. 双层架构（SkWriteBuffer + SkWriter32）

**原因**
- **关注点分离**：`SkWriteBuffer` 处理类型语义，`SkWriter32` 处理内存对齐
- **可扩展性**：可替换底层写入器（如支持流式写入）
- **类型安全**：API 层面强制类型检查

#### 2. Flattenable 的两种序列化模式

**模式 1：工厂索引（SkFactorySet）**
- **适用**：SkPicture 内部使用
- **优点**：紧凑高效，配合工厂表反序列化快
- **缺点**：需要共享工厂表

**模式 2：类型名称字符串**
- **适用**：跨进程、持久化存储
- **优点**：自描述，不依赖外部上下文
- **缺点**：首次写入类型名有开销

**字典压缩优化**
- 重复类型名编码为索引（左移 8 位）
- 利用类型名非空特性（首字节非零）区分字符串和索引

#### 3. 自定义序列化回调（SkSerialProcs）

**设计目标**
- 允许应用层控制敏感数据（如图像、字体）的序列化
- 支持不同传输场景（本地缓存、网络传输、IPC）

**实现**
```cpp
struct SkSerialProcs {
    SkSerialImageProc   fImageProc;
    void*               fImageCtx;
    SkSerialTypefaceProc fTypefaceProc;
    void*               fTypefaceCtx;
    // ... 其他回调
};
```

**应用场景**
- 浏览器：图像序列化为 URL 引用
- 嵌入式：字体序列化为文件路径
- 云端：将大数据上传到 CDN，仅序列化引用

#### 4. 图像 Mipmap 序列化

**动机**
- GPU 纹理通常包含 mipmap 层级
- 完整序列化避免反序列化后重新生成

**格式**
```
[层级数: 4 字节]
对于每个层级:
  [编码大小: 4 字节]
  [编码数据: 变长]
```

每个层级独立编码（如 PNG），支持不同压缩算法。

#### 5. 对象大小回填

**为什么记录对象大小**
- **跳过未知类型**：反序列化时遇到未知 Flattenable，可跳过而不失败
- **向前兼容**：旧版本可跳过新版本的扩展字段

**实现技巧**
```cpp
fWriter.reserve(sizeof(uint32_t));       // 预留 4 字节
size_t offset = fWriter.bytesWritten();
flattenable->flatten(*this);             // 写入对象
size_t objSize = fWriter.bytesWritten() - offset;
fWriter.overwriteTAt(offset - 4, objSize); // 回填大小
```

使用 `overwriteTAt()` 修改已写入的数据。

## 性能考量

### 内存分配优化

1. **初始缓冲区策略**
   - 构造函数接受外部缓冲区
   - 小对象序列化避免堆分配
   - 配合 `SkSWriter32<SIZE>` 使用

2. **字典压缩**
   - `fFlattenableDict` 使用哈希表
   - 查找时间 O(1)
   - 内存开销：每个唯一类型一个条目

3. **对象池化**
   - `SkFactorySet` 和 `SkRefCntSet` 去重对象
   - 减少序列化大小

### 写入性能

1. **批量写入**
   - 数组方法（`writeScalarArray` 等）一次写入整个数组
   - 避免逐元素的虚函数调用开销

2. **委托给 SkWriter32**
   - 简单类型直接调用 `fWriter.writeXxx()`
   - 内联优化，零开销抽象

3. **条件序列化**
   - 采样选项、Flattenable 等仅写入必要字段
   - 减少数据量和写入次数

### 序列化大小优化

1. **类型名压缩**
   - 重复类型仅写入 4 字节索引
   - 常见场景（如多个 `SkColorFilter`）节省显著

2. **图像编码复用**
   - 优先使用原始编码数据（PNG/JPEG）
   - 避免重新编码开销

3. **可选字段**
   - 使用标志位指示是否包含 mipmap、Alpha 类型等
   - 仅在需要时写入额外数据

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| `src/core/SkReadBuffer.h/cpp` | 对应读取器 | 反序列化实现 |
| `src/core/SkWriter32.h/cpp` | 底层依赖 | 二进制写入器 |
| `include/core/SkFlattenable.h` | 序列化对象基类 | 定义 `flatten()` 接口 |
| `src/core/SkPtrRecorder.h` | 依赖 | SkFactorySet/SkRefCntSet 实现 |
| `src/core/SkPaintPriv.h` | 依赖 | SkPaint 序列化辅助 |
| `src/core/SkMipmap.h` | 依赖 | Mipmap 序列化 |
| `include/core/SkSerialProcs.h` | 依赖 | 自定义序列化回调 |
| `src/core/SkPictureRecord.cpp` | 使用者 | SkPicture 录制 |
| `src/effects/imagefilters/*.cpp` | 使用者 | 图像滤镜序列化 |
| `src/shaders/*.cpp` | 使用者 | 着色器序列化 |
