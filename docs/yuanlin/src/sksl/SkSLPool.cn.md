# SkSL::Pool - SkSL 内存池

> 源文件: `src/sksl/SkSLPool.h`, `src/sksl/SkSLPool.cpp`

## 概述

`SkSL::Pool` 是 SkSL（Skia 着色语言）编译器中的自定义内存分配器，专为 SkSL 程序的编译和运行时对象分配设计。它通过线程局部存储（TLS）将内存池绑定到当前线程，并提供全局的 `AllocMemory` / `FreeMemory` 接口。所有继承自 `Poolable` 的类将自动使用内存池进行分配，而非系统默认分配器。

## 架构位置

```
SkSL::Pool
  └── SkSL::MemoryPool (底层内存池实现)

SkSL::Poolable (混入基类)
  └── SkSL IR 节点 (表达式、语句等)

SkSL::AutoAttachPoolToThread (RAII 线程绑定)
```

该模块位于 SkSL 编译器基础设施的最底层，为整个 IR 树提供内存管理。

## 主要类与结构体

### `Pool`
- 管理一个 `SkSL::MemoryPool` 实例
- 通过线程局部变量实现线程绑定
- 提供静态的内存分配/释放接口

### `Poolable`
- 重写 `operator new` 和 `operator delete`
- 继承此类的对象自动使用内存池分配
- 用于 SkSL 的所有 IR 节点

### `AutoAttachPoolToThread`
- RAII 辅助类
- 构造时附加池到线程，析构时分离
- 简化池的生命周期管理

## 公共 API 函数

### Pool 管理
- `static Create()`: 创建新的内存池
- `attachToThread()`: 将池绑定到当前线程（断言当前没有已绑定的池）
- `detachFromThread()`: 从线程分离池
- `static IsAttached()`: 检查当前线程是否有绑定的池

### 内存操作
- `static AllocMemory(size_t size)`: 从线程池分配内存；如果没有绑定的池，使用系统分配器
- `static FreeMemory(void* ptr)`: 释放内存到线程池；如果没有绑定的池，使用系统释放器

## 内部实现细节

### 线程局部存储
```cpp
static thread_local MemoryPool* sMemPool = nullptr;
```
通过 getter/setter 函数访问 TLS 变量，确保所有内存操作路由到正确的池。

### 回退机制
当没有池绑定到线程时，`AllocMemory` 和 `FreeMemory` 回退到全局的 `::operator new` 和 `::operator delete`。这确保了 `Poolable` 对象在池生命周期之外仍能正常分配/释放。

### 析构安全
析构函数检查池是否仍绑定到线程，如果是则触发调试断言并解除绑定，防止悬挂指针。

### 调试日志
通过 `SkVLOG` 宏（默认禁用）可以启用详细的分配/释放日志，用于调试内存问题。

## 依赖关系

- `SkSL::MemoryPool`: 底层内存池实现
- `SkTypes.h`: 调试断言和宏

## 设计模式与设计决策

### 池化分配模式
优化频繁分配/释放小对象（IR 节点）的场景，显著减少系统分配器的调用开销。

### 线程局部绑定
每个编译线程使用独立的池，避免多线程竞争，无需加锁。

### 混入类 (Poolable)
通过 C++ 的运算符重载机制，透明地将内存分配路由到池中，对使用者完全透明。

### RAII 生命周期
`AutoAttachPoolToThread` 确保池的 attach/detach 配对，防止忘记分离。

## 性能考量

- 内存池的分配速度远快于系统 malloc（通常是简单的指针推进）
- 减少了内存碎片（池中的小对象连续存储）
- TLS 访问在现代平台上非常高效（通常是单次内存读取）
- 所有 IR 节点在池中分配，编译结束后一次性释放，避免逐个析构的开销
- 回退到系统分配器确保了正确性，但牺牲了性能（仅在异常路径发生）

## 相关文件

- `src/sksl/SkSLMemoryPool.h`: 底层内存池实现
- `src/sksl/SkSLCompiler.h` / `.cpp`: SkSL 编译器（内存池的主要用户）
- `src/sksl/ir/SkSLExpression.h`: 继承 `Poolable` 的 IR 节点示例
