# GrNonAtomicRef

> 源文件
> - src/gpu/ganesh/GrNonAtomicRef.h

## 概述

`GrNonAtomicRef` 是 Ganesh GPU 后端中提供的一个轻量级、非线程安全的引用计数模板类。它专门用于不需要线程安全保证的场景，通过避免原子操作的开销来提高性能。该模板类使用 CRTP（Curiously Recurring Template Pattern）模式，允许子类定制删除行为，是 Skia 中对性能敏感的内部对象的引用计数基础设施。

## 架构位置

`GrNonAtomicRef` 位于 Ganesh 资源管理层的基础设施中，为单线程或明确知道不会跨线程访问的对象提供引用计数：

```
SkRefCnt (线程安全，原子引用计数)
    │
    ├── 公共 API 对象（多线程安全）
    │
    └── GrNonAtomicRef (非线程安全，性能优化)
        │
        ├── GPU 内部对象
        ├── 临时中间数据结构
        └── 单线程上下文专用对象
```

它是针对已知单线程使用场景的优化替代方案。

## 主要类与结构体

### GrNonAtomicRef<TSubclass>

模板基类，为子类提供非原子引用计数功能。

**模板参数**
- `TSubclass`：继承此模板的子类类型（CRTP 模式）

**继承关系**
- 基类：`SkNoncopyable`（禁止复制）
- 子类：各种 Ganesh 内部类型

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fRefCnt` | `mutable int32_t` | 引用计数器（mutable 允许 const 方法修改） |

## 公共 API 函数

### 构造和析构

| 函数签名 | 说明 |
|----------|------|
| `GrNonAtomicRef()` | 构造函数，初始引用计数为 1 |
| `~GrNonAtomicRef()` | 析构函数（仅在 DEBUG 模式下定义，验证引用计数） |

### 引用计数操作

| 函数签名 | 说明 |
|----------|------|
| `void ref() const` | 增加引用计数 |
| `void unref() const` | 减少引用计数，为 0 时删除对象 |

### 状态查询

| 函数签名 | 说明 |
|----------|------|
| `bool unique() const` | 返回引用计数是否为 1 |
| `int refCnt() const` | 返回当前引用计数值 |

### 辅助函数

| 函数签名 | 说明 |
|----------|------|
| `template<typename T> void GrTDeleteNonAtomicRef(const T* ref)` | 删除非原子引用对象的辅助函数模板 |

## 内部实现细节

### CRTP 模式实现

使用 CRTP（Curiously Recurring Template Pattern）模式实现类型安全的删除：

```cpp
template<typename TSubclass> class GrNonAtomicRef : public SkNoncopyable {
public:
    void unref() const {
        SkASSERT(fRefCnt > 0);
        --fRefCnt;
        if (0 == fRefCnt) {
            GrTDeleteNonAtomicRef(static_cast<const TSubclass*>(this));
            return;
        }
    }
private:
    mutable int32_t fRefCnt;
};
```

关键特性：
- 模板参数 `TSubclass` 是子类类型
- `unref()` 中将 `this` 转换为 `TSubclass*`
- 允许子类定制删除行为（通过特化 `GrTDeleteNonAtomicRef`）

### 引用计数初始化

构造函数初始化引用计数为 1：

```cpp
GrNonAtomicRef() : fRefCnt(1) {}
```

这遵循"构造时已拥有一个引用"的语义，与 `SkRefCnt` 一致。

### ref() 实现

增加引用计数并进行防御性检查：

```cpp
void ref() const {
    // Once the ref cnt reaches zero it should never be ref'ed again.
    SkASSERT(fRefCnt > 0);
    ++fRefCnt;
}
```

断言确保不会在对象已销毁后重新引用。

### unref() 实现

减少引用计数，必要时删除对象：

```cpp
void unref() const {
    SkASSERT(fRefCnt > 0);
    --fRefCnt;
    if (0 == fRefCnt) {
        GrTDeleteNonAtomicRef(static_cast<const TSubclass*>(this));
        return;
    }
}
```

关键点：
- 检查引用计数必须大于 0
- 减量后检查是否为 0
- 为 0 时调用删除函数并立即返回

### 默认删除实现

提供默认的删除实现：

```cpp
template<typename T> inline void GrTDeleteNonAtomicRef(const T* ref) {
    delete ref;
}
```

可以为特定类型特化此模板以实现自定义删除行为（如对象池回收）。

### DEBUG 模式析构检查

在调试模式下验证析构时的引用计数：

```cpp
#ifdef SK_DEBUG
~GrNonAtomicRef() {
    // fRefCnt can be one when a subclass is created statically
    SkASSERT((0 == fRefCnt || 1 == fRefCnt));
    // Set to invalid values.
    fRefCnt = -10;
}
#endif
```

检查点：
- 引用计数应为 0（正常删除）或 1（静态对象）
- 设置为无效值 -10，帮助检测 use-after-free

### mutable 引用计数

`fRefCnt` 声明为 `mutable`：

```cpp
mutable int32_t fRefCnt;
```

这允许 `ref()` 和 `unref()` 声明为 `const`，符合引用计数的语义：
- 逻辑 const：对象的逻辑状态不变
- 物理 non-const：引用计数需要修改

### 禁止拷贝

继承自 `SkNoncopyable`：

```cpp
class GrNonAtomicRef : public SkNoncopyable { ... }
```

防止意外复制，因为引用计数对象不应该被复制。

## 依赖关系

### 依赖的模块

| 模块名 | 用途 |
|--------|------|
| `SkTypes.h` | Skia 基础类型定义 |
| `SkNoncopyable.h` | 禁止拷贝的基类 |
| `<cstdint>` | int32_t 类型 |

### 被依赖的模块

| 模块名 | 使用方式 |
|--------|----------|
| Ganesh 内部对象 | 作为基类提供引用计数 |
| 单线程资源 | 性能关键的内部数据结构 |
| 临时对象 | 短生命周期的中间对象 |

## 设计模式与设计决策

### CRTP（Curiously Recurring Template Pattern）

使用 CRTP 实现静态多态：

```cpp
template<typename TSubclass> class GrNonAtomicRef { ... }

class MyClass : public GrNonAtomicRef<MyClass> { ... }
```

优点：
- 零运行时开销（无虚函数）
- 类型安全的删除
- 允许定制删除行为

### 引用计数语义

遵循标准的引用计数语义：
- 构造时引用计数为 1
- `ref()` 增加计数
- `unref()` 减少计数，为 0 时删除
- `unique()` 检查独占所有权

这与 `SkRefCnt` 和 `std::shared_ptr` 的语义一致。

### 性能优化的权衡

选择非原子引用计数的权衡：

**优点**：
- 避免原子操作开销（可能是数十个 CPU 周期）
- 更好的缓存行为（无内存屏障）
- 更简单的代码生成

**缺点**：
- 不是线程安全的
- 要求明确的单线程使用保证
- 跨线程使用会导致数据竞争

### 防御性编程

多处使用断言验证不变量：

```cpp
SkASSERT(fRefCnt > 0);  // ref() 和 unref() 中
SkASSERT((0 == fRefCnt || 1 == fRefCnt));  // 析构函数中
```

这在开发和测试阶段捕获错误，零发布版开销。

### 可扩展的删除机制

通过模板函数 `GrTDeleteNonAtomicRef` 允许自定义删除：

```cpp
// 默认实现
template<typename T> inline void GrTDeleteNonAtomicRef(const T* ref) {
    delete ref;
}

// 可以为特定类型特化
template<> inline void GrTDeleteNonAtomicRef<MyPooledClass>(const MyPooledClass* ref) {
    g_pool->recycle(ref);  // 回收到对象池
}
```

这提供了类似虚析构函数的灵活性，但无运行时开销。

### const 正确性

`ref()` 和 `unref()` 声明为 `const`：

```cpp
void ref() const;
void unref() const;
```

这反映了引用计数的语义：
- 增加/减少引用不改变对象的逻辑状态
- 允许通过 `const` 指针管理生命周期
- 与智能指针的语义一致

### mutable 的合理使用

`fRefCnt` 使用 `mutable` 是少数合理的场景之一：
- 引用计数是实现细节，不是逻辑状态
- 允许 `const` 方法修改引用计数
- 符合 const 语义的逻辑含义

### 静态对象支持

析构函数允许引用计数为 1：

```cpp
// fRefCnt can be one when a subclass is created statically
SkASSERT((0 == fRefCnt || 1 == fRefCnt));
```

支持静态对象场景，这些对象可能永远不会被 `unref()`。

## 性能考量

### 非原子操作

最重要的性能优化是避免原子操作：

```cpp
// GrNonAtomicRef (快)
++fRefCnt;  // 简单的内存写入
--fRefCnt;  // 简单的内存写入

// SkRefCnt (慢)
fetch_add(&fRefCnt, 1, memory_order_relaxed);  // 原子操作
fetch_sub(&fRefCnt, 1, memory_order_acq_rel);  // 原子操作 + 内存屏障
```

性能差异：
- 非原子：1-2 个 CPU 周期
- 原子：10-50 个 CPU 周期（取决于架构和争用）

### 无虚函数开销

使用 CRTP 而不是虚函数：
- 无虚函数表指针（节省 8 字节/对象）
- 无虚函数调用（节省间接跳转）
- 编译器可以内联

### 紧凑的内存布局

对象大小最小化：
- 仅一个 `int32_t`（4 字节）
- 无虚函数表指针
- 总开销通常 4-8 字节（包括填充）

### 内联友好

所有方法在头文件中定义，完全可内联：

```cpp
void ref() const {
    SkASSERT(fRefCnt > 0);
    ++fRefCnt;
}
```

编译器可以：
- 完全内联 `ref()`/`unref()`
- 消除冗余的引用计数操作
- 优化掉未使用的 `unique()` 调用

### 分支预测友好

`unref()` 中的分支通常可预测：

```cpp
if (0 == fRefCnt) {
    GrTDeleteNonAtomicRef(static_cast<const TSubclass*>(this));
    return;
}
```

大多数 `unref()` 调用不会导致删除，分支预测器可以有效处理。

### 缓存友好性

非原子操作不需要内存屏障：
- 更好的指令流水线
- 减少缓存一致性流量
- 允许更激进的编译器优化

### 零发布版开销的断言

所有断言在发布版中被移除：

```cpp
SkASSERT(fRefCnt > 0);  // 发布版中零开销
```

提供调试保护而不影响性能。

### 使用场景

最适合以下场景：
- **单线程上下文**：对象只在一个线程中使用
- **临时对象**：短生命周期的中间结果
- **内部实现**：不暴露给外部的内部类
- **性能关键路径**：引用计数在热循环中

不适合：
- **跨线程对象**：会导致数据竞争
- **公共 API**：用户可能在多线程中使用
- **长生命周期**：可能在不同线程间传递

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `include/core/SkRefCnt.h` | 对比 | 线程安全的引用计数基类 |
| `include/private/base/SkNoncopyable.h` | 基类 | 禁止拷贝的基类 |
| `include/core/SkTypes.h` | 依赖 | Skia 基础类型和宏 |
| 各种 Ganesh 内部类 | 子类 | 使用 GrNonAtomicRef 的具体类型 |

## 使用示例

```cpp
// 定义使用非原子引用计数的类
class MyGaneshObject : public GrNonAtomicRef<MyGaneshObject> {
public:
    MyGaneshObject() { /* 引用计数自动初始化为 1 */ }

    void doSomething() { /* ... */ }
};

// 使用
void example() {
    // 创建对象，引用计数 = 1
    MyGaneshObject* obj = new MyGaneshObject();

    // 增加引用，引用计数 = 2
    obj->ref();

    // 检查是否独占
    if (obj->unique()) {
        // 不会执行，因为引用计数是 2
    }

    // 减少引用，引用计数 = 1
    obj->unref();

    // 再次减少，引用计数 = 0，对象被删除
    obj->unref();
}

// 自定义删除行为（可选）
class PooledObject : public GrNonAtomicRef<PooledObject> { /* ... */ };

template<>
inline void GrTDeleteNonAtomicRef<PooledObject>(const PooledObject* obj) {
    g_objectPool.recycle(const_cast<PooledObject*>(obj));
}
```

## 与 SkRefCnt 的比较

| 特性 | GrNonAtomicRef | SkRefCnt |
|------|----------------|----------|
| 线程安全 | 否 | 是 |
| 性能 | 更快（~10-50x） | 较慢 |
| 内存屏障 | 无 | 有 |
| 虚函数 | 无（CRTP） | 无 |
| 适用场景 | 单线程内部对象 | 多线程公共 API |
| 对象大小 | 4 字节 | 4 字节 |
| 内联能力 | 完全内联 | 完全内联 |
| 删除定制 | 模板特化 | 虚析构函数 |

选择指南：
- **使用 GrNonAtomicRef**：单线程、性能关键、内部实现
- **使用 SkRefCnt**：多线程、公共 API、安全第一
