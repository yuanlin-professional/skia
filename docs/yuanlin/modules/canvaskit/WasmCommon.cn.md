# WasmCommon.h

> 源文件: modules/canvaskit/WasmCommon.h

## 概述

`WasmCommon.h` 是 CanvasKit 模块的核心头文件,定义了 JavaScript 和 C++ 之间互操作所需的通用类型别名、类型转换工具和数据传输辅助类。该文件为 Emscripten 绑定提供了类型安全的抽象层,使得在 WebAssembly 和 JavaScript 之间传递复杂数据结构变得更加简单和高效。

该头文件是 CanvasKit 所有 C++ 绑定文件的基础依赖,提供了统一的类型系统和内存管理机制,确保跨语言边界的数据传输正确且高效。

## 架构位置

```
skia/
├── modules/
│   └── canvaskit/
│       ├── WasmCommon.h           # 本文件 - WASM 通用定义
│       ├── canvaskit_bindings.cpp # 使用这些类型
│       ├── bidi_bindings.cpp      # 使用这些类型
│       ├── gm_bindings.cpp        # 使用这些类型
│       └── *.cpp                  # 其他绑定文件
```

该文件是所有 CanvasKit C++ 绑定的基础设施,位于类型系统的最底层。

## 主要类与结构体

### JavaScript 类型别名

```cpp
using JSColor = int32_t;
using JSArray = emscripten::val;
using JSObject = emscripten::val;
using JSString = emscripten::val;
using SkPathOrNull = emscripten::val;
using TypedArray = emscripten::val;
using Uint8Array = emscripten::val;
using Uint16Array = emscripten::val;
using Int32Array = emscripten::val;
using Uint32Array = emscripten::val;
using Float32Array = emscripten::val;
```

**用途**: 为 `emscripten::val` 类型提供语义化的别名,提高代码可读性。

**设计考虑**:
- **自文档化**: 通过类型名即可知道预期的 JavaScript 类型
- **类型安全**: 编译时捕获类型错误
- **便于重构**: 统一修改类型定义

### WASM 指针类型别名

```cpp
using WASMPointerF32 = uintptr_t;
using WASMPointerI32 = uintptr_t;
using WASMPointerU8  = uintptr_t;
using WASMPointerU16 = uintptr_t;
using WASMPointerU32 = uintptr_t;
using WASMPointer = uintptr_t;
```

**用途**: 表示 WASM 堆中的内存地址,用于函数签名中传递指针。

**为什么不使用原始指针**:
Emscripten 绑定不允许在函数签名中使用原始指针类型(`float*`, `int*`等),会导致"unbound types"错误。使用 `uintptr_t` 可以绕过这个限制,在 C++ 内部再转换为实际指针。

**示例**:
```cpp
// 错误:Cannot call foo due to unbound types Pi, Pf
void foo(int* data, float* values);

// 正确
void foo(WASMPointerI32 data, WASMPointerF32 values) {
    int* intData = reinterpret_cast<int*>(data);
    float* floatData = reinterpret_cast<float*>(values);
    // ...
}
```

### JSArrayType 模板结构体

```cpp
template <typename T> struct JSArrayType {};
```

**用途**: 将 C++ 类型映射到对应的 JavaScript TypedArray 类型名。

**特化定义**:
```cpp
SPECIALIZE_JSARRAYTYPE( int8_t,    "Int8Array");
SPECIALIZE_JSARRAYTYPE(uint8_t,   "Uint8Array");
SPECIALIZE_JSARRAYTYPE( int16_t,  "Int16Array");
SPECIALIZE_JSARRAYTYPE(uint16_t, "Uint16Array");
SPECIALIZE_JSARRAYTYPE( int32_t,  "Int32Array");
SPECIALIZE_JSARRAYTYPE(uint32_t, "Uint32Array");
SPECIALIZE_JSARRAYTYPE(float,   "Float32Array");
```

**使用场景**: 在 `MakeTypedArray` 中根据 C++ 类型自动选择正确的 JavaScript 类型。

### MakeTypedArray 模板函数

```cpp
template <typename T> TypedArray MakeTypedArray(int count, const T src[]) {
    emscripten::val length = emscripten::val(count);
    emscripten::val jarray = emscripten::val::global(JSArrayType<T>::gName).new_(count);
    jarray.call<void>("set", val(typed_memory_view(count, src)));
    return jarray;
}
```

**功能**: 从 C++ 数组创建 JavaScript TypedArray。

**实现步骤**:
1. 根据类型 T 获取对应的 JavaScript 类型名
2. 在 JavaScript 端创建新的 TypedArray
3. 创建 C++ 数组的内存视图
4. 将数据复制到 JavaScript TypedArray

**使用示例**:
```cpp
float data[] = {1.0f, 2.0f, 3.0f};
Float32Array jsArray = MakeTypedArray(3, data);
// JavaScript 端收到 Float32Array [1.0, 2.0, 3.0]
```

### JSSpan 模板类

```cpp
template <typename T> class JSSpan {
public:
    explicit JSSpan(JSArray src);
    JSSpan(WASMPointer ptr, size_t len, bool takeOwnership);
    ~JSSpan();
    const T* data() const;
    size_t size() const;
private:
    SkSpan<T> fSpan;
    bool fOwned;
};
```

**用途**: 为 JavaScript 数组提供只读访问,管理内存所有权。

**两种构造方式**:

1. **从 JSArray 构造**(性能较低):
```cpp
explicit JSSpan(JSArray src) {
    const size_t len = src["length"].as<size_t>();
    T* data;

    if (src["_ck"].isTrue()) {
        // 直接使用 CanvasKit.Malloc 分配的内存
        fOwned = false;
        data = reinterpret_cast<T*>(src["byteOffset"].as<size_t>());
    } else {
        // 需要复制数据
        fOwned = true;
        data = static_cast<T*>(sk_malloc_throw(len, sizeof(T)));
        // 复制数据...
    }
    fSpan = SkSpan(data, len);
}
```

2. **从 WASM 指针构造**(性能较高):
```cpp
JSSpan(WASMPointer ptr, size_t len, bool takeOwnership)
    : fOwned(takeOwnership) {
    fSpan = SkSpan(reinterpret_cast<T*>(ptr), len);
}
```

**性能注意**:
从 JSArray 构造比从指针构造慢 5-20 倍。建议在 JavaScript 端手动复制数据并传递指针。

**内存管理**:
- `fOwned = true`: 析构时释放内存
- `fOwned = false`: 内存由外部管理,析构时不释放

**使用 malloc/free 的原因**:
明确使用 `malloc/free`(而非 `new/delete`)以与 JavaScript 端的 `CanvasKit.Malloc` 兼容。

## 公共 API 函数

### ptrToSkColor4f

```cpp
SkColor4f ptrToSkColor4f(WASMPointerF32);
```

**功能**: 将 WASM 堆中的 float 指针转换为 `SkColor4f` 对象。

**用途**: 从 JavaScript 传递颜色数据到 C++。

### DecodeImageData

```cpp
std::unique_ptr<SkCodec> DecodeImageData(sk_sp<const SkData>);
```

**功能**: 从 `SkData` 解码图像,返回 `SkCodec`。

**用途**: 图像加载和解码的统一入口。

## 内部实现细节

### SPECIALIZE_JSARRAYTYPE 宏

```cpp
#define SPECIALIZE_JSARRAYTYPE(type, name)                  \
    template <> struct JSArrayType<type> {                  \
        static constexpr const char* const gName = name;    \
    }
```

**作用**: 为每个 C++ 类型特化 `JSArrayType` 模板。

**constexpr 的优势**: 类型名在编译时确定,无运行时开销。

### typed_memory_view 的使用

`typed_memory_view` 是 Emscripten 提供的函数,创建 C++ 内存的 JavaScript 视图:
```cpp
val(typed_memory_view(count, src))
```

**优点**:
- 零拷贝(JavaScript 直接访问 WASM 内存)
- 高性能

**注意事项**:
- 视图的生命周期必须在内存有效期内
- 如果内存被释放,视图变为悬垂引用

### CanvasKit.Malloc 检测

```cpp
if (src["_ck"].isTrue()) {
    // 使用 CanvasKit.Malloc 分配的内存
}
```

**机制**: `CanvasKit.Malloc` 在 JavaScript 端为数组添加 `_ck` 标记,C++ 端通过检测该标记判断是否可以直接使用内存地址。

**性能优化**: 避免不必要的数据复制。

## 依赖关系

### Emscripten 依赖

```cpp
#include <emscripten.h>
#include <emscripten/bind.h>
```

**emscripten::val**: JavaScript 值的 C++ 封装。

**typed_memory_view**: 创建内存视图。

### Skia 依赖

```cpp
#include "include/core/SkData.h"
#include "include/core/SkImage.h"
#include "include/core/SkRefCnt.h"
#include "include/core/SkSpan.h"
#include "include/private/base/SkMalloc.h"
```

**SkSpan**: 轻量级的数据视图。

**SkRefCnt**: 引用计数智能指针。

**sk_malloc_throw**: Skia 的内存分配函数。

## 设计模式与设计决策

### 类型别名模式

通过类型别名提供领域特定的类型系统,提高代码可读性和类型安全。

### 模板元编程

使用模板特化实现类型到字符串的映射,编译时确定,无运行时开销。

### RAII 资源管理

`JSSpan` 使用 RAII 模式管理内存,析构时自动释放资源。

### 零拷贝优化

尽可能使用内存视图和指针传递,避免数据复制。

### 防御性编程

`SafeRef` 和 `SafeUnref` 检查指针是否为空,避免空指针解引用。

## 性能考量

### 数据传输策略

**推荐方式**(快):
```javascript
// JavaScript 端
const data = new Float32Array([1, 2, 3]);
const ptr = CanvasKit._malloc(data.byteLength);
CanvasKit.HEAPF32.set(data, ptr >> 2);
cppFunction(ptr, data.length, true); // takeOwnership=true
```

**不推荐方式**(慢):
```javascript
const data = [1, 2, 3]; // 普通数组
cppFunction(data); // 需要在 C++ 端复制
```

**性能差异**: 5-20倍。

### 内存对齐

WASM 指针按字节寻址,但 TypedArray 可能需要对齐:
```cpp
ptr >> 2  // Float32Array 偏移量(4字节对齐)
```

### 最佳实践

1. **使用 CanvasKit.Malloc**: 允许 C++ 直接访问内存
2. **传递指针和长度**: 避免 JSArray 到 C++ 的转换开销
3. **复用内存**: 对频繁调用的操作,复用已分配的缓冲区
4. **选择合适的所有权**: 根据生命周期决定是否转移所有权

## 相关文件

### 使用此头文件的绑定
- `modules/canvaskit/canvaskit_bindings.cpp` - 主绑定
- `modules/canvaskit/bidi_bindings.cpp` - BiDi 绑定
- `modules/canvaskit/gm_bindings.cpp` - GM 测试绑定
- 所有其他 `*_bindings.cpp` 文件

### Skia 核心
- `include/core/SkSpan.h` - 数据视图
- `include/core/SkData.h` - 数据封装
- `include/private/base/SkMalloc.h` - 内存管理

### Emscripten
- `emscripten/bind.h` - 绑定系统
- `emscripten/val.h` - JavaScript 值封装

### JavaScript 端
- `modules/canvaskit/helper.js` - JavaScript 辅助函数(如 copy1dArray)
- `modules/canvaskit/malloc.js` - CanvasKit.Malloc 实现
