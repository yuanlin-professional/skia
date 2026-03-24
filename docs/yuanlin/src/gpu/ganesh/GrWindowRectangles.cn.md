# GrWindowRectangles

> 源文件: src/gpu/ganesh/GrWindowRectangles.h

## 概述

`GrWindowRectangles` 是 Skia Ganesh GPU 后端中用于管理窗口矩形集合的轻量级容器类。它支持高效地存储和操作最多 8 个矩形区域,主要用于实现高级裁剪功能,特别是在模板缓冲区裁剪之外提供额外的矩形裁剪能力。

该类采用小对象优化策略:单个矩形存储在栈上,多个矩形时使用引用计数的堆分配。支持写时复制(copy-on-write)机制,确保数据共享的高效性和安全性。

## 架构位置

`GrWindowRectangles` 在 Ganesh 裁剪系统中的位置:

- **上层**: 被 `GrWindowRectsState` 和裁剪栈使用
- **同层**: 与 `GrClip` 相关组件协作
- **下层**: 依赖 `GrNonAtomicRef` 实现引用计数

该类是裁剪功能的基础数据结构,为上层提供高效的矩形集合管理。

## 主要类与结构体

### GrWindowRectangles 类

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fCount` | `int` | 矩形数量 |
| `fLocalWindow` / `fRec` | `union` | 联合体:单矩形或多矩形指针 |

**联合体设计**:
```cpp
union {
    SkIRect   fLocalWindow;  // 当 fCount <= 1 时使用
    Rec*      fRec;          // 当 fCount > 1 时使用
};
```

**小对象优化**: 0-1 个矩形时避免堆分配。

### Rec 内部结构体

表示多个矩形的存储。

**继承关系**: 继承自 `GrNonAtomicRef<Rec>`,支持引用计数。

**关键成员**:
```cpp
struct Rec : public GrNonAtomicRef<Rec> {
    Rec(const SkIRect* windows, int numWindows);
    Rec() = default;

    SkIRect fData[kMaxWindows];  // 固定大小数组
};
```

**容量**: 固定支持最多 8 个矩形。

**构造函数**:
```cpp
Rec(const SkIRect* windows, int numWindows) {
    SkASSERT(numWindows <= kMaxWindows);
    memcpy(fData, windows, sizeof(SkIRect) * numWindows);
}
```

## 公共 API 函数

### 构造和析构

```cpp
GrWindowRectangles()                                    // 默认构造:空集合
GrWindowRectangles(const GrWindowRectangles& that)     // 拷贝构造
~GrWindowRectangles()                                   // 析构:释放引用
```

**析构实现**:
```cpp
~GrWindowRectangles() { SkSafeUnref(this->rec()); }
```

安全释放引用计数对象。

### 查询函数

```cpp
bool empty() const                 // 是否为空
int count() const                  // 矩形数量
const SkIRect* data() const        // 获取矩形数组指针
```

**data() 实现**:
```cpp
const SkIRect* data() const {
    return fCount <= 1 ? &fLocalWindow : fRec->fData;
}
```

根据存储模式返回不同指针。

### 修改函数

```cpp
void reset()                                        // 清空集合
SkIRect& addWindow(const SkIRect& window)          // 添加矩形并返回引用
SkIRect& addWindow()                               // 添加空矩形并返回引用
```

### 变换函数

```cpp
GrWindowRectangles makeOffset(int dx, int dy) const
```

**功能**: 创建偏移后的矩形集合。

**优化**: 如果偏移为零,直接返回自身副本。

### 运算符重载

```cpp
GrWindowRectangles& operator=(const GrWindowRectangles&)
bool operator==(const GrWindowRectangles&) const
bool operator!=(const GrWindowRectangles&) const
```

## 内部实现细节

### 小对象优化实现

**单矩形场景**:
```cpp
if (fCount == 0) {
    fCount = 1;
    return fLocalWindow;  // 直接使用栈上的矩形
}
```

**转换到多矩形**:
```cpp
if (fCount == 1) {
    fRec = new Rec(&fLocalWindow, 1);  // 创建堆对象
}
```

### 写时复制机制

```cpp
if (!fRec->unique()) {  // 检查引用计数
    fRec->unref();
    fRec = new Rec(fRec->fData, fCount);  // 拷贝数据
}
```

**触发时机**: 在添加新矩形时,如果 `Rec` 被共享,则先拷贝。

### makeOffset 实现

```cpp
GrWindowRectangles GrWindowRectangles::makeOffset(int dx, int dy) const {
    if (!dx && !dy) {
        return *this;  // 零偏移快速路径
    }
    GrWindowRectangles result;
    result.fCount = fCount;
    SkIRect* windows;
    if (result.fCount > 1) {
        result.fRec = new Rec();  // 分配新 Rec
        windows = result.fRec->fData;
    } else {
        windows = &result.fLocalWindow;
    }
    for (int i = 0; i < fCount; ++i) {
        windows[i] = this->data()[i].makeOffset(dx, dy);
    }
    return result;
}
```

**优化**: 按值返回,依赖 NRVO (Named Return Value Optimization)。

### 赋值操作符实现

```cpp
GrWindowRectangles& GrWindowRectangles::operator=(const GrWindowRectangles& that) {
    SkSafeUnref(this->rec());  // 释放当前引用
    fCount = that.fCount;
    if (fCount <= 1) {
        fLocalWindow = that.fLocalWindow;
    } else {
        fRec = SkRef(that.fRec);  // 共享引用
    }
    return *this;
}
```

**高效性**: 多矩形情况下只增加引用计数,不拷贝数据。

### 相等性比较

```cpp
bool GrWindowRectangles::operator==(const GrWindowRectangles& that) const {
    if (fCount != that.fCount) {
        return false;
    }
    if (fCount > 1 && fRec == that.fRec) {
        return true;  // 共享同一个 Rec,快速路径
    }
    return !fCount || !memcmp(this->data(), that.data(), sizeof(SkIRect) * fCount);
}
```

**优化**:
1. 先比较数量
2. 共享 `Rec` 时直接返回 `true`
3. 最后使用 `memcmp` 比较内容

### addWindow 实现

```cpp
SkIRect& GrWindowRectangles::addWindow() {
    SkASSERT(fCount < kMaxWindows);
    if (fCount == 0) {
        fCount = 1;
        return fLocalWindow;
    }
    if (fCount == 1) {
        fRec = new Rec(&fLocalWindow, 1);
    } else if (!fRec->unique()) {
        fRec->unref();
        fRec = new Rec(fRec->fData, fCount);
    }
    return fRec->fData[fCount++];
}
```

**流程**:
1. 空集合: 使用栈上的 `fLocalWindow`
2. 单矩形: 创建 `Rec` 并迁移数据
3. 多矩形共享: 执行写时复制
4. 多矩形独占: 直接添加

### reset 实现

```cpp
void reset() {
    SkSafeUnref(this->rec());  // 释放引用(如果有)
    fCount = 0;
}
```

**简洁性**: 单行实现,依赖引用计数自动清理。

### rec 辅助方法

```cpp
const Rec* rec() const {
    return fCount <= 1 ? nullptr : fRec;
}
```

**作用**: 统一访问 `Rec` 指针,处理单矩形情况。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkIRect` | 整数矩形定义 |
| `GrNonAtomicRef` | 非原子引用计数基类 |
| `SkRefCnt` | 引用计数工具(SkRef/SkSafeUnref) |
| `<cstring>` | memcpy/memcmp 函数 |

### 被依赖的模块

该类被以下模块使用:
- `GrWindowRectsState`: 封装窗口矩形状态
- `GrClip`: 裁剪系统
- `GrOpsTask`: 渲染任务裁剪
- 硬件加速的窗口裁剪功能

## 设计模式与设计决策

### 小对象优化 (Small Object Optimization)

单矩形存储在对象内部:

**优点**:
- 避免堆分配
- 提高缓存局部性
- 减少内存碎片

**权衡**: 对象大小固定为 `sizeof(SkIRect) + sizeof(int)` (单矩形) 或 `sizeof(Rec*) + sizeof(int)` (多矩形)。

### 写时复制 (Copy-On-Write)

共享的 `Rec` 在修改时才拷贝:

**优点**:
- 拷贝操作只增加引用计数,O(1)
- 不修改时共享内存
- 延迟拷贝到真正需要时

**适用场景**: 裁剪状态经常被拷贝但很少修改。

### 引用计数

使用 `GrNonAtomicRef` 而非 `SkRefCnt`:

**原因**: 窗口矩形通常在单线程中使用,非原子操作更快。

**风险**: 不能跨线程共享。

### 容量限制

硬编码最大 8 个矩形:

**理由**:
- GPU 硬件通常限制窗口矩形数量
- 固定大小简化内存管理
- 8 个足够大多数裁剪场景

### 联合体节省内存

`union` 共用内存:
- 单矩形: `sizeof(SkIRect)` = 16 字节
- 多矩形: `sizeof(Rec*)` = 8 字节

**节省**: 单矩形场景下,总大小约 20 字节(联合体 + 计数)。

## 性能考量

### 栈分配的优势

单矩形情况:
- 无堆分配开销
- 缓存友好
- 构造/析构快速

### 引用计数的开销

拷贝操作:
- 只增加引用计数(一条原子指令)
- 不拷贝矩形数据

修改操作:
- 检查引用计数
- 需要时拷贝(O(n),n <= 8)

### memcpy/memcmp 优化

矩形数据连续存储:
- 利用 CPU 的批量拷贝指令
- 现代 CPU 高度优化这些函数

### 快速路径

`operator==` 的快速路径:
```cpp
if (fCount > 1 && fRec == that.fRec) {
    return true;  // 指针比较,极快
}
```

避免内容比较。

### 固定大小数组

`fData[kMaxWindows]` 固定大小:
- 无动态分配
- 无容量检查
- 内存布局简单

### NRVO 优化

`makeOffset` 返回值优化:
- 编译器消除临时对象
- 直接在目标位置构造

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/core/SkRect.h` | 矩形定义 |
| `src/gpu/ganesh/GrNonAtomicRef.h` | 非原子引用计数 |
| `include/core/SkRefCnt.h` | 引用计数工具 |
| `include/private/base/SkAssert.h` | 断言宏 |
| `src/gpu/ganesh/GrWindowRectsState.h` | 使用该类的状态封装 |
