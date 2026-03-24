# SkTScopedComPtr

> 源文件: src/utils/win/SkTScopedComPtr.h

## 概述

`SkTScopedComPtr` 是 Skia 图形库为 Windows 平台开发的智能指针类,专门用于管理 COM(Component Object Model)接口指针的生命周期。该类通过 RAII(Resource Acquisition Is Initialization)机制自动处理 COM 对象的引用计数,防止内存泄漏和资源管理错误。

作为 Windows 特定的工具类,`SkTScopedComPtr` 类似于标准库的 `std::unique_ptr`,但针对 COM 接口的 `AddRef/Release` 语义进行了特化。

## 架构位置

该文件位于 Skia 的 Windows 平台特定工具模块中:

```
src/utils/win/
  ├── SkTScopedComPtr.h      # COM智能指针(本文件)
  ├── SkObjBase.h            # COM基础定义
  └── SkDWriteNTDDI_VERSION.h
```

主要用于 Skia 的 Windows 字体渲染(DirectWrite)和图形后端(Direct2D/Direct3D)模块。

## 主要类与结构体

### `SkTScopedComPtr<T>`

模板智能指针类,管理 COM 接口指针的生命周期。

#### 模板参数

- `T`: COM 接口类型(必须实现 `IUnknown` 接口)

#### 构造函数

```cpp
constexpr SkTScopedComPtr();                    // 默认构造,指向nullptr
constexpr SkTScopedComPtr(std::nullptr_t);      // nullptr构造
explicit SkTScopedComPtr(T *ptr);               // 接管原始指针
SkTScopedComPtr(SkTScopedComPtr&& that);        // 移动构造
SkTScopedComPtr(const SkTScopedComPtr&) = delete;  // 禁止拷贝构造
```

#### 析构函数

```cpp
~SkTScopedComPtr() { this->reset(); }
```

自动调用 `Release()` 释放 COM 对象引用。

### 辅助函数

#### `SkRefComPtr(T* ptr)`

```cpp
template<typename T> T* SkRefComPtr(T* ptr) {
    ptr->AddRef();
    return ptr;
}
```

增加 COM 对象的引用计数并返回指针。

#### `SkSafeRefComPtr(T* ptr)`

```cpp
template<typename T> T* SkSafeRefComPtr(T* ptr) {
    if (ptr) {
        ptr->AddRef();
    }
    return ptr;
}
```

安全版本,在增加引用计数前检查指针是否为空。

## 公共 API 函数

### 赋值操作符

```cpp
SkTScopedComPtr& operator=(SkTScopedComPtr&& that);  // 移动赋值
SkTScopedComPtr& operator=(const SkTScopedComPtr&) = delete;  // 禁止拷贝赋值
SkTScopedComPtr& operator=(std::nullptr_t);  // 重置为nullptr
```

### 解引用操作符

```cpp
T& operator*() const;    // 解引用,断言指针非空
T* operator->() const;   // 成员访问
```

### 布尔转换

```cpp
explicit operator bool() const { return fPtr != nullptr; }
```

用于条件判断:
```cpp
if (comPtr) {
    // 指针有效
}
```

### 地址操作符

```cpp
T** operator&() { SkASSERT(fPtr == nullptr); return &fPtr; }
```

**危险操作**: 返回内部指针的地址,仅用于 COM API 的输出参数。

**使用限制**:
- 只能在指针为 `nullptr` 时调用
- 用于初始化,例如: `CreateInstance(..., &comPtr)`

### 访问与修改

#### `get()`
```cpp
T* get() const { return fPtr; }
```
返回原始指针,不转移所有权。

#### `reset(T* ptr = nullptr)`
```cpp
void reset(T* ptr = nullptr);
```
释放当前对象并接管新指针。

#### `release()`
```cpp
T* release();
```
释放所有权并返回原始指针,不调用 `Release()`。

#### `swap(SkTScopedComPtr<T>& that)`
```cpp
void swap(SkTScopedComPtr<T>& that);
```
交换两个智能指针的内容。

## 内部实现细节

### COM 引用计数机制

COM 对象使用引用计数管理生命周期:
- **AddRef()**: 增加引用计数
- **Release()**: 减少引用计数,计数为 0 时销毁对象

### reset() 实现

```cpp
void reset(T* ptr = nullptr) {
    if (fPtr) {
        fPtr->Release();  // 释放旧对象
    }
    fPtr = ptr;  // 接管新对象
}
```

**关键点**:
- 先释放旧对象的引用
- 然后接管新对象(不调用 `AddRef`,假设已经持有引用)

### 移动语义

```cpp
SkTScopedComPtr(SkTScopedComPtr&& that) : fPtr(that.release()) {}

SkTScopedComPtr& operator=(SkTScopedComPtr&& that) {
    this->reset(that.release());
    return *this;
}
```

通过 `release()` 转移所有权,避免不必要的引用计数操作。

### 禁止拷贝

```cpp
SkTScopedComPtr(const SkTScopedComPtr&) = delete;
SkTScopedComPtr& operator=(const SkTScopedComPtr&) = delete;
```

**理由**:
- 拷贝需要调用 `AddRef()`,有性能开销
- 强制使用移动语义或显式调用 `SkRefComPtr()`
- 避免意外的引用计数错误

## 依赖关系

### Skia 内部依赖

```cpp
#include "src/base/SkLeanWindows.h"  // 精简的Windows头文件
#include "src/utils/win/SkObjBase.h"  // COM基础定义
```

### COM 依赖

该类假设 `T` 类型实现了 `IUnknown` 接口,具有:
- `AddRef()` 方法
- `Release()` 方法

## 设计模式与设计决策

### 1. RAII 模式

```cpp
SkTScopedComPtr<IDWriteFactory> factory;
hr = DWriteCreateFactory(..., &factory);
// factory 自动在作用域结束时调用 Release()
```

**优点**:
- 异常安全
- 自动资源管理
- 避免忘记调用 `Release()`

### 2. 独占所有权(Unique Ownership)

类似于 `std::unique_ptr`,一次只能有一个所有者:
- 禁止拷贝
- 支持移动
- 明确所有权转移语义

### 3. 显式转换

```cpp
explicit operator bool() const;
```

防止隐式类型转换错误:
```cpp
SkTScopedComPtr<T> ptr;
if (ptr) { ... }  // OK
bool b = ptr;     // 编译错误(C++11+)
```

### 4. 地址操作符陷阱

```cpp
T** operator&() { SkASSERT(fPtr == nullptr); return &fPtr; }
```

**设计考虑**:
- COM API 通常使用输出参数: `CreateInstance(..., void** ppv)`
- 必须确保指针为空,否则会泄漏之前的对象
- 断言保护防止误用

## 性能考量

### 引用计数开销

每次 `AddRef/Release` 调用:
- **线程安全的原子操作**: 约 10-20 个CPU周期
- **函数调用开销**: 约 5-10 个CPU周期
- **总开销**: 约 15-30 纳秒

### 移动 vs 拷贝

```cpp
// 移动:零开销
SkTScopedComPtr<T> p2 = std::move(p1);

// 如果支持拷贝:需要 AddRef + Release
// 约 30-60 纳秒开销
```

### 优化建议

1. **优先使用移动**: `std::move(ptr)`
2. **避免不必要的拷贝**: 传递引用或原始指针
3. **批量操作**: 减少智能指针创建/销毁次数

## 相关文件

### Windows 平台工具

- `SkObjBase.h`: COM 方法宏定义
- `SkDWriteNTDDI_VERSION.h`: DirectWrite 版本控制

### 使用场景

#### DirectWrite 字体渲染

```cpp
#include "src/utils/win/SkTScopedComPtr.h"
#include <dwrite.h>

SkTScopedComPtr<IDWriteFactory> gDWriteFactory;

void InitDirectWrite() {
    HRESULT hr = DWriteCreateFactory(
        DWRITE_FACTORY_TYPE_SHARED,
        __uuidof(IDWriteFactory),
        &gDWriteFactory  // 使用 operator&
    );
    if (FAILED(hr)) {
        // 错误处理
    }
    // gDWriteFactory 自动管理生命周期
}
```

#### COM 查询接口

```cpp
SkTScopedComPtr<IDWriteFontFace> CreateFontFace(IDWriteFont* font) {
    SkTScopedComPtr<IDWriteFontFace> fontFace;
    HRESULT hr = font->CreateFontFace(&fontFace);
    if (FAILED(hr)) {
        return SkTScopedComPtr<IDWriteFontFace>();  // 返回空指针
    }
    return fontFace;  // 移动返回
}
```

#### 智能指针转换

```cpp
// 从 SkTScopedComPtr 到原始指针
void ProcessFont(IDWriteFontFace* face);

SkTScopedComPtr<IDWriteFontFace> fontFace = ...;
ProcessFont(fontFace.get());  // 不转移所有权

// 转移所有权
IDWriteFontFace* rawPtr = fontFace.release();
// 现在需要手动调用 rawPtr->Release()
```

### 与标准库对比

| 特性 | SkTScopedComPtr | std::unique_ptr |
|------|-----------------|-----------------|
| 删除器 | COM Release() | delete |
| 拷贝 | 禁止 | 禁止 |
| 移动 | 支持 | 支持 |
| 平台 | Windows | 跨平台 |
| 用途 | COM对象 | 任意指针 |

### Microsoft ATL 对比

微软的 ATL 库提供了 `CComPtr` 和 `CComQIPtr`:
- **CComPtr**: 类似于 `SkTScopedComPtr`,支持拷贝
- **优势**: `SkTScopedComPtr` 更轻量,无需依赖 ATL
- **劣势**: 功能相对简单,不支持 QueryInterface 包装

## 使用注意事项

### 1. 初始化陷阱

```cpp
// 错误:泄漏之前的对象
SkTScopedComPtr<T> ptr(somePtr);
CreateInstance(&ptr);  // 断言失败!ptr不是nullptr

// 正确:先重置
ptr.reset();
CreateInstance(&ptr);
```

### 2. 引用计数平衡

```cpp
// 情况1:API 返回已增加引用计数的对象
CreateInstance(&ptr);  // ptr已经有引用,直接接管

// 情况2:从已有对象创建智能指针
T* rawPtr = ...;  // 已有引用
SkTScopedComPtr<T> ptr(SkRefComPtr(rawPtr));  // 增加引用
// 或
SkTScopedComPtr<T> ptr(rawPtr);  // 接管引用(不增加)
```

### 3. 线程安全

COM 引用计数是线程安全的,但智能指针本身不是:
- 不要在多线程间共享 `SkTScopedComPtr` 对象
- 可以在多线程间共享底层 COM 对象(通过 `get()`)

`SkTScopedComPtr` 是 Skia 在 Windows 平台上管理 COM 对象的核心工具,通过 RAII 和移动语义提供了安全、高效的资源管理机制,是 DirectWrite 字体渲染和 Direct3D 图形后端实现的基础设施。
