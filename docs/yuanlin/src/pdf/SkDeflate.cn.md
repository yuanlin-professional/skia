# SkDeflate

> 源文件
> - src/pdf/SkDeflate.h
> - src/pdf/SkDeflate.cpp

## 概述

`SkDeflate` 是 Skia PDF 模块中用于数据压缩的工具类，它封装了 zlib 库的 DEFLATE 压缩算法。该类提供了一个流式写入接口 `SkDeflateWStream`，可以将数据实时压缩并写入目标流，支持标准 DEFLATE 格式和 GZIP 格式。

DEFLATE 是一种无损数据压缩算法，被广泛应用于 PDF、PNG、ZIP 等文件格式。`SkDeflateWStream` 通过内部缓冲和分块处理，高效地将未压缩数据转换为压缩流。

## 架构位置

`SkDeflate` 位于 PDF 模块的底层工具层：

```
src/pdf/
├── SkPDFDocument.cpp        // PDF 文档生成，可能使用压缩
├── SkPDFBitmap.cpp          // 位图压缩
├── SkPDFUtils.cpp           // PDF 工具函数
├── SkDeflate.h/cpp          // DEFLATE 压缩（当前模块）
└── SkPDFDevice.cpp          // PDF 设备
```

它提供了一个通用的压缩接口，可被 PDF 生成的多个模块使用。

## 主要类与结构体

### SkDeflateWStream

继承自 `SkWStream`，提供流式压缩写入功能。

**公共接口:**
```cpp
SkDeflateWStream(SkWStream* out, int compressionLevel, bool gzip = false);
~SkDeflateWStream() override;

void finalize();
bool write(const void* buffer, size_t len) override;
size_t bytesWritten() const override;
```

**私有实现:**
```cpp
struct Impl;
std::unique_ptr<Impl> fImpl;
```

使用 Pimpl 模式隐藏 zlib 实现细节。

### SkDeflateWStream::Impl

```cpp
struct SkDeflateWStream::Impl {
    SkWStream* fOut;                                    // 输出流
    unsigned char fInBuffer[SKDEFLATEWSTREAM_INPUT_BUFFER_SIZE];  // 输入缓冲区（4KB）
    size_t fInBufferIndex;                             // 当前缓冲区位置
    z_stream fZStream;                                 // zlib 流状态
};
```

## 公共 API 函数

### 构造函数

```cpp
SkDeflateWStream(SkWStream* out, int compressionLevel, bool gzip = false);
```

**参数：**
- `out`：输出流指针（不获取所有权）
- `compressionLevel`：压缩级别
  - 1：最快速度
  - 9：最高压缩率
  - -1：使用 zlib 的默认级别（通常是 6）
  - 0：理论上无压缩，但由于 zlib 实现问题，用户应自行处理
- `gzip`：是否输出 GZIP 格式
  - `true`：添加 GZIP 头部（RFC 1952）
  - `false`：纯 DEFLATE 流

**实现细节：**
```cpp
SkASSERT(compressionLevel != 0);  // 不支持零压缩
fImpl->fZStream.zalloc = &skia_alloc_func;
fImpl->fZStream.zfree = &skia_free_func;
deflateInit2(&fImpl->fZStream, compressionLevel,
             Z_DEFLATED, gzip ? 0x1F : 0x0F,
             8, Z_DEFAULT_STRATEGY);
```

**窗口位设置：**
- `0x1F` (31)：GZIP 格式，15 位窗口 + GZIP 头部
- `0x0F` (15)：标准 DEFLATE，15 位窗口

### write()

```cpp
bool write(const void* buffer, size_t len) override;
```

**功能：**
- 将数据写入压缩流
- 自动处理缓冲和压缩
- 返回是否成功

**实现流程：**
1. 将数据分块复制到输入缓冲区
2. 缓冲区满时调用 `do_deflate()` 压缩
3. 重复直到所有数据处理完毕

```cpp
while (len > 0) {
    size_t tocopy = std::min(len, sizeof(fImpl->fInBuffer) - fImpl->fInBufferIndex);
    memcpy(fImpl->fInBuffer + fImpl->fInBufferIndex, buffer, tocopy);
    len -= tocopy;
    buffer += tocopy;
    fImpl->fInBufferIndex += tocopy;

    if (sizeof(fImpl->fInBuffer) == fImpl->fInBufferIndex) {
        do_deflate(Z_NO_FLUSH, &fImpl->fZStream, fImpl->fOut,
                   fImpl->fInBuffer, fImpl->fInBufferIndex);
        fImpl->fInBufferIndex = 0;
    }
}
```

### finalize()

```cpp
void finalize();
```

**功能：**
- 结束压缩流
- 刷新所有缓冲数据
- 写入压缩流的尾部信息
- 释放 zlib 资源

**实现：**
```cpp
if (!fImpl->fOut) {
    return;  // 已经 finalize 过
}
do_deflate(Z_FINISH, &fImpl->fZStream, fImpl->fOut,
           fImpl->fInBuffer, fImpl->fInBufferIndex);
deflateEnd(&fImpl->fZStream);
fImpl->fOut = nullptr;  // 标记为已完成
```

**重要：**
- 多次调用是安全的（幂等操作）
- 析构函数自动调用
- finalize 后 write() 将失败

### bytesWritten()

```cpp
size_t bytesWritten() const override;
```

**功能：**
- 返回已写入的未压缩数据字节数
- 不包括压缩后的字节数

**实现：**
```cpp
return fImpl->fZStream.total_in + fImpl->fInBufferIndex;
```

## 内部实现细节

### do_deflate() 核心函数

```cpp
static void do_deflate(int flush, z_stream* zStream, SkWStream* out,
                       unsigned char* inBuffer, size_t inBufferSize)
```

**功能：**
- 执行实际的 zlib 压缩操作
- 处理输入和输出缓冲区
- 循环直到所有数据处理完毕

**实现：**
```cpp
zStream->next_in = inBuffer;
zStream->avail_in = SkToInt(inBufferSize);
unsigned char outBuffer[SKDEFLATEWSTREAM_OUTPUT_BUFFER_SIZE];  // 4224 字节

do {
    zStream->next_out = outBuffer;
    zStream->avail_out = sizeof(outBuffer);
    deflate(zStream, flush);
    out->write(outBuffer, sizeof(outBuffer) - zStream->avail_out);
} while (zStream->avail_in || !zStream->avail_out);
```

**循环条件：**
- `zStream->avail_in`：还有输入数据
- `!zStream->avail_out`：输出缓冲区已满，可能还有更多输出

### 缓冲区大小

```cpp
#define SKDEFLATEWSTREAM_INPUT_BUFFER_SIZE 4096
#define SKDEFLATEWSTREAM_OUTPUT_BUFFER_SIZE 4224
```

**设计考虑：**
- 输入：4KB，典型的内存页大小
- 输出：4224 字节（4096 + 128），通常一次循环就能容纳压缩后的数据

输出缓冲区稍大是因为在最坏情况下，压缩数据可能比原始数据略大（压缩头部开销）。

### 自定义内存分配器

```cpp
template <typename T>
void* skia_alloc_func(void*, T items, T size) {
    if (!SkTFitsIn<size_t>(size)) {
        return nullptr;
    }
    const size_t maxItems = SIZE_MAX / size;
    if (maxItems < items) {
        return nullptr;  // 防止溢出
    }
    return sk_calloc_throw(SkToSizeT(items) * SkToSizeT(size));
}

void skia_free_func(void*, void* address) {
    sk_free(address);
}
```

**目的：**
- 使用 Skia 的内存管理系统
- 兼容不同 zlib 实现的类型要求
- 防止整数溢出攻击

### 压缩级别断言

```cpp
SkASSERT(compressionLevel != 0);
```

**原因：**
注释指出某些 zlib 实现在处理零压缩级别时存在问题（会随机化压缩级别）。虽然零压缩应该是确定性的直通，但为了避免这些破损的实现，要求用户自行处理无压缩情况。

## 依赖关系

**直接依赖:**
```cpp
#include "include/core/SkStream.h"    // SkWStream 基类
#include <zlib.h>                     // z_stream, deflate 函数
#include "src/core/SkTraceEvent.h"    // 性能跟踪
```

**被依赖:**
```cpp
src/pdf/SkPDFDocument.cpp            // PDF 文档压缩
src/pdf/SkPDFBitmap.cpp              // 图像压缩
src/pdf/SkPDFUtils.cpp               // 工具函数
```

## 设计模式与设计决策

### 1. Pimpl 模式

```cpp
struct Impl;
std::unique_ptr<Impl> fImpl;
```

**优点：**
- 隐藏 zlib 的实现细节
- 避免头文件中暴露 `z_stream` 结构
- 减少编译依赖

### 2. RAII 资源管理

```cpp
~SkDeflateWStream() override {
    this->finalize();
}
```

析构函数自动完成压缩并释放资源，防止资源泄漏。

### 3. 流式接口

继承 `SkWStream`，提供统一的流写入接口：
- 与其他 Skia 流对象兼容
- 支持链式组合
- 透明的压缩处理

### 4. 双缓冲设计

输入缓冲区和输出缓冲区分离：
- 输入：累积数据直到足够执行有效压缩
- 输出：临时存储压缩结果
- 减少 zlib 调用次数，提高性能

### 5. 幂等的 finalize()

```cpp
if (!fImpl->fOut) {
    return;
}
```

多次调用安全，简化错误处理。

## 性能考量

### 1. 批量压缩

使用 4KB 输入缓冲区：
- 减少 zlib 调用次数
- 提高压缩率（更大的窗口利用）
- 减少函数调用开销

### 2. 栈上输出缓冲区

```cpp
unsigned char outBuffer[SKDEFLATEWSTREAM_OUTPUT_BUFFER_SIZE];
```

输出缓冲区在栈上分配，避免堆分配开销。

### 3. 压缩级别权衡

```cpp
-1 (default): 平衡压缩率和速度
1: 最快，适合实时场景
9: 最高压缩率，适合文件存储
```

用户可根据需求选择。

### 4. 懒惰压缩

只有在缓冲区满时才调用 zlib：
- 批量处理，提高效率
- 减少上下文切换

### 5. 单次循环优化

输出缓冲区 4224 字节，通常一次就能容纳所有输出：
```cpp
do {
    ...
} while (zStream->avail_in || !zStream->avail_out);
```

大多数情况下循环只执行一次。

## 相关文件

| 文件路径 | 说明 | 关系 |
|---------|------|------|
| `include/core/SkStream.h` | 流接口定义 | 基类 |
| `src/pdf/SkPDFDocument.cpp` | PDF 文档 | 使用压缩 |
| `src/pdf/SkPDFBitmap.cpp` | PDF 位图 | 图像压缩 |
| `src/pdf/SkPDFUtils.cpp` | PDF 工具 | 使用压缩 |
| `src/core/SkTraceEvent.h` | 性能跟踪 | 调试支持 |
| `include/private/base/SkMalloc.h` | 内存分配 | 自定义分配器 |
| `<zlib.h>` | zlib 库 | 压缩引擎 |
