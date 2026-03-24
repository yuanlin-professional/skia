# SkObjBase

> 源文件: src/utils/win/SkObjBase.h

## 概述

`SkObjBase.h` 是 Skia 图形库为 Windows 平台提供的 COM(Component Object Model)基础定义头文件。该文件主要解决了 COM 接口声明和实现之间关于异常规范属性不匹配的问题,通过定义统一的宏来确保接口实现的一致性和编译器警告消除。

这是一个仅包含宏定义的小型头文件,为 Skia 的 Windows COM 组件实现提供标准化的方法声明格式。

## 架构位置

```
src/utils/win/
  ├── SkObjBase.h          # COM基础定义(本文件)
  ├── SkTScopedComPtr.h    # COM智能指针
  └── SkDWriteNTDDI_VERSION.h
```

## 主要类与结构体

该文件不包含类或结构体,仅定义宏。

## 公共 API 函数

### 宏定义

#### `SK_STDMETHODIMP`

```cpp
#define SK_STDMETHODIMP COM_DECLSPEC_NOTHROW STDMETHODIMP
```

**用途**: 定义 COM 方法的实现,返回 `HRESULT` 类型。

**展开为**:
```cpp
COM_DECLSPEC_NOTHROW HRESULT __stdcall
```

#### `SK_STDMETHODIMP_(type)`

```cpp
#define SK_STDMETHODIMP_(type) COM_DECLSPEC_NOTHROW STDMETHODIMP_(type)
```

**用途**: 定义 COM 方法的实现,返回自定义类型。

**展开为**:
```cpp
COM_DECLSPEC_NOTHROW type __stdcall
```

## 内部实现细节

### 问题背景

COM 接口和实现存在属性不匹配问题:

1. **STDMETHOD 宏**(用于接口声明): 包含 `COM_DECLSPEC_NOTHROW` 属性
2. **STDMETHODIMP 宏**(用于方法实现): **不包含** `COM_DECLSPEC_NOTHROW` 属性

这导致编译器发出属性不匹配警告。

### 解决方案

Skia 定义的 `SK_STDMETHODIMP` 在实现端也添加 `COM_DECLSPEC_NOTHROW`:

```cpp
// 接口声明(使用标准STDMETHOD)
interface IMyInterface : public IUnknown {
    STDMETHOD(MyMethod)() PURE;  // 包含COM_DECLSPEC_NOTHROW
};

// 实现(使用SK_STDMETHODIMP)
class MyImpl : public IMyInterface {
public:
    SK_STDMETHODIMP MyMethod() {  // 也包含COM_DECLSPEC_NOTHROW
        return S_OK;
    }
};
```

### COM_DECLSPEC_NOTHROW 说明

- **平台相关**: Windows 特定的异常规范
- **语义**: 标记方法不抛出 C++ 异常
- **与 noexcept 的区别**:
  - `COM_DECLSPEC_NOTHROW`: 平台相关,可配置
  - `noexcept`: C++11 标准关键字,语义稍有不同

### COM 组件的异常约束

COM 理论上不应抛出 C++ 异常:
- COM 是二进制接口标准,跨语言使用
- 异常无法跨越组件边界
- 错误通过 `HRESULT` 返回值传递

但在单个项目内部:
- `COM_DECLSPEC_NOTHROW` 允许配置调整
- 对于纯内部实现,可能放宽限制

### 旧接口兼容性

```cpp
// 旧接口如IUnknown和IStream不包含COM_DECLSPEC_NOTHROW
// 但实现端标记为nothrow不会造成问题(更严格)
```

在实现端标记为 `nothrow` 比接口更严格是安全的,不会破坏兼容性。

## 依赖关系

### 系统头文件

```cpp
#include "src/base/SkLeanWindows.h"  // 精简Windows头文件
#include <objbase.h>                 // COM基础定义
```

### 依赖图

```
SkObjBase.h
  ├── SkLeanWindows.h (Skia精简Windows包装)
  └── <objbase.h> (Windows SDK)
      ├── STDMETHOD
      ├── STDMETHODIMP
      └── COM_DECLSPEC_NOTHROW
```

## 设计模式与设计决策

### 1. 宏包装模式

通过宏对 Windows COM 宏进行二次包装:
- **优点**: 统一 Skia 代码风格,消除警告
- **缺点**: 增加一层间接层,可能降低可读性

### 2. 编译器警告消除

该文件的主要目的是消除 `-Wattribute` 类警告:
- 不改变运行时行为
- 提高代码质量(警告即错误策略)
- 保持与 Windows SDK 的兼容性

### 3. 命名约定

使用 `SK_` 前缀:
- 避免与 Windows SDK 宏冲突
- 清晰标识 Skia 特定的定义
- 保持命名空间整洁

## 性能考量

### 零运行时开销

这些宏纯粹是编译时属性:
- 不产生额外代码
- 不影响调用约定(仍然是 `__stdcall`)
- 不改变函数签名

### 异常处理影响

`COM_DECLSPEC_NOTHROW` 可能影响编译器优化:
- 编译器知道函数不抛异常,可以优化异常处理代码
- 减少异常表(exception table)大小
- 可能提升性能(微小)

## 相关文件

### Skia COM 组件实现

该宏在以下场景中使用:

#### DirectWrite 字体实现

```cpp
class SkStreamFontFileStream : public IDWriteFontFileStream {
public:
    SK_STDMETHODIMP QueryInterface(REFIID iid, void** ppvObject);
    SK_STDMETHODIMP_(ULONG) AddRef();
    SK_STDMETHODIMP_(ULONG) Release();

    SK_STDMETHODIMP ReadFileFragment(
        void const** fragmentStart,
        UINT64 fileOffset,
        UINT64 fragmentSize,
        void** fragmentContext);

    SK_STDMETHODIMP_(void) ReleaseFileFragment(void* fragmentContext);
    SK_STDMETHODIMP GetFileSize(UINT64* fileSize);
    SK_STDMETHODIMP GetLastWriteTime(UINT64* lastWriteTime);
};
```

#### 自定义 COM 对象

```cpp
class SkDWriteGeometrySink : public IDWriteGeometrySink {
public:
    SK_STDMETHODIMP QueryInterface(REFIID riid, void** ppvObject);
    SK_STDMETHODIMP_(ULONG) AddRef();
    SK_STDMETHODIMP_(ULONG) Release();

    SK_STDMETHODIMP_(void) SetFillMode(D2D1_FILL_MODE fillMode);
    SK_STDMETHODIMP_(void) BeginFigure(D2D1_POINT_2F startPoint, D2D1_FIGURE_BEGIN figureBegin);
    // ...
};
```

### 标准宏对比

| 宏 | 用途 | 包含COM_DECLSPEC_NOTHROW |
|----|------|--------------------------|
| `STDMETHOD` | 接口声明 | 是 |
| `STDMETHODIMP` | 返回HRESULT的实现 | **否** |
| `STDMETHODIMP_(type)` | 返回其他类型的实现 | **否** |
| `SK_STDMETHODIMP` | Skia的HRESULT实现 | **是** |
| `SK_STDMETHODIMP_(type)` | Skia的其他类型实现 | **是** |

## 使用示例

### 基本用法

```cpp
#include "src/utils/win/SkObjBase.h"

class MyComObject : public IUnknown {
private:
    LONG fRefCount;

public:
    // IUnknown methods
    SK_STDMETHODIMP QueryInterface(REFIID riid, void** ppvObject) {
        if (riid == IID_IUnknown) {
            *ppvObject = static_cast<IUnknown*>(this);
            AddRef();
            return S_OK;
        }
        return E_NOINTERFACE;
    }

    SK_STDMETHODIMP_(ULONG) AddRef() {
        return InterlockedIncrement(&fRefCount);
    }

    SK_STDMETHODIMP_(ULONG) Release() {
        LONG count = InterlockedDecrement(&fRefCount);
        if (count == 0) {
            delete this;
        }
        return count;
    }
};
```

### 注意事项

1. **一致性**: 所有 COM 方法实现都应使用 `SK_STDMETHODIMP`
2. **返回类型**:
   - `SK_STDMETHODIMP` 用于返回 `HRESULT`
   - `SK_STDMETHODIMP_(ULONG)` 用于返回 `ULONG`(如 `AddRef/Release`)
   - `SK_STDMETHODIMP_(void)` 用于返回 `void`

3. **编译器支持**: 需要支持 `COM_DECLSPEC_NOTHROW` 的编译器(MSVC)

该文件虽小,却是 Skia Windows COM 实现的基础,通过简单的宏定义解决了接口声明和实现之间的属性匹配问题,展示了对编译器警告和代码质量的严格要求。
