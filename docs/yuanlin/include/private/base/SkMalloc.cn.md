# SkMalloc 内存管理模块

> 源文件: `include/private/base/SkMalloc.h`

## 概述
SkMalloc 是 Skia 的内存管理抽象层,提供跨平台的内存分配、释放和操作接口。该模块封装了底层平台的内存分配器,提供统一的 API,支持可选的零初始化、OOM 处理策略、内存大小查询等功能。

## 架构位置
位于 Skia 基础设施层 (private/base),是所有内存分配的核心入口。被几乎所有 Skia 模块使用,包括图像缓冲、路径数据、着色器编译等。

## 内存分配标志

### 分配选项枚举
```cpp
enum {
    SK_MALLOC_ZERO_INITIALIZE   = 1 << 0,  // 零初始化
    SK_MALLOC_THROW             = 1 << 1,  // 失败时抛出异常
};
```

| 标志 | 值 | 行为 |
|------|-----|------|
| `SK_MALLOC_ZERO_INITIALIZE` | 0x01 | 分配的内存初始化为零 |
| `SK_MALLOC_THROW` | 0x02 | 分配失败时终止程序,不返回 nullptr |

可按位或组合使用。

## 公共 API 函数

### 核心分配函数

#### `sk_malloc_flags`
```cpp
SK_API extern void* sk_malloc_flags(size_t size, unsigned flags);
```
- **功能**: 按标志分配内存
- **参数**:
  - `size`: 请求的字节数
  - `flags`: `SK_MALLOC_*` 标志的组合
- **返回**: 内存指针,失败时根据 `SK_MALLOC_THROW` 决定行为
- **对齐**: 至少 4 字节对齐
- **释放**: 使用 `sk_free()` 释放

#### `sk_free`
```cpp
SK_API extern void sk_free(void*);
```
- **功能**: 释放通过 `sk_malloc_*` 分配的内存
- **参数**: 内存指针,允许为 nullptr (安全)
- **特性**: 空指针安全,不会崩溃

#### `sk_out_of_memory`
```cpp
SK_API extern void sk_out_of_memory(void);
```
- **功能**: OOM 处理函数
- **行为**: 必须不返回,应抛出异常或终止程序
- **实现**: 由平台层提供

### 便捷分配函数

#### `sk_malloc_throw`
```cpp
static inline void* sk_malloc_throw(size_t size)
```
- **功能**: 分配内存,失败时终止
- **等价**: `sk_malloc_flags(size, SK_MALLOC_THROW)`
- **用途**: 不希望处理分配失败的场景

#### `sk_calloc_throw`
```cpp
static inline void* sk_calloc_throw(size_t size)
```
- **功能**: 分配零初始化内存,失败时终止
- **等价**: `sk_malloc_flags(size, SK_MALLOC_THROW | SK_MALLOC_ZERO_INITIALIZE)`

#### `sk_calloc_canfail`
```cpp
static inline void* sk_calloc_canfail(size_t size)
```
- **功能**: 分配零初始化内存,失败返回 nullptr
- **Fuzzer 模式**: 限制分配上限为 200KB,防止 OOM
- **返回**: 成功返回指针,失败返回 nullptr

#### `sk_malloc_canfail`
```cpp
static inline void* sk_malloc_canfail(size_t size)
```
- **功能**: 分配未初始化内存,失败返回 nullptr
- **Fuzzer 模式**: 同样有 200KB 限制

### 数组分配函数 (溢出检查)

#### `sk_calloc_throw` (数组版本)
```cpp
SK_API extern void* sk_calloc_throw(size_t count, size_t elemSize);
```
- **功能**: 分配数组,检查 `count * elemSize` 是否溢出
- **安全性**: 防止整数溢出导致的小分配

#### `sk_malloc_throw` (数组版本)
```cpp
SK_API extern void* sk_malloc_throw(size_t count, size_t elemSize);
```
未初始化的数组分配版本。

#### `sk_malloc_canfail` (数组版本)
```cpp
SK_API extern void* sk_malloc_canfail(size_t count, size_t elemSize);
```
可失败的数组分配版本。

### Realloc 函数

#### `sk_realloc_throw`
```cpp
SK_API extern void* sk_realloc_throw(void* buffer, size_t size);
```
- **功能**: 重新分配内存,失败时终止
- **行为**: 类似标准 `realloc`,但保证不返回 nullptr
- **特殊情况**: `size == 0` 时调用 `sk_free` 并返回 nullptr (glibc 行为)

#### `sk_realloc_throw` (数组版本)
```cpp
SK_API extern void* sk_realloc_throw(void* buffer, size_t count, size_t elemSize);
```
带溢出检查的 realloc 版本。

### 内存大小查询

#### `sk_malloc_size`
```cpp
SK_API extern size_t sk_malloc_size(void* addr, size_t size);
```
- **功能**: 查询实际分配的内存大小
- **参数**:
  - `addr`: 分配的指针
  - `size`: 请求时的大小
- **返回**: 实际分配的大小 (>= `size`)
- **用途**: 内存使用统计,某些分配器可能过度分配

## 安全内存操作函数

### `sk_bzero`
```cpp
static inline void sk_bzero(void* buffer, size_t size)
```
- **功能**: 安全的内存清零
- **特性**: `size == 0` 时不调用 `memset` (避免未定义行为)
- **优势**: 比 `memset` 更安全

### `sk_careful_memcpy`
```cpp
static inline void* sk_careful_memcpy(void* dst, const void* src, size_t len)
```
- **功能**: 安全的内存复制
- **问题**: 标准 `memcpy(nullptr, nullptr, 0)` 是未定义行为
- **解决**: `len == 0` 时跳过调用
- **原因**: GCC 可能利用 UB 进行优化,导致意外行为
- **示例问题**:
  ```cpp
  memcpy(dst, src, 0);
  if (src) {  // GCC 可能假设 src 非空,跳过检查
      printf("%x\n", *src);
  }
  ```

### `sk_careful_memmove`
```cpp
static inline void* sk_careful_memmove(void* dst, const void* src, size_t len)
```
安全的重叠内存移动版本。

### `sk_careful_memcmp`
```cpp
static inline int sk_careful_memcmp(const void* a, const void* b, size_t len)
```
- **功能**: 安全的内存比较
- **特殊处理**: `len == 0` 时返回 0 (认为相等)

## 内部实现细节

### Fuzzer 模式的内存限制
```cpp
#if defined(SK_BUILD_FOR_FUZZER)
    if (size > 200000) {
        return nullptr;
    }
#endif
```
- **目的**: 减少模糊测试时的 OOM 概率
- **限制**: 200KB 上限
- **影响**: `sk_malloc_canfail` 和 `sk_calloc_canfail`

### 未定义行为防护
所有 `sk_careful_*` 函数通过条件检查避免标准库的未定义行为:
```cpp
if (len) {
    memcpy(dst, src, len);
}
```
仅在 `len > 0` 时调用标准函数。

### 平台实现要求
以下函数必须由平台层实现:
- `sk_malloc_flags` - 实际的内存分配
- `sk_free` - 内存释放
- `sk_out_of_memory` - OOM 处理
- `sk_realloc_throw` - 内存重分配
- `sk_malloc_size` - 大小查询

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| `SkAPI.h` | SK_API 导出宏 |
| `<cstring>` | memcpy, memset 等函数 |

### 被依赖的模块
几乎所有 Skia 模块:
- 图像缓冲区分配
- 路径数据存储
- 字体表数据
- 着色器编译缓存
- GPU 资源管理

## 设计模式与设计决策

### 统一的分配接口
**决策**: 封装平台特定的分配器
**优势**:
- 跨平台一致性
- 可插拔的内存分配器
- 统一的错误处理策略

### 标志位设计
使用位掩码而非多个函数:
```cpp
sk_malloc_flags(size, SK_MALLOC_ZERO_INITIALIZE | SK_MALLOC_THROW);
```
- 灵活组合选项
- 避免函数爆炸

### 双版本 API 设计
提供 `_throw` 和 `_canfail` 两版本:
- `_throw`: 简化错误处理,适合不可恢复场景
- `_canfail`: 显式错误处理,适合可降级场景

### 安全优先
`sk_careful_*` 系列防止未定义行为,虽然有轻微性能开销,但显著提升稳定性。

### 数组分配溢出检查
```cpp
sk_malloc_throw(width, height);  // 自动检查 width * height 溢出
```
防止整数溢出导致的安全漏洞。

## 性能考量

### 内联小函数
所有便捷函数声明为 `inline`,在 Release 构建中无函数调用开销。

### 最小的安全检查开销
`sk_careful_*` 系列的条件检查通常被编译器优化:
```cpp
if (len) { ... }  // 分支预测良好
```

### 对齐保证
4 字节对齐满足大多数类型需求,避免未对齐访问的性能损失。

### Fuzzer 模式的权衡
200KB 限制可能导致某些测试路径未覆盖,但显著提高了模糊测试的有效性。

## 平台相关说明

### 不同平台的分配器
- **Android**: jemalloc 或 Bionic libc allocator
- **iOS**: Apple's malloc zone allocator
- **Windows**: HeapAlloc 或 malloc
- **Linux**: glibc malloc 或 tcmalloc
- **Emscripten**: dlmalloc

### OOM 处理差异
- **移动平台**: 通常抛出异常或终止
- **桌面平台**: 可能尝试释放缓存后重试
- **Web**: JavaScript 异常

## 使用示例

### 基本分配
```cpp
// 简单分配,失败时终止
void* buffer = sk_malloc_throw(1024);
ProcessData(buffer);
sk_free(buffer);
```

### 零初始化数组
```cpp
int* array = static_cast<int*>(sk_calloc_throw(100, sizeof(int)));
// array 所有元素初始化为 0
sk_free(array);
```

### 可失败分配
```cpp
void* largeBuffer = sk_malloc_canfail(10 * 1024 * 1024);
if (!largeBuffer) {
    // 降级处理
    UseSmallerBuffer();
} else {
    ProcessWithLargeBuffer(largeBuffer);
    sk_free(largeBuffer);
}
```

### 安全的内存操作
```cpp
void CopyData(const uint8_t* src, size_t srcLen, uint8_t* dst) {
    // 即使 srcLen == 0 也安全
    sk_careful_memcpy(dst, src, srcLen);
}
```

### Realloc 使用
```cpp
void* buffer = sk_malloc_throw(100);
// ... 使用 buffer ...
buffer = sk_realloc_throw(buffer, 200);  // 扩展到 200 字节
sk_free(buffer);
```

### 查询实际分配大小
```cpp
void* ptr = sk_malloc_throw(1000);
size_t actualSize = sk_malloc_size(ptr, 1000);  // 可能 > 1000
// 可利用额外空间
sk_free(ptr);
```

## 相关文件
| 文件 | 关系 |
|------|------|
| `SkAutoMalloc.h` | RAII 风格内存管理 |
| `SkData.h` | 不可变数据块封装 |
| `SkTArray.h` | 使用 SkMalloc 的动态数组 |
| 平台特定实现文件 | 实现具体分配逻辑 |

## 历史与演进
- 2017 年重构,统一内存分配接口
- 引入 `_canfail` 系列支持可降级场景
- 添加 Fuzzer 模式支持
- 增强数组分配的溢出检查
