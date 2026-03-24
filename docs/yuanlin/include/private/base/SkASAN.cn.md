# SkASAN

> 源文件: `include/private/base/SkASAN.h`

## 概述
SkASAN 是 Skia 对 AddressSanitizer (ASan) 的集成接口,提供了一组内联函数用于手动标记内存区域的可访问性状态。它允许自定义内存分配器与 ASan 工具集成,实现更精确的内存错误检测。

## 架构位置
该文件位于 Skia 基础设施层的调试和诊断子系统中。它为内存分配器、缓冲池等需要自定义内存管理的模块提供 ASan 集成能力,在调试版本中帮助检测内存越界、释放后使用等问题。

## 主要宏定义

### SK_SANITIZE_ADDRESS
```cpp
#ifdef __SANITIZE_ADDRESS__
    #define SK_SANITIZE_ADDRESS 1
#endif
#if !defined(SK_SANITIZE_ADDRESS) && defined(__has_feature)
    #if __has_feature(address_sanitizer)
        #define SK_SANITIZE_ADDRESS 1
    #endif
#endif
```

**说明**: 检测是否启用了 AddressSanitizer:
- GCC 通过 `__SANITIZE_ADDRESS__` 宏
- Clang 通过 `__has_feature(address_sanitizer)` 特性检测
- 启用后值为 1,未启用则不定义

## 公共 API 函数

### `sk_asan_poison_memory_region`
```cpp
static inline void sk_asan_poison_memory_region(
    [[maybe_unused]] void const volatile* addr,
    [[maybe_unused]] size_t size)
```

- **功能**: 将指定内存区域标记为不可访问(有毒)
- **参数**:
  - `addr` - 内存区域的起始地址
  - `size` - 内存区域的字节大小
- **行为**:
  - 启用 ASan 时: 调用 `__asan_poison_memory_region`,任何访问该区域的操作将触发 ASan 错误
  - 未启用 ASan 时: 空操作(编译器优化后无开销)
- **使用场景**: 标记已分配但未使用的内存,如对象池中的空闲槽位

### `sk_asan_unpoison_memory_region`
```cpp
static inline void sk_asan_unpoison_memory_region(
    [[maybe_unused]] void const volatile* addr,
    [[maybe_unused]] size_t size)
```

- **功能**: 将指定内存区域标记为可访问(解毒)
- **参数**:
  - `addr` - 内存区域的起始地址
  - `size` - 内存区域的字节大小
- **行为**:
  - 启用 ASan 时: 调用 `__asan_unpoison_memory_region`,允许正常访问该区域
  - 未启用 ASan 时: 空操作
- **使用场景**: 标记准备使用的内存,如从对象池分配出的内存块

### `sk_asan_address_is_poisoned`
```cpp
static inline int sk_asan_address_is_poisoned(
    [[maybe_unused]] void const volatile* addr)
```

- **功能**: 检查指定地址是否处于中毒状态
- **参数**: `addr` - 要检查的内存地址
- **返回值**:
  - 启用 ASan 时: 如果地址有毒返回非零值,否则返回 0
  - 未启用 ASan 时: 始终返回 0
- **使用场景**: 调试和断言,验证内存状态是否符合预期

## 内部实现细节

### 条件编译
所有函数都使用条件编译:
```cpp
#ifdef SK_SANITIZE_ADDRESS
    __asan_poison_memory_region(addr, size);
#endif
```
在未启用 ASan 的构建中,函数体为空,编译器会完全优化掉调用,实现零开销。

### 参数属性
使用 `[[maybe_unused]]` 属性标记参数:
- 避免未启用 ASan 时的未使用参数警告
- 保持函数签名一致性
- 兼容 C++17 标准

### volatile 限定符
参数声明为 `void const volatile*`:
- `const`: 表示函数不修改内存内容
- `volatile`: 防止编译器优化掉相关的内存访问
- 与 ASan 运行时接口保持一致

### 外部函数声明
```cpp
extern "C" {
    void __asan_poison_memory_region(void const volatile *addr, size_t size);
    void __asan_unpoison_memory_region(void const volatile *addr, size_t size);
    int __asan_address_is_poisoned(void const volatile *addr);
}
```
声明 LLVM ASan 运行时库提供的函数,使用 C 链接避免名称修饰。

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| <cstddef> | size_t 类型定义 |
| LLVM ASan Runtime | __asan_* 系列函数的实现(链接时) |

### 被依赖的模块
- 自定义内存分配器(SkArenaAlloc, SkBlockAllocator)
- 内存池实现
- 缓冲区管理器
- 任何需要精细内存错误检测的模块

## 设计模式与设计决策

### 零开销抽象
通过条件编译和内联函数实现:
- 调试版本: 提供完整的 ASan 集成
- 发布版本: 完全无性能开销(函数调用被优化掉)
- 相同的代码路径,不同的行为

### 接口统一
所有 Skia 代码通过 `sk_asan_*` 接口访问 ASan 功能:
- 隐藏平台差异(GCC vs Clang)
- 提供默认实现(未启用时)
- 便于未来扩展或替换实现

### 静态内联
所有函数都是 `static inline`:
- 避免链接符号冲突
- 允许编译器在调用点优化
- 不增加二进制大小

## 性能考量

### 零开销抽象
在未启用 ASan 的构建中:
- 函数体为空
- 编译器完全内联并优化掉调用
- 不产生任何指令
- 不影响发布版本性能

### ASan 开销
启用 ASan 时:
- 每次内存访问增加检查逻辑
- 内存占用增加(影子内存)
- 运行时性能下降约 2-5 倍
- 仅用于开发和测试环境

### 内联优化
静态内联使得编译器可以:
- 在编译时展开函数调用
- 与周围代码一起优化
- 消除不必要的参数传递

## 使用场景

### 自定义内存池
```cpp
class MemoryPool {
    char buffer[4096];

    MemoryPool() {
        // 初始化时标记整个缓冲区为不可访问
        sk_asan_poison_memory_region(buffer, sizeof(buffer));
    }

    void* allocate(size_t size) {
        // 分配时解除标记
        void* ptr = /* 从 buffer 中分配 */;
        sk_asan_unpoison_memory_region(ptr, size);
        return ptr;
    }

    void deallocate(void* ptr, size_t size) {
        // 释放时重新标记为不可访问
        sk_asan_poison_memory_region(ptr, size);
    }
};
```

### Arena 分配器
```cpp
// 分配大块内存,标记为有毒
void* arena = malloc(megabytes);
sk_asan_poison_memory_region(arena, megabytes);

// 按需解毒使用的部分
void* block = arena + offset;
sk_asan_unpoison_memory_region(block, blockSize);
```

### 缓冲区边界保护
```cpp
// 在缓冲区边界留下红区(red zone)
char buffer[128];
sk_asan_poison_memory_region(buffer + 120, 8);  // 保护最后 8 字节
```

## 相关文件
| 文件 | 关系 |
|------|------|
| src/core/SkArenaAlloc.h | 使用 ASan 接口实现 Arena 分配器 |
| src/core/SkBlockAllocator.h | 块分配器的 ASan 集成 |
| src/gpu/GrMemoryPool.h | GPU 内存池的 ASan 支持 |
| build/sanitizers/* | 构建配置,启用 ASan 选项 |

## 注意事项

### 粒度对齐
ASan 影子内存以 8 字节为单位:
- 中毒/解毒操作应该对齐到 8 字节边界
- 非对齐操作可能导致部分字节的状态模糊
- 建议在分配器中使用对齐的块大小

### 性能影响
启用 ASan 的构建:
- 不适合性能基准测试
- 仅用于调试和测试
- 内存占用显著增加

### 平台支持
ASan 支持情况:
- **Clang**: 全平台支持(Linux, macOS, Windows)
- **GCC**: Linux 和部分 Unix 平台
- **MSVC**: 部分支持(需要特定版本)

### 与其他工具的交互
- 与 Valgrind 不兼容(不能同时使用)
- 可以与 ThreadSanitizer (TSan) 一起使用
- 可以与 UndefinedBehaviorSanitizer (UBSan) 一起使用

## 相关 ASan 文档
- LLVM AddressSanitizer: https://clang.llvm.org/docs/AddressSanitizer.html
- ASan 手动标记: https://github.com/google/sanitizers/wiki/AddressSanitizerManualPoisoning
