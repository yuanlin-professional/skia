# TestSupport

> 源文件
> - tools/partition_alloc/TestSupport.h
> - tools/partition_alloc/TestSupport.cpp

## 概述

TestSupport 是一个用于测试环境的工具模块,提供了在 Skia 测试中启用和配置 PartitionAlloc 分配器的支持功能。该模块封装了 PartitionAlloc 的初始化逻辑,使测试代码能够方便地使用 Chromium 的内存分配器进行测试。

PartitionAlloc 是 Chromium 开发的高性能内存分配器,具有安全性和性能优势。本模块为 Skia 的测试框架提供了一个简洁的接口来启用这个分配器。

## 架构位置

TestSupport 位于 Skia 项目的测试工具层,具体架构位置如下:

```
skia/
├── tools/                          # 工具目录
│   └── partition_alloc/           # PartitionAlloc 相关工具
│       ├── TestSupport.h          # 测试支持头文件
│       └── TestSupport.cpp        # 测试支持实现
├── tests/                         # 测试代码(使用方)
└── include/                       # 公共头文件
```

该模块属于测试基础设施层,为测试代码提供内存分配器配置支持。它依赖于 Chromium 的 PartitionAlloc 库,这是一个外部依赖。

## 主要类与结构体

### 命名空间 skiatest

该模块中的所有功能都定义在 `skiatest` 命名空间下,与 Skia 的测试框架保持一致。

### 核心函数

**InitializePartitionAllocForTesting()**
- **功能**: 为测试环境初始化 PartitionAlloc 分配器
- **返回值**: void
- **用途**: 在测试开始前调用,配置并启用 PartitionAlloc 作为内存分配器
- **特点**: 仅在支持 allocator shim 的平台上生效

## 公共 API 函数

### InitializePartitionAllocForTesting()

```cpp
void InitializePartitionAllocForTesting();
```

这是模块提供的唯一公共 API,用于初始化 PartitionAlloc 分配器。

**使用场景**:
- 在测试套件初始化阶段调用
- 需要测试内存分配行为时使用
- 评估 PartitionAlloc 性能影响时使用

**行为**:
- 如果编译时启用了 `USE_ALLOCATOR_SHIM`,则配置 PartitionAlloc
- 启用线程缓存(如果支持),以提升性能
- 如果未启用 allocator shim,函数为空操作

## 内部实现细节

### 条件编译

模块大量使用条件编译来处理不同平台和配置:

```cpp
#if PA_BUILDFLAG(USE_ALLOCATOR_SHIM)
    // 实际的初始化代码
#endif
```

这个宏控制是否编译 PartitionAlloc 初始化代码。只有在支持 allocator shim 的平台上才会执行实际操作。

### 初始化步骤

`InitializePartitionAllocForTesting()` 内部执行两个关键步骤:

1. **配置分区 (ConfigurePartitionsForTesting)**
   - 调用 `allocator_shim::ConfigurePartitionsForTesting()`
   - 设置 PartitionAlloc 的基本配置
   - 为测试环境优化内存分区

2. **启用线程缓存 (EnableThreadCacheIfSupported)**
   - 调用 `PartitionAllocMalloc::Allocator()->EnableThreadCacheIfSupported()`
   - 如果平台支持,启用线程本地缓存
   - 减少锁竞争,提升多线程性能

### 平台支持

模块通过 PartitionAlloc 的构建标志系统来检测平台支持:
- `PA_BUILDFLAG(USE_ALLOCATOR_SHIM)`: 检查是否支持分配器替换
- 不支持的平台上,函数为空实现,不会有运行时开销

## 依赖关系

### 外部依赖

1. **PartitionAlloc 库**
   - `partition_alloc/buildflags.h`: 构建标志定义
   - `partition_alloc/shim/allocator_shim.h`: 分配器 shim 接口
   - `partition_alloc/shim/allocator_shim_default_dispatch_to_partition_alloc.h`: PartitionAlloc 分发器

### 依赖图

```
TestSupport
    ↓
PartitionAlloc Buildflags
    ↓
Allocator Shim (条件依赖)
    ↓
PartitionAllocMalloc Allocator
```

### 被依赖方

- Skia 测试框架
- 单元测试套件
- 性能基准测试

## 设计模式与设计决策

### 简单工厂模式

模块采用简单的函数接口,隐藏了 PartitionAlloc 初始化的复杂性。测试代码只需调用一个函数,无需关心平台差异和配置细节。

### 条件编译策略

使用条件编译而非运行时检查的设计决策:
- **优点**: 零运行时开销,不支持的平台完全不包含相关代码
- **权衡**: 需要在编译时确定支持性,无法动态切换

### 命名空间隔离

将功能放在 `skiatest` 命名空间下:
- 明确表明这是测试专用功能
- 避免与生产代码混淆
- 与 Skia 测试框架的命名约定保持一致

### 最小化接口原则

只暴露一个函数,保持 API 表面最小:
- 降低使用复杂度
- 便于维护和演化
- 减少错误使用的可能性

## 性能考量

### 启用线程缓存

调用 `EnableThreadCacheIfSupported()` 是关键的性能优化:
- **线程缓存**: 每个线程维护本地内存池
- **减少锁竞争**: 大部分分配/释放无需全局锁
- **提升吞吐量**: 多线程测试性能显著提升

### 零开销抽象

在不支持 PartitionAlloc 的平台上:
- 函数编译为空
- 无运行时检查开销
- 无额外的二进制大小增加

### 初始化开销

该函数设计为在测试启动阶段调用一次:
- 初始化开销被均摊到整个测试运行周期
- 避免在热路径上进行初始化
- 一次配置,多次使用

## 相关文件

### 头文件
- `tools/partition_alloc/TestSupport.h`: 公共接口定义

### 实现文件
- `tools/partition_alloc/TestSupport.cpp`: 功能实现

### PartitionAlloc 依赖
- `partition_alloc/buildflags.h`: 构建配置
- `partition_alloc/shim/allocator_shim.h`: 分配器替换接口
- `partition_alloc/shim/allocator_shim_default_dispatch_to_partition_alloc.h`: PartitionAlloc 实现

### 使用示例位置
- `tests/`: Skia 单元测试
- 各种测试工具和基准测试程序

TestSupport 模块虽然代码量小,但为 Skia 测试框架提供了重要的内存分配器配置能力,使得测试能够在更真实的内存管理环境下运行,有助于发现潜在的内存问题。
