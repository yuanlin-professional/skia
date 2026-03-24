# SkCFObject

> 源文件: `include/ports/SkCFObject.h`

## 概述

`SkCFObject` 提供了一个智能指针模板类 `sk_cfp<T>`，用于管理 Apple CoreFoundation 对象的生命周期。它自动处理 `CFRetain` 和 `CFRelease` 调用，类似于 Skia 的 `sk_sp<T>` 智能指针，但专门针对 CoreFoundation 对象。该工具极大简化了在 macOS 和 iOS 平台上与 CoreFoundation API 的互操作，避免常见的引用计数错误。

## 架构位置

该头文件位于 `include/ports/` 目录，属于 Skia 的平台移植层(Ports Layer)。它是 Apple 平台集成的基础设施，为所有需要与 CoreFoundation 交互的 Skia 代码提供内存管理支持，特别是字体管理(`SkTypeface_mac`)和图像编解码等模块。

## 条件编译

整个接口仅在 Apple 平台可用：
```cpp
#ifdef __APPLE__
// 所有定义
#endif
```

这确保代码只在 macOS、iOS、tvOS 和 watchOS 上编译。

## 辅助函数

### `SkCFSafeRetain`

```cpp
template <typename T> static inline T SkCFSafeRetain(T obj) {
    if (obj) {
        CFRetain(obj);
    }
    return obj;
}
```

- **功能**: 安全地对 CoreFoundation 对象调用 `CFRetain`，自动处理空指针
- **参数**: `obj` - CoreFoundation 对象指针(如 `CFStringRef`, `CTFontRef`)
- **返回值**: 返回相同的对象指针(引用计数已增加)
- **空指针安全**: 如果 `obj` 为 `nullptr`/`nil`，不执行任何操作

### `SkCFSafeRelease`

```cpp
template <typename T> static inline void SkCFSafeRelease(T obj) {
    if (obj) {
        CFRelease(obj);
    }
}
```

- **功能**: 安全地对 CoreFoundation 对象调用 `CFRelease`，自动处理空指针
- **参数**: `obj` - CoreFoundation 对象指针
- **返回值**: 无返回值
- **空指针安全**: 如果 `obj` 为 `nullptr`/`nil`，不执行任何操作

## 主要类

### `sk_cfp<T>`

智能指针模板类，管理 CoreFoundation 对象的生命周期。

#### 类型定义

```cpp
using element_type = T;
```
- 提供被管理对象的类型别名

#### 构造函数

##### 默认构造函数

```cpp
constexpr sk_cfp();
constexpr sk_cfp(std::nullptr_t);
```
- **功能**: 创建空的智能指针(不持有任何对象)
- **初始值**: 内部指针为 `nil`

##### 拷贝构造函数

```cpp
sk_cfp(const sk_cfp<T>& that);
```
- **功能**: 从另一个智能指针拷贝，共享对象所有权
- **行为**: 调用 `CFRetain` 增加引用计数
- **语义**: 两个智能指针都持有对象的引用

##### 移动构造函数

```cpp
sk_cfp(sk_cfp<T>&& that);
```
- **功能**: 从另一个智能指针移动所有权
- **行为**: 不调用 `CFRetain` 或 `CFRelease`，直接转移所有权
- **语义**: 源智能指针变为空，目标智能指针持有对象

##### 采纳构造函数

```cpp
explicit sk_cfp(T obj);
```
- **功能**: 采纳一个裸指针，接管其所有权
- **行为**: 不调用 `CFRetain`(假设调用者已持有引用)
- **使用场景**: 包装从 CoreFoundation 创建函数(如 `CFStringCreateWithCString`)返回的对象
- **注意**: 显式构造，防止意外类型转换

#### 析构函数

```cpp
~sk_cfp();
```
- **功能**: 自动释放持有的对象
- **行为**: 调用 `CFRelease`，引用计数减 1
- **调试模式**: 在调试构建中将内部指针设为 `nil`

#### 赋值运算符

##### 空指针赋值

```cpp
sk_cfp<T>& operator=(std::nullptr_t);
```
- **功能**: 释放当前对象，变为空指针
- **行为**: 调用 `reset()` 方法

##### 拷贝赋值

```cpp
sk_cfp<T>& operator=(const sk_cfp<T>& that);
```
- **功能**: 从另一个智能指针拷贝赋值
- **行为**:
  1. 对新对象调用 `CFRetain`
  2. 对旧对象调用 `CFRelease`(通过 `reset`)
- **自赋值安全**: 检查 `this != &that` 防止自赋值问题

##### 移动赋值

```cpp
sk_cfp<T>& operator=(sk_cfp<T>&& that);
```
- **功能**: 移动赋值，转移所有权
- **行为**: 不调用 `CFRetain`，只调用 `CFRelease`(释放旧对象)

#### 访问器方法

##### `get()`

```cpp
T get() const;
```
- **功能**: 获取底层 CoreFoundation 对象指针
- **返回值**: 裸指针(不改变引用计数)
- **生命周期**: 返回的指针在智能指针有效期内有效

##### `operator*()`

```cpp
T operator*() const;
```
- **功能**: 解引用运算符，获取对象指针
- **断言**: 在调试模式下断言对象非空
- **使用场景**: 当确定对象非空时，提供简洁的语法

##### `operator bool()`

```cpp
explicit operator bool() const;
```
- **功能**: 布尔转换，检查是否持有对象
- **返回值**: 如果持有对象返回 `true`，否则返回 `false`
- **显式转换**: 防止意外的隐式类型转换

#### 修改方法

##### `reset()`

```cpp
void reset(T object = nil);
```
- **功能**: 采纳新对象，释放旧对象
- **参数**: `object` - 新的 CoreFoundation 对象(默认为 `nil`)
- **行为**:
  1. 先保存旧对象指针
  2. 设置新对象
  3. 释放旧对象(按此顺序避免自赋值问题)
- **不调用 `CFRetain`**: 假设新对象已持有引用

##### `retain()`

```cpp
void retain(T object);
```
- **功能**: 共享新对象，释放旧对象
- **参数**: `object` - 新的 CoreFoundation 对象
- **行为**:
  1. 对新对象调用 `CFRetain`
  2. 通过 `reset` 释放旧对象
- **自赋值安全**: 检查 `fObject != object` 避免不必要的操作

##### `release()`

```cpp
[[nodiscard]] T release();
```
- **功能**: 释放所有权，返回裸指针
- **返回值**: 原始对象指针
- **行为**: 将内部指针设为 `nil`，不调用 `CFRelease`
- **使用场景**: 将对象所有权转移给其他代码(如 CoreFoundation API)
- **警告属性**: `[[nodiscard]]` 确保调用者不忽略返回值

#### 关键成员变量

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fObject` | `T` | 被管理的 CoreFoundation 对象指针，初始值为 `nil` |

## 比较运算符

### 智能指针之间比较

```cpp
template <typename T> inline bool operator==(const sk_cfp<T>& a, const sk_cfp<T>& b);
template <typename T> inline bool operator!=(const sk_cfp<T>& a, const sk_cfp<T>& b);
```
- **功能**: 比较两个智能指针是否指向同一对象
- **比较方式**: 比较底层指针地址(而非对象内容)

### 与空指针比较

```cpp
template <typename T> inline bool operator==(const sk_cfp<T>& a, std::nullptr_t);
template <typename T> inline bool operator==(std::nullptr_t, const sk_cfp<T>& b);
template <typename T> inline bool operator!=(const sk_cfp<T>& a, std::nullptr_t);
template <typename T> inline bool operator!=(std::nullptr_t, const sk_cfp<T>& b);
```
- **功能**: 检查智能指针是否为空
- **等价操作**: `a == nullptr` 等价于 `!a`

## 辅助工厂函数

### `sk_ret_cfp`

```cpp
template <typename T> sk_cfp<T> sk_ret_cfp(T obj);
```

- **功能**: 创建智能指针并调用 `CFRetain`
- **参数**: `obj` - CoreFoundation 对象指针
- **返回值**: 持有该对象的 `sk_cfp<T>`
- **行为**: 调用 `SkCFSafeRetain(obj)` 增加引用计数
- **与构造函数区别**:
  - 构造函数采纳所有权(不 retain)
  - `sk_ret_cfp` 共享所有权(会 retain)

## 内部实现细节

### 引用计数管理

`sk_cfp` 遵循 CoreFoundation 的引用计数规则：
- **Create 规则**: `CF...Create...` 函数返回的对象引用计数为 1，使用构造函数采纳
- **Copy 规则**: `CF...Copy...` 函数返回的对象引用计数为 1，使用构造函数采纳
- **Get 规则**: `CF...Get...` 函数返回的对象不增加引用计数，使用 `sk_ret_cfp` 包装

### 自赋值安全

`reset()` 方法的实现避免了自赋值问题：
```cpp
void reset(T object = nil) {
    T oldObject = fObject;  // 先保存
    fObject = object;       // 再设置
    SkCFSafeRelease(oldObject); // 最后释放
}
```
这个顺序确保即使 `object == fObject`，对象也不会被过早释放。

### 与 sk_sp 的相似性

`sk_cfp` 的设计参考了 Skia 的 `sk_sp`：
- **统一语义**: 两者都是智能指针，API 高度一致
- **熟悉感**: Skia 开发者可以无缝使用 `sk_cfp`
- **差异**: `sk_cfp` 使用 `CFRetain`/`CFRelease`，`sk_sp` 使用 `ref()`/`unref()`

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| CoreFoundation | 提供 `CFRetain`/`CFRelease` 函数 |
| `SkTypes.h` | Skia 基础类型和宏(如 `SkASSERT`) |
| `<cstddef>` | `std::nullptr_t` 类型 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| `SkTypeface_mac.h` | 管理 `CTFontRef` 对象 |
| 字体管理实现 | 管理各种 CoreText 对象 |
| 图像编解码 | 管理 `CGImageRef`、`CGDataProviderRef` 等 |
| macOS/iOS 端口代码 | 所有与 CoreFoundation 交互的代码 |

## 设计模式与设计决策

### RAII (资源获取即初始化)

`sk_cfp` 是典型的 RAII 模式实现：
- **构造时获取**: 构造函数接管对象所有权
- **析构时释放**: 析构函数自动调用 `CFRelease`
- **异常安全**: 即使发生异常，对象也会被正确释放

### 显式语义

通过显式构造和方法命名区分采纳和共享：
- **采纳**: 构造函数 `sk_cfp<T>(obj)` 或 `reset(obj)`
- **共享**: `sk_ret_cfp(obj)` 或 `retain(obj)`
- **清晰意图**: 代码可读性高，引用计数管理明确

### 防御性编程

安全函数(`SkCFSafeRetain`/`SkCFSafeRelease`)自动处理空指针：
- **简化调用**: 调用者无需手动检查空指针
- **减少错误**: 避免空指针解引用崩溃

## 性能考量

### 零开销抽象

`sk_cfp` 是零开销抽象：
- **内存布局**: 只包含一个指针(与裸指针相同)
- **内联函数**: 简单方法可以完全内联
- **编译器优化**: 现代编译器可以消除大部分开销

### 引用计数开销

引用计数的固有成本：
- **原子操作**: `CFRetain`/`CFRelease` 使用原子操作(线程安全)
- **缓存一致性**: 多核系统中可能导致缓存失效
- **不可避免**: 使用 CoreFoundation API 必须付出的代价

### 与裸指针对比

| 方面 | sk_cfp | 裸指针 |
|------|--------|--------|
| 内存安全 | 自动管理 | 手动管理(易出错) |
| 代码复杂度 | 简洁 | 需要大量 retain/release |
| 性能 | 零开销(相同) | 基准 |
| 异常安全 | 是 | 否(需要 try-finally) |

## 平台相关说明

### macOS 和 iOS 差异

`sk_cfp` 在所有 Apple 平台上行为一致：
- **macOS**: 完全支持
- **iOS**: 完全支持
- **tvOS**: 完全支持
- **watchOS**: 完全支持

### CoreFoundation 类型兼容性

`sk_cfp` 可以管理所有 CoreFoundation 类型：
- **基础类型**: `CFStringRef`, `CFNumberRef`, `CFDataRef`
- **容器类型**: `CFArrayRef`, `CFDictionaryRef`, `CFSetRef`
- **CoreText**: `CTFontRef`, `CTFontDescriptorRef`, `CTLineRef`
- **CoreGraphics**: `CGImageRef`, `CGColorRef`, `CGContextRef`(需要类型转换)

### Objective-C 互操作

CoreFoundation 对象可以与 Objective-C 对象桥接：
```cpp
// CoreFoundation → Objective-C (免费桥接)
CFStringRef cfString = ...;
NSString* nsString = (__bridge NSString*)cfString;

// sk_cfp 在桥接时的使用
sk_cfp<CFStringRef> cfpString(CFStringCreateWithCString(...));
NSString* nsString = (__bridge NSString*)cfpString.get();
```

## 使用示例

### 基础用法

```cpp
// 采纳 Create 函数返回的对象
sk_cfp<CFStringRef> str1(CFStringCreateWithCString(nullptr, "Hello", kCFStringEncodingUTF8));
// str1 析构时自动释放

// 共享 Get 函数返回的对象
CTFontRef font = CTFontCreateWithName(CFSTR("Arial"), 12.0, nullptr);
sk_cfp<CTFontRef> font1 = sk_ret_cfp(CTFontCopyFamilyName(font));
CFRelease(font);
```

### 拷贝和移动

```cpp
sk_cfp<CFStringRef> str1(CFStringCreateWithCString(nullptr, "World", kCFStringEncodingUTF8));

// 拷贝(引用计数增加)
sk_cfp<CFStringRef> str2 = str1;  // str1 和 str2 都持有引用

// 移动(无引用计数操作)
sk_cfp<CFStringRef> str3 = std::move(str1);  // str1 变为空
```

### 容器中存储

```cpp
std::vector<sk_cfp<CTFontRef>> fonts;

for (int i = 0; i < 10; ++i) {
    CFStringRef name = CFStringCreateWithFormat(nullptr, nullptr, CFSTR("Font%d"), i);
    CTFontRef font = CTFontCreateWithName(name, 12.0, nullptr);
    fonts.emplace_back(font);  // 采纳所有权
    CFRelease(name);
}
// fonts 析构时自动释放所有字体
```

### 与 CoreFoundation API 交互

```cpp
sk_cfp<CFMutableArrayRef> array(CFArrayCreateMutable(nullptr, 0, &kCFTypeArrayCallBacks));

for (int i = 0; i < 5; ++i) {
    sk_cfp<CFNumberRef> num(CFNumberCreate(nullptr, kCFNumberIntType, &i));
    CFArrayAppendValue(array.get(), num.get());  // get() 获取裸指针
}

// 转移所有权给 CoreFoundation API
CFArrayRef immutableArray = array.release();  // array 变为空
// 调用者现在负责释放 immutableArray
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/core/SkRefCnt.h` | Skia 的引用计数基类和 `sk_sp<T>` 智能指针 |
| `include/ports/SkTypeface_mac.h` | 使用 `sk_cfp` 管理 `CTFontRef` |
| `src/ports/SkFontHost_mac.cpp` | macOS 字体实现，大量使用 `sk_cfp` |
| `src/ports/SkImageEncoder_CG.cpp` | CoreGraphics 图像编码器 |
| CoreFoundation 框架 | Apple 的基础对象和服务框架 |
