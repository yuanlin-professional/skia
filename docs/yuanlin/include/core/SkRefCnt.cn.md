# SkRefCnt

> 源文件: `include/core/SkRefCnt.h`

## 概述

`SkRefCnt.h` 是 Skia 图形库引用计数内存管理系统的核心头文件。它定义了 Skia 中几乎所有共享对象的生命周期管理基础设施，包括引用计数基类 `SkRefCntBase`、其标准派生类 `SkRefCnt`、轻量级非虚引用计数模板 `SkNVRefCnt`、以及智能指针模板 `sk_sp`。

引用计数是 Skia 中最基本的内存管理策略。当多个对象共享同一个资源时，引用计数跟踪当前有多少拥有者。每个新的拥有者调用 `ref()` 增加计数，释放时调用 `unref()` 减少计数。当计数降为零时，对象自动销毁。

这套机制被 Skia 中的核心类型广泛使用，包括 `SkSurface`、`SkImage`、`SkPicture`、`SkTypeface`、`SkShader` 等。

## 架构位置

`SkRefCnt.h` 是 Skia 核心基础设施层的一部分：

```
include/core/
├── SkRefCnt.h       <-- 本文件：引用计数与智能指针
├── SkTypes.h        <-- 基础类型和宏
├── SkSurface.h      <-- 使用 SkRefCnt 的 Surface 类
├── SkImage.h        <-- 使用 SkRefCnt 的 Image 类
└── ...              <-- 几乎所有核心类型都依赖此文件
```

它处于依赖层次的最底层，几乎没有对 Skia 其他模块的依赖，但被几乎所有 Skia 模块所引用。

## 主要类与结构体

### `SkRefCntBase`

线程安全的引用计数基类，是所有引用计数对象的根基类。

```cpp
class SK_API SkRefCntBase {
public:
    SkRefCntBase() : fRefCnt(1) {}
    virtual ~SkRefCntBase();
    bool unique() const;
    void ref() const;
    void unref() const;
private:
    virtual void internal_dispose() const;
    mutable std::atomic<int32_t> fRefCnt;
};
```

关键特性：
- 初始引用计数为 1（创建者即首个拥有者）
- 析构函数断言引用计数为 1
- 禁止拷贝和移动操作
- `internal_dispose()` 是虚函数，允许子类（如 `SkWeakRefCnt`）自定义销毁行为

### `SkRefCnt`

```cpp
class SK_API SkRefCnt : public SkRefCntBase {};
```
`SkRefCntBase` 的标准派生类，是大多数 Skia 公共类的基类。通过 `SK_REF_CNT_MIXIN_INCLUDE` 宏支持自定义混入。在 Google3 构建系统中提供 `deref()` 别名。

### `SkNVRefCnt<Derived>`

```cpp
template <typename Derived>
class SkNVRefCnt {
public:
    SkNVRefCnt() : fRefCnt(1) {}
    bool unique() const;
    void ref() const;
    void unref() const;
    void deref() const;
    bool refCntGreaterThan(int32_t threadIsolatedTestCnt) const;
};
```
非虚（Non-Virtual）引用计数模板，仅占 4 字节（相比虚基类的 8 或 16 字节）。适用于派生类本身不需要虚函数表的场景。使用 CRTP（Curiously Recurring Template Pattern）模式，通过 `delete (const Derived*)this` 直接删除派生类对象，避免了虚析构函数的开销。

额外提供 `refCntGreaterThan()` 方法，用于在已知线程隔离引用数的前提下安全地检测是否有其他线程持有引用。

### `sk_sp<T>`

```cpp
template <typename T> class SK_TRIVIAL_ABI sk_sp {
public:
    using element_type = T;
    constexpr sk_sp();
    constexpr sk_sp(std::nullptr_t);
    sk_sp(const sk_sp<T>& that);      // 拷贝：ref
    sk_sp(sk_sp<T>&& that);            // 移动：无 ref/unref
    explicit sk_sp(T* obj);            // 领养裸指针
    ~sk_sp();                           // unref
    // ... 赋值运算符、比较运算符、解引用运算符等
    T* get() const;
    void reset(T* ptr = nullptr);
    [[nodiscard]] T* release();
    void swap(sk_sp<T>& that);
};
```

Skia 专用的智能指针，功能类似 `std::shared_ptr`，但专为 `ref()`/`unref()` 接口设计。

关键特性：
- 使用 `SK_TRIVIAL_ABI` 属性标记为平凡可重定位（trivially relocatable），使编译器可以将"移动构造 + 析构"优化为 `memcpy`
- 支持协变类型转换（`sk_sp<Derived>` 可隐式转换为 `sk_sp<Base>`）
- 提供 `release()` 方法以转移所有权（标记为 `[[nodiscard]]`）
- 支持 CTAD（C++17 Class Template Argument Deduction）

## 公共 API 函数

### 引用计数操作

#### `SkRefCntBase::ref()`
```cpp
void ref() const;
```
递增引用计数。使用 `std::memory_order_relaxed` 原子操作，因为增加引用不需要建立先行发生（happens-before）关系。

#### `SkRefCntBase::unref()`
```cpp
void unref() const;
```
递减引用计数。如果计数降至零则销毁对象。使用 `std::memory_order_acq_rel` 以确保释放操作的内存可见性正确排序。

#### `SkRefCntBase::unique()`
```cpp
bool unique() const;
```
检查是否只有一个拥有者。使用 `std::memory_order_acquire` 确保在返回 true 时，所有之前拥有者的操作均已完成。注意：该方法可能返回 true 即使在多线程场景下有短暂的竞争条件，因此被标记为"可能返回 true"。

### 辅助函数模板

#### `SkRef`
```cpp
template <typename T> static inline T* SkRef(T* obj);
```
对非空对象调用 `ref()` 并返回指针。要求 obj 非空。

#### `SkSafeRef`
```cpp
template <typename T> static inline T* SkSafeRef(T* obj);
```
空安全版本的 `ref()`，如果 obj 为 `nullptr` 则不执行操作。

#### `SkSafeUnref`
```cpp
template <typename T> static inline void SkSafeUnref(T* obj);
```
空安全版本的 `unref()`，如果 obj 为 `nullptr` 则不执行操作。

### 智能指针辅助工厂

#### `sk_make_sp`
```cpp
template <typename T, typename... Args>
sk_sp<T> sk_make_sp(Args&&... args);
```
类似 `std::make_shared`，使用完美转发构造对象并包装为 `sk_sp`。注意：与 `std::make_shared` 不同，它不会将对象和引用计数分配在同一内存块中。

#### `sk_ref_sp`
```cpp
template <typename T> sk_sp<T> sk_ref_sp(T* obj);
template <typename T> sk_sp<T> sk_ref_sp(const T* obj);
```
从裸指针创建 `sk_sp` 并调用 `ref()`。与 `sk_sp` 构造函数（采纳语义，不调用 ref）不同，此函数执行额外的引用。`const` 版本会执行 `const_cast` 以去除常量性。

## 内部实现细节

### 内存序（Memory Order）设计

引用计数的原子操作使用了精心选择的内存序：

1. **`ref()` - `memory_order_relaxed`**: 增加引用计数不需要任何内存屏障。这是安全的，因为调用者在调用 `ref()` 时必然已经持有一个有效引用。

2. **`unref()` - `memory_order_acq_rel`**:
   - Release 语义确保在 `unref()` 之前对对象的所有写入对随后执行删除的线程可见。
   - Acquire 语义（在计数降为零时生效）确保删除操作能看到所有其他线程对对象的修改。

3. **`unique()` - `memory_order_acquire`**: Acquire 语义确保当返回 true 时，所有之前拥有者通过 `unref()` 进行的释放操作（包括对对象的写入）都已完成。

### `internal_dispose()` 机制

```cpp
virtual void internal_dispose() const {
#ifdef SK_DEBUG
    SkASSERT(0 == this->getRefCnt());
    fRefCnt.store(1, std::memory_order_relaxed);
#endif
    delete this;
}
```
在 Debug 模式下，销毁前先断言引用计数为 0，然后将其重置为 1 以便析构函数中的断言（期望引用计数为 1）能够通过。这种"重置后删除"的模式虽然看起来不寻常，但保证了析构函数中的断言逻辑一致性。

### `SkNVRefCnt` 的 CRTP 模式

```cpp
void unref() const {
    if (1 == fRefCnt.fetch_add(-1, std::memory_order_acq_rel)) {
        SkDEBUGCODE(fRefCnt.store(1, std::memory_order_relaxed));
        delete (const Derived*)this;
    }
}
```
通过 CRTP 在编译时确定实际的派生类型，使用 `delete (const Derived*)this` 直接删除，无需虚析构函数。这节省了虚函数表指针的空间（通常 8 字节）。

### `sk_sp` 的 reset 安全性

```cpp
void reset(T* ptr = nullptr) {
    T* oldPtr = fPtr;
    fPtr = ptr;
    SkSafeUnref(oldPtr);
}
```
先保存旧指针再更新，最后才 unref 旧指针。这种顺序防止了 `unref` 触发析构链中再次调用 `reset` 导致的重入问题（参见 LWG issue 998 和 2262）。

## 依赖关系

- **`include/core/SkTypes.h`** - Skia 基础类型和宏定义
- **`include/private/base/SkDebug.h`** - 调试断言宏（`SkASSERT`、`SkASSERTF`、`SkDEBUGCODE`）
- **标准库**: `<atomic>`, `<cstddef>`, `<cstdint>`, `<iosfwd>`, `<type_traits>`, `<utility>`

## 设计模式与设计决策

### 1. 侵入式引用计数
Skia 采用侵入式引用计数（引用计数存储在对象内部），而非 `std::shared_ptr` 的非侵入式方案。优势包括：
- 避免额外的控制块分配
- 可以从裸指针安全地创建 `sk_sp`（因为引用计数在对象中）
- 内存局部性更好

### 2. CRTP 无虚开销方案
`SkNVRefCnt` 通过 CRTP 模式在不需要虚函数的场景下节省内存。对于频繁创建的小对象（如内部缓存条目），4 字节与 16 字节的差异可能相当显著。

### 3. `SK_TRIVIAL_ABI` 优化
`sk_sp` 使用 `SK_TRIVIAL_ABI` 属性，使编译器可以将其视为平凡可重定位的类型。在函数调用和返回时，`sk_sp` 可以通过寄存器传递而非栈传递，显著减少了 ref/unref 调用。

### 4. 不可复制的引用计数对象
`SkRefCntBase` 和 `SkNVRefCnt` 都禁止了拷贝和移动操作。这是正确的语义——引用计数对象通过 `ref()`/`unref()` 共享，而非通过值拷贝。

### 5. `[[nodiscard]]` on `release()`
`sk_sp::release()` 被标记为 `[[nodiscard]]`，防止开发者意外丢弃返回的裸指针导致内存泄漏。

### 6. `const` 方法的可变引用计数
`ref()` 和 `unref()` 被声明为 `const` 方法，引用计数字段使用 `mutable` 修饰。这符合逻辑——引用计数不是对象"逻辑状态"的一部分，修改引用计数不应要求对象的可变性。

## 性能考量

1. **原子操作开销**: 在无竞争的情况下，`memory_order_relaxed` 的原子递增在大多数架构上几乎与普通递增一样快。`memory_order_acq_rel` 在 x86 上也很高效（x86 的 `fetch_add` 本身就是全屏障）。

2. **无虚函数表的 `SkNVRefCnt`**: 对于不需要虚析构的类型，使用 `SkNVRefCnt` 可以在每个对象上节省 8 字节（64 位系统上的 vtable 指针大小），在创建大量小对象时效果显著。

3. **`sk_sp` 的移动语义**: 移动 `sk_sp` 不执行任何原子操作（仅指针赋值和置空），比拷贝（需要 `ref()`）快得多。应尽可能使用 `std::move` 传递 `sk_sp`。

4. **`sk_sp` 的平凡可重定位性**: `SK_TRIVIAL_ABI` 属性使得容器（如 `std::vector<sk_sp<T>>`）在重新分配内存时可以使用 `memcpy` 而非逐个移动构造和析构。

5. **`unique()` 的 acquire 屏障**: 仅在返回 true 时才真正需要 acquire 屏障，返回 false 的快速路径不需要任何同步开销。

## 相关文件

- `include/core/SkTypes.h` - Skia 基础类型和宏
- `include/private/base/SkDebug.h` - 调试断言
- `include/core/SkSurface.h` - 继承自 SkRefCnt 的 Surface 类
- `include/core/SkImage.h` - 继承自 SkRefCnt 的 Image 类
- `include/core/SkPicture.h` - 继承自 SkRefCnt 的 Picture 类
- `include/core/SkTypeface.h` - 继承自 SkRefCnt 的 Typeface 类
- `src/core/SkWeakRefCnt.h` - 弱引用计数扩展（覆写 `internal_dispose`）
