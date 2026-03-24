# SkDWriteFontFileStream - DirectWrite 字体文件流适配器

> 源文件:
> - `src/utils/win/SkDWriteFontFileStream.h`
> - `src/utils/win/SkDWriteFontFileStream.cpp`

## 概述

SkDWriteFontFileStream 模块提供了 Skia 流系统与 DirectWrite 字体文件流之间的双向适配器。它包含两个类：`SkDWriteFontFileStream` 将 DirectWrite 的 `IDWriteFontFileStream` 包装为 Skia 的 `SkStreamMemory`，而 `SkDWriteFontFileStreamWrapper` 将 Skia 的 `SkStreamAsset` 包装为 DirectWrite 的 `IDWriteFontFileStream`。

## 架构位置

```
Skia Windows 字体后端
├── SkTypeface_win_dw
│   ├── SkDWriteFontFileStream (DWrite -> Skia 方向)
│   │   └── IDWriteFontFileStream -> SkStreamMemory
│   └── SkDWriteFontFileStreamWrapper (Skia -> DWrite 方向)
│       └── SkStreamAsset -> IDWriteFontFileStream
├── 字体数据读取 / 加载
└── DirectWrite API
```

## 主要类与结构体

### `SkDWriteFontFileStream`
- 继承自 `SkStreamMemory`，将 `IDWriteFontFileStream` 适配为 Skia 可读流。
- **成员变量**:
  - `fFontFileStream` (SkTScopedComPtr): 持有的 DirectWrite 流引用。
  - `fPos` (size_t): 当前读取位置。
  - `fLockedMemory` (const void*): 锁定的内存基地址（用于 `getMemoryBase()`）。
  - `fFragmentLock` (void*): 内存片段的锁句柄。

### `SkDWriteFontFileStreamWrapper`
- 实现 `IDWriteFontFileStream` COM 接口，将 Skia 的 `SkStreamAsset` 暴露给 DirectWrite。
- **成员变量**:
  - `fRefCount` (ULONG): COM 引用计数。
  - `fStream` (unique_ptr\<SkStreamAsset\>): 持有的 Skia 流。
  - `fStreamMutex` (SkMutex): 保护流操作的互斥锁。

## 公共 API 函数

### SkDWriteFontFileStream

#### 流操作
- `read()`: 从 DirectWrite 流读取数据，处理缓冲区为 null（跳过）和读取越界的情况。
- `isAtEnd()`: 检查是否到达流末尾。
- `rewind()`: 重置位置到 0。
- `getPosition()`: 返回当前读取位置。
- `seek()`: 定位到指定位置（钳制到流长度）。
- `move()`: 相对移动位置。
- `getLength()`: 通过 `GetFileSize()` 获取流总长度。
- `getMemoryBase()`: 首次调用时锁定整个文件内容到内存，后续直接返回缓存指针。
- `duplicate()` / `fork()`: 创建流的副本/分支。

### SkDWriteFontFileStreamWrapper

#### `Create` (静态工厂)
```cpp
static HRESULT Create(SkStreamAsset* stream, SkDWriteFontFileStreamWrapper** streamFontFileStream);
```
- 创建包装 Skia 流的 DirectWrite 流。

#### COM 接口方法
- `ReadFileFragment()`: 从 Skia 流读取数据片段。支持两种模式：
  - 如果流有内存基地址，直接返回偏移后的指针（零拷贝）。
  - 否则，在互斥锁保护下 seek+read 数据到新分配的缓冲区。
- `ReleaseFileFragment()`: 释放由 `ReadFileFragment` 分配的缓冲区。
- `GetFileSize()`: 返回流长度。
- `GetLastWriteTime()`: 返回 `E_NOTIMPL`（此概念不适用于内存流）。

## 内部实现细节

### read() 的三种路径
1. **buffer == null**: 跳过模式，仅移动位置指针。
2. **正常读取**: 调用 `ReadFileFragment` 获取数据，`memcpy` 到目标缓冲区后释放片段。
3. **部分读取回退**: 如果请求的大小超出流末尾，自动减少读取量到剩余大小。

### getMemoryBase() 的惰性锁定
首次调用时通过 `ReadFileFragment` 锁定整个文件内容，锁句柄保存在 `fFragmentLock` 中，在析构函数中释放。后续调用直接返回缓存的内存指针。

### ReadFileFragment 的线程安全
当 Skia 流没有内存基地址时，`ReadFileFragment` 使用 `SkAutoMutexExclusive` 加锁保护 seek+read 操作，因为该方法可能被多线程调用。

### 边界检查
`ReadFileFragment` 在读取前验证 `fileOffset + fragmentSize` 不超过文件大小，使用 `SkTFitsIn<size_t>` 检查 UINT64 值能否安全转换为 size_t。

## 依赖关系

- `include/core/SkStream.h`: Skia 流基类。
- `include/core/SkTypes.h`: 基础类型。
- `include/private/base/SkMutex.h`: 互斥锁。
- `include/private/base/SkTFitsIn.h`: 类型范围检查。
- `include/private/base/SkTemplates.h`: `AutoTMalloc` 内存管理。
- `src/utils/win/SkTScopedComPtr.h`: COM 指针 RAII 封装。
- `src/utils/win/SkObjBase.h`: COM 方法宏。
- `src/utils/win/SkHRESULT.h`: HRESULT 错误处理宏。
- `<dwrite.h>`: DirectWrite API。

## 设计模式与设计决策

1. **双向适配器模式**: 两个类分别实现 Skia->DWrite 和 DWrite->Skia 方向的流适配。
2. **惰性初始化**: `getMemoryBase()` 延迟到首次调用时锁定内存。
3. **零拷贝优化**: `ReadFileFragment` 在有内存基地址时直接返回偏移指针，避免数据复制。
4. **线程安全**: 对非内存映射流使用互斥锁保护多线程访问。

## 性能考量

1. **零拷贝路径**: 基于内存映射的流可以直接返回指针，无需数据复制。
2. **内存锁定缓存**: `getMemoryBase()` 的结果被缓存，避免重复锁定操作。
3. **互斥锁开销**: 对于非内存映射流，每次 `ReadFileFragment` 都需要获取锁，可能成为多线程瓶颈。
4. **部分读取优化**: `read()` 中的分段读取策略确保即使请求超出范围也能返回尽可能多的数据。

## 相关文件

- `src/utils/win/SkDWrite.h/.cpp`: DirectWrite 核心工具。
- `src/utils/win/SkTScopedComPtr.h`: COM 智能指针。
- `src/utils/win/SkHRESULT.h`: 错误处理宏。
- `include/core/SkStream.h`: Skia 流基类定义。
