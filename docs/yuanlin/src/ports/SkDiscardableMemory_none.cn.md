# SkDiscardableMemory_none

> 源文件: [src/ports/SkDiscardableMemory_none.cpp](../../../../src/ports/SkDiscardableMemory_none.cpp)

## 概述

本文件提供了 `SkDiscardableMemory::Create()` 的默认实现，将可丢弃内存的创建委托给全局的可丢弃内存池 (`SkGetGlobalDiscardableMemoryPool()`)。当平台没有原生的可丢弃内存支持（如 Android 的 `ashmem` 或 iOS 的 `NSDiscardableContent`）时使用此实现。

## 架构位置

```
SkDiscardableMemory (接口)
  ├── 平台原生实现 (Android ashmem 等)
  └── 默认实现 (本文件)
        └── SkGetGlobalDiscardableMemoryPool()
              └── SkDiscardableMemoryPool (软件模拟)
```

## 主要类与结构体

本文件不定义类或结构体。

## 公共 API 函数

| 函数签名 | 功能说明 |
|---------|---------|
| `SkDiscardableMemory* SkDiscardableMemory::Create(size_t bytes)` | 从全局内存池创建指定大小的可丢弃内存块 |

## 内部实现细节

实现仅一行:
```cpp
SkDiscardableMemory* SkDiscardableMemory::Create(size_t bytes) {
    return SkGetGlobalDiscardableMemoryPool()->create(bytes);
}
```

`SkGetGlobalDiscardableMemoryPool()` 返回一个全局单例的 `SkDiscardableMemoryPool`，该池使用普通堆内存模拟可丢弃行为:
- 分配时标记为"锁定"，数据保证可用
- 解锁后数据可能在内存压力下被丢弃
- 再次锁定时如果数据已丢弃，返回失败

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `include/core/SkTypes.h` | 基础类型 |
| `include/private/chromium/SkDiscardableMemory.h` | 可丢弃内存接口 |
| `src/lazy/SkDiscardableMemoryPool.h` | 全局内存池 |

## 设计模式与设计决策

1. **默认后备实现**: 为没有原生可丢弃内存的平台提供软件模拟
2. **全局池委托**: 所有可丢弃内存通过统一的全局池管理，便于监控和控制内存使用
3. **极简实现**: 单行函数体，最大限度减少此文件的维护负担

## 性能考量

- 软件模拟的可丢弃内存不如操作系统原生实现高效（无法利用系统级内存压力通知）
- 全局内存池有自己的内存上限策略，在内存紧张时会主动丢弃已解锁的块
- 适用于桌面平台等内存相对充裕的环境
- 内存池本身有同步开销（需要线程安全），但在低频操作场景下可忽略
- 相比 Android 的 ashmem 实现，缺少操作系统级别的"可丢弃"语义，系统低内存时无法被内核自动回收

## 使用场景

可丢弃内存在 Skia 中主要用于:
- 图像解码缓存：解码后的像素数据存储在可丢弃内存中，在内存压力下可被释放
- `SkCachedData` 内部使用可丢弃内存存储缓存条目
- 字体光栅化缓存中也可能使用可丢弃内存

本文件作为"无原生支持"平台的默认实现，在以下情况被编译:
- 桌面 Linux
- macOS (虽然 macOS 有 NSPurgeableData，但 Skia 不使用它)
- 没有特定可丢弃内存实现的其他平台

## 全局内存池

`SkGetGlobalDiscardableMemoryPool()` 返回的内存池具有以下特性:
- 全局单例，所有可丢弃内存共享
- 可配置的内存上限
- 使用 LRU (最近最少使用) 策略丢弃已解锁的块
- 线程安全的 lock/unlock 操作

## 相关文件

- `include/private/chromium/SkDiscardableMemory.h` — 可丢弃内存接口定义
- `src/lazy/SkDiscardableMemoryPool.h` — 内存池声明
- `src/lazy/SkDiscardableMemoryPool.cpp` — 内存池实现
