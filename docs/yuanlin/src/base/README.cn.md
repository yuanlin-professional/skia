# src/base - Skia 基础工具库

## 概述

`src/base` 是 Skia 图形库的最底层基础模块，提供了整个 Skia 运行所需的核心工具类和基础设施。该目录包含的文件不属于公共 API 的一部分（公共 API 的基础头文件位于 `include/private/base`），而是 Skia 内部实现专用的私有基础组件。按照 Skia 的分层设计原则，本目录中的文件仅依赖系统头文件或 `base` 包内的其他文件，不依赖 Skia 的上层模块。

本模块的历史可以追溯到 Skia 的早期开发阶段。许多文件最初是 Android Open Source Project 的一部分（如 `SkRandom.h`、`SkTSort.h`、`SkTSearch.h` 等，版权标注为 2006 年），随着 Skia 从 Android 独立为通用的 2D 图形库后，这些基础组件被不断优化和重构。2016 年前后，Google 引入了 `SkArenaAlloc` 等现代化的内存分配器；2019-2023 年间，`SkBlockAllocator`、`SkBezierCurves`、`SkCubics` 等新组件相继加入，反映了 Skia 在高性能内存管理和精确数学计算方面的持续演进。

从功能上划分，`src/base` 涵盖了五大核心领域：**内存管理**（Arena 分配器、块分配器、自动内存管理）、**数据结构**（优先队列、双向链表、块列表、Zip 迭代器）、**数学与数值计算**（贝塞尔曲线、二次/三次方程求解、安全数学运算、位操作）、**并发原语**（自旋锁、共享互斥锁、信号量）以及**通用工具**（Base64 编解码、UTF 编码转换、字节序处理、随机数生成等）。

该模块的设计哲学是"零外部依赖、最小化开销"。所有组件仅依赖 C++ 标准库和操作系统原语，确保 Skia 能在各种平台（Windows、macOS、Linux、Android、iOS、WebAssembly）上保持一致的行为。模块中大量使用了模板元编程和编译期计算来消除运行时开销，体现了 Skia 团队对性能的极致追求。

## 架构图

```
+============================================================================+
|                            src/base 基础工具层                               |
+============================================================================+
|                                                                            |
|  +-------------------+   +-------------------+   +----------------------+  |
|  |   内存管理子系统    |   |   数据结构子系统    |   |   数学/数值计算子系统   |  |
|  |                   |   |                   |   |                      |  |
|  | SkArenaAlloc      |   | SkTBlockList      |   | SkBezierCurves       |  |
|  | SkArenaAllocList  |   | SkTDPQueue        |   | SkCubics             |  |
|  | SkBlockAllocator  |   | SkTInternalLList  |   | SkQuads              |  |
|  | SkAutoMalloc      |   | SkZip             |   | SkSafeMath           |  |
|  | SkContainers      |   | SkFixedArray      |   | SkMathPriv           |  |
|  +-------------------+   +-------------------+   | SkHalf               |  |
|                                                   | SkFloatBits          |  |
|  +-------------------+   +-------------------+   +----------------------+  |
|  |   并发原语子系统    |   |   通用工具子系统    |                            |
|  |                   |   |                   |                            |
|  | SkSpinlock        |   | SkBase64          |                            |
|  | SkSharedMutex     |   | SkUTF             |                            |
|  | SkSemaphore       |   | SkEndian          |                            |
|  |                   |   | SkRandom          |                            |
|  +-------------------+   | SkUtils           |                            |
|                          | SkNoDestructor    |                            |
|  +-------------------+   | SkScopeExit       |                            |
|  |  平台抽象子系统     |   | SkTLazy           |                            |
|  |                   |   | SkTSearch/SkTSort  |                            |
|  | SkLeanWindows     |   | SkStringView      |                            |
|  | SkMSAN            |   | SkTime            |                            |
|  | SkTime            |   | SkVx (SIMD)       |                            |
|  +-------------------+   +-------------------+                            |
|                                                                            |
+============================================================================+
                    |                          ^
                    |  依赖                     |  被依赖
                    v                          |
    +----------------------------+   +---------------------------+
    | include/private/base       |   | src/core, src/gpu,        |
    | (公共基础头文件)             |   | src/pathops, modules/...  |
    | SkAssert, SkSpan, SkMalloc |   | (Skia 上层模块)            |
    | SkMath, SkNoncopyable ...  |   +---------------------------+
    +----------------------------+
```

## 目录结构

`src/base` 目录是一个扁平结构，没有子目录。所有文件直接位于该目录下，共包含约 66 个文件（含 `.h` 和 `.cpp`）。以下按功能类别组织：

### 内存管理
| 文件 | 说明 |
|------|------|
| `SkArenaAlloc.h/.cpp` | Arena 分配器，支持栈上预分配和斐波那契增长策略 |
| `SkArenaAllocList.h` | 基于 Arena 分配器的单链表 |
| `SkBlockAllocator.h/.cpp` | 低级块分配器，支持多种增长策略（固定、线性、斐波那契、指数） |
| `SkAutoMalloc.h` | 自动管理的堆内存块，支持栈上小缓冲区优化 |
| `SkContainers.cpp` | 容器相关的内存分配辅助函数 |
| `SkMalloc.cpp` | `sk_malloc` / `sk_free` 等底层内存分配封装 |

### 数据结构
| 文件 | 说明 |
|------|------|
| `SkTBlockList.h` | 基于块分配器的类型化列表，兼具数组和链表特性 |
| `SkTDPQueue.h` | 模板化优先队列（最小/最大堆） |
| `SkTInternalLList.h` | 侵入式双向链表 |
| `SkFixedArray.h` | 固定容量数组，适合编译期已知上限的场景 |
| `SkZip.h` | 并行迭代多个容器的 Zip 工具 |
| `SkDeque.cpp` | 双端队列实现 |
| `SkTDArray.cpp` | 动态数组辅助实现 |
| `SkBuffer.h/.cpp` | 轻量级内存读写缓冲区 |

### 数学与数值计算
| 文件 | 说明 |
|------|------|
| `SkBezierCurves.h/.cpp` | 贝塞尔曲线（二次和三次）求值、细分与求交 |
| `SkCubics.h/.cpp` | 三次方程求根（实数根、有效范围根、二分法求根） |
| `SkQuads.h/.cpp` | 二次方程求根，基于 Kahan 的高精度判别式计算 |
| `SkSafeMath.h/.cpp` | 溢出安全的算术运算 |
| `SkMathPriv.h/.cpp` | 私有数学工具：CLZ/CTZ/PopCount、整数平方根、2 的幂运算 |
| `SkHalf.h/.cpp` | 16 位半精度浮点数支持 |
| `SkFloatBits.h` | 浮点数与位模式之间的转换 |
| `SkFloatingPoint.cpp` | 浮点数辅助运算 |

### 并发原语
| 文件 | 说明 |
|------|------|
| `SkSpinlock.h/.cpp` | 轻量级自旋锁，基于原子操作 |
| `SkSharedMutex.h/.cpp` | 读写锁，支持共享读和独占写 |
| `SkSemaphore.cpp` | 信号量实现 |
| `SkThreadID.cpp` | 线程 ID 获取 |

### 编码与字符串
| 文件 | 说明 |
|------|------|
| `SkBase64.h/.cpp` | Base64 编码和解码 |
| `SkUTF.h/.cpp` | UTF-8/UTF-16/UTF-32 编码转换与验证 |
| `SkStringView.h` | `std::string_view` 的 C++20/23 扩展（starts_with、ends_with、contains） |

### SIMD 向量
| 文件 | 说明 |
|------|------|
| `SkVx.h` | `skvx::Vec<N,T>` SIMD 向量库，支持 SSE/AVX/NEON/WASM SIMD/LSX |

### 通用工具
| 文件 | 说明 |
|------|------|
| `SkRandom.h` | Marsaglia multiply-with-carry 伪随机数生成器 |
| `SkEndian.h` | 字节序转换（16/32/64 位，大/小端） |
| `SkUtils.h/.cpp` | `sk_unaligned_load`/`sk_unaligned_store`/`sk_bit_cast` 等底层工具 |
| `SkNoDestructor.h` | 阻止静态变量析构，避免全局析构器问题 |
| `SkScopeExit.h` | RAII 作用域退出回调（类似 Go 的 defer） |
| `SkTLazy.h` | 延迟初始化包装器和写时复制包装器 |
| `SkTSearch.h/.cpp` | 模板化二分查找 |
| `SkTSort.h` | 堆排序和内省排序 |
| `SkRectMemcpy.h` | 矩形区域内存拷贝（逐行拷贝） |
| `SkBitmaskEnum.h` | 枚举类型的位掩码运算符重载 |
| `SkEnumBitMask.h` | 类型安全的枚举位掩码包装器 |
| `SkTime.h/.cpp` | 单调时钟（纳秒级） |

### 平台与调试
| 文件 | 说明 |
|------|------|
| `SkLeanWindows.h` | 精简的 Windows.h 引入（避免宏污染） |
| `SkMSAN.h` | MemorySanitizer 接口封装 |
| `SkDebug.cpp` | 调试输出 |
| `SkLog.cpp` | 日志功能 |
| `BUILD.bazel` | Bazel 构建配置 |

## 关键类与函数

### SkArenaAlloc
- **文件**: `SkArenaAlloc.h` / `SkArenaAlloc.cpp`
- **职责**: 高性能 Arena 分配器。在分配器生命周期结束时统一销毁所有已分配对象。设计目标是最小化底层的堆分配次数。
- **关键方法**:
  - `make<T>(args...)` - 在 Arena 中构造一个 T 对象，返回指针
  - `makeArray<T>(count)` - 分配并零初始化 T 类型数组
  - `makeArrayDefault<T>(count)` - 分配默认初始化的数组（基本类型不初始化）
  - `makeArrayCopy<T>(span)` - 复制一个 SkSpan 到 Arena 中
  - `makeBytesAlignedTo(size, align)` - 分配指定对齐的原始字节
- **设计要点**:
  - 使用斐波那契数列（`SkFibBlockSizes`）作为块增长策略，避免严格倍增导致的内存浪费
  - 对 POD 类型零开销，非 POD 类型每对象仅 4 字节开销
  - 支持通过 `SkSTArenaAlloc<N>` 在栈上预留 N 字节的内联存储
  - `SkArenaAllocWithReset` 子类支持重置，可重用分配器

### SkBlockAllocator
- **文件**: `SkBlockAllocator.h` / `SkBlockAllocator.cpp`
- **职责**: 低级块分配器，提供块内空间预留、调整和释放的原语。建议由更高层的分配器（如 `SkTBlockList`）封装使用。
- **关键方法**:
  - `allocate<Align, Padding>(size)` - 在当前块或新块中分配指定对齐的空间
  - `Block::avail<Align, Padding>()` - 查询当前块的可用空间
  - `Block::ptr(offset)` - 将块内偏移量转换为可用指针
  - `Block::release(start, end)` - 释放块内指定范围
- **增长策略** (`GrowthPolicy` 枚举):
  - `kFixed` - 固定大小
  - `kLinear` - 线性增长（N * 块数）
  - `kFibonacci` - 斐波那契增长
  - `kExponential` - 指数增长（2^块数 * N）
- **设计要点**: 单次分配上限为 512MB，所有内部操作使用 `int` 类型以避免溢出检查

### SkTBlockList
- **文件**: `SkTBlockList.h`
- **职责**: 基于 `SkBlockAllocator` 的类型化列表容器，结合了数组和链表的优势。
- **关键方法**:
  - `push_back()` / `emplace_back()` - O(1) 尾部追加
  - `pop_back()` - O(1) 尾部删除
  - `front()` / `back()` - O(1) 首尾访问
  - `reset()` - 清空所有元素
  - `concat()` - O(B) 合并另一个列表
- **复杂度**: 追加/删除 O(1)，随机访问 O(N/B)，迭代每步 O(1)

### skvx::Vec (SkVx)
- **文件**: `SkVx.h`
- **职责**: Skia 的 SIMD 向量库，是 `SkNx<N,T>` 的 v1.5 后继者。利用 Clang/GCC 向量扩展和平台特定内联函数实现高性能向量运算。
- **关键特性**:
  - `Vec<N,T>` 始终具有 `N*sizeof(T)` 的大小和对齐，可安全跨翻译单元使用
  - 支持 SSE/SSE4.1/AVX、ARM NEON、WebAssembly SIMD、LoongArch LSX/LASX
  - 通过 `SKVX_ALWAYS_INLINE` 强制内联避免 ODR 违规
  - 提供 `skvx::from_half` / `skvx::to_half` 等半精度浮点数向量化转换

### SkSafeMath
- **文件**: `SkSafeMath.h` / `SkSafeMath.cpp`
- **职责**: 提供溢出检测的安全算术运算，是运行时安全检查的关键组件。
- **关键方法**:
  - `mul(x, y)` - 安全的 `size_t` 乘法，自动选择 32/64 位实现
  - `add(x, y)` - 安全加法
  - `addInt(a, b)` / `mulInt(x, y)` - 有符号整数的安全加法和乘法
  - `alignUp(x, alignment)` - 安全的对齐向上取整
  - `castTo<TDst>(value)` - 带范围检查的类型转换
  - `ok()` - 检查整条运算链是否发生了溢出
- **静态方法**: `Add()`、`Mul()`、`Align4()` 提供饱和运算（溢出时返回最大值）

### SkBezierCubic / SkBezierQuad
- **文件**: `SkBezierCurves.h` / `SkBezierCurves.cpp`
- **职责**: 贝塞尔曲线的数学运算，包括曲线求值、细分和水平线求交。
- **关键方法**:
  - `SkBezierCubic::EvalAt(curve, t)` - 计算三次贝塞尔曲线在参数 t 处的坐标
  - `SkBezierCubic::Subdivide(curve, t, twoCurves)` - 在参数 t 处将曲线细分为两段
  - `SkBezierCubic::ConvertToPolynomial(curve, yValues)` - 转换为多项式表示
  - `SkBezierCubic::IntersectWithHorizontalLine()` - 与水平线求交
  - `SkBezierQuad::IntersectWithHorizontalLine()` - 二次贝塞尔与水平线求交

### SkCubics
- **文件**: `SkCubics.h` / `SkCubics.cpp`
- **职责**: 三次方程 `A*t^3 + B*t^2 + C*t + D = 0` 的求根。
- **关键方法**:
  - `RootsReal(A, B, C, D, solution)` - 求所有实数根（至多 3 个）
  - `RootsValidT(A, B, C, D, solution)` - 求 [0, 1] 范围内的实数根
  - `BinarySearchRootsValidT()` - 使用二分法求根，精度更高但速度较慢
  - `EvalAt(A, B, C, D, t)` - 使用 Horner 法（`std::fma` 链）求值

### SkQuads
- **文件**: `SkQuads.h` / `SkQuads.cpp`
- **职责**: 二次方程 `A*t^2 + B*t + C = 0` 的求根，采用 W. Kahan 的高精度算法。
- **关键方法**:
  - `Discriminant(A, B, C)` - 计算精确到 2 位的判别式
  - `Roots(A, B, C)` - 返回判别式和两个根
  - `RootsReal(A, B, C, solution)` - 返回至多 2 个实数根
  - `EvalAt(A, B, C, t)` - 求值

### SkSharedMutex
- **文件**: `SkSharedMutex.h` / `SkSharedMutex.cpp`
- **职责**: 读写锁实现，类似 `pthread_rwlock`。Release 构建使用高性能的无锁实现（源自 Preshing 的方案），Debug 构建使用带调试信息的版本。
- **关键方法**:
  - `acquire()` / `release()` - 独占（写）锁的获取和释放
  - `acquireShared()` / `releaseShared()` - 共享（读）锁的获取和释放
  - `assertHeld()` / `assertHeldShared()` - 断言锁已持有
- **辅助类**: `SkAutoSharedMutexExclusive`、`SkAutoSharedMutexShared` 提供 RAII 风格的锁管理

### SkSpinlock
- **文件**: `SkSpinlock.h` / `SkSpinlock.cpp`
- **职责**: 基于原子操作的轻量级自旋锁。
- **关键方法**:
  - `acquire()` - 获取锁（fast path: 单次原子交换；slow path: 回退到离线自旋循环）
  - `tryAcquire()` - 尝试获取锁，失败立即返回 false
  - `release()` - 释放锁
- **辅助类**: `SkAutoSpinlock` 提供 RAII 风格的锁管理

### SkRandom
- **文件**: `SkRandom.h`
- **职责**: 基于 Marsaglia multiply-with-carry "mother of all" 算法的伪随机数生成器。无全局状态，支持多实例独立使用。
- **关键方法**:
  - `nextU()` - 返回 32 位无符号随机数
  - `nextF()` - 返回 [0, 1) 范围的浮点数
  - `nextRangeU(min, max)` - 返回 [min, max] 范围的无符号整数
  - `nextBool()` - 返回随机布尔值
  - `setSeed(seed)` - 使用 LCG 重置种子

### SkNoDestructor
- **文件**: `SkNoDestructor.h`
- **职责**: 阻止类型 T 的析构函数在程序退出时运行。用于解决 Chromium/Skia 禁止全局构造器和析构器的约束。
- **设计要点**:
  - 内部使用 `alignas(T) std::byte fStorage[sizeof(T)]` 存储对象
  - 在 Leak Sanitizer 模式下保留额外指针以辅助可达性分析
  - 仅用于函数局部静态变量或全局 `constinit` 变量

### SkTLazy / SkTCopyOnFirstWrite
- **文件**: `SkTLazy.h`
- **职责**: `SkTLazy<T>` 提供延迟初始化，内部基于 `std::optional`。`SkTCopyOnFirstWrite<T>` 实现写时复制语义。
- **关键方法**:
  - `SkTLazy::init(args...)` - 原地构造对象
  - `SkTLazy::isValid()` - 检查对象是否已初始化
  - `SkTCopyOnFirstWrite::writable()` - 首次调用时复制原始对象，返回可写指针

### SkZip
- **文件**: `SkZip.h`
- **职责**: 允许并行遍历多个容器，类似 Python 的 `zip()` 函数。迭代器和 `operator[]` 返回元组。
- **关键方法**:
  - `operator[](i)` - 返回所有容器第 i 个元素的元组
  - `begin()` / `end()` - 支持范围 for 循环
  - `first(n)` / `last(n)` / `subspan(offset, count)` - 子范围访问
- **辅助函数**: `SkMakeZip(ts...)` 自动推导类型和大小

### SkUTF
- **文件**: `SkUTF.h` / `SkUTF.cpp`
- **职责**: Unicode 编码处理工具集，支持 UTF-8、UTF-16、UTF-32 之间的转换。
- **关键方法**:
  - `CountUTF8()` / `CountUTF16()` / `CountUTF32()` - 计算 Unicode 码点数
  - `NextUTF8()` / `NextUTF16()` / `NextUTF32()` - 逐码点遍历
  - `ToUTF8()` / `ToUTF16()` - 码点到编码序列的转换
  - `UTF8ToUTF16()` / `UTF16ToUTF8()` - 批量编码转换

## 依赖关系

### 上游依赖（本模块依赖的模块）

- **`include/private/base`** - 公共基础头文件集合，提供以下核心类型和工具：
  - `SkAssert.h` - 断言宏（`SkASSERT`、`SkASSERT_RELEASE`）
  - `SkSpan_impl.h` - `SkSpan<T>` 视图类型
  - `SkMalloc.h` - `sk_malloc_throw`、`sk_free` 等内存分配原语
  - `SkNoncopyable.h` - 不可复制基类
  - `SkMath.h` - 基本数学工具
  - `SkTo.h` / `SkTFitsIn.h` - 安全类型转换
  - `SkSemaphore.h` - 信号量声明
  - `SkMutex.h` - 互斥锁声明
  - `SkFeatures.h` - 平台特性检测宏
  - `SkASAN.h` - AddressSanitizer 接口
  - `SkTemplates.h` - 模板工具
  - `SkTArray.h` / `SkTDArray.h` - 动态数组
- **`@skia_user_config//:user_config`** - 用户配置（通过 Bazel 依赖引入）
- **C++ 标准库** - `<atomic>`、`<optional>`、`<type_traits>`、`<cstring>`、`<cmath>` 等
- **系统头文件** - 平台特定的 SIMD 内联函数头文件（如 `<immintrin.h>`、`<arm_neon.h>`）

### 下游被依赖（依赖本模块的模块）

根据 `BUILD.bazel` 中的 `visibility` 配置，以下模块可以依赖 `src/base`：

- **`src/` 子包** - Skia 核心实现的所有子目录（`src/core`、`src/gpu`、`src/pathops`、`src/effects` 等）
- **`modules/` 子包** - Skia 的功能模块（SkShaper、SkParagraph、Skottie 等）
- **`tests/` 子包** - 单元测试
- **`bench/` 子包** - 性能基准测试
- **`tools/` 子包** - 开发工具和示例
- **`experimental/` 子包** - 实验性功能
- **`rust/` 子包** - Rust 绑定
- **SkSL 编译器** - `skslc_srcs` 文件组被导出为 SkSL 编译器的依赖

### 外部依赖（第三方库）

本模块**不依赖任何第三方库**。这是 Skia 基础层的核心设计原则。所有功能仅依赖 C++ 标准库和操作系统原语。唯一的间接外部依赖是通过 `@skia_user_config` 引入的用户构建配置。

## 设计模式分析

### RAII 模式（资源获取即初始化）

本模块广泛使用 RAII 模式管理资源生命周期：

- **`SkAutoMalloc`** - 封装堆内存的生命周期，析构时自动调用 `sk_free`
- **`SkAutoSpinlock`** - 构造时获取锁，析构时释放
- **`SkAutoSharedMutexExclusive`** / **`SkAutoSharedMutexShared`** - 读写锁的 RAII 封装
- **`SkScopeExit`** - 通用的作用域退出回调，实现类似 Go `defer` 的功能
- **`SkArenaAlloc`** - 析构时统一销毁所有分配的对象

### 模板策略模式

通过模板参数实现编译期策略选择：

- **`SkTSearch`** - 通过模板比较函子（`LESS`）自定义搜索行为
- **`SkTDPQueue`** - 通过 `LESS` 和 `INDEX` 模板参数定制优先队列的比较逻辑和索引追踪
- **`SkTSort`** - 通过模板比较器自定义排序行为
- **`SkFibBlockSizes<kMaxSize>`** - 通过模板参数限制最大块大小

### 小缓冲区优化（SBO）

多个类使用栈上预分配缓冲区来避免小对象的堆分配：

- **`SkSTArenaAlloc<N>`** - 继承 `std::array<char, N>` 作为内联存储
- **`SkAutoSMalloc<N>`** - 内部维护 `uint32_t fStorage[kSize >> 2]` 的栈上缓冲区
- **`SkAutoAsciiToLC`** - 内置 64+1 字节的 `fStorage` 缓冲区

### 写时复制模式

- **`SkTCopyOnFirstWrite<T>`** - 初始持有 `const T*` 指针，首次调用 `writable()` 时才复制对象。这在图形管线中大量用于避免不必要的对象复制。

### 静态工厂方法模式

数学计算类使用纯静态方法提供功能：

- **`SkBezierCubic`** / **`SkBezierQuad`** - 所有方法均为静态
- **`SkCubics`** / **`SkQuads`** - 所有方法均为静态
- **`SkBase64`** - 编解码方法均为静态
- **`SkSafeMath`** 的 `Add`、`Mul`、`Align4` 为静态饱和运算

### 侵入式数据结构模式

- **`SkTInternalLList<T>`** - 要求元素类型通过 `SK_DECLARE_INTERNAL_LLIST_INTERFACE(ClassName)` 宏在类内部声明 `fPrev`/`fNext` 指针。这避免了外部节点包装的额外内存开销。

## 数据流

### 内存分配数据流

```
调用方请求分配
       |
       v
SkArenaAlloc::make<T>(args...)
       |
       +---> 检查当前块剩余空间
       |        |
       |        +-- 足够 --> 在当前块中对齐分配，移动 fCursor
       |        |
       |        +-- 不足 --> ensureSpace() 分配新块
       |                        |
       |                        v
       |                  SkFibBlockSizes::nextBlockSize()
       |                  (斐波那契增长策略计算下一块大小)
       |                        |
       |                        v
       |                  sk_malloc_throw(blockSize)
       |                        |
       |                        v
       |                  安装 NextBlock footer，链接到块链
       |
       v
  对于非 POD 类型：安装析构 footer（FooterAction + padding）
       |
       v
  placement new 构造对象，返回指针
```

### Arena 析构数据流

```
~SkArenaAlloc()
       |
       v
  RunDtorsOnBlock(fDtorCursor)
       |
       +---> 从块尾部向前遍历 Footer 链
       |        |
       |        +-- FooterAction == SkipPod --> 跳过 POD 数据
       |        |
       |        +-- FooterAction == destructor --> 调用对象析构函数 T::~T()
       |        |
       |        +-- FooterAction == array destructor --> 读取 count，逐一析构
       |        |
       |        +-- FooterAction == NextBlock --> 释放当前块，跳转到前一个块
       |
       v
  所有对象析构完成，所有堆块释放
```

### 贝塞尔曲线计算数据流

```
控制点数组 [X0,Y0, X1,Y1, X2,Y2, X3,Y3]
       |
       v
SkBezierCubic::ConvertToPolynomial(curve, yValues)
       |
       v
  多项式系数 [A, B, C, D]
       |
       v
SkCubics::RootsValidT(A, B, C, D, solutions)
       |
       +---> 使用解析公式求根
       |     或使用 BinarySearchRootsValidT 二分法求根
       |
       v
  过滤 [0, 1] 范围外的根
       |
       v
  返回有效交点参数 t 值
```

## 平台特定说明

### Windows 平台

- **`SkLeanWindows.h`** - 提供精简的 `<windows.h>` 引入方式。定义 `WIN32_LEAN_AND_MEAN` 减少不必要的 Windows API 引入，定义 `NOMINMAX` 避免 `min`/`max` 宏与 C++ 标准库冲突。使用后会清理这些宏定义以避免影响其他代码。
- **`SkUtils.h`** - 在 MSVC 32 位 x86 构建中，使用 `__vectorcall` 调用约定（`SK_FP_SAFE_ABI`）来避免 ST0 寄存器在返回浮点值时修改 NaN 位模式的问题。
- **`SkMathPriv.h`** - `SkBSwap32` 在 MSVC 上使用 `_byteswap_ulong`，其他平台使用 `__builtin_bswap32`。

### SIMD 平台适配 (SkVx.h)

`SkVx.h` 根据编译目标自动选择最佳的 SIMD 指令集：

| 平台 | 头文件 | 指令集 |
|------|--------|--------|
| x86 (AVX) | `<immintrin.h>` | AVX/AVX2 |
| x86 (SSE4.1) | `<smmintrin.h>` | SSE4.1 |
| x86 (SSE) | `<emmintrin.h>` + `<xmmintrin.h>` | SSE/SSE2 |
| ARM | `<arm_neon.h>` | NEON |
| WebAssembly | `<wasm_simd128.h>` | WASM SIMD 128 |
| LoongArch (LASX) | `<lasxintrin.h>` + `<lsxintrin.h>` | LASX + LSX |
| LoongArch (LSX) | `<lsxintrin.h>` | LSX |

可通过定义 `SKVX_DISABLE_SIMD` 宏完全禁用 SIMD，回退到纯标量实现。

### Memory Sanitizer (MSAN) 支持

- **`SkMSAN.h`** - 封装 LLVM MSAN 的 `__msan_check_mem_is_initialized` 和 `__msan_unpoison` 接口。
  - `sk_msan_assert_initialized(begin, end)` - 断言内存区域已初始化
  - `sk_msan_mark_initialized(begin, end, skbug)` - 强制标记内存为已初始化（需附带 bug 跟踪号）

### Google3 (Blaze) 构建特殊处理

- **`SkAutoMalloc.h`** - 在 `SK_BUILD_FOR_GOOGLE3` 环境下，`SkAutoSMalloc` 的栈上缓冲区上限被限制为 4KB，以适应 Google 内部更严格的栈帧大小限制。

## 构建系统

本模块使用 Bazel 构建系统，定义在 `BUILD.bazel` 中。源文件被分为两组：

1. **`skslc_srcs`** - 被 SkSL 编译器共享的源文件（11 个），包括核心分配器和数学工具。
2. **`srcs`** - 完整的源文件集（包含 `skslc_srcs` 和其余 14 个文件）。

构建目标 `base` 还依赖 `//src/ports:base_srcs` 提供平台相关的实现。

## 相关文档与参考

### Skia 内部文档
- `src/base/README.md` - 本目录的原始 README（简要说明）
- `include/private/base/README.md` - 公共基础头文件的说明

### 算法参考
- W. Kahan, "On the Cost of Floating-Point Computation Without Extra-Precise Arithmetic" - `SkQuads` 中判别式计算和求根算法的理论基础
- Jeff Preshing, ["Semaphores are Surprisingly Versatile"](http://preshing.com/20150316/semaphores-are-surprisingly-versatile/) - `SkSharedMutex` 高性能实现的算法来源
- "Numerical Recipes in C" (1992) - `SkRandom` 中 LCG 常数的参考来源

### 外部链接
- [Skia 官方文档](https://skia.org/)
- [Skia 源码仓库](https://skia.googlesource.com/skia/)
- [Unicode FAQ: UTF-16](https://unicode.org/faq/utf_bom.html#utf16-2) - `SkUTF` 中代理对检测的参考
