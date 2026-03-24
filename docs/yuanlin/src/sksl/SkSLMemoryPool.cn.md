# SkSLMemoryPool — SkSL 编译器内存池

> 源文件：[`src/sksl/SkSLMemoryPool.h`](../../src/sksl/SkSLMemoryPool.h)

## 概述

SkSLMemoryPool.h 定义了 SkSL 编译器使用的内存池类。该内存池基于 Skia 的 `SkArenaAlloc` 实现，为 SkSL 编译过程中创建的 IR（中间表示）节点提供快速的内存分配。内存池采用 arena 分配策略，分配快速但不支持单个对象的释放，所有内存在内存池销毁时一次性回收。

该文件仅 46 行，是一个简洁的头文件实现。

## 架构位置

```
SkSL 编译器
  └── 内存管理
        └── MemoryPool (SkSLMemoryPool.h)
              └── SkSTArenaAlloc (src/base/SkArenaAlloc.h)
```

`MemoryPool` 在 SkSL 编译管线中负责为编译期间产生的所有 IR 节点提供内存分配服务。通过 `ProgramSettings::fUseMemoryPool` 标志控制是否启用。

## 主要类与结构体

### `MemoryPool`

```cpp
class MemoryPool {
public:
    static std::unique_ptr<MemoryPool> Make();
    void* allocate(size_t size);
    void release(void*);
private:
    static constexpr size_t kAlignment = ...;
    SkSTArenaAlloc<65536> fArena{/*firstHeapAllocation=*/32768};
};
```

- 使用 `SkSTArenaAlloc<65536>` 作为底层分配器，初始内联缓冲区大小为 64KB
- 首次堆分配大小为 32KB
- 对齐保证：默认使用 `alignof(std::max_align_t)`，在 Emscripten 环境下强制为 8 字节

## 公共 API 函数

```cpp
static std::unique_ptr<MemoryPool> Make();
```
- 工厂方法，创建并返回一个新的内存池实例

```cpp
void* allocate(size_t size);
```
- 从内存池分配指定大小的内存块
- 返回的指针满足 `kAlignment` 对齐要求
- 委托给 `SkArenaAlloc::makeBytesAlignedTo`

```cpp
void release(void*);
```
- 空操作（no-op），`SkArenaAlloc` 不支持回收单个分配
- 所有内存在 `MemoryPool` 对象销毁时统一释放

## 内部实现细节

### 对齐处理

```cpp
#ifdef SK_FORCE_8_BYTE_ALIGNMENT
    static constexpr size_t kAlignment = 8;
#else
    static constexpr size_t kAlignment = alignof(std::max_align_t);
#endif
```

这是针对 Emscripten 的一个兼容性修复（参考 emscripten issue #10072）。由于 Skia 不使用 `long double`（16 字节），在 Emscripten 环境下将对齐降低到 8 字节是安全的。

### Arena 分配策略

`SkSTArenaAlloc<65536>` 提供 64KB 的内联存储。当内联存储耗尽后，以 32KB 为单位从堆上分配新的内存块。这种策略优化了编译过程中大量小对象的分配模式。

## 依赖关系

- `include/core/SkTypes.h` — Skia 基础类型和断言宏
- `src/base/SkArenaAlloc.h` — Arena 分配器实现
- `<memory>` — `std::unique_ptr`, `std::make_unique`

## 设计模式与设计决策

- **Arena 分配模式**：编译器 IR 节点的生命周期与编译过程绑定，适合使用 arena 分配器一次性释放所有内存。
- **工厂方法**：通过 `Make()` 静态方法创建实例，返回 `unique_ptr` 管理生命周期。
- **空 release 方法**：保留 `release` 接口但不执行操作，使调用者可以保持一致的分配/释放代码模式，同时底层使用高效的 arena 策略。

## 性能考量

1. **分配速度**：Arena 分配通常只需一次指针前进操作，远快于通用的 `malloc`/`new`。
2. **内存局部性**：连续分配的 IR 节点在内存中相邻，有利于 CPU 缓存。
3. **64KB 内联缓冲区**：大多数简单着色器的 IR 节点可完全在内联缓冲区中分配，避免堆分配。
4. **批量释放**：避免了逐个释放对象的开销，`MemoryPool` 销毁时一次性回收所有内存。
5. **可选启用**：通过 `ProgramSettings::fUseMemoryPool` 控制。在调查内存损坏问题时可禁用，便于使用 sanitizer 工具检测。

## 相关文件

- `src/base/SkArenaAlloc.h` — 底层 arena 分配器
- `src/sksl/SkSLProgramSettings.h` — `fUseMemoryPool` 开关
- `src/sksl/SkSLCompiler.h` — SkSL 编译器（内存池的主要使用者）
- `src/sksl/ir/SkSLIRNode.h` — IR 节点基类（使用内存池分配）
