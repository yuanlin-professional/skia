# SkWeakRefCnt

> 源文件: `include/private/SkWeakRefCnt.h`

## 概述

SkWeakRefCnt 是一个引用计数基类,在 SkRefCnt 的基础上增加了弱引用支持。它允许对象被多个所有者共享,同时支持在对象不再被强引用持有时进入"已释放"状态,但弱引用仍然可以存在。这种机制对于实现缓存系统、打破循环引用和延迟资源清理非常有用。

## 架构位置

SkWeakRefCnt 位于 Skia 的核心内存管理层,是高级引用计数系统的组成部分。它继承自 SkRefCnt,为需要弱引用语义的对象提供了基础设施。该类主要用于纹理缓存、字体管理和其他需要复杂生命周期管理的子系统。

## 主要类与结构体

### SkWeakRefCnt

提供强引用和弱引用的双重引用计数管理。

**继承关系**: `SkRefCnt` → `SkWeakRefCnt`

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fRefCnt | std::atomic<int32_t> | 强引用计数(继承自 SkRefCnt) |
| fWeakCnt | std::atomic<int32_t> | 弱引用计数(本类新增) |

**引用计数不变式**:
```
fWeakCnt = #weak_refs + (fRefCnt > 0 ? 1 : 0)
```
即:弱引用计数 = 显式弱引用数 + (强引用存在时的隐式弱引用)

## 公共 API 函数

### 构造与析构

#### `SkWeakRefCnt()`
- **功能**: 默认构造函数,初始化强引用计数为 1,弱引用计数为 1
- **参数**: 无
- **说明**:
  - 强引用集体持有一个隐式弱引用
  - 初始状态只有构造者持有强引用

#### `~SkWeakRefCnt() override`
- **功能**: 析构函数,断言弱引用计数为 1
- **参数**: 无
- **说明**:
  - 只有在弱引用计数为 1 时才能安全析构
  - Debug 模式下会验证这个条件

### 强引用操作

#### `[[nodiscard]] bool try_ref() const`
- **功能**: 尝试从弱引用创建强引用
- **参数**: 无
- **返回值**:
  - true: 成功创建强引用,调用者现在持有额外的强引用
  - false: 强引用计数已为 0,无法创建强引用
- **说明**:
  - 调用者必须已经是所有者(持有强引用或弱引用)
  - 成功时需要调用 `unref()` 来释放新的强引用
  - 原有的弱引用仍需调用 `weak_unref()`
  - 比直接调用 `ref()` 开销更大

**使用示例**:
```cpp
SkWeakRefCnt* myRef = strongRef.weak_ref();
// ... strongRef.unref() 可能被调用
if (myRef->try_ref()) {
    // 使用 myRef,现在是强引用
    myRef->unref();
} else {
    // myRef 处于已释放状态
}
myRef->weak_unref();
```

### 弱引用操作

#### `void weak_ref() const`
- **功能**: 增加弱引用计数
- **参数**: 无
- **返回值**: 无
- **说明**:
  - 必须由 `weak_unref()` 调用平衡
  - 要求强引用计数和弱引用计数都大于 0
  - 无内存屏障,是轻量级操作

#### `void weak_unref() const`
- **功能**: 减少弱引用计数,计数归零时删除对象
- **参数**: 无
- **返回值**: 无
- **说明**:
  - 使用 acquire-release 内存序,确保线程安全
  - 当弱引用计数降到 1 时,调用对象的析构函数
  - 对象必须通过 new 分配,不能在栈上

#### `bool weak_expired() const`
- **功能**: 检查强引用是否已全部释放
- **参数**: 无
- **返回值**: true 表示所有强引用已释放,对象处于已释放状态
- **说明**:
  - 使用 relaxed 内存序,开销很小
  - 返回 true 后,`try_ref()` 将永远返回 false

### 调试辅助

#### `int32_t getWeakCnt() const` (仅 Debug 模式)
- **功能**: 获取当前弱引用计数
- **参数**: 无
- **返回值**: 当前的弱引用计数值
- **说明**: 仅在 SK_DEBUG 宏定义时可用,用于调试和断言

## 内部实现细节

### 原子操作与内存序

#### atomic_conditional_acquire_strong_ref()

这是 `try_ref()` 的核心实现,使用 compare-and-swap 循环:

```cpp
int32_t prev = fRefCnt.load(std::memory_order_relaxed);
do {
    if (0 == prev) {
        break;  // 强引用已释放,失败
    }
} while(!fRefCnt.compare_exchange_weak(prev, prev+1,
        std::memory_order_acquire,  // 成功时获取屏障
        std::memory_order_relaxed)); // 失败时无屏障
return prev;
```

**关键点**:
- **无锁算法**: 使用 CAS 避免互斥锁的开销
- **获取屏障**: 成功时确保后续代码不会重排到增加之前
- **快速失败**: 如果 prev 为 0,立即退出循环

### 生命周期状态转换

对象的生命周期有三个阶段:

1. **活跃状态**: fRefCnt > 0, fWeakCnt >= 1
   - 对象完全可用
   - 可以进行正常操作

2. **已释放状态**: fRefCnt = 0, fWeakCnt > 0
   - 强引用已全部释放
   - 调用了 `weak_dispose()`
   - 弱引用仍然存在
   - 对象定义的部分功能可能仍可用

3. **销毁状态**: fRefCnt = 0, fWeakCnt = 0
   - 调用析构函数
   - 对象内存被释放

### internal_dispose() 的处理流程

当强引用计数归零时:
1. 调用虚函数 `weak_dispose()`,让对象清理资源
2. 调用 `weak_unref()` 释放隐式弱引用
3. 如果这是最后一个弱引用,对象被删除

### 内存屏障策略

不同操作使用不同的内存序:
- **ref()**: release 屏障(阻止之前的写入重排到增加之后)
- **try_ref()**: acquire 屏障(阻止之后的读取重排到增加之前)
- **weak_ref()**: relaxed(无屏障,性能最优)
- **weak_unref()**: acq_rel(双向屏障,确保清理的可见性)

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `include/core/SkRefCnt.h` | 基类,提供强引用计数 |
| `include/core/SkTypes.h` | SK_API 等宏定义 |
| `<atomic>` | 原子操作 |
| `<cstdint>` | int32_t 类型 |

### 被依赖的模块

- **SkPathRef**: 路径引用使用弱引用避免循环依赖
- **GrGpuResource**: GPU 资源使用弱引用实现资源缓存
- **SkTypeface**: 字体使用弱引用管理字体缓存
- **纹理代理**: 延迟纹理创建使用弱引用

## 设计模式与设计决策

### 引用计数双层设计

分离强引用和弱引用的优势:
- **资源管理**: 强引用控制对象功能,弱引用控制内存
- **避免悬空指针**: 弱引用可以安全检测对象是否已释放
- **缓存友好**: 缓存可以持有弱引用,不阻止对象释放

### 隐式弱引用设计

强引用集体持有一个隐式弱引用的理由:
- **简化内存管理**: 确保强引用存在时对象不会被删除
- **延迟删除**: 对象释放可以分两个阶段:功能释放和内存释放
- **避免竞态**: 强引用释放时不会立即删除对象

### weak_dispose() 虚函数

提供 `weak_dispose()` 钩子的原因:
- **自定义清理**: 允许派生类定义"已释放"状态的行为
- **资源解耦**: 可以在强引用释放时清理资源,但保留对象结构
- **缓存支持**: 对象可以标记自己"已失效",但仍可查询元信息

### try_ref() 的必要性

为什么需要 `try_ref()` 而不只用 `ref()`:
- **线程安全**: 在多线程环境中,强引用可能在检查后立即释放
- **弱引用语义**: 弱引用不能直接升级为强引用,需要尝试
- **失败处理**: 提供了检测对象已释放的机制

## 性能考量

### 原子操作开销

- **try_ref()**: 需要 CAS 循环,比普通 `ref()` 慢
- **weak_ref()**: 只需一次 relaxed 原子增加,很快
- **weak_unref()**: 需要 acq_rel 屏障,中等开销

### 缓存行抖动

fRefCnt 和 fWeakCnt 在同一个对象中:
- **优点**: 局部性好,通常在同一缓存行
- **缺点**: 可能导致 false sharing(如果多线程频繁访问)

### 使用建议

- **高频访问**: 尽量持有强引用,避免频繁 `try_ref()`
- **缓存场景**: 使用弱引用,但在实际使用前升级为强引用
- **单线程优化**: 如果确定单线程,可以直接检查 `weak_expired()`

## 典型应用场景

### 纹理缓存

```cpp
// 缓存持有弱引用
std::map<Key, sk_sp<SkWeakRefCnt>> textureCache;

// 查找时尝试升级
if (auto cached = cache[key]) {
    if (cached->try_ref()) {
        return cached;  // 成功复用
    }
}
// 缓存失效,创建新纹理
```

### 打破循环引用

```cpp
class Parent : public SkRefCnt {
    sk_sp<Child> fChild;  // 强引用
};

class Child : public SkWeakRefCnt {
    SkWeakRefCnt* fParent;  // 弱引用,避免循环
};
```

### 延迟资源清理

```cpp
void weak_dispose() const override {
    // 释放 GPU 资源
    fTexture.reset();
    // 但保留 CPU 端元数据
}
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/core/SkRefCnt.h` | 基类,提供强引用计数机制 |
| `src/core/SkPathRef.cpp` | 使用 SkWeakRefCnt 实现路径引用 |
| `src/gpu/ganesh/GrGpuResource.h` | GPU 资源使用弱引用 |
| `include/core/SkTypeface.h` | 字体使用弱引用管理缓存 |
| `src/core/SkResourceCache.cpp` | 资源缓存使用弱引用 |
