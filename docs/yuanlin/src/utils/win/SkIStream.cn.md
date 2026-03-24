# SkIStream - Windows IStream 适配器

> 源文件:
> - `src/utils/win/SkIStream.h`
> - `src/utils/win/SkIStream.cpp`

## 概述

SkIStream 模块提供了 Skia 流系统与 Windows COM IStream 接口之间的适配器。它包含三个类：`SkBaseIStream` 是提供默认 E_NOTIMPL 实现的基类，`SkIStream` 是包装 SkStreamAsset 的只读 IStream，`SkWIStream` 是包装 SkWStream 的只写 IStream。这些适配器使 Skia 的流可以被需要 IStream 接口的 Windows API（如 WIC、XPS 等）使用。

## 架构位置

```
Skia Windows 平台集成
├── Windows 图像编解码 (WIC)
│   └── IStream 接口需求
├── XPS 文档输出
│   └── IStream 接口需求
└── SkIStream (本模块 - 流接口适配)
    ├── SkBaseIStream (基类 - 默认实现)
    ├── SkIStream (只读适配: SkStreamAsset -> IStream)
    └── SkWIStream (只写适配: SkWStream -> IStream)
```

## 主要类与结构体

### `SkBaseIStream`
- 实现 IStream COM 接口的基类。
- 提供 IUnknown 方法的标准实现（QueryInterface, AddRef, Release）。
- 所有 ISequentialStream 和 IStream 方法默认返回 `E_NOTIMPL`。
- **成员变量**: `_refcount` (LONG) - 引用计数。

### `SkIStream`
- 继承自 `SkBaseIStream`，将 `SkStreamAsset` 适配为只读 IStream。
- **成员变量**:
  - `fSkStream` (unique_ptr\<SkStream\>): 持有的 Skia 流。
  - `fLocation` (ULARGE_INTEGER): 当前位置追踪。
- 覆盖了 Read、Write (返回 STG_E_CANTSAVE)、Seek 和 Stat 方法。

### `SkWIStream`
- 继承自 `SkBaseIStream`，将 `SkWStream` 适配为只写 IStream。
- **成员变量**: `fSkWStream` (SkWStream*) - 借用的写流指针。
- 覆盖了 Write、Commit 和 Stat 方法。

## 公共 API 函数

### `SkIStream::CreateFromSkStream`
```cpp
static HRESULT CreateFromSkStream(std::unique_ptr<SkStreamAsset>, IStream** ppStream);
```
- **功能**: 创建包装 SkStreamAsset 的只读 IStream。
- **所有权**: 接管 SkStreamAsset 的所有权。

### `SkWIStream::CreateFromSkWStream`
```cpp
static HRESULT CreateFromSkWStream(SkWStream* stream, IStream** ppStream);
```
- **功能**: 创建包装 SkWStream 的只写 IStream。
- **所有权**: 不接管 SkWStream 的所有权（借用指针）。

## 内部实现细节

### SkIStream::Seek 的三种模式
1. **STREAM_SEEK_SET**: 先 rewind 到起始位置，然后 skip 到目标位置。
2. **STREAM_SEEK_CUR**: 从当前位置 skip 指定距离。
3. **STREAM_SEEK_END**: 先 rewind，然后 skip 到 (总长度 + 偏移量)。

由于 SkStream 不直接支持从末尾的 Seek，实现使用 rewind + skip 的组合来模拟。

### SkIStream::Stat
- 返回流的基本统计信息。
- 要求 `STATFLAG_NONAME` 标志（不返回名称），否则返回 `STG_E_INVALIDFLAG`。
- 设置 `grfMode = STGM_READ` 表示只读。

### SkWIStream 的生命周期管理
- 析构时调用 `fSkWStream->flush()` 确保所有缓冲数据被写出。
- `Commit` 方法也调用 `flush()`。
- Stat 中设置 `cbSize = 0`（写流不跟踪总大小）和 `grfMode = STGM_WRITE`。

### QueryInterface 支持
基类的 `QueryInterface` 支持三种接口：`IUnknown`、`IStream` 和 `ISequentialStream`，返回同一个对象指针。

## 依赖关系

- `include/core/SkStream.h`: Skia 流类。
- `include/core/SkTypes.h`: 基础类型。
- `src/base/SkLeanWindows.h`: Windows 头文件。
- `src/utils/win/SkObjBase.h`: COM 方法宏。
- `<ole2.h>`: IStream 接口定义。

## 设计模式与设计决策

1. **NVI (Non-Virtual Interface) + 适配器模式**: 基类提供默认的 E_NOTIMPL 实现，子类只覆盖需要的方法。
2. **读写分离**: 读和写分别由不同的子类处理，职责清晰。
3. **只读写保护**: `SkIStream::Write` 返回 `STG_E_CANTSAVE`，明确拒绝写操作。
4. **所有权语义差异**: `SkIStream` 接管流所有权（通过 `unique_ptr`），而 `SkWIStream` 仅借用指针。这反映了读流需要独立管理缓冲而写流通常由调用者管理的实际需求。

## 性能考量

1. **Seek 效率**: `STREAM_SEEK_SET` 和 `STREAM_SEEK_END` 需要 rewind + skip，对于大型流可能较慢。这是因为底层 SkStream 不支持随机访问的限制。
2. **无内存映射**: 与 `SkDWriteFontFileStreamWrapper` 不同，此实现不支持零拷贝路径。
3. **引用计数**: 使用 `InterlockedIncrement`/`InterlockedDecrement` 实现线程安全的引用计数。

## 相关文件

- `include/core/SkStream.h`: Skia 流基类。
- `src/utils/win/SkObjBase.h`: COM 接口宏。
- `src/ports/SkImageEncoder_WIC.cpp`: WIC 图像编码器，使用 IStream 输出。
