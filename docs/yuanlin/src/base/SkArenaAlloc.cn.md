# SkArenaAlloc

> 源文件: `src/base/SkArenaAlloc.h`, `src/base/SkArenaAlloc.cpp`

## 概述

SkArenaAlloc 是 Skia 中的高性能竞技场分配器,优化了对象分配和批量销毁场景。它首先从用户提供的内存块分配,耗尽后从堆分配,使用斐波那契序列控制块大小增长。该分配器在销毁时自动运行所有非 POD 对象的析构函数,最小化内存管理开销。

## 架构位置

- **所属子系统**: 基础设施层 (Base Infrastructure)
- **层级**: 内存管理 - 高级分配器
- **作用域**: 为 Skia 的绘图操作、路径构建、着色器等提供临时对象分配

## 主要类与结构体

### SkArenaAlloc

竞技场分配器主类,支持类型安全的对象分配和自动析构。

**继承关系**: 无直接继承

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fDtorCursor | char* | 指向下一个需要运行析构函数的位置 |
| fCursor | char* | 指向下一次分配的位置 |
| fEnd | char* | 当前块的结束位置 |
| fFibonacciProgression | SkFibBlockSizes | 斐波那契块大小计算器 |

### SkArenaAllocWithReset

支持重置操作的竞技场分配器变体,可多次重用。

**继承关系**: SkArenaAlloc → SkArenaAllocWithReset

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fFirstBlock | char* const | 初始块指针 |
| fFirstSize | uint32_t | 初始块大小 |
| fFirstHeapAllocationSize | uint32_t | 首次堆分配大小 |

### SkFibBlockSizes

基于斐波那契序列的块大小生成器。

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fIndex | uint32_t:6 | 当前斐波那契索引(最大 47) |
| fBlockUnitSize | uint32_t:26 | 基本块单元大小 |

### Footer 结构

存储在每个分配块末尾的元数据,用于析构函数调用。

**关键成员**:
| 成员 | 类型 | 说明 |
|------|------|------|
| unaligned_action | uint8_t[sizeof(FooterAction*)] | 析构函数指针(未对齐存储) |
| padding | uint8_t | 对齐填充量 |

### FooterAction 类型

```cpp
using FooterAction = char* (char*);
```
析构函数回调类型,接收块结束指针,返回对象起始指针。

## 公共 API 函数

### `SkArenaAlloc(char*, size_t, size_t)`
- **功能**: 构造分配器,可选使用预分配块
- **参数**:
  - `block`: 初始内存块指针(可为 nullptr)
  - `blockSize`: 初始块大小
  - `firstHeapAllocation`: 首次堆分配大小
- **返回值**: 无

### `template <typename Ctor> auto make(Ctor&& ctor)`
- **功能**: 使用提供的构造器函数分配并构造对象
- **参数**: `ctor` - 接收 void* 并返回构造对象指针的 lambda
- **返回值**: 构造的对象指针(类型自动推导)
- **示例**:
  ```cpp
  auto obj = alloc.make([&](void* p) {
      return new(p) MyClass(args...);
  });
  ```

### `template <typename T, typename... Args> T* make(Args&&... args)`
- **功能**: 分配并构造 T 类型对象
- **参数**: 转发给 T 的构造函数的参数
- **返回值**: 指向新构造对象的指针
- **特殊处理**: POD 类型不调用构造函数

### `template <typename T> T* make()`
- **功能**: 默认构造 T 类型对象
- **返回值**: 指向新对象的指针
- **优化**: POD 类型仅分配内存,不初始化

### `template <typename T> T* makeArrayDefault(size_t count)`
- **功能**: 分配 T 类型数组,执行默认初始化
- **参数**: `count` - 数组元素数量
- **返回值**: 数组指针
- **行为**: 原始类型保持未初始化,类类型调用默认构造函数

### `template <typename T> T* makeArray(size_t count)`
- **功能**: 分配 T 类型数组,执行值初始化
- **参数**: `count` - 数组元素数量
- **返回值**: 数组指针
- **行为**: 原始类型零初始化,类类型调用默认构造函数

### `template <typename T, typename Initializer> T* makeInitializedArray(size_t, Initializer)`
- **功能**: 分配数组并使用初始化器函数初始化每个元素
- **参数**:
  - `count`: 数组大小
  - `initializer`: 函数对象 `T initializer(size_t index)`
- **返回值**: 数组指针

### `template <typename T> T* makeArrayCopy(SkSpan<const T>)`
- **功能**: 分配并拷贝数组
- **参数**: `toCopy` - 要拷贝的源数组
- **返回值**: 新数组指针
- **优化**: trivially_copyable 类型使用 memcpy

### `void* makeBytesAlignedTo(size_t size, size_t align)`
- **功能**: 分配指定大小和对齐的原始字节
- **参数**:
  - `size`: 字节数
  - `align`: 对齐要求
- **返回值**: 对齐的内存指针
- **用途**: 当类型化分配不适用时使用

## 内部实现细节

### 析构函数链

SkArenaAlloc 使用链式 Footer 存储析构信息:

```
[POD data][Footer1]->[Non-POD Object][Footer2]->[Array][Footer3]->nullptr
```

每个 Footer 包含:
1. **FooterAction 指针**: 指向析构函数 lambda
2. **padding 字节**: 对齐偏移量

析构函数链类型:
- **end_chain**: 链结束标记,返回 nullptr
- **SkipPod**: 跳过 POD 数据段
- **对象析构器**: 调用单个对象的析构函数
- **数组析构器**: 循环调用数组元素的析构函数
- **NextBlock**: 释放堆块并递归处理前一个块

### 内存布局示例

```
Block 1:
[SkArenaAlloc 头部]
[POD: int x 3][uint32_t: count=3][Footer: SkipPod, pad=0]
[MyClass obj1][Footer: ~MyClass, pad=2]
[MyClass obj2][Footer: ~MyClass, pad=0]
[char* nextBlock][Footer: NextBlock, pad=0]

Block 2 (堆):
[MyClass array[5]][uint32_t: count=5][Footer: array dtor, pad=1]
...
```

### 块大小计算

使用 SkFibBlockSizes 生成斐波那契序列:
```cpp
uint32_t nextBlockSize() {
    uint32_t result = SkFibonacci47[fIndex] * fBlockUnitSize;
    if (fIndex + 1 < 47 &&
        SkFibonacci47[fIndex + 1] < kMaxSize / fBlockUnitSize) {
        fIndex += 1;
    }
    return result;
}
```

块大小: F(0)×unit, F(1)×unit, F(2)×unit, ..., F(46)×unit

### POD 优化

对于 trivially_destructible 类型:
1. 不安装 Footer
2. 不跟踪析构函数
3. 零开销存储

检测:
```cpp
if (std::is_trivially_destructible<T>::value) {
    // 快速路径:仅分配,无 Footer
    objStart = this->allocObject(size, alignment);
    fCursor = objStart + size;
}
```

### 对齐处理

```cpp
char* allocObject(uint32_t size, uint32_t alignment) {
    uintptr_t mask = alignment - 1;
    uintptr_t alignedOffset = (~reinterpret_cast<uintptr_t>(fCursor) + 1) & mask;
    uintptr_t totalSize = size + alignedOffset;
    if (totalSize > static_cast<uintptr_t>(fEnd - fCursor)) {
        this->ensureSpace(size, alignment);
        alignedOffset = (~reinterpret_cast<uintptr_t>(fCursor) + 1) & mask;
    }
    return fCursor + alignedOffset;
}
```

使用位运算快速计算对齐偏移,避免分支。

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| SkASAN.h | 内存安全检测 |
| SkMalloc.h | 底层堆分配(sk_malloc_throw) |
| SkTFitsIn.h | 类型范围检查 |
| SkSpan_impl.h | 数组视图支持 |

### 被依赖的模块
- **SkRasterPipeline**: 使用 SkArenaAlloc 分配管道阶段
- **SkPath**: 临时路径构建器使用竞技场分配
- **SkShader**: 着色器实例分配
- **SkCanvas**: 临时绘图状态存储

## 设计模式与设计决策

### 设计模式
1. **对象池模式**: 块重用减少堆分配
2. **RAII 模式**: 析构函数自动调用
3. **策略模式**: 斐波那契增长策略

### 设计决策

**为什么使用斐波那契序列?**
- 指数增长过快,导致大量未使用空间(slop)
- 斐波那契在增长速度和空间利用率间取得平衡
- 在 Android 上实测效果更好

**为什么分离 POD 和非 POD 路径?**
- POD 类型无需析构,避免 Footer 开销
- 典型每 POD 项零开销,每块 8 字节开销
- 非 POD 每项 4 字节,每数组 8 字节开销

**为什么用 Footer 而不是对象头部?**
- 对象按需要的对齐分配,无需额外空间
- Footer 可存储在对齐间隙中
- 反向遍历析构更高效

**为什么支持初始块参数?**
- 允许栈分配小场景避免堆
- 嵌入式存储减少指针跳转
- 对小型绘图操作零堆分配

## 性能考量

### 时间复杂度
- `make<T>()`: O(1) 均摊
- `makeArray<T>(n)`: O(n) 构造时间 + O(1) 均摊分配
- 析构: O(M) M 为非 POD 对象数量
- `reset()` (WithReset 版本): O(M)

### 空间效率
- **POD 开销**: 0 字节每对象 + ~8 字节每块
- **非 POD 开销**: ~4 字节每对象 (Footer)
- **数组开销**: ~8 字节每数组 (count + Footer)
- **块开销**: sizeof(char*) + sizeof(Footer) = ~16 字节

### 内存碎片
- **内部碎片**: 对齐浪费最多 (align-1) 字节每分配
- **外部碎片**: 块末尾剩余空间,通过斐波那契增长缓解
- **峰值内存**: 当前块 + 所有之前块(直到析构)

### 缓存友好性
- 线性分配模式,良好空间局部性
- 所有对象在连续块中,减少缓存缺失
- 析构时顺序访问提高缓存命中

## 相关文件
| 文件 | 关系 |
|------|------|
| src/base/SkBlockAllocator.h | 类似的块管理逻辑 |
| include/private/base/SkMalloc.h | 底层内存分配 |
| src/core/SkRasterPipeline.h | 主要使用者 |

## 模板辅助类

### SkSTArenaAlloc<InlineStorageSize>

带内联存储的竞技场分配器模板:
```cpp
template <size_t InlineStorageSize>
class SkSTArenaAlloc : private std::array<char, InlineStorageSize>,
                       public SkArenaAlloc {
public:
    explicit SkSTArenaAlloc(size_t firstHeapAllocation = InlineStorageSize)
        : SkArenaAlloc{this->data(), this->size(), firstHeapAllocation} {}
};
```

**用途**: 在栈上预分配小缓冲区,常见大小 256, 512, 1024, 4096 字节。

### SkSTArenaAllocWithReset<InlineStorageSize>

支持重置的内联存储版本,用于可重用的分配器。

## 使用示例

### 示例 1: 基本对象分配
```cpp
SkArenaAlloc alloc(4096);
auto* obj1 = alloc.make<MyClass>(arg1, arg2);
auto* obj2 = alloc.make<MyClass>();
// 析构时自动调用 ~MyClass()
```

### 示例 2: 数组分配
```cpp
SkArenaAlloc alloc(4096);
float* array = alloc.makeArray<float>(100);  // 零初始化
// 析构时无需手动释放
```

### 示例 3: 栈内联分配
```cpp
SkSTArenaAlloc<512> alloc;
// 前 512 字节在栈上,无堆分配
for (int i = 0; i < 10; ++i) {
    alloc.make<SmallObject>();
}
```

### 示例 4: 可重用分配器
```cpp
SkSTArenaAllocWithReset<1024> alloc;
for (int frame = 0; frame < 100; ++frame) {
    // ... 分配帧数据 ...
    alloc.reset();  // 清理并重用
}
```

## 注意事项

1. **线程安全**: 不是线程安全的,每线程独立实例
2. **对象生命周期**: 所有对象与分配器同生共死
3. **指针稳定性**: 对象指针稳定直到分配器销毁
4. **虚函数**: 支持带虚函数的对象(vptr 正确初始化)
5. **异常安全**: 使用 sk_malloc_throw,分配失败抛出异常
6. **ASAN 兼容**: 完全支持 AddressSanitizer 检测
