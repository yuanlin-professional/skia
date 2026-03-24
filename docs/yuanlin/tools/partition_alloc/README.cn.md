# Skia Partition Alloc 分区分配器工具

## 概述

`tools/partition_alloc` 提供了 Chromium PartitionAlloc 内存分配器的测试支持功能。PartitionAlloc 是 Chromium 开发的高性能内存分配器，通过内存分区隔离来增强安全性并减少内存碎片。该模块允许 Skia 测试在启用 PartitionAlloc 分配器的环境下运行，以验证 Skia 与 Chromium 内存管理系统的兼容性。

## 目录结构

```
tools/partition_alloc/
├── BUILD.gn          # GN 构建配置
├── TestSupport.h     # 测试支持函数声明
└── TestSupport.cpp   # 测试支持函数实现
```

## API 接口

### TestSupport.h

```cpp
namespace skiatest {

// 启用 PartitionAlloc 分配器用于测试
void InitializePartitionAllocForTesting();

// TODO(351867706): 添加悬挂指针检查初始化
// void InitializeDanglingPointerChecksForTesting();

}  // namespace skiatest
```

### TestSupport.cpp

实现 `InitializePartitionAllocForTesting()` 函数：

```cpp
void InitializePartitionAllocForTesting() {
#if PA_BUILDFLAG(USE_ALLOCATOR_SHIM)
    // 配置分区用于测试
    allocator_shim::ConfigurePartitionsForTesting();
    // 启用线程缓存（如果支持）
    allocator_shim::internal::PartitionAllocMalloc::Allocator()
        ->EnableThreadCacheIfSupported();
#endif
}
```

## 技术细节

### PartitionAlloc 概念

PartitionAlloc 是 Chromium 的内存分配器，核心特性：

- **内存分区**: 不同类型的分配使用不同的内存区域
- **安全性**: 隔离不同用途的内存，减少 Use-After-Free 等漏洞
- **线程缓存**: 每个线程维护本地缓存，减少锁竞争
- **分配器垫片（Allocator Shim）**: 替换系统默认的 malloc/free

### 条件编译

该模块使用 `PA_BUILDFLAG(USE_ALLOCATOR_SHIM)` 条件编译：

- 仅在构建系统启用了分配器垫片时激活
- 在不支持的平台上，函数体为空（无操作）
- 依赖 `<partition_alloc/buildflags.h>` 提供构建标志

### 线程缓存

`EnableThreadCacheIfSupported()` 启用 PartitionAlloc 的线程缓存机制：

- 为每个线程分配本地缓存
- 小对象分配可以完全在线程缓存中完成
- 减少全局锁的争用，提升多线程性能

## 使用场景

1. **Chromium 集成测试**: 验证 Skia 在 Chromium 的 PartitionAlloc 环境下的正确性
2. **内存安全测试**: 检测 Skia 中潜在的内存安全问题
3. **性能验证**: 确保 Skia 在使用 PartitionAlloc 时不出现性能退化

## 构建

```bash
# GN 构建
ninja -C out/Release
```

需要在 GN 参数中启用 PartitionAlloc 支持才能编译激活此功能。

## 与其他模块的关系

- **tests/**: Skia 测试框架在初始化时可调用此模块
- **third_party/partition_alloc/**: PartitionAlloc 源码
- **src/core/SkMemory_malloc.cpp**: Skia 默认的内存分配实现
