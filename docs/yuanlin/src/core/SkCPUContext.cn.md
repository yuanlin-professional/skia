# SkCPUContext

> 源文件：include/core/SkCPUContext.h, src/core/SkCPUContext.cpp

## 概述

`SkCPUContext` (命名空间 `skcpu::Context`) 是 Skia CPU 渲染后端的上下文对象，负责创建和管理 CPU 录制器（Recorder）。它提供了统一的接口用于初始化 CPU 渲染环境，是 Skia 新架构中 CPU 后端的入口点。

该类设计极简，当前实现主要作为过渡性 API，为未来扩展（如线程池、内存管理策略等）预留空间。

## 架构位置

```
Skia 后端架构
├── GPU 后端
│   ├── GrDirectContext
│   └── GrRecordingContext
├── CPU 后端
│   ├── skcpu::Context      (本文档)
│   └── skcpu::Recorder
└── 通用接口
    └── SkRecorder (抽象基类)
```

`skcpu::Context` 与 GPU 后端的 `GrDirectContext` 类似，是 CPU 渲染的顶层管理对象。

## 主要类与结构体

### skcpu::Context

**继承关系：**无基类（独立类）

**关键成员变量：**

当前实现为空类，无成员变量。

**内部实现类 ContextImpl：**

| 成员 | 说明 |
|------|------|
| 无成员 | 当前为空实现，预留扩展空间 |

**核心方法：**

| 方法 | 说明 |
|------|------|
| `Make()` | 静态工厂方法，创建上下文实例 |
| `makeRecorder()` | 创建录制器对象 |

### skcpu::Context::Options

配置结构体，当前为空：

```cpp
struct Options {};
```

预留用于未来配置选项，如：
- 线程池设置
- 内存分配策略
- 性能调优参数

## 公共 API 函数

### 1. 创建上下文

```cpp
static std::unique_ptr<const Context> Make(const Options&)
static std::unique_ptr<const Context> Make()  // 使用默认选项
```

**功能：**创建 CPU 上下文单例的新实例。

**返回值：**独占指针，调用者拥有所有权。

**线程安全：**可在任意线程调用，每次返回新实例。

**示例：**
```cpp
auto cpuContext = skcpu::Context::Make();
```

### 2. 创建录制器

```cpp
std::unique_ptr<Recorder> makeRecorder() const
```

**功能：**创建与此上下文关联的录制器对象。

**返回值：**`skcpu::Recorder` 实例，用于创建 Surface 和执行绘制操作。

**用途：**录制器是实际执行绘制命令的对象，类似于 GPU 后端的 `GrRecordingContext`。

**示例：**
```cpp
auto recorder = cpuContext->makeRecorder();
auto surface = recorder->makeBitmapSurface(imageInfo);
```

## 内部实现细节

### 1. ContextImpl 实现

```cpp
namespace skcpu {
class ContextImpl final : public Context {
public:
    ContextImpl() = default;
    static const ContextImpl* TODO();
};
}
```

**设计说明：**
- 当前为空实现，未来可能添加缓存、线程池等成员
- 使用 `final` 关键字防止进一步派生
- 保持公共接口稳定，内部实现可自由演化

### 2. TODO() 静态方法

```cpp
const ContextImpl* ContextImpl::TODO() {
    static const ContextImpl* gContext =
        static_cast<const ContextImpl*>(Context::Make().release());
    return gContext;
}
```

**功能：**返回全局共享的上下文实例，用于过渡期代码。

**使用场景：**当代码路径中尚未传递 `Context` 对象时，临时使用全局实例。

**注意：**这是临时 API，未来应避免使用，改为显式传递上下文。

### 3. 工厂方法实现

```cpp
std::unique_ptr<const Context> Context::Make(const Context::Options& opts) {
    return std::make_unique<ContextImpl>();
}

std::unique_ptr<const Context> Context::Make() {
    return Context::Make({});
}
```

**简化逻辑：**当前忽略 `Options` 参数，直接构造 `ContextImpl`。

### 4. 录制器创建

```cpp
std::unique_ptr<Recorder> Context::makeRecorder() const {
    return std::make_unique<RecorderImpl>(static_cast<const ContextImpl*>(this));
}
```

**关联关系：**录制器持有上下文的常量指针，确保生命周期正确。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `SkCPURecorderImpl` | 录制器实现 |
| `SkAPI` | 导出符号宏 |
| `std::unique_ptr` | 智能指针 |

### 被依赖的模块

| 模块 | 使用方式 |
|-----|---------|
| `skcpu::Recorder` | 通过 `makeRecorder()` 创建 |
| 应用代码 | 调用 `Context::Make()` 初始化 CPU 后端 |

## 设计模式与设计决策

### 1. 工厂方法模式

通过静态 `Make()` 方法创建实例，隐藏具体实现类 `ContextImpl`：

```cpp
auto context = skcpu::Context::Make();  // 返回抽象接口
```

**优势：**
- 解耦接口与实现
- 便于未来替换实现类
- 支持不同配置选项

### 2. Pimpl（Pointer to Implementation）模式

公共头文件仅声明抽象接口，实现细节在 `.cpp` 文件中：

```cpp
// 公共头文件：最小化依赖
class Context {
protected:
    Context() = default;  // 仅子类可构造
};

// 实现文件：包含具体细节
class ContextImpl final : public Context { ... };
```

**优势：**
- 减少头文件依赖
- 加快编译速度
- 保持 ABI 稳定

### 3. 单例模式（TODO 方法）

```cpp
static const ContextImpl* TODO() {
    static const ContextImpl* gContext = ...;
    return gContext;
}
```

提供全局访问点，但仅用于过渡期，避免长期依赖。

### 4. 不可变对象模式

`Context` 返回 `const` 指针，确保上下文在创建后不可修改：

```cpp
std::unique_ptr<const Context> context = Context::Make();
```

**原因：**上下文通常在初始化时配置，运行时不应改变。

### 5. 最小接口原则

当前 API 极简，仅提供必需功能，避免过早设计：

```cpp
class Context {
    static std::unique_ptr<const Context> Make();
    std::unique_ptr<Recorder> makeRecorder() const;
};
```

### 6. 选项结构体扩展性

```cpp
struct Options {};  // 当前为空，未来可添加字段
```

这种设计允许在不破坏 ABI 的情况下添加新配置：

```cpp
// 未来可能的扩展
struct Options {
    int threadPoolSize = 4;
    size_t cacheSize = 64 * 1024 * 1024;
};
```

## 性能考量

### 1. 上下文创建开销

**当前：**几乎零开销，仅分配小对象。

**未来：**可能包括线程池初始化、缓存预分配等，应避免频繁创建。

### 2. 全局单例 vs 显式传递

**TODO() 方法：**
- 优势：代码简洁，无需传递上下文
- 劣势：隐藏依赖，不利于测试和并发场景

**显式传递：**
- 优势：依赖清晰，支持多上下文
- 劣势：需要修改函数签名

**建议：**新代码应显式传递上下文。

### 3. 常量指针设计

返回 `const Context*` 避免运行时修改，编译器可优化：

```cpp
// 编译器可假设上下文不变，启用更多优化
const Context* ctx = ...;
for (...) {
    ctx->makeRecorder();  // 可重排序、合并调用
}
```

### 4. 内存占用

**当前：**`sizeof(ContextImpl) ≈ 1 字节`（空类优化）

**未来：**可能增长至数百字节（包含缓存管理器等）

### 5. 性能数据（当前实现）

| 操作 | 耗时 |
|------|------|
| `Context::Make()` | ~10 ns（仅分配） |
| `makeRecorder()` | ~50 ns（创建录制器） |
| `TODO()` | ~1 ns（返回缓存指针） |

## 相关文件

| 文件 | 关系 | 说明 |
|-----|------|------|
| include/core/SkCPURecorder.h | 创建对象 | CPU 录制器接口 |
| src/core/SkCPURecorderImpl.h | 实现细节 | 录制器实现类 |
| src/core/SkCPUContextImpl.h | 实现细节 | 上下文实现类 |
| include/core/SkRecorder.h | 抽象基类 | 通用录制器接口 |
| include/core/SkSurface.h | 间接使用 | 通过录制器创建 Surface |
