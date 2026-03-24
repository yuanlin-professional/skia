# SkTLazy

> 源文件: src/base/SkTLazy.h

## 概述

`SkTLazy` 是 Skia 中提供延迟初始化(lazy initialization)功能的模板类库。它包含两个核心类:`SkTLazy<T>` 和 `SkTCopyOnFirstWrite<T>`,前者实现了延迟构造对象的能力,后者实现了写时复制(copy-on-write)模式。这些工具能够优化不必要的对象构造和复制,提升性能并减少内存使用。

模块基于 C++17 的 `std::optional` 实现,提供了类型安全的延迟初始化机制。在很多场景下,对象可能并不需要被创建或修改,使用延迟初始化可以避免不必要的开销。

## 架构位置

```
src/base/
├── SkTLazy.h            // 延迟初始化模板类
└── (其他基础工具)
    ↓
src/core/
├── SkPaint.cpp          // 使用延迟初始化优化
├── SkCanvas.cpp         // 使用写时复制模式
└── SkPath.cpp           // 路径操作中的延迟构造
```

该模块是基础设施层的工具类,被 Skia 核心渲染代码广泛使用,特别是在需要条件性构造对象的场景中。

## 主要类与结构体

### SkTLazy<T>

延迟初始化容器,在需要时才构造 T 类型对象。

**继承关系:**
- 无继承关系(独立模板类)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fValue | std::optional<T> | 存储实际对象的可选容器 |

### SkTCopyOnFirstWrite<T>

写时复制容器,初始持有常量对象的指针,仅在第一次写入时复制对象。

**继承关系:**
- 无继承关系(独立模板类)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fObj | const T* | 指向当前对象的指针(只读) |
| fLazy | std::optional<T> | 存储复制后的可写对象 |

## 公共 API 函数

### SkTLazy<T> 类方法

| 方法 | 功能说明 |
|------|---------|
| `SkTLazy()` | 默认构造,不创建对象 |
| `explicit SkTLazy(const T* src)` | 从源对象复制构造(可选) |
| `T* init(Args&&... args)` | 原位构造对象,销毁旧对象 |
| `T* set(const T& src)` | 复制赋值对象 |
| `T* set(T&& src)` | 移动赋值对象 |
| `void reset()` | 销毁对象,恢复未初始化状态 |
| `bool isValid() const` | 检查是否已初始化 |
| `T* get()` / `const T* get() const` | 获取对象指针(必须已初始化) |
| `T* getMaybeNull()` | 安全获取指针,未初始化返回 nullptr |
| `T* operator->()` | 指针访问运算符 |
| `T& operator*()` | 解引用运算符 |

### SkTCopyOnFirstWrite<T> 类方法

| 方法 | 功能说明 |
|------|---------|
| `explicit SkTCopyOnFirstWrite(const T& initial)` | 构造,初始指向常量对象 |
| `SkTCopyOnFirstWrite()` | 默认构造,延迟初始化 |
| `void init(const T& initial)` | 初始化指向的对象(仅用于默认构造后) |
| `void initIfNeeded(Args&&... args)` | 如果未初始化则原位构造 |
| `T* writable()` | 获取可写指针,首次调用时复制对象 |
| `const T* get() const` | 获取只读指针 |
| `const T* operator->() const` | 常量指针访问 |
| `operator const T*() const` | 隐式转换为常量指针 |
| `const T& operator*() const` | 解引用为常量引用 |

## 内部实现细节

### SkTLazy 实现机制

`SkTLazy` 本质上是对 `std::optional<T>` 的封装,提供更符合 Skia 习惯的接口:

```cpp
template <typename T>
class SkTLazy {
    template <typename... Args>
    T* init(Args&&... args) {
        fValue.emplace(std::forward<Args>(args)...);  // 原位构造
        return this->get();
    }

    void reset() {
        fValue.reset();  // 调用析构函数
    }

    bool isValid() const {
        return fValue.has_value();
    }
};
```

**关键设计**:
- 使用 `emplace` 进行原位构造,避免额外的移动或复制
- `set` 方法总是返回同一个指针,方便链式调用
- 提供 `getMaybeNull` 作为安全访问方式

### SkTCopyOnFirstWrite 实现机制

写时复制模式的核心逻辑:

```cpp
T* writable() {
    SkASSERT(fObj);
    if (!fLazy.has_value()) {
        fLazy = *fObj;           // 首次写入时复制
        fObj = &fLazy.value();   // 更新指针
    }
    return &fLazy.value();
}
```

**状态转换**:
1. **初始状态**: `fObj` 指向外部常量对象,`fLazy` 为空
2. **首次写入**: 复制对象到 `fLazy`,更新 `fObj` 指向副本
3. **后续写入**: 直接返回 `fLazy` 中的对象

### 赋值运算符特殊处理

```cpp
SkTCopyOnFirstWrite& operator=(const SkTCopyOnFirstWrite& that) {
    fLazy = that.fLazy;
    fObj  = fLazy.has_value() ? &fLazy.value() : that.fObj;
    return *this;
}
```

复制时需要判断:
- 如果源对象已经复制过(`fLazy` 有值),则复制副本
- 否则,共享源对象的常量指针

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| include/private/base/SkAssert.h | 断言检查 |
| optional (C++17) | 底层存储实现 |
| utility | std::forward, std::move |

**被依赖的模块:**

| 模块 | 使用场景 |
|------|---------|
| src/core/SkPaint.cpp | 延迟构造复杂的绘制属性 |
| src/core/SkCanvas.cpp | 保存/恢复状态时的写时复制 |
| src/core/SkPath.cpp | 路径操作中的临时对象 |
| src/gpu/ | GPU 资源的延迟初始化 |

## 设计模式与设计决策

### 延迟初始化模式

`SkTLazy` 实现了经典的延迟初始化模式:
- **动机**: 对象可能永远不会被使用,避免不必要的构造开销
- **适用场景**: 构造成本高的对象、条件性使用的对象
- **权衡**: 增加了检查开销,但通常值得

### 写时复制模式(COW)

`SkTCopyOnFirstWrite` 实现了写时复制模式:
- **动机**: 多数情况下对象是只读的,只在修改时才需要副本
- **适用场景**: 函数参数传递、状态保存/恢复
- **优势**: 避免不必要的复制,共享常量数据

**使用场景示例**:
```cpp
void processObject(const Thing& thing) {
    SkTCopyOnFirstWrite<Thing> workingCopy(&thing);

    // 只读访问,无复制
    if (workingCopy->needsProcessing()) {
        // 首次写入时才复制
        workingCopy.writable()->modify();
    }

    return *workingCopy;  // 可能是原对象或副本
}
```

### RAII 资源管理

两个类都遵循 RAII 原则:
- 构造函数获取资源(或不获取)
- 析构函数自动释放资源
- 移动语义支持,避免不必要的复制

### 类型安全设计

- 使用模板提供编译时类型检查
- `get()` 要求对象已初始化(断言检查)
- `getMaybeNull()` 提供运行时安全访问

## 性能考量

### SkTLazy 性能特征

**优势**:
- 避免不必要的构造函数调用
- 无动态内存分配(对象存储在栈上)
- 编译器可以优化掉 `std::optional` 的开销

**开销**:
- 额外的 bool 标志(通常 1 字节,对齐后可能更多)
- 每次访问都需要检查 `has_value()`
- 增加代码大小(模板实例化)

### SkTCopyOnFirstWrite 性能特征

**最佳情况**(纯只读):
- 零复制开销
- 仅指针解引用,极低开销

**最坏情况**(总是写入):
- 一次完整的对象复制
- 比直接传值多一个条件分支

**适用场景**:
- 写入概率 < 50% 时有明显优势
- 对象复制成本越高,收益越大

### 内存布局

**SkTLazy 内存布局**:
```
| bool has_value | padding | T object |
```

**SkTCopyOnFirstWrite 内存布局**:
```
| const T* fObj | std::optional<T> fLazy |
```

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| include/private/base/SkAssert.h | 提供断言宏 |
| src/core/SkPaint.h | 使用 SkTLazy 管理可选属性 |
| src/core/SkCanvas.cpp | 使用 SkTCopyOnFirstWrite 优化状态保存 |
| src/core/SkDevice.h | 设备抽象中的延迟初始化 |

## 使用示例

```cpp
// 示例 1: SkTLazy 基本使用
SkTLazy<SkPaint> lazyPaint;

if (needsSpecialPaint) {
    SkPaint* paint = lazyPaint.init();  // 原位构造
    paint->setColor(SK_ColorRED);
}

if (lazyPaint.isValid()) {
    canvas->drawRect(rect, *lazyPaint);
}

// 示例 2: 条件性初始化
SkTLazy<ComplexObject> obj;
if (condition1) {
    obj.init(param1, param2);
} else if (condition2) {
    obj.set(existingObject);
}

// 示例 3: SkTCopyOnFirstWrite 只读场景
void drawShape(const SkPaint& paint) {
    SkTCopyOnFirstWrite<SkPaint> workingPaint(paint);

    // 只读访问,无复制
    if (workingPaint->getColor() == SK_ColorBLUE) {
        // 无修改,直接使用原对象
        canvas->drawRect(rect, *workingPaint);
    }
}

// 示例 4: SkTCopyOnFirstWrite 写入场景
void drawShapeWithModification(const SkPaint& paint) {
    SkTCopyOnFirstWrite<SkPaint> workingPaint(paint);

    // 首次写入时复制
    if (needsModification) {
        workingPaint.writable()->setAlpha(128);  // 触发复制
        workingPaint.writable()->setStrokeWidth(2.0f);  // 使用已复制的对象
    }

    canvas->drawRect(rect, *workingPaint);
}

// 示例 5: 延迟初始化参数
void processOptionalPath(const SkPath* optPath) {
    SkTLazy<SkPath> lazyPath;

    const SkPath* path = optPath;
    if (!path) {
        path = lazyPath.set(createDefaultPath());  // 仅在需要时创建
    }

    usePath(*path);
}

// 示例 6: 重复使用
SkTLazy<SkMatrix> matrix;
for (int i = 0; i < count; ++i) {
    if (needsTransform[i]) {
        matrix.init(transforms[i]);  // 每次都会销毁旧对象
        canvas->setMatrix(*matrix);
    }
    drawItem(i);
}

// 示例 7: 移动语义
SkTLazy<ExpensiveObject> createObject() {
    SkTLazy<ExpensiveObject> obj;
    obj.init(param1, param2);
    return obj;  // 移动构造,无复制
}
```

## 注意事项

### SkTLazy 使用注意

1. **生命周期**: `get()` 返回的指针在 `reset()` 或 `init()` 后失效
2. **断言检查**: `get()` 和 `operator*` 在未初始化时会触发断言(debug 模式)
3. **线程安全**: 非线程安全,需要外部同步
4. **异常安全**: 如果 T 的构造函数抛异常,对象保持未初始化状态

### SkTCopyOnFirstWrite 使用注意

1. **初始对象生命周期**: 必须确保初始对象在使用期间有效
2. **写入检测**: 调用 `writable()` 即触发复制,即使未实际修改
3. **const 正确性**: 只能通过 `writable()` 修改,保持了 const 语义
4. **默认构造延迟**: 使用默认构造函数后必须调用 `init()` 才能使用

### 性能陷阱

1. **过度使用**: 简单对象使用延迟初始化可能得不偿失
2. **重复初始化**: `init()` 会销毁旧对象再构造新对象,有开销
3. **错误预期**: 如果对象总是被使用,延迟初始化反而增加开销
4. **写时复制误用**: 如果总是会写入,直接复制更高效

## 最佳实践

1. **适用对象**: 构造成本高、条件性使用的对象
2. **优先 SkTLazy**: 对于纯延迟初始化场景
3. **优先 SkTCopyOnFirstWrite**: 对于读多写少的场景
4. **安全访问**: 使用 `getMaybeNull()` 避免断言失败
5. **及时 reset**: 不再需要时调用 `reset()` 释放资源
6. **性能测试**: 在实际场景中测试是否真的提升性能
