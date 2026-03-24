# SkRecord

> 源文件: src/core/SkRecord.h, src/core/SkRecord.cpp

## 概述

`SkRecord` 是 Skia 录制系统的核心容器,用于存储 Canvas 调用的序列。它是一个类型安全的异构数组,可以存储来自 `SkRecords` 命名空间的任意命令类型。`SkRecord` 提供了高效的内存分配、多态访问和命令修改功能,是实现延迟渲染、优化和序列化的基础数据结构。

## 架构位置

`SkRecord` 位于 Skia 绘图引擎的录制层核心:
- 由 `SkRecordCanvas` 填充命令
- 被 `SkRecordDraw` 回放到 Canvas
- 被 `SkRecordOpts` 优化
- 被 `SkRecordedDrawable` 和 `SkBigPicture` 持有
- 提供统一的命令序列存储抽象

## 主要类与结构体

### SkRecord

**继承关系:**
```
SkRefCnt
  └── SkRecord
```

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fRecords` | `AutoTMalloc<Record>` | 命令指针和类型的数组 |
| `fCount` | `int` | 当前命令数量 |
| `fReserved` | `int` | 已分配的容量 |
| `fAlloc` | `SkArenaAlloc` | Arena 内存分配器,默认 256 字节块 |
| `fApproxBytesAllocated` | `size_t` | 近似已分配字节数 |

### Record (内部结构体)

**功能:** 封装类型擦除的命令指针。

**成员:**
- `SkRecords::Type fType`: 命令类型 ID
- `void* fPtr`: 指向实际命令的指针

**关键方法:**

```cpp
template <typename T>
T* set(T* ptr);  // 设置类型和指针

template <typename F>
auto visit(F&& f) const;  // 多态访问(const)

template <typename F>
auto mutate(F&& f);  // 多态修改(non-const)
```

### Destroyer (内部结构体)

**功能:** 析构命令对象的仿函数。

```cpp
struct Destroyer {
    template <typename T>
    void operator()(T* record) { record->~T(); }
};
```

## 公共 API 函数

### 构造与析构

```cpp
SkRecord() = default;
~SkRecord() override;
```

析构函数遍历所有命令并调用其析构函数。

### count

```cpp
int count() const
```
返回记录的命令数量。

### visit

```cpp
template <typename F>
auto visit(int i, F&& f) const -> decltype(f(SkRecords::NoOp()))
```

**功能:** 用仿函数 `f` 访问第 `i` 个命令(const 版本)。

**仿函数接口:**
```cpp
template <typename T>
R operator()(const T& record) { ... }
```

**实现:** 通过 switch-case 分发到具体类型。

### mutate

```cpp
template <typename F>
auto mutate(int i, F&& f) -> decltype(f((SkRecords::NoOp*)nullptr))
```

**功能:** 用仿函数 `f` 修改第 `i` 个命令(non-const 版本)。

**仿函数接口:**
```cpp
template <typename T>
R operator()(T* record) { ... }
```

### alloc

```cpp
template <typename T>
T* alloc(size_t count = 1)
```

**功能:** 从 arena 分配 `count` 个 `T` 类型的连续空间。

**特点:**
- 支持任意类型,不限于 `SkRecords::*`
- 内存由 `SkRecord` 管理,析构时释放
- 失败时抛出异常
- 更新 `fApproxBytesAllocated`

### append

```cpp
template <typename T>
T* append()
```

**功能:** 添加新命令到末尾,返回可用于 placement new 的指针。

**流程:**
1. 检查容量,必要时调用 `grow()`
2. 分配命令对象(如果非空类型)
3. 在 `fRecords` 中存储指针和类型
4. 增加 `fCount`

### replace

```cpp
template <typename T>
T* replace(int i)
```

**功能:** 用新类型 `T` 替换第 `i` 个命令。

**流程:**
1. 析构旧命令
2. 分配新命令
3. 更新 `fRecords[i]`

**注意:** 旧命令的引用将失效。

### bytesUsed

```cpp
size_t bytesUsed() const
```

返回对象占用的总字节数:
- `fApproxBytesAllocated`(arena 分配的数据)
- `sizeof(SkRecord)`(对象自身)

### defrag

```cpp
void defrag()
```

**功能:** 移除所有 `NoOp` 命令,压缩记录。

**实现:** 使用 `std::remove_if`:
```cpp
Record* noops = std::remove_if(fRecords.get(), fRecords.get() + fCount,
                                [](Record op) { return op.type() == SkRecords::NoOp_Type; });
fCount = noops - fRecords.get();
```

**效果:**
- 改变命令索引
- 保持命令顺序
- 可能改变 `count()`

## 内部实现细节

### grow 方法

```cpp
void grow()
```

**容量增长策略:**
- 初始容量: 4
- 增长因子: 2x
- 使用 `realloc` 避免拷贝

### allocCommand 方法

```cpp
template <typename T>
std::enable_if_t<std::is_empty<T>::value, T*> allocCommand();

template <typename T>
std::enable_if_t<!std::is_empty<T>::value, T*> allocCommand();
```

**优化:** 空类型(如 `NoOp`)返回单例,节省内存。

### Record::visit/mutate 实现

使用宏生成的 switch 语句实现类型分发:

```cpp
#define CASE(T) case SkRecords::T##_Type: return f(*(const SkRecords::T*)this->ptr());
switch(this->type()) { SK_RECORD_TYPES(CASE) }
#undef CASE
```

### Arena 分配器优势

- 批量分配减少系统调用
- 局部性好,提高缓存命中率
- 一次性释放所有内存,快速析构

### 内存对齐

`alloc` 使用 `alignas(T)` 确保正确对齐:
```cpp
struct RawBytes {
    alignas(T) char data[sizeof(T)];
};
```

### 类型安全保证

- `set` 方法断言类型和指针匹配
- `visit/mutate` 的 switch 涵盖所有 `SK_RECORD_TYPES`
- `SkDEBUGFAIL` 捕获不应到达的分支

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| `SkRecords` | 命令类型定义 |
| `SkArenaAlloc` | 内存分配器 |
| `SkRefCnt` | 引用计数基类 |
| `SkTemplates` | AutoTMalloc 模板 |

**被依赖的模块:**

| 模块 | 关系 |
|------|------|
| `SkRecordCanvas` | 填充命令 |
| `SkRecordDraw` | 回放命令 |
| `SkRecordOpts` | 优化命令 |
| `SkRecordedDrawable` | 持有记录 |
| `SkBigPicture` | 持有记录 |
| `SkRecordPattern` | 模式匹配 |

## 设计模式与设计决策

### 1. 类型擦除(Type Erasure)
通过 `void*` 和类型 ID 实现异构容器,同时保持类型安全。

### 2. 访问者模式(Visitor Pattern)
`visit` 和 `mutate` 允许外部代码对命令进行多态操作,无需了解具体类型。

### 3. Arena 分配器(Arena Allocator)
批量分配和一次性释放,优化频繁的小对象分配。

### 4. RAII(Resource Acquisition Is Initialization)
析构函数自动清理所有命令和内存。

### 5. 引用计数(Reference Counting)
继承 `SkRefCnt` 允许多个对象共享同一 `SkRecord`。

### 6. 单例模式(Singleton)
空类型命令返回单例,节省内存。

### 7. 增长策略
2x 增长因子平衡内存使用和重分配次数。

## 性能考量

### 1. 内存局部性
Arena 分配器将命令数据紧密排列,提高缓存命中率。

### 2. 避免虚函数
使用类型 ID 和 switch 分发,比虚表更高效。

### 3. 延迟清理
`replace` 和优化过程原地标记 `NoOp`,统一由 `defrag` 清理。

### 4. 智能增长
初始容量 4 避免小场景的浪费,2x 增长避免频繁重分配。

### 5. 空类型优化
`NoOp` 等空命令不占用 arena 内存。

### 6. 内存追踪
`fApproxBytesAllocated` 提供快速的内存使用估算。

### 7. 对齐保证
正确对齐避免硬件异常和性能惩罚。

### 8. defrag 效率
使用 `std::remove_if` 单次遍历完成清理,时间复杂度 O(n)。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `src/core/SkRecords.h` | 命令类型定义 |
| `src/core/SkRecordCanvas.h` | 录制命令 |
| `src/core/SkRecordDraw.h` | 回放命令 |
| `src/core/SkRecordOpts.h` | 优化命令 |
| `src/core/SkRecordPattern.h` | 模式匹配 |
| `src/core/SkRecordedDrawable.h` | 持有 SkRecord |
| `src/core/SkBigPicture.h` | 持有 SkRecord |
| `src/base/SkArenaAlloc.h` | Arena 分配器 |
| `include/core/SkRefCnt.h` | 引用计数基类 |
| `include/private/base/SkTemplates.h` | AutoTMalloc |
