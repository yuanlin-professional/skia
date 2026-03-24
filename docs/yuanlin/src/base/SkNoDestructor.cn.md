# SkNoDestructor

> 源文件: src/base/SkNoDestructor.h

## 概述

`SkNoDestructor` 是 Skia 中用于管理函数局部静态变量的 RAII 包装类，其核心特性是**永不调用析构函数**。它主要用于解决具有非平凡析构函数的静态变量的析构顺序问题，是 Chromium `base::NoDestructor` 的改编版本。该类通过跳过析构函数的调用，避免了全局/静态对象析构时可能出现的顺序依赖问题和内存泄漏检测的误报。

这个工具类特别适合用于单例模式、全局配置对象、线程安全的静态初始化等场景，确保对象在整个程序生命周期内都可用。

## 架构位置

`SkNoDestructor` 位于 Skia 基础设施层的内存管理模块中：

- **层级**: src/base（基础工具层）
- **用途**: 管理函数局部静态变量，避免全局析构器
- **应用场景**: 单例、全局配置、线程安全的延迟初始化

在 Skia 架构中，它是一个底层工具，被需要静态存储期但禁止析构的对象使用。

## 主要类与结构体

### SkNoDestructor<T>

永不析构的对象包装模板类。

**继承关系**:
- 无继承关系

**模板参数**:
- `T`: 被包装的类型（必须非平凡析构）

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fStorage` | `alignas(T) std::byte[sizeof(T)]` | 原始字节数组，用于存储 T 的实例 |
| `fStoragePtr` (仅 LSan/ASan) | `T*` | 指向 placement-new 对象的指针，辅助泄漏检测器 |

## 公共 API 函数

### 构造函数

```cpp
// 转发参数构造
template <typename... Args>
explicit SkNoDestructor(Args&&... args);

// 拷贝构造（T 的拷贝）
explicit SkNoDestructor(const T& x);

// 移动构造（T 的移动）
explicit SkNoDestructor(T&& x);
```

**特点**:
- 使用 placement-new 在 `fStorage` 中构造对象
- 支持完美转发，可传递任意构造参数
- 显式构造，防止隐式转换

### 析构函数

```cpp
~SkNoDestructor() = default;
```

**关键特性**:
- **不调用 T 的析构函数**
- 对象内存在程序结束时被操作系统回收
- 这是类的核心设计目的

### 访问操作符

```cpp
const T& operator*() const;
T& operator*();

const T* operator->() const;
T* operator->();
```

**用途**:
- 像智能指针一样访问被包装的对象
- 提供引用和指针访问方式

### 获取指针

```cpp
const T* get() const;
T* get();
```

**用途**:
- 直接获取对象指针

### 禁用的操作

```cpp
SkNoDestructor(const SkNoDestructor&) = delete;             // 禁用拷贝
SkNoDestructor& operator=(const SkNoDestructor&) = delete;  // 禁用赋值
```

**原因**:
- 拷贝会导致多个实例管理同一块内存
- 静态对象不应该被复制

## 内部实现细节

### 构造函数实现

```cpp
template <typename... Args>
explicit SkNoDestructor(Args&&... args) {
    new (fStorage) T(std::forward<Args>(args)...);
}

explicit SkNoDestructor(const T& x) {
    new (fStorage) T(x);
}

explicit SkNoDestructor(T&& x) {
    new (fStorage) T(std::move(x));
}
```

**要点**:
- 使用 placement-new 在预分配的内存中构造对象
- `std::forward` 保持参数的值类别（左值/右值）
- 直接在 `fStorage` 上构造，无堆分配

### 访问器实现

```cpp
const T* get() const {
    return reinterpret_cast<const T*>(fStorage);
}

T* get() {
    return reinterpret_cast<T*>(fStorage);
}

const T& operator*() const { return *get(); }
T& operator*() { return *get(); }

const T* operator->() const { return get(); }
T* operator->() { return get(); }
```

**要点**:
- 简单的类型转换，将字节数组重新解释为 T 指针
- 无额外开销

### 内存对齐

```cpp
alignas(T) std::byte fStorage[sizeof(T)];
```

**作用**:
- `alignas(T)` 确保 `fStorage` 的对齐要求与 T 相同
- 满足 placement-new 的对齐需求

### Leak Sanitizer 支持

```cpp
#if defined(__clang__) && defined(__has_feature)
#if __has_feature(leak_sanitizer) || __has_feature(address_sanitizer)
    T* fStoragePtr = reinterpret_cast<T*>(fStorage);
#endif
#endif
```

**问题背景**:
- LSan（Leak Sanitizer）可能误报 `SkNoDestructor` 包装的对象为泄漏
- 原因: LSan 不认为字节数组中的对象是可达的

**解决方案**:
- 持有一个显式指针 `fStoragePtr`
- LSan 能够识别该指针，将对象标记为可达
- 仅在启用 LSan/ASan 时编译

## 静态断言

### 禁止平凡析构类型

```cpp
static_assert(!std::is_trivially_destructible_v<T>,
              "T is trivially destructible; please use a function-local static of type T "
              "directly instead");
```

**原因**:
- 若 T 的析构函数是平凡的（无需清理），则直接使用静态变量即可
- `SkNoDestructor` 会增加不必要的复杂性

### 禁止平凡构造+析构类型

```cpp
static_assert(!(std::is_trivially_constructible_v<T> && std::is_trivially_destructible_v<T>),
              "T is trivially constructible and destructible; please use a constinit object of "
              "type T directly instead");
```

**原因**:
- 若 T 既平凡构造又平凡析构，应使用 `constinit` 静态变量
- 零运行时开销

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `<cstddef>` | `std::byte` 类型 |
| `<new>` | placement-new |
| `<type_traits>` | 类型特性检查 |
| `<utility>` | `std::forward`, `std::move` |

### 被依赖的模块

`SkNoDestructor` 作为静态对象管理工具，被以下场景使用：

| 使用场景 | 说明 |
|---------|------|
| 单例模式 | 函数局部静态单例，线程安全初始化 |
| 全局配置 | 存储全局配置字符串、映射表等 |
| 缓存对象 | 程序生命周期内的全局缓存 |
| 默认对象 | 提供默认值的静态对象 |

## 设计模式与设计决策

### 设计模式

1. **RAII 反模式**:
   - 正常 RAII: 析构时释放资源
   - `SkNoDestructor`: 析构时**不**释放资源
   - 特殊场景下的合理选择

2. **单例辅助模式**:
   - 配合函数局部静态变量实现线程安全的单例
   ```cpp
   const MyType& getInstance() {
       static const SkNoDestructor<MyType> instance(...);
       return *instance;
   }
   ```

3. **Placement-new 模式**:
   - 在栈分配的内存中构造对象
   - 完全控制对象生命周期

### 设计决策

1. **永不析构的理由**:
   - **避免析构顺序问题**: 静态对象析构顺序未定义，可能导致使用已销毁的对象
   - **避免"静态初始化顺序灾难"**: 全局对象的析构同样有顺序问题
   - **简化程序退出**: 操作系统会回收内存，无需显式清理

2. **仅用于函数局部静态**:
   - 全局 `SkNoDestructor` 仍会生成静态初始化器（除非 constinit 构造）
   - 函数局部静态保证延迟初始化且线程安全（C++11 起）

3. **禁止拷贝**:
   - 静态对象应该是唯一的
   - 拷贝会违反单例语义

4. **显式构造函数**:
   - 防止意外的隐式转换
   - 强调这是特殊的包装类

5. **支持任意构造参数**:
   - 完美转发允许传递任意数量和类型的参数
   - 支持初始化列表（通过拷贝/移动构造）

6. **静态断言强制正确使用**:
   - 编译时检查类型是否真的需要 `SkNoDestructor`
   - 防止滥用

7. **LSan 特殊处理**:
   - 解决工具误报问题
   - 不影响非调试构建

## 性能考量

### 性能特征

**构造开销**:
- 与 T 的构造函数相同（placement-new 本身无开销）
- 首次访问时初始化（函数局部静态）

**析构开销**:
- **零开销**（不调用析构函数）

**访问开销**:
- 与直接访问相同（简单指针转换，完全内联）

**内存占用**:
- `sizeof(SkNoDestructor<T>) = sizeof(T) + padding`
- 调试构建（LSan）额外增加一个指针（8 字节）

### 与其他方法的比较

| 方法 | 构造 | 析构 | 内存泄漏检测 | 线程安全 |
|------|------|------|-------------|---------|
| 普通静态变量 | 程序启动 | 程序结束 | 正常 | 否（需手动同步） |
| 函数局部静态 | 首次调用 | 程序结束 | 正常 | 是（C++11+） |
| `SkNoDestructor` + 函数静态 | 首次调用 | **永不** | 需 LSan 支持 | 是 |
| `std::unique_ptr` 静态 | 首次赋值 | 程序结束 | 正常 | 需手动同步 |

### 使用建议

1. **适用场景**:
   - 函数局部静态单例
   - 程序生命周期内始终需要的对象
   - 对象的析构可能访问已销毁的资源

2. **不适用场景**:
   - 需要显式清理的资源（文件句柄、数据库连接等）
   - 非静态变量（会导致内存泄漏）
   - 平凡析构的类型（直接用静态变量）

3. **最佳实践**:
   ```cpp
   const std::string& getDefaultText() {
       // 必须：使用 const 和引用返回
       static const SkNoDestructor<std::string> s("Hello world!");
       return *s;
   }

   // 复杂初始化
   const Config& getConfig() {
       static const SkNoDestructor<Config> config([] {
           Config c;
           c.load("config.json");
           return c;
       }());
       return *config;
   }
   ```

4. **陷阱避免**:
   - 不要在非静态变量中使用（会泄漏内存）
   - 不要依赖析构函数的副作用
   - 注意 LSan 可能需要额外配置

## 使用示例

### 简单单例

```cpp
const MyClass& getInstance() {
    static const SkNoDestructor<MyClass> instance(arg1, arg2);
    return *instance;
}
```

### Lambda 初始化

```cpp
const std::vector<int>& getPrimes() {
    static const SkNoDestructor<std::vector<int>> primes([] {
        std::vector<int> v;
        // 计算质数...
        return v;
    }());
    return *primes;
}
```

### 非 const 单例（慎用）

```cpp
MyCache& getGlobalCache() {
    static SkNoDestructor<MyCache> cache;
    return *cache;
}
```

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| Chromium `base/no_destructor.h` | 原始实现来源 |
| `include/private/base/SkOnce.h` | 另一种线程安全初始化方法 |
| `src/lazy/SkLazyPtr.h` | 延迟初始化指针（另一种单例方案） |
| C++20 `constinit` | 编译时初始化的静态变量（替代方案） |
