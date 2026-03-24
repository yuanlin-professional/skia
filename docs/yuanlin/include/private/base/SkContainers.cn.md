# SkContainers

> 源文件: `include/private/base/SkContainers.h`

## 概述
SkContainers 提供了 Skia 容器类使用的内存分配工具和辅助函数。核心是 SkContainerAllocator 类,负责容器的内存分配策略,包括容量对齐、增长因子计算和安全的内存分配接口。

## 架构位置
该文件位于 Skia 基础设施层的容器支持子系统中。它为 SkTArray、SkTDArray 等容器类提供统一的内存分配策略,确保内存对齐、容量规划和溢出检测的一致性。

## 主要类与结构体

### SkContainerAllocator
容器内存分配器类,封装了容器的内存分配逻辑和容量管理策略。

**继承关系**: 无基类 → SkContainerAllocator

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fSizeOfT | const size_t | 单个元素的字节大小 |
| fMaxCapacity | const int64_t | 容器允许的最大容量(元素数量) |

**关键常量**:
| 常量名 | 值 | 说明 |
|--------|-----|------|
| kCapacityMultiple | 8 | 容量向上对齐的基本单位(字节) |

## 公共 API 函数

### SkContainerAllocator 方法

#### `SkContainerAllocator(size_t sizeOfT, int maxCapacity)`
- **功能**: 构造一个容器分配器
- **参数**:
  - `sizeOfT` - 元素类型的 sizeof 值
  - `maxCapacity` - 容器允许的最大元素数量
- **说明**: 用于初始化容器的分配策略

#### `SkSpan<std::byte> allocate(int capacity, double growthFactor = 1.0)`
- **功能**: 分配指定容量的内存
- **参数**:
  - `capacity` - 请求的元素数量
  - `growthFactor` - 增长因子,用于计算实际分配容量(默认 1.0)
- **返回值**: std::byte 的 span,表示分配的内存区域
- **行为**:
  - capacity 为 0 时返回空 span
  - 失败时中止程序(abort)
  - 分配的内存需要使用 `sk_free()` 释放
- **说明**: 实际分配容量可能大于请求值,以减少重新分配次数

#### `template <typename T> static constexpr size_t RoundUp(size_t capacity)`
- **功能**: 将容量向上舍入到 kCapacityMultiple 的倍数
- **参数**: `capacity` - 原始容量(元素数量)
- **返回值**: 舍入后的容量(元素数量)
- **实现**:
  ```cpp
  SkAlignTo(capacity * sizeof(T), kCapacityMultiple) / sizeof(T)
  ```
- **说明**: constexpr 函数,可以在编译期计算

### 全局辅助函数

#### `SkSpan<std::byte> sk_allocate_canfail(size_t size)`
- **功能**: 尝试分配指定大小的内存,失败时返回空 span
- **参数**: `size` - 请求的字节大小(必须 > 0)
- **返回值**: 成功时返回有效 span,失败时返回空 span
- **说明**: 不会中止程序,允许调用者处理分配失败

#### `SkSpan<std::byte> sk_allocate_throw(size_t size)`
- **功能**: 分配指定大小的内存,失败时中止程序
- **参数**: `size` - 请求的字节大小
- **返回值**: 有效的 span,size 为 0 时返回空 span
- **说明**: 用于不允许失败的分配场景

#### `SK_SPI void sk_report_container_overflow_and_die()`
- **功能**: 报告容器溢出错误并终止程序
- **说明**: 当容量计算溢出或超过限制时调用

## 内部实现细节

### 容量对齐策略
```cpp
static constexpr int64_t kCapacityMultiple = 8;
```
所有容量向上对齐到 8 字节的倍数:
- **ASAN 对齐**: 匹配 AddressSanitizer 的影子内存粒度(8 字节)
- **结构体对齐**: 匹配 64 位机器上的典型结构体对齐
- **缓存行**: 减少假共享,提高缓存效率

### roundUpCapacity 方法
```cpp
size_t roundUpCapacity(int64_t capacity) const
```
- 将容量舍入到 kCapacityMultiple 的倍数
- 限制在 [0, fMaxCapacity] 范围内
- 使用 int64_t 避免中间计算溢出

### growthFactorCapacity 方法
```cpp
size_t growthFactorCapacity(int capacity, double growthFactor) const
```
- 根据增长因子计算新容量
- 确保新容量在合理范围内
- 避免过小或过大的增长

### 内存分配实现
分配器使用底层的 `sk_malloc_canfail` 或 `sk_malloc_throw`:
- 与 `sk_free()` 配对使用
- 支持对齐要求
- 提供溢出检测

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/private/base/SkAPI.h | SK_SPI 宏定义 |
| include/private/base/SkAlign.h | SkAlignTo 对齐函数 |
| include/private/base/SkSpan_impl.h | SkSpan 容器视图 |
| <cstddef> | size_t, std::byte 类型 |
| <cstdint> | int64_t 类型 |

### 被依赖的模块
- SkTArray (动态数组)
- SkTDArray (传统动态数组)
- 其他 Skia 容器类
- 容器单元测试

## 设计模式与设计决策

### 策略模式
SkContainerAllocator 封装了分配策略:
- 容量对齐规则
- 增长因子计算
- 最大容量限制
- 允许不同容器共享相同的分配逻辑

### 类型擦除
使用 `size_t fSizeOfT` 而非模板:
- 减少代码膨胀
- 运行时灵活性
- 缩短编译时间

### 双重安全检查
提供两种分配接口:
- `sk_allocate_canfail`: 允许失败,调用者处理
- `sk_allocate_throw`: 不允许失败,直接中止
- 根据场景选择合适的语义

### constexpr 容量计算
`RoundUp` 是 constexpr 函数:
- 编译期优化机会
- 栈分配场景的静态大小计算
- 零运行时开销

## 性能考量

### 内存对齐优化
对齐到 8 字节边界:
- **ASAN 友好**: 避免部分中毒的字节
- **缓存效率**: 减少跨缓存行访问
- **SIMD 友好**: 许多 SIMD 指令要求对齐

### 增长因子
通过 growthFactor 参数控制重新分配频率:
- 默认 1.0: 精确分配,不浪费空间
- > 1.0: 预分配更多空间,减少重新分配次数
- 典型值 1.5 或 2.0: 平衡空间和时间

### 批量分配
一次分配多个元素的空间:
- 减少 malloc 调用次数
- 降低内存分配器开销
- 提高连续性,改善缓存命中率

### 溢出检测
使用 int64_t 进行中间计算:
- 避免 int32_t 乘法溢出
- 安全地检测超出限制的请求
- 及早检测编程错误

## 使用场景

### SkTArray 分配
```cpp
template<typename T>
class SkTArray {
    SkContainerAllocator fAllocator{sizeof(T), maxCapacity};

    void reserve(int capacity) {
        auto span = fAllocator.allocate(capacity, 1.5);  // 1.5x 增长
        // 使用 span.data() 和 span.size()
    }
};
```

### 容量预计算
```cpp
// 编译期计算对齐容量
constexpr size_t aligned = SkContainerAllocator::RoundUp<MyStruct>(100);
SkAlignedSTStorage<aligned, MyStruct> storage;
```

### 安全的尝试分配
```cpp
auto span = sk_allocate_canfail(largeSize);
if (span.empty()) {
    // 处理分配失败
    return fallbackPath();
}
// 使用分配的内存
```

### 保证成功的分配
```cpp
auto span = sk_allocate_throw(sizeof(T) * count);
// 确保 span 有效,无需检查
T* array = reinterpret_cast<T*>(span.data());
```

## 相关文件
| 文件 | 关系 |
|------|------|
| include/private/base/SkTArray.h | 使用 SkContainerAllocator 实现 |
| include/private/base/SkAlign.h | 提供 SkAlignTo 函数 |
| include/private/base/SkSpan_impl.h | 提供 SkSpan 类型 |
| src/core/SkContainers.cpp | 实现文件 |
| tests/SkContainersTest.cpp | 单元测试 |

## 注意事项

### 容量限制
- 最大容量由构造时指定
- 超过限制会触发 abort
- 用于防止编程错误导致的过度分配

### 内存释放
分配的内存必须使用 `sk_free()` 释放:
```cpp
auto span = allocator.allocate(100);
// ... 使用内存
sk_free(span.data());
```

### ASAN 集成
kCapacityMultiple = 8 与 ASAN 影子内存对齐:
- 避免红区(red zone)问题
- 提高 ASAN 检测精度
- 减少误报

### 溢出安全
使用 int64_t 避免整数溢出:
```cpp
// 安全的大小计算
int64_t bytes = int64_t(capacity) * int64_t(fSizeOfT);
if (bytes > INT_MAX) {
    sk_report_container_overflow_and_die();
}
```

### 空容量处理
allocate(0) 返回空 span:
- 不执行实际分配
- 返回的 span.data() 可能为 nullptr
- 调用者需要检查 span.empty()
