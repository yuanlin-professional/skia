# GrBackendTextureImageGenerator - 跨上下文后端纹理图像生成器

> 源文件: `src/gpu/ganesh/GrBackendTextureImageGenerator.h`, `src/gpu/ganesh/GrBackendTextureImageGenerator.cpp`

## 概述

`GrBackendTextureImageGenerator` 用于在不同 `GrContext` 之间共享 GPU 纹理。它将一个上下文（生产者）中的纹理包装为图像生成器，通过信号量（semaphore）同步后，可在另一个上下文（消费者）中作为纹理源使用。此功能主要由 Flutter 使用，支持多线程 GPU 资源共享场景。

## 架构位置

```
GrContext-A (生产者)                     GrContext-B (消费者)
    |                                         |
GrTexture ---> GrBackendTextureImageGenerator ---> LazyProxy ---> GrTexture (包装)
    |                   |                                              |
    +--- Semaphore -----+---------- waitSemaphore -------------------+
```

## 主要类与结构体

### `GrBackendTextureImageGenerator`

继承自 `GrTextureGenerator`，标记为 `final`。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fRefHelper` | `RefHelper*` | 引用计数辅助对象（管理纹理和信号量生命周期） |
| `fBorrowingMutex` | `SkMutex` | 保护借出操作的互斥锁 |
| `fBackendTexture` | `GrBackendTexture` | 后端纹理句柄 |
| `fSurfaceOrigin` | `GrSurfaceOrigin` | 纹理原点方向 |

### `RefHelper` (内部类)

管理纹理的跨上下文共享状态。

| 成员 | 说明 |
|------|------|
| `fOriginalTexture` | 原始纹理引用 |
| `fOwningContextID` | 拥有者上下文 ID |
| `fBorrowedTextureKey` | 借出纹理的唯一键（缓存复用） |
| `fBorrowingContextReleaseProc` | 借出方的释放回调（裸指针，通过原子操作保证安全） |
| `fBorrowingContextID` | 当前借出方上下文 ID |
| `fSemaphore` | GPU 信号量 |

## 公共 API 函数

### `Make()`

```cpp
static std::unique_ptr<GrTextureGenerator> Make(const sk_sp<GrTexture>&, GrSurfaceOrigin,
                                                 std::unique_ptr<GrSemaphore>,
                                                 SkColorType, SkAlphaType, sk_sp<SkColorSpace>);
```

从已有纹理创建生成器。验证颜色类型与格式兼容性。

## 内部实现细节

### 借出协议

`onGenerateTexture` 实现了严格的单消费者借出协议：
1. 获取互斥锁。
2. 检查是否已被另一个上下文借出（若是，拒绝并发出警告）。
3. 若同一上下文重复借出，复用已有的 `releaseProcHelper`。
4. 若首次借出，创建新的 `RefCntedCallback` 作为释放回调。
5. 释放互斥锁。
6. 创建懒代理，其回调中等待信号量并包装后端纹理。

### 纹理复用

通过 `fBorrowedTextureKey` 在资源缓存中查找已包装的纹理，避免对同一后端纹理重复创建 `GrTexture` 包装。

### 线程安全的资源释放

`RefHelper` 析构时通过 `GrResourceCache::ReturnResourceFromThread` 将原始纹理释放回正确的线程，避免跨线程资源释放问题。

## 依赖关系

- **上游依赖**: `GrTextureGenerator`、`GrSemaphore`、`GrProxyProvider`。
- **被依赖**: Flutter 跨上下文纹理共享、`SkImage::MakeCrossContextFromPixmap`。

## 设计模式与设计决策

1. **单消费者限制**: Vulkan 不允许多个消费者等待同一信号量，因此限制为单消费者。
2. **懒代理**: 延迟纹理包装到实际需要时，支持录制阶段的使用。
3. **互斥锁保护**: 确保多线程安全的借出/归还操作。

## 性能考量

- 信号量等待仅在懒代理首次实例化时执行一次。
- `UniqueKey` 缓存避免重复包装。
- 限制为 DirectContext 以简化同步逻辑。

## 相关文件

- `include/private/gpu/ganesh/GrTextureGenerator.h` - 纹理生成器基类
- `src/gpu/ganesh/GrSemaphore.h` - GPU 信号量
- `src/gpu/ganesh/GrProxyProvider.h` - 代理提供者
- `src/gpu/RefCntedCallback.h` - 引用计数回调
