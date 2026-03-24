# SkStream

> 源文件
> - include/core/SkStream.h
> - src/core/SkStream.cpp

## 概述

`SkStream` 是 Skia 中字节流的抽象基类,提供了统一的读写接口,支持文件、内存和动态缓冲区等多种后端。该系统包含一个完整的流类层次结构,从最基本的 `SkStream` 到支持寻址的 `SkStreamAsset`,以及输出流 `SkWStream`。流系统是 Skia 资源加载、序列化和数据传输的基础设施。

## 架构位置

`SkStream` 位于 Skia 核心 I/O 层,是多个子系统的基础:

- **编解码器**: 图像解码器通过 `SkStream` 读取图像数据
- **序列化**: `SkPicture`、字体等对象的序列化和反序列化
- **文件 I/O**: 统一的文件访问接口
- **网络传输**: 可扩展到网络流等高级用途

## 主要类与结构体

### 流类层次结构

**继承关系**:
```
SkStream (基础读流)
  └── SkStreamRewindable (可回退)
        └── SkStreamSeekable (可寻址)
              └── SkStreamAsset (已知长度)
                    └── SkStreamMemory (内存流)

SkWStream (基础写流)
  ├── SkNullWStream (空流)
  ├── SkFILEWStream (文件写流)
  └── SkDynamicMemoryWStream (动态内存写流)
```

### SkStream (抽象基类)

**关键成员变量**: 无(纯抽象)

**核心虚函数**:

| 函数 | 说明 |
|------|------|
| `read(void* buffer, size_t size)` | 读取或跳过指定字节数(纯虚函数) |
| `isAtEnd()` | 检查是否到达流末尾(纯虚函数) |
| `peek(void* buffer, size_t size)` | 窥视数据不改变位置(可选) |

### SkStreamAsset (最常用子类)

**关键成员变量**: 无(纯虚函数)

**必须实现**:

| 函数 | 说明 |
|------|------|
| `getLength()` | 返回流总长度 |
| `getPosition()` | 返回当前位置 |
| `seek(size_t position)` | 跳转到指定位置 |
| `rewind()` | 回退到开头 |

### SkFILEStream (文件输入流)

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fFILE` | `std::shared_ptr<FILE>` | 共享文件句柄 |
| `fStart` | `size_t` | 流起始位置(文件偏移) |
| `fEnd` | `size_t` | 流结束位置 |
| `fCurrent` | `size_t` | 当前读取位置 |

### SkMemoryStream (内存输入流)

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fData` | `sk_sp<const SkData>` | 数据引用 |
| `fOffset` | `size_t` | 当前偏移量 |

### SkDynamicMemoryWStream (动态内存输出流)

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fHead` | `Block*` | 内存块链表头 |
| `fTail` | `Block*` | 内存块链表尾 |
| `fBytesWrittenBeforeTail` | `size_t` | 尾块之前的总字节数 |

## 公共 API 函数

### 读取基本类型

```cpp
// 读取整数类型
bool readS8(int8_t*);
bool readS16(int16_t*);
bool readS32(int32_t*);
bool readS64(int64_t*);
bool readU8(uint8_t*);
bool readU16(uint16_t*);
bool readU32(uint32_t*);
bool readU64(uint64_t*);

// 读取浮点和特殊类型
bool readScalar(SkScalar*);
bool readBool(bool*);
bool readPackedUInt(size_t*);      // 压缩整数格式
```

### 流控制

```cpp
// 导航
size_t skip(size_t size);           // 跳过字节
bool seek(size_t position);         // 绝对定位
bool move(long offset);             // 相对移动
bool rewind();                      // 回到开头

// 查询
bool hasLength() const;
size_t getLength() const;
bool hasPosition() const;
size_t getPosition() const;
```

### 流复制

```cpp
std::unique_ptr<SkStream> duplicate() const;  // 从头开始的新流
std::unique_ptr<SkStream> fork() const;       // 保持当前位置的新流
```

### 写流 API

```cpp
// SkWStream
bool write(const void* buffer, size_t size);
void flush();
size_t bytesWritten() const;

// 辅助写入函数
bool write8(U8CPU value);
bool write16(U16CPU value);
bool write32(uint32_t value);
bool write64(uint64_t value);
bool writeText(const char text[]);
bool writeScalar(SkScalar);
bool writePackedUInt(size_t);
```

## 内部实现细节

### 压缩整数编码

`readPackedUInt` 和 `writePackedUInt` 使用变长编码优化存储:

```cpp
// 0-253: 1字节
// 254-65535: 3字节 (0xFE + uint16)
// 65536+: 5字节 (0xFF + uint32)

bool SkStream::readPackedUInt(size_t* i) {
    uint8_t byte;
    if (!this->read(&byte, 1)) return false;

    if (byte == 0xFE) {
        uint16_t i16;
        if (!this->readU16(&i16)) return false;
        *i = i16;
    } else if (byte == 0xFF) {
        uint32_t i32;
        if (!this->readU32(&i32)) return false;
        *i = i32;
    } else {
        *i = byte;
    }
    return true;
}
```

### 文件流偏移管理

`SkFILEStream` 支持文件子区域,通过三元组(fStart, fCurrent, fEnd)管理:

```cpp
size_t SkFILEStream::read(void* buffer, size_t size) {
    // 限制读取不超过流边界
    if (size > fEnd - fCurrent) {
        size = fEnd - fCurrent;
    }
    // sk_qread 使用绝对文件位置
    size_t bytesRead = sk_qread(fFILE.get(), buffer, size, fCurrent);
    fCurrent += bytesRead;
    return bytesRead;
}
```

### 动态内存流块管理

`SkDynamicMemoryWStream` 使用链表管理可变大小的内存块:

```cpp
struct Block {
    Block*  fNext;
    char*   fCurr;    // 当前写入位置
    char*   fStop;    // 块结束位置

    char* start() { return (char*)(this + 1); }  // 数据紧跟结构体
    size_t avail() const { return fStop - fCurr; }
    size_t written() const { return fCurr - start(); }
};

// 块大小策略: max(请求大小, 4096字节)
constexpr size_t SkDynamicMemoryWStream_MinBlockSize = 4096;
```

### 内存流零拷贝优化

`detachAsStream()` 避免复制内存,直接包装块链表:

```cpp
std::unique_ptr<SkStreamAsset> SkDynamicMemoryWStream::detachAsStream() {
    if (fHead == fTail) {
        // 单块优化: 通过 realloc 缩减内存
        ptrdiff_t used = fTail->fCurr - (char*)fTail;
        fHead = (Block*)sk_realloc_throw(fTail, used);
    }
    // 包装为 SkBlockMemoryStream,共享引用计数
    auto stream = std::make_unique<SkBlockMemoryStream>(
        sk_make_sp<SkBlockMemoryRefCnt>(fHead), this->bytesWritten());
    fHead = nullptr;  // 转移所有权
    return stream;
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkData` | 内存数据包装和管理 |
| `SkOSFile` | 跨平台文件操作(sk_fopen, sk_fread等) |
| `SkString` | 字符串处理辅助 |
| `SkSafeMath` | 溢出安全的数学运算 |
| `SkMalloc` | 内存分配(sk_malloc, sk_realloc) |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| 图像编解码器 | `SkCodec` 及其子类使用流读取图像数据 |
| 字体系统 | `SkTypeface` 序列化和加载 |
| `SkPicture` | 绘制命令序列化 |
| `SkDocument` | PDF/SVG 等文档生成 |
| 数据传输 | 网络下载、资源加载 |

## 设计模式与设计决策

### 1. 模板方法模式

基类定义算法骨架,子类实现具体步骤:

```cpp
class SkStream {
    size_t skip(size_t size) {
        return this->read(nullptr, size);  // 复用 read 实现
    }

    virtual size_t read(void* buffer, size_t size) = 0;  // 子类实现
};
```

### 2. 策略模式

不同流类型实现不同的读写策略:
- `SkMemoryStream`: 直接内存访问
- `SkFILEStream`: 系统调用
- `SkDynamicMemoryWStream`: 链表管理

### 3. 零拷贝设计

多处使用智能指针和数据共享避免复制:

```cpp
// SkMemoryStream 共享 SkData
SkMemoryStream(sk_sp<const SkData> data) : fData(std::move(data)) {}

// SkFILEStream 共享文件句柄
std::shared_ptr<FILE> fFILE;
```

### 4. 懒惰求值

`MakeFromFile` 尝试 mmap,失败才使用 FILE:

```cpp
std::unique_ptr<SkStreamAsset> SkStream::MakeFromFile(const char path[]) {
    auto data(mmap_filename(path));  // 尝试内存映射
    if (data) {
        return std::make_unique<SkMemoryStream>(std::move(data));
    }
    return std::make_unique<SkFILEStream>(path);  // 回退到文件流
}
```

## 性能考量

### 1. 内存对齐

动态内存流确保4字节对齐:

```cpp
bool SkDynamicMemoryWStream::write(const void* buffer, size_t count) {
    size = SkAlign4(size);  // 强制4字节对齐
    // ...
}

void padToAlign4() {
    int padBytes = -(int)fTail->written() & 0x03;
    // 填充到4的倍数
}
```

### 2. 块大小策略

最小块4KB,避免频繁分配:

```cpp
size = std::max<size_t>(count, SkDynamicMemoryWStream_MinBlockSize - sizeof(Block));
```

### 3. peek 优化

`SkMemoryStream::peek` 利用可重置性实现无拷贝窥视:

```cpp
size_t SkMemoryStream::peek(void* buffer, size_t size) const {
    const size_t currentOffset = fOffset;
    SkMemoryStream* nonConstThis = const_cast<SkMemoryStream*>(this);
    const size_t bytesRead = nonConstThis->read(buffer, size);
    nonConstThis->fOffset = currentOffset;  // 恢复位置
    return bytesRead;
}
```

### 4. 文件读取批处理

`sk_qread` 避免多次系统调用:

```cpp
size_t bytesRead = sk_qread(fFILE.get(), buffer, size, fCurrent);
```

### 5. 内存复用

`writeToAndReset` 系列函数在复制时释放源内存:

```cpp
bool SkDynamicMemoryWStream::writeToAndReset(SkWStream* dst) {
    for (Block* block = fHead; block != nullptr; ) {
        dst->write(block->start(), block->written());
        Block* next = block->fNext;
        sk_free(block);  // 边复制边释放
        block = next;
    }
}
```

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/core/SkStream.h` | 公共接口定义 |
| `src/core/SkStream.cpp` | 核心实现 |
| `src/core/SkStreamPriv.h` | 内部辅助函数 |
| `src/core/SkOSFile*.cpp` | 平台相关文件操作 |
| `include/core/SkData.h` | 数据容器 |
| `src/codec/SkCodec.cpp` | 流的主要使用者 |
| `src/core/SkPictureRecorder.cpp` | 序列化使用示例 |
