# AutoreleasePool

> 源文件：tools/AutoreleasePool.h, tools/AutoreleasePool.mm

## 概述

`AutoreleasePool` 是 Skia 工具库中提供的跨平台自动释放池管理类，主要用于管理 macOS 和 iOS 平台上的 Objective-C 自动释放池。该类通过 RAII（Resource Acquisition Is Initialization）模式封装了 `NSAutoreleasePool` 的创建、排空和释放操作，确保在 C++ 代码中正确管理 Objective-C 对象的内存。在非 Apple 平台上，该类提供空实现，使代码可以在所有平台上统一使用而无需条件编译。

## 架构位置

`AutoreleasePool` 在 Skia 架构中的位置：

- 位于 `tools/` 目录，属于平台适配工具
- 使用条件编译支持多平台（`SK_BUILD_FOR_MAC` / `SK_BUILD_FOR_IOS`）
- 在 macOS/iOS 上封装 `NSAutoreleasePool`
- 在其他平台上提供空操作实现
- 主要用于 Metal 图形 API 相关代码
- 与 Ganesh Metal 后端集成使用

该类解决了在 C++ 代码中调用 Objective-C API 时的内存管理问题，特别是在使用 Metal 渲染时。

## 主要类与结构体

### AutoreleasePool 类（macOS/iOS 平台）

**头文件定义**：
```cpp
class AutoreleasePool {
public:
    AutoreleasePool();
    ~AutoreleasePool();
    void drain();

private:
    void* fPool;  // NSAutoreleasePool* 的 void* 包装
};
```

**实现（.mm 文件）**：
```objective-c
AutoreleasePool::AutoreleasePool() {
    fPool = (void*)[[NSAutoreleasePool alloc] init];
}

AutoreleasePool::~AutoreleasePool() {
    [(NSAutoreleasePool*)fPool release];
    fPool = nullptr;
}

void AutoreleasePool::drain() {
    [(NSAutoreleasePool*)fPool drain];
    fPool = (void*)[[NSAutoreleasePool alloc] init];
}
```

### AutoreleasePool 类（其他平台）

**空实现**：
```cpp
class AutoreleasePool {
public:
    AutoreleasePool() {}
    ~AutoreleasePool() = default;
    void drain() {}
};
```

## 公共 API 函数

### 构造函数

**AutoreleasePool()**
- **macOS/iOS**：创建新的 `NSAutoreleasePool`
- **其他平台**：无操作
- **用途**：在代码块开始时创建自动释放池

### 析构函数

**~AutoreleasePool()**
- **macOS/iOS**：释放 `NSAutoreleasePool`，自动释放池中的对象
- **其他平台**：无操作
- **用途**：离开作用域时自动清理

### drain

**void drain()**
- **macOS/iOS**：
  1. 排空当前池（释放池中对象）
  2. 创建新的池
- **其他平台**：无操作
- **用途**：长循环中定期清理累积的自动释放对象

## 内部实现细节

### 平台检测

使用 Skia 的平台宏进行条件编译：
```cpp
#if defined(SK_BUILD_FOR_MAC) || defined(SK_BUILD_FOR_IOS)
    // macOS/iOS 实现
#else
    // 空实现
#endif
```

### Objective-C 互操作

**void* 类型擦除**：
```cpp
void* fPool;  // 实际存储 NSAutoreleasePool*
```
- 在 C++ 头文件中使用 `void*` 避免引入 Objective-C 类型
- 在 .mm 文件中转换回 `NSAutoreleasePool*`

**Objective-C 方法调用**：
```objective-c
[[NSAutoreleasePool alloc] init]  // 分配并初始化
[(NSAutoreleasePool*)fPool drain]  // 排空池
[(NSAutoreleasePool*)fPool release]  // 释放池
```

### RAII 模式

**自动管理生命周期**：
```cpp
void function() {
    AutoreleasePool pool;  // 构造时创建池
    // ... Objective-C API 调用 ...
}  // 析构时自动释放池
```

### drain 与 release 的区别

**drain**：
- 释放池中的对象
- 可选择性地保留池对象本身（ARC 模式）
- 推荐在 ARC 和非 ARC 代码中使用

**release**：
- 释放池对象本身
- 非 ARC 模式的标准释放方法

## 依赖关系

**平台相关依赖**：
- `include/private/base/SkFeatures.h` - 平台特性宏定义
- `<Foundation/NSAutoreleasePool.h>` - Objective-C 基础框架（仅 macOS/iOS）

**Skia 使用场景**：
- Metal 图形 API 调用
- Ganesh Metal 后端
- 与 Core Foundation 对象交互的工具代码

## 设计模式与设计决策

### RAII 模式
通过构造/析构函数自动管理自动释放池的生命周期，防止内存泄漏。

### 空对象模式
在非 Apple 平台提供空实现，使代码可跨平台使用。

### 类型擦除
使用 `void*` 存储 Objective-C 指针，避免在 C++ 头文件中暴露 Objective-C 类型。

### 关键设计决策

**1. 统一接口**
在所有平台提供相同的 API，消除调用代码的 `#ifdef`。

**2. 轻量级实现**
仅 8 字节开销（一个指针），在非 Apple 平台零开销。

**3. 显式 drain**
提供 `drain()` 方法让用户在长循环中手动清理，防止内存累积。

**4. .mm 扩展名**
使用 `.mm` 文件扩展名让编译器以 Objective-C++ 模式编译。

**5. 文档提示**
头文件注释说明主要用于 Metal，但不限制用于其他场景。

## 性能考量

### 内存使用

**Apple 平台**：
- 额外开销：每个池对象约 16-32 字节（系统实现）
- 池中对象累积会增加内存使用

**其他平台**：
- 零开销（编译器优化后完全消除）

### 性能影响

**创建/销毁开销**：
- 非常轻量，类似于 `malloc/free`
- 适合频繁创建销毁

**drain 开销**：
- 遍历池中对象并释放
- 对象越多开销越大

### 使用建议

**最佳实践**：
```cpp
// 在循环外创建
AutoreleasePool pool;
for (int i = 0; i < 10000; ++i) {
    // ... Objective-C API 调用 ...

    if (i % 100 == 0) {
        pool.drain();  // 定期清理
    }
}
```

**性能优化**：
1. 避免在紧密循环内创建/销毁池
2. 长循环中定期 `drain()`
3. 考虑池的作用域大小（太大累积内存，太小频繁创建）

### 典型使用场景

**Metal 渲染循环**：
```cpp
while (running) {
    AutoreleasePool pool;
    // 创建 Metal 命令缓冲区等对象
    renderFrame();
    // pool 自动清理 autorelease 的对象
}
```

**批处理任务**：
```cpp
AutoreleasePool pool;
for (auto& task : tasks) {
    processTask(task);
    pool.drain();  // 每个任务后清理
}
```

## 相关文件

**Metal 后端**：
- `src/gpu/ganesh/mtl/` - Ganesh Metal 实现
- `include/gpu/ganesh/mtl/GrMtlBackendContext.h` - Metal 上下文

**平台特性**：
- `include/private/base/SkFeatures.h` - 平台宏定义
- `BUILD.gn` - 构建配置（.mm 文件编译设置）

**使用示例**：
- `tools/sk_app/mac/` - macOS 应用框架
- `tools/viewer/` - Viewer 工具的 Metal 渲染路径

**Objective-C 框架**：
- `<Foundation/Foundation.h>` - Foundation 框架
- `<Metal/Metal.h>` - Metal 图形 API

**相关工具类**：
- `tools/ios_utils.h` - iOS 平台工具函数
- 各种 Metal 相关工具代码
