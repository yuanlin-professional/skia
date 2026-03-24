# SkAlign

> 源文件: `include/private/base/SkAlign.h`

## 概述
SkAlign 提供了一套内联模板函数,用于执行各种内存对齐操作。它支持常见的对齐需求(2、4、8、16 字节),以及指针对齐和任意 2 的幂次对齐。这些函数是 constexpr 的,可以在编译期计算,广泛用于内存分配、数据结构布局和性能优化。

## 架构位置
该头文件位于 Skia 基础设施层的内存管理工具中,是底层工具函数库的一部分。它为内存分配器、容器类、图像缓冲区等需要精确控制内存对齐的模块提供基础设施。

## 公共 API 函数

### 固定对齐函数

#### `SkAlign2<T>`
```cpp
template <typename T> static constexpr T SkAlign2(T x) {
    return (x + 1) >> 1 << 1;
}
```
- **功能**: 将值向上对齐到 2 的倍数(偶数)
- **参数**: `x` - 要对齐的值(可以是整数或指针)
- **返回值**: 大于等于 x 的最小 2 的倍数
- **算法**: (x + 1) / 2 * 2,使用位操作优化
- **示例**:
  - `SkAlign2(0)` → 0
  - `SkAlign2(1)` → 2
  - `SkAlign2(2)` → 2
  - `SkAlign2(5)` → 6

#### `SkAlign4<T>`
```cpp
template <typename T> static constexpr T SkAlign4(T x) {
    return (x + 3) >> 2 << 2;
}
```
- **功能**: 向上对齐到 4 的倍数
- **返回值**: 大于等于 x 的最小 4 的倍数
- **示例**:
  - `SkAlign4(0)` → 0
  - `SkAlign4(1)` → 4
  - `SkAlign4(4)` → 4
  - `SkAlign4(7)` → 8

#### `SkAlign8<T>`
```cpp
template <typename T> static constexpr T SkAlign8(T x) {
    return (x + 7) >> 3 << 3;
}
```
- **功能**: 向上对齐到 8 的倍数
- **常见用途**: double、int64_t、指针(64位)对齐
- **示例**:
  - `SkAlign8(0)` → 0
  - `SkAlign8(1)` → 8
  - `SkAlign8(9)` → 16

#### `SkAlign16<T>`
```cpp
template <typename T> static constexpr T SkAlign16(T x) {
    return (x + 15) >> 4 << 4;
}
```
- **功能**: 向上对齐到 16 的倍数
- **常见用途**: SIMD 类型(SSE、NEON)、缓存行对齐
- **示例**:
  - `SkAlign16(0)` → 0
  - `SkAlign16(1)` → 16
  - `SkAlign16(17)` → 32

### 对齐检查函数

#### `SkIsAlign2<T>`
```cpp
template <typename T> static constexpr bool SkIsAlign2(T x) {
    return 0 == (x & 1);
}
```
- **功能**: 检查值是否已对齐到 2 的倍数
- **返回值**: 对齐返回 true,否则 false
- **算法**: 检查最低位是否为 0

#### `SkIsAlign4<T>`
```cpp
template <typename T> static constexpr bool SkIsAlign4(T x) {
    return 0 == (x & 3);
}
```
- **功能**: 检查是否对齐到 4
- **算法**: 检查低 2 位是否全为 0

#### `SkIsAlign8<T>`
```cpp
template <typename T> static constexpr bool SkIsAlign8(T x) {
    return 0 == (x & 7);
}
```
- **功能**: 检查是否对齐到 8
- **算法**: 检查低 3 位是否全为 0

#### `SkIsAlign16<T>`
```cpp
template <typename T> static constexpr bool SkIsAlign16(T x) {
    return 0 == (x & 15);
}
```
- **功能**: 检查是否对齐到 16
- **算法**: 检查低 4 位是否全为 0

### 指针对齐函数

#### `SkAlignPtr<T>`
```cpp
template <typename T> static constexpr T SkAlignPtr(T x) {
    static_assert(sizeof(void*) == 4 || sizeof(void*) == 8);
    return sizeof(void*) == 8 ? SkAlign8(x) : SkAlign4(x);
}
```
- **功能**: 根据平台指针大小对齐
- **行为**:
  - 64位平台: 对齐到 8 字节
  - 32位平台: 对齐到 4 字节
- **静态断言**: 确保指针是 4 或 8 字节
- **使用场景**: 对齐指针或指针大小的数据

#### `SkIsAlignPtr<T>`
```cpp
template <typename T> static constexpr bool SkIsAlignPtr(T x) {
    static_assert(sizeof(void*) == 4 || sizeof(void*) == 8);
    return sizeof(void*) == 8 ? SkIsAlign8(x) : SkIsAlign4(x);
}
```
- **功能**: 检查是否按指针大小对齐
- **返回值**: 根据平台检查 4 或 8 字节对齐

### 通用对齐函数

#### `SkAlignTo<T>`
```cpp
template <typename T> static constexpr T SkAlignTo(T x, T alignment) {
    SkASSERT(alignment && (alignment & (alignment - 1)) == 0);
    return (x + alignment - 1) & ~(alignment - 1);
}
```
- **功能**: 对齐到任意 2 的幂次边界
- **参数**:
  - `x` - 要对齐的值
  - `alignment` - 对齐边界(必须是 2 的幂次)
- **返回值**: 大于等于 x 的最小 alignment 的倍数
- **断言**: 检查 alignment 是 2 的幂次
- **算法**: `(x + alignment - 1) & ~(alignment - 1)`
- **示例**:
  - `SkAlignTo(10, 8)` → 16
  - `SkAlignTo(16, 8)` → 16
  - `SkAlignTo(17, 32)` → 32

#### `SkAlignNonPow2<T>`
```cpp
template <typename T> static constexpr T SkAlignNonPow2(T x, T alignment) {
    return ((x + alignment - 1) / alignment) * alignment;
}
```
- **功能**: 对齐到任意值(不要求是 2 的幂次)
- **参数**:
  - `x` - 要对齐的值
  - `alignment` - 对齐边界(任意正整数)
- **返回值**: 大于等于 x 的最小 alignment 的倍数
- **算法**: 向上除法取整,然后乘以 alignment
- **示例**:
  - `SkAlignNonPow2(10, 7)` → 14
  - `SkAlignNonPow2(14, 7)` → 14
  - `SkAlignNonPow2(15, 7)` → 21

## 内部实现细节

### 位操作优化
固定对齐函数使用位操作代替除法和乘法:
```cpp
// SkAlign8(x) 的等价表达式:
(x + 7) >> 3 << 3
// 相当于
((x + 7) / 8) * 8
// 但位操作更快
```

**原理**:
- `>> 3`: 除以 8(右移 3 位)
- `<< 3`: 乘以 8(左移 3 位)
- `+ 7`: 向上取整

### 掩码检查
对齐检查使用位掩码:
```cpp
// SkIsAlign8(x)
0 == (x & 7)
// 等价于
x % 8 == 0
// 但位操作更快
```

### constexpr 优化
所有函数都是 constexpr:
- 编译期常量可以在编译时计算
- 零运行时开销
- 支持在常量表达式上下文中使用

### 2 的幂次检查
```cpp
alignment && (alignment & (alignment - 1)) == 0
```
**原理**:
- `alignment - 1`: 翻转最低的 1 位及其右侧所有位
- `alignment & (alignment - 1)`: 2 的幂次结果为 0
- 例如: `8 & 7` = `1000 & 0111` = 0

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/private/base/SkAssert.h | SkASSERT 断言宏 |
| <cstddef> | size_t 类型 |

### 被依赖的模块
| 模块 | 用途 |
|------|------|
| SkContainerAllocator | 容量对齐计算 |
| SkArenaAlloc | Arena 分配器对齐 |
| SkGlyph | 字形数据对齐 |
| SkImageInfo | 像素行对齐 |
| GPU 内存管理器 | 缓冲区对齐 |

## 设计模式与设计决策

### 模板泛型
使用模板支持多种类型:
```cpp
// 可以对齐整数
int aligned = SkAlign4(10);

// 可以对齐指针(转换为整数)
void* ptr = ...;
uintptr_t aligned_addr = SkAlign8(reinterpret_cast<uintptr_t>(ptr));
```

### constexpr 设计
所有函数都是 constexpr:
- 支持编译期计算
- 允许在常量初始化中使用
- 编译器优化机会

### 位操作实现
使用位操作而非除法/模运算:
- 性能优势(在某些架构上)
- 编译器更容易优化
- 生成更少的指令

### 静态断言
使用静态断言保证前提条件:
- 编译期检查,零运行时开销
- 提前发现错误
- 文档化函数要求

## 性能考量

### 编译期优化
```cpp
constexpr size_t bufferSize = SkAlign16(100);  // 编译期计算为 112
char buffer[bufferSize];  // 直接使用常量
```

### 位操作效率
在大多数 CPU 上:
- 位移操作: 1 个周期
- 整数除法: 10-40 个周期
- 位操作对齐比除法快得多

### 内联优化
所有函数都是简短的内联函数:
- 编译器完全内联
- 无函数调用开销
- 允许进一步优化

### 分支预测
对齐检查函数无分支:
```cpp
return 0 == (x & mask);  // 无分支,直接返回布尔值
```

## 使用场景

### 内存分配器
```cpp
void* allocate(size_t size) {
    // 对齐到 8 字节边界
    size_t aligned_size = SkAlign8(size);
    return malloc(aligned_size);
}
```

### 图像行对齐
```cpp
size_t computeRowBytes(int width, int bytesPerPixel) {
    size_t minBytes = width * bytesPerPixel;
    // 对齐到 4 字节,提高访问效率
    return SkAlign4(minBytes);
}
```

### 结构体布局
```cpp
class Allocator {
    char* allocate(size_t size) {
        // 确保分配的地址对齐到指针大小
        size_t aligned_size = SkAlignPtr(size);
        char* ptr = fCurrent;
        fCurrent += aligned_size;
        return ptr;
    }
};
```

### SIMD 优化
```cpp
void processPixels(const uint8_t* src, uint8_t* dst, size_t count) {
    // 检查是否对齐到 16 字节,可以使用 SIMD
    if (SkIsAlign16(reinterpret_cast<uintptr_t>(src)) &&
        SkIsAlign16(reinterpret_cast<uintptr_t>(dst))) {
        // 使用 SSE/NEON 快速路径
        processSIMD(src, dst, count);
    } else {
        // 使用标量路径
        processScalar(src, dst, count);
    }
}
```

### 容器容量规划
```cpp
template<typename T>
size_t roundUpCapacity(size_t capacity) {
    // 对齐到 8 字节倍数的元素数量
    return SkAlign8(capacity * sizeof(T)) / sizeof(T);
}
```

### 缓存行对齐
```cpp
// 假设缓存行是 64 字节
constexpr size_t kCacheLineSize = 64;

struct alignas(kCacheLineSize) CacheLine {
    char data[SkAlignTo(sizeof(MyStruct), kCacheLineSize)];
};
```

## 相关文件
| 文件 | 关系 |
|------|------|
| include/private/base/SkContainers.h | 使用对齐函数计算容量 |
| include/private/base/SkAlignedStorage.h | 对齐存储实现 |
| src/core/SkArenaAlloc.h | Arena 分配器对齐 |
| include/core/SkImageInfo.h | 图像行对齐 |

## 注意事项

### 对齐值必须是 2 的幂次
```cpp
// 正确
size_t size = SkAlignTo(100, 8);

// 错误:alignment 不是 2 的幂次
size_t size = SkAlignTo(100, 7);  // 断言失败!

// 对于非 2 的幂次,使用 SkAlignNonPow2
size_t size = SkAlignNonPow2(100, 7);
```

### 整数溢出
```cpp
// 小心溢出
uint8_t small = 255;
uint8_t aligned = SkAlign4(small);  // 可能溢出!

// 使用更大的类型
size_t aligned = SkAlign4(static_cast<size_t>(small));
```

### 指针对齐
```cpp
void* ptr = malloc(100);

// 错误:不能直接对齐指针
void* aligned = SkAlign8(ptr);  // 编译错误!

// 正确:转换为整数,对齐后转回
uintptr_t addr = reinterpret_cast<uintptr_t>(ptr);
addr = SkAlign8(addr);
void* aligned = reinterpret_cast<void*>(addr);
```

### constexpr 上下文
```cpp
// 可以在常量表达式中使用
constexpr size_t kBufferSize = SkAlign16(137);  // OK

// 也可以在运行时使用
size_t size = getUserInput();
size = SkAlign16(size);  // OK
```

### 性能权衡
过度对齐可能浪费空间:
```cpp
// 对于小分配,对齐开销可能很大
struct SmallObject {
    char data[3];  // 3 字节
};

// 对齐到 8 字节
size_t size = SkAlign8(sizeof(SmallObject));  // 8 字节,浪费 5 字节!

// 考虑使用更小的对齐
size_t size = SkAlign4(sizeof(SmallObject));  // 4 字节,浪费 1 字节
```

### 平台差异
```cpp
// SkAlignPtr 的行为依赖平台
size_t aligned = SkAlignPtr(10);
// 32 位平台: 12
// 64 位平台: 16

// 如果需要固定行为,使用显式函数
size_t aligned = SkAlign8(10);  // 总是 16
```
