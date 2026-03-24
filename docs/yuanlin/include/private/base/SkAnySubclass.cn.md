# SkAnySubclass

> 源文件: `include/private/base/SkAnySubclass.h`

## 概述
SkAnySubclass 是一个类型擦除模板容器,能够在栈上存储基类 Base 的任何子类对象(大小不超过 Size 字节),无需堆分配。它特别适用于在编译时不知道具体子类类型,但运行时类型集合有限且已知的场景,如平台或后端的接口实现。

## 架构位置
该模板类位于 Skia 基础设施层的类型擦除工具中。常用于实现平台特定功能(如窗口系统集成)或后端特定实现(如 GPU 驱动适配),在不使用虚函数动态分配的情况下支持多态。

## 主要类与结构体

### SkAnySubclass<Base, Size>
类型擦除容器,在固定大小的缓冲区中存储 Base 的子类实例。

**模板参数**:
- `Base` (typename): 基类类型
- `Size` (size_t): 缓冲区字节大小,必须足够容纳所有可能的子类

**继承关系**: 无基类 → SkAnySubclass<Base, Size>

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fData | alignas(8) std::byte[Size] | 8 字节对齐的存储缓冲区 |
| fValid | bool | 标记缓冲区是否包含有效对象 |

## 公共 API 函数

### 构造和析构

#### `SkAnySubclass() = default`
- **功能**: 创建一个空的容器
- **初始状态**: `fValid = false`,不包含对象

#### `~SkAnySubclass()`
- **功能**: 析构容器
- **行为**:
  - 如果包含对象,调用 `get()->~Base()` 析构
  - 通过基类指针调用虚析构函数或平凡析构函数

### 禁用的特殊成员函数
```cpp
SkAnySubclass(const SkAnySubclass&) = delete;
SkAnySubclass& operator=(const SkAnySubclass&) = delete;
SkAnySubclass(SkAnySubclass&&) = delete;
SkAnySubclass& operator=(SkAnySubclass&&) = delete;
```
- **说明**: 禁止拷贝和移动,避免复杂的对象管理和所有权语义

### 对象构造

#### `template <typename T, typename... Args> void emplace(Args&&... args)`
- **功能**: 在容器中原地构造类型 T 的对象
- **参数**:
  - `T` - 要构造的子类类型
  - `Args...` - 转发给 T 构造函数的参数
- **静态断言**:
  - `std::is_base_of_v<Base, T>`: T 必须是 Base 的子类
  - `sizeof(T) <= Size`: T 的大小必须不超过缓冲区
  - `std::has_virtual_destructor_v<Base> || std::is_trivially_destructible_v<T>`: 确保析构安全
- **前提条件**: `!fValid` (断言容器为空)
- **行为**:
  1. 使用 placement new 在 fData 中构造 T
  2. 设置 `fValid = true`

### 对象销毁

#### `void reset()`
- **功能**: 销毁容器中的对象(如果有)
- **行为**:
  - 如果 `fValid` 为 true,调用 `get()->~Base()`
  - 设置 `fValid = false`
- **说明**: 可以在空容器上安全调用

### 状态查询

#### `bool has_value() const`
- **功能**: 检查容器是否包含对象
- **返回值**: 包含对象返回 true

#### `explicit operator bool() const`
- **功能**: 转换为 bool,语义同 has_value()
- **返回值**: 包含对象返回 true
- **使用**: 允许在条件表达式中使用,如 `if (container) { ... }`

### 对象访问

#### `Base* get()`
- **功能**: 获取存储对象的基类指针
- **返回值**: 指向 Base 的指针
- **前提条件**: `fValid` 为 true (通过断言检查)
- **实现**: 使用 `std::launder` 确保指针有效性

#### `const Base* get() const`
- **功能**: 获取 const 基类指针
- **返回值**: 指向 const Base 的指针

#### `Base* operator->()`
- **功能**: 箭头运算符,访问成员
- **返回值**: 调用 `get()`
- **使用**: `container->member_function()`

#### `const Base* operator->() const`
- **功能**: const 版本的箭头运算符

#### `Base& operator*()`
- **功能**: 解引用运算符,获取对象引用
- **返回值**: `*get()`
- **使用**: `(*container).member`

#### `const Base& operator*() const`
- **功能**: const 版本的解引用运算符

## 内部实现细节

### 对齐策略
```cpp
alignas(8) std::byte fData[Size];
```
- 使用 `alignas(8)` 确保 8 字节对齐
- 对于大多数类型足够,包括指针和 double
- 如果子类有更严格的对齐要求,可能需要调整

### std::launder 使用
```cpp
return std::launder(reinterpret_cast<Base*>(fData));
```
- `std::launder` 避免编译器的严格别名优化导致的问题
- 确保指针指向实际构造的对象
- C++17 特性,处理 placement new 后的指针转换

### 静态断言保证
1. **类型关系**: `std::is_base_of_v<Base, T>`
   - 确保类型安全,只能存储子类

2. **大小检查**: `sizeof(T) <= Size`
   - 编译期检查缓冲区大小
   - 避免缓冲区溢出

3. **析构安全**: `std::has_virtual_destructor_v<Base> || std::is_trivially_destructible_v<T>`
   - 确保通过基类指针析构是安全的
   - 要么基类有虚析构函数
   - 要么子类是平凡析构的

### 完美转发
```cpp
template <typename T, typename... Args>
void emplace(Args&&... args) {
    new (fData) T(std::forward<Args>(args)...);
}
```
- 使用 `std::forward` 完美转发参数
- 保持参数的值类别(左值/右值)
- 支持移动语义

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/private/base/SkAssert.h | SkASSERT 断言宏 |
| <cstddef> | std::byte, size_t |
| <new> | placement new |
| <type_traits> | 类型特性检查 |
| <utility> | std::forward |

### 被依赖的模块
- 平台窗口系统集成
- GPU 后端实现(Vulkan, Metal, D3D)
- 字体管理器平台实现
- 任何需要类型擦除的接口实现

## 设计模式与设计决策

### 类型擦除模式
SkAnySubclass 实现了类型擦除:
- 编译时类型安全(通过模板和静态断言)
- 运行时多态(通过基类指针访问)
- 无需堆分配(栈上存储)

### 小缓冲区优化(SBO)
类似于 std::function 和 std::any 的 SBO:
- 小对象存储在栈上
- 避免动态内存分配开销
- 提高缓存局部性

### 禁止复制语义
不支持拷贝和移动的设计决策:
- 简化实现,避免深拷贝逻辑
- 避免所有权不明确的问题
- 需要共享时应使用指针或引用

### 单对象容器
一次只能存储一个对象:
- 调用 emplace 前必须 reset
- 简化生命周期管理
- 类似于 std::optional 的语义

## 性能考量

### 零堆分配
所有数据在栈上:
- 避免 malloc/free 开销
- 避免堆碎片
- 自动生命周期管理

### 缓存友好
局部性优势:
- 对象与容器在相同内存区域
- 提高缓存命中率
- 减少内存访问延迟

### 虚函数调用
通过基类指针访问:
- 一次虚函数调用开销
- 与直接堆分配的多态对象相同
- 但避免了分配器开销

### 编译时优化
静态断言在编译期检查:
- 零运行时开销
- 编译失败优于运行时错误
- 类型安全保证

## 使用场景

### 平台特定实现
```cpp
class WindowBase {
    virtual void show() = 0;
    virtual ~WindowBase() = default;
};

class WindowWin : public WindowBase { /* ... */ };
class WindowMac : public WindowBase { /* ... */ };

SkAnySubclass<WindowBase, 256> window;
#ifdef SK_BUILD_FOR_WIN
    window.emplace<WindowWin>(handle);
#else
    window.emplace<WindowMac>(nswindow);
#endif
window->show();
```

### GPU 后端切换
```cpp
class GpuBackend {
    virtual void submit() = 0;
    virtual ~GpuBackend() = default;
};

SkAnySubclass<GpuBackend, 512> backend;
switch (api) {
    case API::kVulkan:
        backend.emplace<VulkanBackend>(device);
        break;
    case API::kMetal:
        backend.emplace<MetalBackend>(device);
        break;
}
```

### 延迟初始化
```cpp
class Manager {
    SkAnySubclass<Backend, 256> fBackend;

    void initialize(BackendType type) {
        if (fBackend) {
            fBackend.reset();
        }

        switch (type) {
            case BackendType::kA:
                fBackend.emplace<BackendA>();
                break;
            case BackendType::kB:
                fBackend.emplace<BackendB>();
                break;
        }
    }
};
```

## 相关文件
| 文件 | 关系 |
|------|------|
| include/private/base/SkAlignedStorage.h | 类似的栈上存储工具 |
| include/private/base/SkTLazy.h | 延迟初始化容器 |
| src/gpu/ganesh/GrDirectContext.cpp | 可能使用场景 |

## 注意事项

### 缓冲区大小选择
- 必须足够容纳所有可能的子类
- 过大浪费栈空间
- 过小导致编译错误
- 建议通过 `sizeof` 测量实际子类大小

### 对齐要求
- 当前对齐到 8 字节
- 如果子类需要更严格对齐(如 16 字节的 SIMD 类型),需要修改 alignas

### 虚析构函数要求
基类必须有虚析构函数或子类平凡析构:
```cpp
class Base {
public:
    virtual ~Base() = default;  // 必需!
};
```

### emplace 前置条件
```cpp
SkASSERT(!fValid);  // emplace 前必须为空
```
如果已有对象,必须先调用 reset()。

### 异常安全
- 构造函数抛出异常会导致 fValid 为 false
- 容器保持有效但为空状态
- 调用者需要检查 has_value()

### 线程安全
- 不是线程安全的
- 多线程访问需要外部同步
- 不适合跨线程传递
