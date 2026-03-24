# GpuRefCnt

> 源文件:
> - `src/gpu/GpuRefCnt.h`

## 概述

`GpuRefCnt.h` 定义了 Skia GPU 层中用于自定义引用计数的智能指针模板 `gr_sp`，以及基于它的两个常用别名 `gr_cb`（命令缓冲区引用）和 `gr_rp`（回收引用）。与标准的 `sk_sp` 不同，`gr_sp` 允许指定自定义的引用和解引用成员函数指针，从而支持同一对象上的多种独立引用计数机制。

## 架构位置

```
Skia 引用计数体系
  ├── sk_sp<T> (标准智能指针，调用 ref()/unref())
  └── gr_sp<T, Ref, Unref> (GPU 自定义智能指针)
        ├── gr_cb<T> = gr_sp<T, refCommandBuffer, unrefCommandBuffer>
        └── gr_rp<T> = gr_sp<T, ref, recycle>
```

## 主要类与结构体

### `gr_sp<T, Ref, Unref>`
通用 GPU 智能指针模板：
- **T**：所管理对象的类型。
- **Ref**：引用计数递增的成员函数指针（使用 `auto` 推导，支持基类函数）。
- **Unref**：引用计数递减的成员函数指针。
- 接口与 `sk_sp` 类似：支持拷贝构造、移动构造、赋值、解引用、`reset()`、`release()`。
- 支持从 `sk_sp<T>` 构造和赋值（会调用自定义 Ref）。
- 支持派生类到基类的隐式转换（通过 `std::is_convertible` SFINAE）。

### `gr_cb<T>`
```cpp
template <typename T>
using gr_cb = gr_sp<T, &T::refCommandBuffer, &T::unrefCommandBuffer>;
```
- 用于追踪 GPU 资源在命令缓冲区中的使用。
- 调用 `refCommandBuffer()` / `unrefCommandBuffer()` 而非标准的 `ref()` / `unref()`。
- 允许 GPU 资源在逻辑上已不被 Skia 使用时仍能安全地被 GPU 命令缓冲区引用。

### `gr_rp<T>`
```cpp
template <typename T>
using gr_rp = gr_sp<T, &T::ref, &T::recycle>;
```
- 在解引用时调用 `recycle()` 而非 `unref()`，允许对象被回收重用而非销毁。
- 辅助函数 `gr_ref_rp(T*)` 在包装指针时额外调用 `ref()`（与构造函数的"采纳"语义不同）。

## 公共 API 函数

### 构造函数
- **`gr_sp()`** / **`gr_sp(nullptr_t)`**：空构造。
- **`gr_sp(const gr_sp&)`**：拷贝构造，调用 `Ref()`。
- **`gr_sp(gr_sp&&)`**：移动构造，不调用 `Ref()/Unref()`。
- **`gr_sp(const sk_sp<T>&)`**：从 `sk_sp` 拷贝构造，调用 `Ref()`。
- **`gr_sp(sk_sp<T>&&)`**：从 `sk_sp` 移动构造，但仍调用 `Ref()`（因为 sk_sp 和 gr_sp 使用不同的引用计数）。
- **`explicit gr_sp(T*)`**：采纳裸指针，不调用 `Ref()`。

### 赋值运算符
- **`operator=(nullptr_t)`**：重置为空。
- **`operator=(const gr_sp&)`**：拷贝赋值。
- **`operator=(gr_sp&&)`**：移动赋值。
- **`operator=(const sk_sp<T>&)`** / **`operator=(sk_sp<T>&&)`**：从 `sk_sp` 赋值。

### 访问与管理
- **`get()`**：返回裸指针。
- **`operator*()`** / **`operator->()`**：解引用。
- **`operator bool()`**：非空检查。
- **`reset(T* = nullptr)`**：替换管理的对象，对旧对象调用 `Unref()`。

### 辅助函数
- **`gr_ref_rp(T*)`** / **`gr_ref_rp(const T*)`**：创建 `gr_rp` 并对传入指针调用 `ref()`。

## 内部实现细节

### auto 函数指针
模板参数 `Ref` 和 `Unref` 使用 `auto` 而非显式的成员函数指针类型。这是因为如果函数定义在 `T` 的基类上，编译器需要正确的基类函数指针类型。使用 `auto` 让编译器自动推导正确的类型。

### SafeRef / SafeUnref
内部静态辅助函数，在调用 `Ref` / `Unref` 前检查指针非空，提供空安全性。

### release() 的可见性
`release()` 被标记为 `private` 并使用 `[[nodiscard]]`，仅在移动构造/赋值中使用，防止外部代码不安全地获取裸指针。

### 调试支持
析构函数中使用 `SkDEBUGCODE` 将指针置空，帮助在调试版本中检测使用已析构对象的错误。

## 依赖关系

- **Skia 核心**: `SkRefCnt`（`sk_sp`）、`SkAssert`
- **C++ 标准库**: `std::is_convertible`、`std::enable_if`

## 设计模式与设计决策

1. **策略模式**：通过模板参数传入引用/解引用函数指针，实现同一智能指针框架下的多种引用计数策略。
2. **双重引用计数**：`gr_cb` 实现了独立于标准引用计数的"命令缓冲区使用计数"，允许资源在逻辑释放后仍被 GPU 使用，支持 scratch 资源复用。
3. **回收 vs 销毁**：`gr_rp` 将 `unref` 替换为 `recycle`，使资源在引用计数归零时被回收到缓存池而非销毁。
4. **sk_sp 互操作**：显式支持从 `sk_sp` 的构造和赋值，便于在不同引用计数体系之间安全转换。

## 性能考量

- **零开销抽象**：`gr_sp` 的大小与裸指针相同（仅一个 `T*` 成员），模板内联使得引用计数操作无额外间接调用开销。
- **移动语义优化**：移动构造和赋值不调用任何引用计数函数，仅交换指针。
- **SafeRef/SafeUnref 内联**：标记为 `static inline`，编译器可完全内联消除空检查分支。

## 相关文件

- `include/core/SkRefCnt.h` - `sk_sp` 和 `SkRefCnt` 定义
- `src/gpu/ganesh/GrGpuResource.h` - GPU 资源基类，提供 `refCommandBuffer()/unrefCommandBuffer()`
- `src/gpu/graphite/Resource.h` - Graphite 资源基类
