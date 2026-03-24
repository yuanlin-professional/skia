# FrontBufferedStream - 前置缓冲流

> 源文件:
> - `client_utils/android/FrontBufferedStream.h`
> - `client_utils/android/FrontBufferedStream.cpp`

## 概述

FrontBufferedStream 是一种专门为 Android 图像解码设计的流包装器，它缓冲流前部的 X 个字节以支持有限范围的 rewind（回绕）操作。与通用缓冲流不同，一旦读取超过缓冲区大小，缓冲将不再生效。这种设计专门针对以下场景：调用者确知 rewind 只会在前 X 个字节范围内发生，且被包装的底层流可能不支持 rewind。

## 架构位置

```
Android 图像解码流程
├── SkStream (可能不可回绕)
│   └── FrontBufferedStream (提供有限回绕能力)  <── 本模块
│       └── SkAndroidCodec / BitmapRegionDecoder
```

该类位于 `android::skia` 命名空间，是 Android 客户端工具层的基础设施组件。常用于图像解码前的格式嗅探：先读取文件头判断格式，然后 rewind 回起点开始正式解码。

## 主要类与结构体

### `android::skia::FrontBufferedStream` (公共接口)

仅包含一个静态工厂方法的接口类。

### 匿名命名空间中的 `FrontBufferedStream` (内部实现)

- **继承**: `SkStreamRewindable`
- **成员变量**:
  - `fStream` (`unique_ptr<SkStream>`): 被包装的底层流
  - `fHasLength` / `fLength`: 长度信息（从底层流获取）
  - `fOffset`: 当前读取偏移量
  - `fBufferedSoFar`: 已缓冲的字节数
  - `fBufferSize`: 缓冲区总大小
  - `fBuffer` (`char*`): 缓冲区指针
  - `fStorage[kStorageSize]`: 栈上小缓冲区（`kStorageSize = SkCodec::MinBufferedBytesNeeded()`）

## 公共 API 函数

| 函数 | 描述 |
|------|------|
| `FrontBufferedStream::Make(stream, minBufferSize)` | 创建一个能缓冲至少 `minBufferSize` 字节的可回绕流 |

### 内部实现的流接口

| 函数 | 描述 |
|------|------|
| `read(buffer, size)` | 读取数据，优先从缓冲区读取 |
| `peek(buffer, size)` | 查看数据但不移动读取位置 |
| `isAtEnd()` | 判断是否到达流末尾 |
| `rewind()` | 回绕到流起点（仅在缓冲区范围内有效）|
| `hasLength()` / `getLength()` | 获取流长度信息 |

## 内部实现细节

### 三阶段读取策略

`read()` 方法将读取分为三个阶段，按优先级依次执行：

1. **`readFromBuffer`**: 如果 `fOffset < fBufferedSoFar`，从已缓冲的数据中读取。这发生在 rewind 之后
2. **`bufferAndWriteTo`**: 如果缓冲区未满且流未结束，从底层流读取新数据，同时缓冲和输出
3. **`readDirectlyFromStream`**: 缓冲区已满后，直接从底层流读取，不再缓冲

### 小缓冲区优化（SBO）

```cpp
inline static constexpr size_t kStorageSize = SkCodec::MinBufferedBytesNeeded();
char fStorage[kStorageSize];
```

当请求的缓冲区大小不超过 `kStorageSize` 时，使用栈上的 `fStorage` 数组，避免堆分配。只有当缓冲区需求较大时才使用 `malloc`。

### 缓冲区释放优化

当读取超过缓冲区范围后（`readDirectlyFromStream` 被调用），如果缓冲区是堆分配的，立即释放以回收内存：

```cpp
if (bytesReadDirectly > 0 && fBuffer != fStorage) {
    free(fBuffer);
    fBuffer = nullptr;
}
```

### Rewind 限制

`rewind()` 仅在 `fOffset <= fBufferSize` 时成功，一旦读取超过缓冲区大小就不再支持回绕。

### peek 实现

`peek()` 通过临时保存 `fOffset`、执行 `read()`、恢复 `fOffset` 来实现非破坏性查看。使用 `const_cast` 绕过 const 限制。

### 长度信息

流的长度在构造时计算为 `fStream->getLength() - fStream->getPosition()`，仅在底层流同时支持 `hasPosition()` 和 `hasLength()` 时有效。

## 依赖关系

- **Skia 流**: `SkStream`（底层流基类）、`SkStreamRewindable`（可回绕流接口）
- **编解码器**: `SkCodec`（`MinBufferedBytesNeeded()` 常量）
- **标准库**: `<algorithm>`（`std::min`）、`<memory>`

## 设计模式与设计决策

- **装饰器模式**: 包装现有 `SkStream`，添加缓冲和回绕能力
- **小缓冲区优化（SBO）**: 栈上预分配小缓冲区避免小需求场景的堆分配
- **所有权转移**: `Make()` 接管 `SkStream` 的 `unique_ptr` 所有权
- **匿名命名空间封装**: 内部实现类放在匿名命名空间中，仅通过公共接口暴露
- **不可复制**: `onDuplicate()` 返回 `nullptr`，该流不支持复制
- **渐进式降级**: 缓冲区满后自动切换到直通模式，不影响后续读取

## 性能考量

- 三阶段读取策略最小化了不必要的数据复制
- `kStorageSize` 使用 `SkCodec::MinBufferedBytesNeeded()` 作为内联缓冲区大小，这是编解码器格式嗅探所需的最小字节数，覆盖了最常见的使用场景
- 缓冲区用完后立即释放，避免长期占用无用内存
- `readFromBuffer` 中使用 `memcpy` 进行批量复制，效率高
- `peek` 的实现虽然不是零拷贝，但通过复用 `read` 逻辑保持了代码简洁性
- 构造时一次性确定长度信息，避免后续重复查询

## 相关文件

- `include/core/SkStream.h` - 流基类定义
- `include/codec/SkCodec.h` - 编解码器（`MinBufferedBytesNeeded`）
- `client_utils/android/BitmapRegionDecoder.h` - 位图区域解码器（常见使用者）
- `include/codec/SkAndroidCodec.h` - Android 编解码器
