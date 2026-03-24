# SkData

> 源文件
> - include/core/SkData.h
> - src/core/SkData.cpp

## 概述

`SkData` 是 Skia 图形库中用于管理不可变数据缓冲区的引用计数类。它提供了一种高效、安全的方式来共享和传递二进制数据,支持多种数据来源包括内存拷贝、文件映射、流读取等。该类的设计强调零拷贝优化和灵活的内存管理策略。

SkData 的不可变性保证了线程安全的共享,其引用计数机制允许多个对象持有同一数据而无需拷贝。通过可自定义的释放回调,SkData 可以包装各种内存来源,包括 C++ 分配、malloc、mmap、常量数据等。

## 架构位置

`SkData` 位于 Skia 核心基础设施层,作为数据容器被广泛使用:

```
Skia Core Infrastructure
  ├─ Memory Management
  │   ├─ SkRefCnt (引用计数基类)
  │   └─ SkData ← 当前模块(不可变数据容器)
  ├─ I/O & Serialization
  │   ├─ SkStream (流读取)
  │   ├─ SkFILE (文件操作)
  │   └─ Picture Serialization
  └─ High-Level Usage
      ├─ SkImage (图像数据编码)
      ├─ SkTypeface (字体文件数据)
      ├─ SkPicture (序列化图形命令)
      └─ Shader Resources (着色器字节码)
```

SkData 是 Skia 中传递任意二进制数据的标准方式。

## 主要类与结构体

### SkData

**继承关系**:
- 基类: `SkNVRefCnt<SkData>` (非虚析构的引用计数)

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fReleaseProc | ReleaseProc | 释放回调函数指针 |
| fReleaseProcContext | void* | 释放回调的上下文数据 |
| fSpan | SkSpan<std::byte> | 数据缓冲区的视图(指针+大小) |

**核心职责**:
- 提供对不可变数据缓冲区的只读访问
- 管理数据缓冲区的生命周期(通过引用计数和释放回调)
- 支持多种数据源的包装和转换
- 提供子集视图和拷贝功能

### ReleaseProc

```cpp
typedef void (*ReleaseProc)(const void* ptr, void* context);
```

自定义释放回调类型。当 SkData 的引用计数降为零时调用,负责释放底层数据。

**常见实现**:
- `NoopReleaseProc`: 空操作,用于常量数据
- `sk_free_releaseproc`: 调用 `sk_free()` 释放 malloc 分配的内存
- `sk_mmap_releaseproc`: 调用 `sk_fmunmap()` 解除文件映射
- Lambda 函数: 如 `[](const void*, void* ctx) { ((SkData*)ctx)->unref(); }` 用于子集共享

## 公共 API 函数

### 属性查询

```cpp
size_t size() const
const void* data() const
bool empty() const
const uint8_t* bytes() const
SkSpan<const uint8_t> byteSpan() const
```

获取数据缓冲区的大小、指针和视图。所有访问都是只读的。

### 可变访问(谨慎使用)

```cpp
void* writable_data()
```

获取可写指针。**警告**: 仅在确保没有其他线程访问时使用,违反不可变性约定可能导致数据竞争。

### 比较操作

```cpp
bool operator==(const SkData& rhs) const
bool operator!=(const SkData& rhs) const
bool equals(const SkData* other) const
static bool Equals(const SkData* a, const SkData* b)
```

比较两个 SkData 的内容是否相等(大小和字节内容都相同)。

### 子集操作

```cpp
sk_sp<SkData> copySubset(size_t offset, size_t length) const
```
创建子集的深拷贝。

**参数**:
- `offset`: 子集起始偏移
- `length`: 子集长度

**返回值**: 新的 SkData 对象,如果 offset+length 超出范围则返回 nullptr

```cpp
sk_sp<SkData> shareSubset(size_t offset, size_t length)
```
创建子集的引用视图(零拷贝)。

**实现**: 返回新 SkData 指向原数据的子区域,并持有原 SkData 的引用,延长其生命周期。

```cpp
size_t copyRange(size_t offset, size_t length, void* buffer) const
```
拷贝数据范围到调用者提供的缓冲区。

**返回值**: 实际拷贝的字节数(可能小于 length 如果超出范围)

### 静态工厂函数

#### 从内存创建

```cpp
static sk_sp<SkData> MakeWithCopy(const void* data, size_t length)
```
拷贝数据创建新 SkData。内存由 SkData 管理,使用 placement new 分配在 SkData 对象之后。

```cpp
static sk_sp<SkData> MakeUninitialized(size_t length)
```
分配未初始化的内存。调用者应使用 `writable_data()` 填充数据。

```cpp
static sk_sp<SkData> MakeZeroInitialized(size_t length)
```
分配零初始化的内存。

```cpp
static sk_sp<SkData> MakeWithCString(const char cstr[])
```
拷贝 C 字符串(包括终止符)。如果 cstr 为 nullptr,视为空字符串。

```cpp
static sk_sp<SkData> MakeWithProc(const void* ptr, size_t length,
                                    ReleaseProc proc, void* ctx)
```
包装现有内存,使用自定义释放回调。

```cpp
static sk_sp<SkData> MakeWithoutCopy(const void* data, size_t length)
```
包装常量数据(如全局变量),无需释放。使用 `NoopReleaseProc`。

```cpp
static sk_sp<SkData> MakeFromMalloc(const void* data, size_t length)
```
接管 malloc/sk_malloc 分配的内存,SkData 负责调用 sk_free。

#### 从文件创建

```cpp
static sk_sp<SkData> MakeFromFileName(const char path[])
```
使用内存映射(mmap)读取文件。失败返回 nullptr。

```cpp
static sk_sp<SkData> MakeFromFILE(FILE* f)
```
使用内存映射从 FILE* 读取。不会关闭文件。

```cpp
static sk_sp<SkData> MakeFromFD(int fd)
```
使用内存映射从文件描述符读取。不会关闭 fd。

#### 从流创建

```cpp
static sk_sp<SkData> MakeFromStream(SkStream* stream, size_t size)
```
从流中读取指定大小的数据。

**注意**: 会提前检查流剩余长度,避免分配过大缓冲区导致 OOM。

#### 其他工厂函数

```cpp
static sk_sp<SkData> MakeEmpty()
```
返回共享的空 SkData 单例(零拷贝)。

```cpp
static sk_sp<SkData> MakeSubset(const SkData* src, size_t offset, size_t length)
```
**已弃用**: 使用 `src->shareSubset()` 代替。兼容性封装,失败时返回空 SkData 而非 nullptr。

## 内部实现细节

### 内存布局优化

SkData 有两种内存布局:

**1. 独立内存布局**(使用 `MakeWithProc`/`MakeFromMalloc`):
```
[SkData对象: 32字节] -> [外部数据缓冲区]
```

**2. 内嵌内存布局**(使用 `MakeWithCopy`/`MakeUninitialized`):
```
[SkData对象: 32字节][数据缓冲区: N字节]
```

内嵌布局通过 placement new 实现:
```cpp
const size_t actualLength = length + sizeof(SkData);
void* storage = ::operator new (actualLength);
sk_sp<SkData> data(new (storage) SkData(length));
```

构造函数设置 `fSpan` 指向紧跟在对象之后的内存:
```cpp
SkData::SkData(size_t size)
    : fReleaseProc(nullptr)
    , fReleaseProcContext(nullptr)
    , fSpan{(std::byte*)(this + 1), size}  // this+1 跳过对象本身
{}
```

### 共享子集实现

`shareSubset()` 通过引用计数共享实现零拷贝:

```cpp
this->ref();  // 增加原始 SkData 的引用计数
return SkData::MakeWithProc(this->bytes() + offset, length,
    [](const void*, void* ctx) {
        ((SkData*)ctx)->unref();  // 释放时减少引用计数
    }, this);
```

新 SkData 的 `fSpan` 指向原数据的子区域,但生命周期绑定到原 SkData。

### 空 SkData 单例

```cpp
sk_sp<SkData> SkData::MakeEmpty() {
    static SkData* empty = new SkData({}, nullptr, nullptr);
    return sk_ref_sp(empty);
}
```

全局唯一的空对象,避免重复分配。永不释放(引用计数永远 > 0)。

### 内存映射实现

文件映射使用平台特定的 `sk_fmmap()`:
- **Unix/Linux**: `mmap()` 系统调用
- **Windows**: `CreateFileMapping()` + `MapViewOfFile()`

映射的内存在 SkData 析构时通过 `sk_mmap_releaseproc` 解除映射。

**优势**:
- 零拷贝:文件内容直接映射到进程地址空间
- 惰性加载:只有访问时才触发实际 I/O
- 内核优化:多进程共享同一文件的物理内存

### 比较优化

```cpp
bool SkData::operator==(const SkData& other) const {
    if (this == &other) {
        return true;  // 同一对象快速返回
    }
    return size() == other.size() &&
           !sk_careful_memcmp(data(), other.data(), size());
}
```

`sk_careful_memcmp` 是时间恒定的 memcmp,避免时序攻击(在安全敏感场景重要)。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| include/core/SkRefCnt.h | 引用计数基类 |
| include/core/SkSpan.h | 类型安全的缓冲区视图 |
| include/core/SkStream.h | 流读取接口 |
| src/core/SkOSFile.h | 文件操作和内存映射 |
| include/private/base/SkMalloc.h | 内存分配函数 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| include/core/SkImage.h | 存储编码的图像数据(JPEG/PNG 等) |
| include/core/SkTypeface.h | 字体文件数据 |
| include/core/SkPicture.h | 序列化的绘图命令 |
| src/gpu/ | GPU 资源数据(着色器、缓冲区) |
| src/codec/ | 图像解码器输入 |
| src/pdf/ | PDF 文档数据流 |

## 设计模式与设计决策

### 设计模式

1. **不可变对象模式**: 数据一旦创建不可修改,线程安全
2. **引用计数模式**: 自动内存管理,共享所有权
3. **策略模式**: 通过 ReleaseProc 支持不同的内存管理策略
4. **单例模式**: 空 SkData 全局共享
5. **工厂模式**: 多种静态工厂函数适应不同数据源

### 设计决策

**为何不可变**:
- 线程安全:多个线程可以同时读取无需同步
- 哈希友好:可作为哈希表键(内容不变,哈希值稳定)
- 简化生命周期:无需担心修改影响其他持有者

**为何使用引用计数而非 std::shared_ptr**:
- 性能:引用计数内嵌在对象中,减少一次内存分配
- 控制:自定义释放逻辑,支持多种内存来源
- 历史:Skia 在 C++11 之前开发,引用计数是现有架构

**为何提供 writable_data()**:
- 实用性:创建后需要填充数据的场景(如解码器输出)
- 性能:避免先填充缓冲区再拷贝到 SkData
- 责任:调用者需确保线程安全,文档明确警告

**内嵌内存布局的优势**:
- 减少内存分配次数:一次分配同时获得对象和数据
- 提高缓存局部性:对象和数据相邻,减少 cache miss
- 简化内存管理:无需单独跟踪数据缓冲区

**为何支持内存映射**:
- 大文件性能:避免将整个文件读入内存
- 内存效率:操作系统按需加载页面
- 零拷贝:直接访问文件内容

**子集共享 vs 拷贝**:
- `shareSubset`:零开销,适合临时操作
- `copySubset`:独立生命周期,适合长期持有
- 给调用者选择权,平衡性能和安全

## 性能考量

### 优化策略

1. **零拷贝路径**: `MakeWithoutCopy`, `MakeFromMalloc`, 文件映射
2. **内嵌内存**: 减少分配次数和间接访问
3. **引用计数共享**: 避免数据拷贝
4. **空对象单例**: 零拷贝的空数据
5. **快速相等性检查**: 指针比较优先于内容比较

### 性能特征

| 操作 | 时间复杂度 | 典型开销 |
|------|-----------|---------|
| MakeEmpty() | O(1) | ~5ns(引用计数增加) |
| MakeWithCopy() | O(N) | 分配+拷贝,~1μs + 0.5GB/s |
| MakeFromMalloc() | O(1) | ~50ns(对象分配) |
| MakeWithoutCopy() | O(1) | ~50ns |
| MakeFromFileName() | O(1) | ~10μs(mmap 系统调用) |
| shareSubset() | O(1) | ~100ns(新对象+闭包) |
| copySubset() | O(N) | 同 MakeWithCopy |
| operator==() | O(N) | memcmp,~5GB/s |
| ref/unref | O(1) | ~2ns(原子操作) |

### 内存占用

- **对象大小**: 32 字节(64 位系统)
  - SkNVRefCnt: 4 字节引用计数
  - ReleaseProc: 8 字节函数指针
  - void*: 8 字节上下文
  - SkSpan: 16 字节(指针+大小)
- **内嵌数据**: 对象大小 + 数据大小
- **外部数据**: 仅对象大小

### 潜在瓶颈

- **大内存拷贝**: `MakeWithCopy` 受限于内存带宽
- **频繁创建/销毁**: 引用计数原子操作有开销
- **内存映射超大文件**: 可能耗尽虚拟地址空间(32 位系统)

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| include/core/SkRefCnt.h | 基类 | 引用计数实现 |
| include/core/SkStream.h | 依赖 | 流读取接口 |
| src/core/SkOSFile.h | 依赖 | 文件操作和 mmap |
| include/core/SkImage.h | 使用者 | 图像编码数据存储 |
| include/core/SkPicture.h | 使用者 | 序列化数据存储 |
| include/core/SkTypeface.h | 使用者 | 字体文件数据 |
| src/codec/SkCodec.cpp | 使用者 | 解码器输入 |
| tests/DataTest.cpp | 测试 | 单元测试 |
