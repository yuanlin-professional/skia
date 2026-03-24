# SkUniqueCFRef — Core Foundation 对象的 RAII 智能指针

> 源文件: `src/utils/mac/SkUniqueCFRef.h`

## 概述

`SkUniqueCFRef.h` 定义了一个类型别名模板 `SkUniqueCFRef<T>`，用于以 RAII（资源获取即初始化）方式管理 Apple Core Foundation (CF) 对象的生命周期。Core Foundation 的对象（如 `CGImageRef`、`CFStringRef`、`CGColorSpaceRef` 等）采用手动引用计数管理（`CFRetain`/`CFRelease`），容易出现资源泄漏。`SkUniqueCFRef` 通过 `std::unique_ptr` 包装，在作用域结束时自动调用 `CFRelease` 释放资源。

该文件仅在 macOS (`SK_BUILD_FOR_MAC`) 或 iOS (`SK_BUILD_FOR_IOS`) 平台上编译。

## 架构位置

```
Skia
└── src/utils/mac/
    ├── SkUniqueCFRef.h         // 本文件
    ├── SkCreateCGImageRef.cpp  // 使用者：CG 图像互操作
    ├── SkCGBase.h              // CG 基础定义
    └── SkCGGeometry.h          // CG 几何定义
```

该模块是 Skia 在 Apple 平台上进行资源管理的基础工具，被所有涉及 CF/CG 对象操作的模块广泛使用。

## 主要类与结构体

### `SkUniqueCFRef<CFRef>`（类型别名模板）

```cpp
template <typename CFRef> using SkUniqueCFRef =
    std::unique_ptr<std::remove_pointer_t<CFRef>, SkFunctionObject<CFRelease>>;
```

- **模板参数**: `CFRef` — Core Foundation 引用类型（如 `CGImageRef`、`CFStringRef`）
- **底层实现**: `std::unique_ptr`，元素类型为去除指针后的类型，删除器为 `CFRelease` 的函数对象封装
- **类型变换**: `std::remove_pointer_t<CFRef>` 将 `CGImageRef`（即 `CGImage*`）转换为 `CGImage`，满足 `unique_ptr` 要求的非指针类型
- **删除器**: `SkFunctionObject<CFRelease>` 是 Skia 提供的函数指针封装，将 `CFRelease` 包装为零大小的可调用对象

## 公共 API 函数

作为类型别名，`SkUniqueCFRef` 继承了 `std::unique_ptr` 的全部接口：

| 方法 | 功能 |
|------|------|
| `get()` | 获取底层 CF 对象指针 |
| `release()` | 释放所有权并返回指针 |
| `reset()` | 替换管理的对象 |
| 析构函数 | 自动调用 `CFRelease` |
| `operator bool()` | 检查是否持有对象 |

### 典型使用方式

```cpp
SkUniqueCFRef<CGColorSpaceRef> cs(CGColorSpaceCreateWithName(kCGColorSpaceSRGB));
// 使用 cs.get() 访问底层指针
// 作用域结束时自动调用 CFRelease
```

## 内部实现细节

实现利用了 C++ 模板元编程的两个关键技术：

1. **`std::remove_pointer_t`**: CF 引用类型（如 `CGImageRef`）本质上是指向不透明结构体的指针（如 `CGImage*`）。`unique_ptr` 需要一个非指针类型作为模板参数，因此需要去除指针层
2. **`SkFunctionObject<CFRelease>`**: 将全局函数 `CFRelease` 包装为零大小的函数对象类型。这使得 `unique_ptr` 不需要在每个实例中存储函数指针，与裸指针具有相同的内存大小

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `include/core/SkTypes.h` | 平台编译宏定义 |
| `include/private/base/SkTemplates.h` | `SkFunctionObject` 函数对象封装 |
| `<CoreFoundation/CoreFoundation.h>` | `CFRelease` 函数和 CF 类型定义 |
| `<memory>` | `std::unique_ptr` |
| `<type_traits>` | `std::remove_pointer_t` |

## 设计模式与设计决策

1. **RAII 模式**: 通过 C++ 的确定性析构确保 CF 对象在任何退出路径（包括异常）上都被正确释放
2. **零开销抽象**: `SkFunctionObject` 使删除器为零大小类型，`SkUniqueCFRef` 的大小与裸指针完全相同
3. **类型别名而非继承**: 使用 `using` 别名而非自定义类，最大化利用 `std::unique_ptr` 已有的接口和行为
4. **条件编译**: 整个定义在 Apple 平台宏保护下，非 Apple 平台不会引入 Core Foundation 依赖
5. **独占所有权**: 使用 `unique_ptr`（而非 `shared_ptr`）表达独占所有权语义，与 CF 的 Create/Copy 所有权规则匹配

## 性能考量

- 零额外内存开销：与裸指针相同大小
- 零运行时开销：删除器在编译时内联，析构仅调用 `CFRelease`
- 移动语义：支持高效的所有权转移

## 相关文件

- `include/private/base/SkTemplates.h` — `SkFunctionObject` 定义
- `src/utils/mac/SkCreateCGImageRef.cpp` — 主要使用者
- `src/utils/mac/SkCGBase.h` — CG 基础定义
- `src/ports/SkFontHost_mac_ct.cpp` — Core Text 字体中使用
