# MtlBackendSemaphore - Metal 后端信号量

> 源文件: `src/gpu/graphite/mtl/MtlBackendSemaphore.mm`

## 概述

MtlBackendSemaphore.mm 实现了 Skia Graphite Metal 后端的信号量（Semaphore）支持。它定义了 `MtlBackendSemaphoreData` 类作为 Metal 特定的信号量数据存储，并在 `BackendSemaphores` 命名空间中提供了创建和查询 Metal 信号量的公共工厂函数。

Metal 的信号量机制基于 `MTLEvent` 对象和关联的 `uint64_t` 值。MTLEvent 用于在命令缓冲区之间同步 GPU 工作，通过信号（signal）和等待（wait）操作实现跨队列或跨帧的依赖管理。

## 架构位置

```
Graphite 后端抽象层
  -> BackendSemaphore (跨后端信号量接口)
    -> MtlBackendSemaphoreData (Metal 实现)
      -> CFTypeRef (MTLEvent)
      -> uint64_t (信号值)
```

MtlBackendSemaphore 是 Graphite 跨后端信号量抽象的 Metal 特定实现。

## 主要类与结构体

### `MtlBackendSemaphoreData`（内部类）
- **基类**: `BackendSemaphoreData`
- **成员**:
  - `fMtlEvent` (`CFTypeRef`): 持有 `id<MTLEvent>` 对象
  - `fMtlValue` (`uint64_t`): 信号量的期望值
- **方法**:
  - `event()`: 返回 MTLEvent
  - `value()`: 返回信号量值
  - `type()`: 返回 `BackendApi::kMetal`（仅调试构建）
  - `copyTo()`: 将数据拷贝到 `AnyBackendSemaphoreData` 容器

## 公共 API 函数

| 函数 | 命名空间 | 说明 |
|------|----------|------|
| `MakeMetal(CFTypeRef, uint64_t)` | `BackendSemaphores` | 创建 Metal 后端信号量 |
| `GetMtlEvent(const BackendSemaphore&)` | `BackendSemaphores` | 从通用信号量中提取 MTLEvent |
| `GetMtlValue(const BackendSemaphore&)` | `BackendSemaphores` | 从通用信号量中提取信号量值 |

## 内部实现细节

### BackendSemaphore 的类型擦除
`MakeMetal` 通过 `BackendSemaphorePriv::Make` 将 Metal 特定的数据封装进跨后端的 `BackendSemaphore` 类型。`BackendSemaphore` 使用类型擦除（通过 `AnyBackendSemaphoreData`）存储后端特定数据。

### 安全提取模式
`GetMtlEvent` 和 `GetMtlValue` 先验证信号量的有效性和后端类型，无效时返回 `nullptr` 或 `0`。内部辅助函数 `get_and_cast_data` 使用 `static_cast` 向下转型，调试构建中通过 `SkASSERT` 验证类型。

### CFTypeRef 的使用
使用 `CFTypeRef`（而非 `id<MTLEvent>`）作为存储类型，因为 Objective-C 对象类型不能直接在 C++ 类中使用。`CFTypeRef` 是 Core Foundation 的通用引用类型，可以在 C++ 和 Objective-C 之间桥接。

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `src/gpu/graphite/BackendSemaphorePriv.h` | 后端信号量的私有创建接口 |
| `include/gpu/graphite/mtl/MtlGraphiteTypes_cpp.h` | Metal Graphite 类型定义 |
| `src/gpu/graphite/mtl/MtlGraphiteUtils.h` | Metal 工具函数 |
| `include/gpu/MutableTextureState.h` | 纹理状态 |
| `<Metal/Metal.h>` | Metal 框架 |

## 设计模式与设计决策

1. **类型擦除模式**: 通过 `BackendSemaphoreData` 基类和 `AnyBackendSemaphoreData` 容器实现跨后端的统一信号量接口，隐藏 Metal 特定细节。

2. **命名空间工厂**: 使用 `BackendSemaphores` 命名空间的自由函数而非类静态方法，使公共 API 更清晰。

3. **防御性编程**: 提取函数在后端类型不匹配时安全返回默认值，而非断言失败。

## 性能考量

1. **CFTypeRef 桥接**: CFTypeRef 不持有 Objective-C 的 ARC 引用计数，使用者需要自行管理 MTLEvent 的生命周期。
2. **轻量数据类**: MtlBackendSemaphoreData 仅存储一个指针和一个 uint64_t，拷贝操作非常廉价。

## 相关文件

- `src/gpu/graphite/BackendSemaphorePriv.h` - 信号量私有 API
- `include/gpu/graphite/BackendSemaphore.h` - 公共信号量接口
- `src/gpu/graphite/mtl/MtlCommandBuffer.h` - Metal 命令缓冲区（使用信号量同步）
- `src/gpu/graphite/mtl/MtlGraphiteUtils.h` - Metal 工具函数
