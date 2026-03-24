# SkMalloc - 安全内存分配辅助函数
> 源文件: `src/base/SkMalloc.cpp`

## 概述
SkMalloc 模块提供了一组重载的内存分配辅助函数，用于处理"数量×大小"形式的内存分配请求。这些函数通过使用 SkSafeMath 工具防止整数溢出攻击，确保在分配大量小对象时不会因为乘法溢出而分配过小的内存，从而避免缓冲区溢出漏洞。

## 架构位置
SkMalloc 位于 Skia 基础内存管理模块（src/base）中，扩展了核心内存分配 API（定义在 include/private/base/SkMalloc.h）。它为上层的容器类、图像缓冲区、GPU 资源等模块提供安全的批量对象分配能力。

## 公共 API 函数

### `void* sk_calloc_throw(size_t count, size_t elemSize)`
- **功能**: 分配并清零 `count * elemSize` 字节的内存，失败时抛出异常
- **参数**:
  - count: 元素数量
  - elemSize: 单个元素大小（字节）
- **返回值**: 指向已清零内存的指针
- **安全性**: 使用 SkSafeMath::Mul 防止整数溢出
- **异常**: 分配失败或溢出时抛出 std::bad_alloc（由底层 sk_calloc_throw 单参数版本实现）

### `void* sk_malloc_throw(size_t count, size_t elemSize)`
- **功能**: 分配 `count * elemSize` 字节的内存（不清零），失败时抛出异常
- **参数**: 同 sk_calloc_throw
- **返回值**: 指向未初始化内存的指针
- **安全性**: 使用 SkSafeMath::Mul 防止整数溢出
- **性能**: 比 calloc 快（不清零内存）
- **用途**: 分配后会立即覆盖数据的场景

### `void* sk_realloc_throw(void* buffer, size_t count, size_t elemSize)`
- **功能**: 重新分配内存至 `count * elemSize` 字节，失败时抛出异常
- **参数**:
  - buffer: 原始内存指针（可为 nullptr）
  - count: 新的元素数量
  - elemSize: 单个元素大小
- **返回值**: 指向重新分配内存的指针（可能与原指针不同）
- **安全性**: 使用 SkSafeMath::Mul 防止整数溢出
- **行为**: 保留原有数据（在新大小范围内）

### `void* sk_malloc_canfail(size_t count, size_t elemSize)`
- **功能**: 分配 `count * elemSize` 字节的内存，失败时返回 nullptr（不抛出异常）
- **参数**: 同 sk_malloc_throw
- **返回值**: 成功返回内存指针，失败返回 nullptr
- **安全性**: 使用 SkSafeMath::Mul 防止整数溢出
- **用途**: 性能关键路径中需要优雅处理失败的场景

## 内部实现细节

### 安全乘法机制
所有函数都遵循相同的模式：
```cpp
void* sk_malloc_throw(size_t count, size_t elemSize) {
    return sk_malloc_throw(SkSafeMath::Mul(count, elemSize));
}
```

**关键设计**:
1. 调用 `SkSafeMath::Mul(count, elemSize)` 执行安全乘法
2. 如果溢出，SkSafeMath::Mul 返回 SIZE_MAX（最大 size_t 值）
3. 单参数版本的 sk_malloc_throw 检测到巨大尺寸会失败（抛异常或返回 nullptr）

### 为何需要这些重载
直接使用 `malloc(count * elemSize)` 的危险：
```cpp
// 假设在 32 位系统上
size_t count = 0x10000;           // 65536
size_t elemSize = 0x10000;        // 65536
size_t total = count * elemSize;  // 溢出！结果为 0
void* ptr = malloc(total);        // 实际分配 0 字节或极小内存
// 后续访问 ptr[0] ... ptr[count-1] 导致缓冲区溢出
```

使用 SkSafeMath::Mul 的保护：
```cpp
size_t total = SkSafeMath::Mul(count, elemSize);  // 返回 SIZE_MAX
void* ptr = sk_malloc_throw(total);  // 检测到异常大小，抛出异常
```

### 单参数版本在何处定义
这些函数调用的单参数版本定义在 `include/private/base/SkMalloc.h` 中：
- `void* sk_malloc_throw(size_t size)`
- `void* sk_calloc_throw(size_t size)`
- `void* sk_realloc_throw(void* ptr, size_t size)`
- `void* sk_malloc_canfail(size_t size)`

双参数版本作为便利接口，封装了安全乘法逻辑。

### 命名约定
- **throw**: 分配失败时抛出 std::bad_alloc 异常
- **canfail**: 分配失败时返回 nullptr，不抛出异常
- **calloc**: 分配并清零内存
- **malloc**: 分配但不清零内存
- **realloc**: 重新分配现有内存

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/private/base/SkMalloc.h | 单参数版本的内存分配函数声明 |
| src/base/SkSafeMath.h | 提供 SkSafeMath::Mul 安全乘法 |

### 被依赖的模块
- 容器类（TArray, STArray, SkDeque）
- 图像缓冲区分配（SkBitmap, SkPixmap）
- 路径数据存储（SkPath）
- 字体缓存（SkGlyphCache）
- GPU 资源管理（Buffer 分配）
- 编解码器（临时缓冲区）

## 设计模式与设计决策

### 重载而非模板
使用函数重载而非模板：
```cpp
// 采用的方式
void* sk_malloc_throw(size_t count, size_t elemSize);

// 未采用的方式
template<typename T>
T* sk_malloc_throw(size_t count);
```

**原因**:
- 更好的 ABI 稳定性（函数重载而非模板实例化）
- 避免头文件依赖增加
- 更清晰的类型转换语义
- 与 C 风格分配函数习惯一致

### 防御性编程
多层次的安全保护：
1. **第一层**: SkSafeMath::Mul 检测溢出
2. **第二层**: 单参数分配函数检查大小合理性
3. **第三层**: 底层 malloc/realloc 的内存耗尽处理

### 统一的失败处理
提供两种失败处理策略：
- **throw 版本**: 用于构造函数、初始化代码
- **canfail 版本**: 用于可恢复的分配失败（如缓存、优化路径）

这种设计允许调用者根据上下文选择合适的错误处理方式。

### 最小化代码重复
通过委托给单参数版本，避免重复实现：
- 4 个双参数函数仅需 4 行实现
- 所有复杂逻辑（异常、对齐、平台差异）在单参数版本中统一处理

## 性能考量

### 内联机会
这些函数定义在 .cpp 文件中，可能不会被内联：
- **优点**: 减少代码膨胀
- **缺点**: 额外的函数调用开销
- **实际影响**: 内存分配本身开销较大（锁、系统调用），函数调用开销可忽略

### 安全检查的成本
SkSafeMath::Mul 的开销：
- 一次乘法
- 一次溢出检查（通常为条件跳转）
- 现代 CPU 可能仅需 2-3 个周期
- 相比 malloc（可能数百周期），成本微不足道

### calloc vs malloc + memset
sk_calloc_throw 使用系统 calloc：
- 系统 calloc 可能利用操作系统的零页优化
- 比 malloc + memset 更高效（特别是大内存）
- 某些系统延迟实际清零（copy-on-write）

### realloc 的性能特性
sk_realloc_throw 使用系统 realloc：
- 可能原地扩展（避免拷贝）
- 缩小时通常原地操作
- 扩大时可能需要拷贝（O(n) 复杂度）

## 安全性考量

### 整数溢出攻击防护
真实世界的漏洞场景：
```cpp
// 恶意输入：width = 0x10001, height = 0x10000
uint32_t width = ParseWidth(untrustedInput);
uint32_t height = ParseHeight(untrustedInput);
// 在 32 位系统：width * height * 4 溢出
uint8_t* pixels = malloc(width * height * sizeof(uint32_t));
// pixels 指向很小的缓冲区，后续写入导致缓冲区溢出
```

使用 Skia 的安全分配：
```cpp
uint8_t* pixels = sk_calloc_throw(width * height, sizeof(uint32_t));
// SkSafeMath::Mul 检测溢出，抛出异常，避免漏洞
```

### SIZE_MAX 作为哨兵值
SkSafeMath::Mul 在溢出时返回 SIZE_MAX：
- SIZE_MAX 是平台最大的 size_t 值（通常 2^64 - 1 或 2^32 - 1）
- 试图分配这么大的内存必然失败
- 即使在某些极端情况下不失败，也不太可能导致溢出攻击

### 异常安全性
throw 版本使用异常：
- 分配失败时清理栈
- RAII 对象自动析构
- 避免需要手动检查每次分配

canfail 版本用于：
- 性能关键路径（避免异常开销）
- C 风格代码接口
- 需要明确控制流的场景

## 相关文件
| 文件 | 关系 |
|------|------|
| include/private/base/SkMalloc.h | 单参数分配函数声明及核心实现 |
| src/base/SkSafeMath.h | 提供溢出检测的安全算术运算 |
| include/private/base/SkTArray.h | 使用这些函数分配数组存储 |
| src/core/SkBitmap.cpp | 使用这些函数分配像素存储 |
| src/core/SkPath.cpp | 使用这些函数分配路径点 |
| src/gpu/ganesh/GrGpuBuffer.cpp | 使用这些函数分配 GPU 缓冲区 |
| src/codec/*.cpp | 编解码器使用这些函数分配临时缓冲区 |
