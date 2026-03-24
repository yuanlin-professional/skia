# SkRasterPipelineContextUtils

> 源文件: src/core/SkRasterPipelineContextUtils.h

## 概述

`SkRasterPipelineContextUtils` 是一个轻量级的工具命名空间，提供了用于优化 Raster Pipeline 上下文数据传递的辅助函数。它实现了一种智能的"小对象优化"（Small Object Optimization）策略：对于足够小的上下文结构体（不超过指针大小），直接将其位转换为指针传递，避免内存分配和间接访问；对于较大的结构体，则在 arena 分配器中分配并传递指针。这是一个纯编译期优化工具，零运行时开销。

## 架构位置

`SkRasterPipelineContextUtils` 位于 Raster Pipeline 的优化工具层：

- **使用者**: `SkRasterPipeline`、各种着色器和特效的管道构建代码
- **依赖**: `SkArenaAlloc`、`SkUtils`（提供 `sk_bit_cast`）
- **设计目标**: 减少内存分配，优化缓存局部性

该工具是纯头文件实现，通过模板内联实现零开销抽象。

## 主要类与结构体

该文件不包含类或结构体，仅提供模板函数和类型别名。

### 类型别名

| 类型别名 | 定义 | 说明 |
|---------|------|------|
| `UnpackedType<T>` | `conditional<sizeof(T) <= sizeof(void*), T, const T&>` | 决定返回值类型（按值或按引用） |

### 关键函数模板

| 函数 | 功能 |
|------|------|
| `Pack<T>(const T&, SkArenaAlloc*)` | 将上下文打包为 `void*` |
| `Unpack<T>(const T*)` | 将 `void*` 解包为原始类型 |

## 公共 API 函数

### Pack - 上下文打包

```cpp
template <typename T>
[[maybe_unused]] static void* Pack(const T& ctx, SkArenaAlloc* alloc);
```

**功能**：将上下文结构体转换为 `void*`，策略如下：
- 如果 `sizeof(T) <= sizeof(void*)`：直接位转换（bit-cast）为指针
- 否则：在 `alloc` 中分配副本，返回副本指针

**使用场景**：管道操作需要传递上下文时

**示例**：
```cpp
struct SmallCtx { int x; };          // 4 字节（32 位）或 8 字节（64 位）
struct LargeCtx { int data[10]; };   // 40 字节

SmallCtx sctx{42};
LargeCtx lctx{...};

// 小对象：位转换，无分配
void* sptr = SkRPCtxUtils::Pack(sctx, alloc);

// 大对象：分配并拷贝
void* lptr = SkRPCtxUtils::Pack(lctx, alloc);  // alloc->make<LargeCtx>(lctx)
```

### Unpack - 上下文解包

```cpp
template <typename T>
[[maybe_unused]] static UnpackedType<T> Unpack(const T* ctx);
```

**功能**：从 `void*` 恢复原始类型：
- 如果 `sizeof(T) <= sizeof(void*)`：位转换回原类型（按值返回）
- 否则：返回引用（`const T&`）

**返回类型**：
- 小对象：`T`（值）
- 大对象：`const T&`（引用）

**示例**：
```cpp
// 小对象解包
SmallCtx sctx = SkRPCtxUtils::Unpack<SmallCtx>((SmallCtx*)sptr);
// 类型: SmallCtx（值）

// 大对象解包
const LargeCtx& lctx = SkRPCtxUtils::Unpack<LargeCtx>((LargeCtx*)lptr);
// 类型: const LargeCtx&（引用）
```

## 内部实现细节

### 编译期分支

使用 `if constexpr` 实现零运行时开销的分支：

```cpp
template <typename T>
static void* Pack(const T& ctx, SkArenaAlloc* alloc) {
    if constexpr (sizeof(T) <= sizeof(void*)) {
        // 编译期分支：小对象路径
        return sk_bit_cast<void*>(ctx);
    } else {
        // 编译期分支：大对象路径
        return alloc->make<T>(ctx);
    }
}
```

编译器会根据 `sizeof(T)` 在编译时选择一条路径，另一条路径完全不生成代码。

### 位转换机制

对于小对象，使用 `sk_bit_cast` 进行类型双关（type punning）：

```cpp
struct SmallCtx { int x; };
SmallCtx ctx{42};

// 32 位系统示例
// ctx 的内存布局: [00 00 00 2A] (小端序)
// bit-cast 后指针值: 0x2A000000（取决于平台字节序）
void* ptr = sk_bit_cast<void*>(ctx);

// 恢复
SmallCtx restored = sk_bit_cast<SmallCtx>(ptr);
// restored.x == 42
```

**注意**：这要求 `T` 是 trivially-copyable 类型。

### UnpackedType 的类型选择

```cpp
template <typename T>
using UnpackedType = typename std::conditional<
    sizeof(T) <= sizeof(void*),
    T,              // 小对象：按值返回
    const T&        // 大对象：按引用返回
>::type;
```

**设计理由**：
- 小对象本身就在"指针"中，按值返回无开销
- 大对象在堆上，返回引用避免拷贝

### 平台差异

该优化在不同平台上表现不同：

| 平台 | 指针大小 | 小对象阈值 | 示例 |
|------|---------|-----------|------|
| 32 位 | 4 字节 | ≤ 4 字节 | `int`, `float`, `uint32_t` |
| 64 位 | 8 字节 | ≤ 8 字节 | `int64_t`, `double`, 两个 `int` |

```cpp
struct TwoInts { int a, b; };  // 8 字节

// 32 位系统：sizeof(void*) == 4，不满足 <= 条件，会分配
void* ptr = Pack(TwoInts{1, 2}, alloc);  // alloc->make<TwoInts>

// 64 位系统：sizeof(void*) == 8，满足条件，位转换
void* ptr = Pack(TwoInts{1, 2}, alloc);  // sk_bit_cast
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkArenaAlloc` | 为大对象分配内存 |
| `SkUtils` | 提供 `sk_bit_cast` 函数 |
| `<type_traits>` | `std::conditional` |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `SkRasterPipeline` | 传递操作上下文 |
| 着色器实现 | 打包渐变、采样器等上下文 |
| 特效实现 | 打包颜色过滤、混合等上下文 |

## 设计模式与设计决策

### 1. 小对象优化（Small Object Optimization）

这是 C++ 标准库中常用的优化技术（如 `std::string` 的 SSO）：

**核心思想**：
- 小数据直接存储在"指针"中（in-place storage）
- 大数据存储在堆上，指针指向它

**优点**：
- 减少内存分配次数
- 提高缓存命中率
- 消除间接访问开销

### 2. 零开销抽象（Zero-Cost Abstraction）

使用 `if constexpr` 和模板内联：

```cpp
// 编译前
void* ptr = Pack(ctx, alloc);

// 编译后（小对象）
void* ptr = sk_bit_cast<void*>(ctx);

// 编译后（大对象）
void* ptr = alloc->make<T>(ctx);
```

没有运行时分支，没有额外开销。

### 3. 类型安全的类型双关

使用 `sk_bit_cast` 而非 C 风格转换：

```cpp
// 不安全（未定义行为）
void* ptr = *(void**)&ctx;

// 安全（定义良好）
void* ptr = sk_bit_cast<void*>(ctx);
```

`sk_bit_cast` 确保类型兼容性检查。

### 4. 属性标记

```cpp
[[maybe_unused]] static void* Pack(...)
```

`[[maybe_unused]]` 防止编译器在某些翻译单元中未使用时发出警告。

### 5. 静态函数设计

所有函数都是静态的（命名空间级别），强调：
- 无状态
- 纯工具函数
- 不应被实例化

## 性能考量

### 1. 内存分配开销

**小对象优化**：
```
无优化版本:
  alloc->make<SmallCtx>(ctx);  // 调用分配器，可能触发新块分配
  管道访问: *ctx               // 间接内存访问

优化版本:
  sk_bit_cast<void*>(ctx);     // 纯编译期操作，零指令
  管道访问: bit_cast(ctx)      // 直接从"指针"提取
```

**测量结果**（假设）：
- 小对象：节省 ~10-20 条指令 + 1 次缓存访问
- 大对象：无差异（仍需分配）

### 2. 缓存局部性

小对象存储在管道的内联数据中，而非分散在堆上：

```
无优化:
  Stage { op, ctx* } → ctx* → MemoryCtx { pixels, stride }
                        ↑ 缓存未命中

优化:
  Stage { op, ctx_inlined }  // ctx 数据直接在这里
                        ↑ 无额外内存访问
```

### 3. 指令级并行

位转换是单周期操作，而内存分配可能涉及：
- 函数调用
- 条件分支（检查剩余空间）
- 内存拷贝

### 4. 边界情况

```cpp
struct ExactFit { int64_t x; };  // 在 64 位系统上恰好 8 字节

// 满足 <= 条件，使用位转换
void* ptr = Pack(ExactFit{42}, alloc);
```

恰好等于指针大小的类型享受优化。

### 5. 多线程友好

小对象优化避免了 arena 分配器的同步：

```cpp
// 无优化：需要锁定 alloc（如果多线程共享）
void* ptr = alloc->make<SmallCtx>(ctx);

// 优化：无需锁定，纯本地操作
void* ptr = sk_bit_cast<void*>(ctx);
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/core/SkRasterPipeline.h` | 主要使用者 | 管道系统 |
| `src/core/SkRasterPipelineOpContexts.h` | 数据定义 | 被打包的上下文类型 |
| `src/base/SkArenaAlloc.h` | 依赖 | 内存分配器 |
| `src/base/SkUtils.h` | 依赖 | 提供 `sk_bit_cast` |
| `include/private/base/SkTemplates.h` | 相关 | 其他模板工具 |

## 典型使用场景

### 场景 1: 打包简单的常量上下文

```cpp
struct ConstantCtx {
    int32_t value;  // 4 字节
    SkRPOffset dst; // 4 字节（uint32_t）
};  // 总共 8 字节

ConstantCtx ctx{42, 100};

// 64 位系统：位转换
void* packed = SkRPCtxUtils::Pack(ctx, alloc);

pipeline.append(SkRasterPipelineOp::copy_constant, packed);

// 管道内部使用时
auto ctx = SkRPCtxUtils::Unpack<ConstantCtx>((ConstantCtx*)packed);
// ctx.value == 42, ctx.dst == 100
```

### 场景 2: 打包复杂的采样器上下文

```cpp
struct SamplerCtx {
    float x[16];  // 64 字节
    float y[16];  // 64 字节
    // ... 更多字段
};  // 远大于指针大小

SamplerCtx ctx;
// ... 初始化 ctx ...

// 总是分配（大对象）
void* packed = SkRPCtxUtils::Pack(ctx, alloc);

pipeline.append(SkRasterPipelineOp::bilinear_setup, packed);

// 管道内部
const SamplerCtx& ctx = SkRPCtxUtils::Unpack<SamplerCtx>((SamplerCtx*)packed);
// 返回引用，避免拷贝
```

### 场景 3: 条件优化示例

```cpp
template <typename Ctx>
void addStage(SkRasterPipeline* p, SkRasterPipelineOp op,
              const Ctx& ctx, SkArenaAlloc* alloc) {
    void* packed = SkRPCtxUtils::Pack(ctx, alloc);
    p->append(op, packed);
}

// 使用
struct SmallCtx { int x; };
struct LargeCtx { int data[100]; };

addStage(p, op1, SmallCtx{1}, alloc);   // 位转换
addStage(p, op2, LargeCtx{...}, alloc); // 分配

// 同一个函数，编译器生成两个优化版本
```

### 场景 4: 平台差异处理

```cpp
struct Coord { float x, y; };  // 8 字节

// 32 位系统
#if INTPTR_MAX == INT32_MAX
    // sizeof(void*) == 4，不满足 ≤ 条件
    // Coord 会被分配到堆上
    void* ptr = Pack(Coord{1.0f, 2.0f}, alloc);  // alloc->make
#else
    // 64 位系统
    // sizeof(void*) == 8，满足条件
    // Coord 被位转换
    void* ptr = Pack(Coord{1.0f, 2.0f}, alloc);  // bit-cast
#endif

// 使用代码无需关心差异
```

## 安全性考量

### 1. 类型要求

被 bit-cast 的类型必须满足：
- Trivially copyable（平凡可拷贝）
- Standard layout（标准布局）

```cpp
struct Safe { int x; };  // OK

struct Unsafe {
    std::string s;  // 非平凡类型
};
// bit-cast 会导致未定义行为
```

### 2. 对齐要求

位转换后的指针可能未对齐：

```cpp
struct SmallCtx { char c; };  // 1 字节
void* ptr = sk_bit_cast<void*>(SmallCtx{'A'});
// ptr 的值为 'A'（0x41），可能未对齐

// 使用时需注意
SmallCtx ctx = sk_bit_cast<SmallCtx>(ptr);  // OK，位转换回来
// 但不能: *(SmallCtx*)ptr  // 未定义行为（未对齐访问）
```

### 3. 生命周期管理

```cpp
// 错误示例
void* dangling() {
    SmallCtx ctx{42};
    return SkRPCtxUtils::Pack(ctx, alloc);  // OK，位拷贝
}

void* ptr = dangling();
SmallCtx restored = SkRPCtxUtils::Unpack<SmallCtx>((SmallCtx*)ptr);
// OK，值已经在 ptr 中，无悬空问题

// 大对象情况
LargeCtx* bad = alloc->make<LargeCtx>(...);
// alloc 析构后，指针悬空
```

Skia 使用 arena 分配器，所有上下文与管道生命周期绑定，避免悬空指针。
