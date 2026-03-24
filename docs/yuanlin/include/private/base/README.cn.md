# include/private/base - Skia 私有基础设施头文件

## 概述

`include/private/base` 目录包含 Skia 最底层的基础设施头文件，提供了平台抽象、内存管理、线程同步、数学工具、容器类型和编译器属性等核心功能。这些头文件是 Skia 整个代码库的基石，几乎所有其他 Skia 模块都直接或间接依赖于此目录中的定义。

该目录的设计理念是提供轻量级、高效的基础工具，避免对 C++ 标准库的过度依赖。例如，`SkMutex` 使用自定义信号量实现而非 `std::mutex`，`skia_private::TArray` 提供了针对 Skia 使用模式优化的动态数组，`SkFixed` 定义了 16.16 定点数算术运算。这些自定义实现确保了 Skia 在各种嵌入环境（包括受限的标准库实现）中的可移植性。

本目录中的文件按功能可分为以下几类：平台检测与配置（`SkFeatures.h`、`SkLoadUserConfig.h`、`SkAPI.h`）、内存管理（`SkMalloc.h`、`SkContainers.h`）、线程与同步（`SkMutex.h`、`SkSemaphore.h`、`SkOnce.h`、`SkThreadID.h`）、数学与数值（`SkFixed.h`、`SkFloatingPoint.h`、`SkMath.h`）以及容器与模板（`SkTArray.h`、`SkTDArray.h`、`SkDeque.h`、`SkTemplates.h`）。

这些头文件虽然标记为私有，但在 Skia 内部被极为广泛地使用，构成了 Skia 构建系统和运行时的基础层。

## 目录结构

```
include/private/base/
├── SingleOwner.h          # 单所有者线程安全验证（调试专用）
├── SkAlign.h              # 内存对齐工具
├── SkAlignedStorage.h     # 对齐存储模板
├── SkAnySubclass.h        # 类型擦除的子类内联存储
├── SkAPI.h                # SK_API / SK_SPI 导出宏定义
├── SkASAN.h               # AddressSanitizer 标注宏
├── SkAssert.h             # 断言宏（SkASSERT、SK_ABORT 等）
├── SkAttributes.h         # 编译器属性宏（SK_ALWAYS_INLINE 等）
├── SkContainers.h         # 容器内存分配工具
├── SkCPUTypes.h           # CPU 架构类型检测
├── SkDebug.h              # 调试输出（SkDebugf）
├── SkDeque.h              # 双端队列容器
├── SkFeatures.h           # 平台特性检测（OS、字节序、CPU）
├── SkFixed.h              # 16.16 定点数类型与运算
├── SkFloatingPoint.h      # 浮点数工具函数
├── SkLoadUserConfig.h     # 用户配置加载与验证
├── SkLog.h                # 日志宏
├── SkLogPriority.h        # 日志优先级定义
├── SkMacros.h             # 通用宏（SK_ARRAY_COUNT 等）
├── SkMalloc.h             # 内存分配函数（sk_malloc、sk_free）
├── SkMath.h               # 数学工具函数
├── SkMutex.h              # 互斥锁实现
├── SkNoncopyable.h        # 不可复制基类
├── SkOnce.h               # 单次初始化工具
├── SkPoint_impl.h         # 点类型的内部实现
├── SkSafe32.h             # 32位安全整数运算
├── SkSemaphore.h          # 信号量实现
├── SkSpan_impl.h          # Span（范围视图）内部实现
├── SkTArray.h             # 动态数组模板 TArray
├── SkTDArray.h            # 传统动态数组（POD 类型）
├── SkTemplates.h          # 通用模板工具集
├── SkTFitsIn.h            # 类型范围检查模板
├── SkThreadAnnotations.h  # 线程安全注解宏
├── SkThreadID.h           # 线程 ID 获取
├── SkTLogic.h             # 类型逻辑工具（same_cv_t 等）
├── SkTo.h                 # 安全类型转换（SkToInt、SkToU8 等）
├── SkTPin.h               # 值范围钳制模板
├── SkTypeTraits.h         # 类型特征（可平凡重定位检测）
└── BUILD.bazel            # Bazel 构建配置
```

## 关键类与函数

### 内存管理
- **`sk_malloc_flags()`**: 核心内存分配函数，支持 `SK_MALLOC_ZERO_INITIALIZE`（零初始化）和 `SK_MALLOC_THROW`（失败时抛异常）标志。
- **`sk_free()`**: 释放由 `sk_malloc` 分配的内存。
- **`sk_realloc_throw()`**: 重新分配内存，失败时终止程序。
- **`sk_malloc_size()`**: 返回实际分配的内存块大小。

### 线程与同步
- **`SkMutex`**: 基于 `SkSemaphore` 的互斥锁，提供 `acquire()`/`release()` 和调试模式下的所有权检查。
- **`SkAutoMutexExclusive`**: RAII 风格的互斥锁守卫。
- **`SkSemaphore`**: 轻量级信号量，结合用户空间原子计数器和操作系统信号量，基于 Preshing 的部分自旋策略。
- **`SkOnce`**: 确保函数只执行一次的线程安全工具。
- **`skgpu::SingleOwner`**: 调试工具，验证对象仅从单一线程被访问。

### 容器
- **`skia_private::TArray<T>`**: Skia 的主要动态数组，支持通过 `MEM_MOVE` 参数控制元素移动方式（`memcpy` 或移动构造函数），针对可平凡重定位类型自动优化。
- **`SkDeque`**: 双端队列，以链表方式管理固定大小元素的内存块。
- **`SkSpan<T>`**: 非拥有的连续内存范围视图。

### 数学与数值
- **`SkFixed`**: 16.16 定点数类型（`int32_t`），提供 `SkFixedToFloat`/`SkFloatToFixed` 转换宏。
- **`SkIsNaN()`/`SkIsFinite()`**: 浮点数 NaN 和有限性检查，针对 `clang-cl` 生成更优代码。
- **`sk_float_round()`**: 通过先转换为 `double` 进行四舍五入以避免浮点精度问题。

### 断言与调试
- **`SkASSERT()`**: 调试模式断言，release 模式下为空操作。
- **`SK_ABORT()`**: 不可恢复错误的终止函数。
- **`SK_ASSUME()`**: 编译器优化提示，告知编译器某个条件始终为真。
- **`SK_LIKELY`/`SK_UNLIKELY`**: 分支预测提示。

### 平台与配置
- **`SkFeatures.h`**: 自动检测目标平台（`SK_BUILD_FOR_WIN`、`SK_BUILD_FOR_ANDROID` 等）、CPU 字节序和架构。
- **`SkAPI.h`**: 定义 `SK_API`（公共符号导出）和 `SK_SPI`（半私有接口导出）。
- **`SkLoadUserConfig.h`**: 加载用户配置文件并验证 `SK_DEBUG`/`SK_RELEASE` 和字节序配置的一致性。

## 依赖关系

- **上游依赖**: C/C++ 标准库头文件（`<cstdint>`、`<atomic>`、`<algorithm>` 等）、`include/config/SkUserConfig.h`（用户自定义配置）
- **下游消费者**: `include/core/`（几乎所有公共核心头文件）、`include/private/`（所有私有头文件）、`src/`（所有源代码实现）
- **关键依赖链**: `SkFeatures.h` -> `SkLoadUserConfig.h` -> `SkAPI.h` -> `SkDebug.h` -> `SkAssert.h`

## 相关文档与参考

- [Skia 构建配置指南](https://skia.org/docs/user/build/) - 了解如何通过 `SkUserConfig.h` 自定义构建
- [Preshing 信号量文章](http://preshing.com/20150316/semaphores-are-surprisingly-versatile/) - `SkSemaphore` 的设计灵感来源
- [Clang Thread Safety Analysis](https://clang.llvm.org/docs/ThreadSafetyAnalysis.html) - `SkThreadAnnotations.h` 中注解的参考
- `include/config/SkUserConfig.h` - 用户可自定义的构建配置
- `include/private/` - 父目录私有头文件文档
- `include/core/SkTypes.h` - 包含本目录多个基础头文件的公共入口
