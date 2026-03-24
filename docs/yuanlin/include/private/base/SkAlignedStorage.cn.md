# SkAlignedStorage

> 源文件: `include/private/base/SkAlignedStorage.h`

## 概述
SkAlignedStorage 提供了一个类模板,用于分配具有特定对齐要求的未初始化存储空间。它是一个轻量级的 RAII 容器,确保存储空间正确对齐到类型 T 的对齐边界,适用于需要延迟构造对象或手动控制对象生命周期的场景。

## 架构位置
该模板类位于 Skia 基础设施层的内存管理子系统中,属于底层工具类。它为需要手动内存管理的代码提供类型安全的对齐存储,常用于实现对象池、optional 类型、variant 类型等高级容器。

## 主要类与结构体

### SkAlignedSTStorage<N, T>
模板类,提供可存储 N 个类型 T 对象的对齐存储空间。

**模板参数**:
- `N` (int): 存储的对象数量
- `T` (typename): 对象类型,用于确定对齐要求

**继承关系**: 无基类 → SkAlignedSTStorage<N, T>

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fStorage | alignas(T) std::byte[sizeof(T) * N] | 对齐到 T 的对齐边界的字节数组 |

## 公共 API 函数

### 构造函数
```cpp
SkAlignedSTStorage()
```
- **功能**: 创建一个未初始化的存储对象
- **说明**: 不对存储空间进行任何初始化,调用者负责使用 placement new 构造对象

### 禁用的特殊成员函数
```cpp
SkAlignedSTStorage(SkAlignedSTStorage&&) = delete;
SkAlignedSTStorage(const SkAlignedSTStorage&) = delete;
SkAlignedSTStorage& operator=(SkAlignedSTStorage&&) = delete;
SkAlignedSTStorage& operator=(const SkAlignedSTStorage&) = delete;
```
- **说明**: 禁止拷贝和移动操作,确保存储对象不能被复制,避免不明确的所有权语义

### 访问方法

#### `void* get()`
- **功能**: 获取存储空间的 void 指针
- **返回值**: 指向存储空间的非 const void 指针
- **使用场景**: 与 placement new 配合使用构造对象

#### `const void* get() const`
- **功能**: 获取存储空间的 const void 指针
- **返回值**: 指向存储空间的 const void 指针

#### `std::byte* data()`
- **功能**: 获取存储空间的字节指针
- **返回值**: 指向存储空间的 std::byte 指针
- **使用场景**: 将存储视为字节数组进行低级操作

#### `const std::byte* data() const`
- **功能**: 获取存储空间的 const 字节指针
- **返回值**: 指向存储空间的 const std::byte 指针

#### `size_t size() const`
- **功能**: 获取存储空间的字节大小
- **返回值**: 存储空间的总字节数 (sizeof(T) * N)
- **实现**: 调用 `std::size(fStorage)`

## 内部实现细节

### 对齐机制
```cpp
alignas(T) std::byte fStorage[sizeof(T) * N];
```
- 使用 `alignas(T)` 说明符确保数组对齐到类型 T 的对齐要求
- 例如: `alignas(int64_t)` 确保 8 字节对齐
- 这对于包含对齐敏感类型(如 SIMD 类型、原子类型)的 T 至关重要

### 字节数组存储
- 使用 `std::byte` 而非 `char` 作为底层存储
- `std::byte` 更明确地表示"原始字节"语义
- 避免与字符类型的混淆

### 无初始化
- 构造函数不初始化 fStorage 数组
- 避免不必要的初始化开销
- 调用者负责使用 placement new 构造对象

### 容器接口
提供类似标准容器的接口:
- `data()`: 类似 std::vector::data()
- `size()`: 类似 std::vector::size()
- 便于在需要容器接口的上下文中使用

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| <cstddef> | std::byte 类型定义 |
| <iterator> | std::size 函数 |

### 被依赖的模块
- SkAutoTMalloc (栈上小对象优化)
- SkTLazy (延迟构造包装器)
- SkAnySubclass (类型擦除容器)
- 自定义内存分配器

## 设计模式与设计决策

### RAII 边界
仅管理存储空间的生命周期,不管理对象生命周期:
- 构造函数不调用 T 的构造函数
- 析构函数不调用 T 的析构函数
- 调用者完全控制对象的构造和销毁时机

### 类型安全的对齐
通过模板参数 T 自动推导对齐要求:
- 不需要手动指定对齐值
- 编译时保证正确对齐
- 类型安全,避免对齐错误

### 禁止复制
删除拷贝和移动操作避免:
- 存储空间的意外复制
- 对象所有权的混淆
- 需要移动语义时应在更高层实现

### 零开销抽象
- 仅是对原始数组的薄封装
- 编译器完全内联所有方法
- 零运行时开销

## 性能考量

### 编译时计算
- 大小和对齐在编译时确定
- 不需要运行时计算或查找
- 优化器可以完全展开

### 栈分配
- 通常在栈上分配
- 避免堆分配开销
- 自动生命周期管理

### 缓存友好
- 连续的内存布局
- 适合存储小型对象数组
- 提高空间局部性

### 内联优化
- 所有方法都是简单的内联函数
- 编译器可以完全优化掉函数调用
- 直接访问底层数组

## 使用场景

### Placement New 构造
```cpp
SkAlignedSTStorage<1, MyClass> storage;
MyClass* obj = new (storage.get()) MyClass(args);
// 使用 obj
obj->~MyClass();  // 手动析构
```

### 延迟初始化
```cpp
class LazyObject {
    SkAlignedSTStorage<1, ExpensiveObject> fStorage;
    bool fInitialized = false;

public:
    ExpensiveObject* get() {
        if (!fInitialized) {
            new (fStorage.get()) ExpensiveObject();
            fInitialized = true;
        }
        return reinterpret_cast<ExpensiveObject*>(fStorage.get());
    }
};
```

### 对象池
```cpp
template<typename T, int N>
class ObjectPool {
    SkAlignedSTStorage<N, T> fStorage;
    bool fUsed[N] = {false};

public:
    T* allocate() {
        for (int i = 0; i < N; ++i) {
            if (!fUsed[i]) {
                fUsed[i] = true;
                void* ptr = reinterpret_cast<std::byte*>(fStorage.data()) + i * sizeof(T);
                return new (ptr) T();
            }
        }
        return nullptr;
    }
};
```

### 栈上数组
```cpp
void processPoints() {
    SkAlignedSTStorage<128, SkPoint> pointStorage;
    SkPoint* points = reinterpret_cast<SkPoint*>(pointStorage.get());

    for (int i = 0; i < 128; ++i) {
        new (&points[i]) SkPoint{float(i), float(i)};
    }

    // 处理 points

    for (int i = 0; i < 128; ++i) {
        points[i].~SkPoint();
    }
}
```

## 相关文件
| 文件 | 关系 |
|------|------|
| include/private/base/SkTLazy.h | 使用 SkAlignedStorage 实现延迟构造 |
| include/private/base/SkAnySubclass.h | 类似的对齐存储实现 |
| include/private/base/SkAutoMalloc.h | 相关的内存管理工具 |

## 注意事项

### 对象生命周期管理
- **必须手动调用析构函数**: 存储对象不会自动销毁其中构造的对象
- **placement new 配对**: 每次 placement new 都需要对应的显式析构调用
- **异常安全**: 需要在异常处理中正确清理对象

### 类型转换
使用 `reinterpret_cast` 将 void* 转换为 T*:
```cpp
T* ptr = reinterpret_cast<T*>(storage.get());
```
确保只在已构造对象的情况下转换。

### 对齐要求
- 自动满足 T 的对齐要求
- 对于 over-aligned 类型(对齐要求超过 alignof(std::max_align_t)),确保编译器支持

### 数组索引
存储 N > 1 时,手动计算数组元素位置:
```cpp
T* array = reinterpret_cast<T*>(storage.get());
T* element = &array[index];  // 或 array + index
```

### C++17 废弃
标准库的 `std::aligned_storage` 在 C++23 中被废弃,SkAlignedStorage 提供了更简洁的替代方案。
