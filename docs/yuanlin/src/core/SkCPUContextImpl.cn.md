# SkCPUContextImpl

> 源文件：src/core/SkCPUContextImpl.h

## 概述

`SkCPUContextImpl` 是 `skcpu::Context` 的内部实现类，位于 `skcpu` 命名空间。它是 CPU 渲染上下文的具体实现，当前为极简设计，主要作为未来扩展的框架预留。

该类是实现细节，不应被外部代码直接使用，所有访问应通过公共 API `skcpu::Context`。

## 架构位置

```
skcpu::Context (公共接口)
  └── ContextImpl (私有实现)
        └── 被 RecorderImpl 引用
```

## 主要类与结构体

### ContextImpl

**继承关系：**`skcpu::Context`

**关键成员变量：**

| 成员 | 类型 | 说明 |
|------|------|------|
| 无 | - | 当前为空类 |

**核心方法：**

| 方法 | 说明 |
|------|------|
| `ContextImpl()` | 默认构造函数 |
| `TODO()` | 静态方法，返回全局单例 |

## 公共 API 函数

### 1. 构造函数

```cpp
ContextImpl() = default
```

**功能：**使用默认构造，当前无需初始化操作。

### 2. 全局单例访问

```cpp
static const ContextImpl* TODO()
```

**功能：**返回全局共享的上下文实例。

**实现：**
```cpp
const ContextImpl* ContextImpl::TODO() {
    static const ContextImpl* gContext =
        static_cast<const ContextImpl*>(Context::Make().release());
    return gContext;
}
```

**使用场景：**
- 过渡期代码，当无法传递上下文时
- `skcpu::Recorder::TODO()` 内部调用

**注意：**这是临时 API，未来应被移除。

## 内部实现细节

### 1. 类定义

```cpp
namespace skcpu {
class ContextImpl final : public Context {
public:
    ContextImpl() = default;
    static const ContextImpl* TODO();
};
}
```

**设计要点：**
- `final` 关键字防止进一步派生
- 所有成员使用默认实现
- 预留扩展空间（未来可添加缓存、线程池等）

### 2. 单例实现

使用函数局部静态变量（C++11 保证线程安全）：

```cpp
static const ContextImpl* gContext = ...;  // 懒初始化，线程安全
```

### 3. 内存管理

```cpp
Context::Make().release()
```

将所有权转移给静态指针，生命周期与程序相同（直到程序退出）。

**潜在问题：**程序退出时不会析构，但因为是空类，无需清理。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `skcpu::Context` | 基类 |

### 被依赖的模块

| 模块 | 使用方式 |
|-----|---------|
| `skcpu::RecorderImpl` | 持有 `const ContextImpl*` |
| `skcpu::Context` | 在 `Make()` 中构造实例 |
| `skcpu::Recorder` | 通过 `TODO()` 间接访问 |

## 设计模式与设计决策

### 1. Pimpl（桥接）模式

公共接口 `Context` 与实现 `ContextImpl` 分离：

**优势：**
- 隐藏实现细节
- 减少头文件依赖
- 保持 ABI 稳定

### 2. 单例模式（有限使用）

仅用于过渡期的 `TODO()` 方法，不推荐长期使用。

### 3. 空对象模式

当前实现为空类，未来逐步填充功能：

**优势：**
- API 接口提前确定
- 允许渐进式开发
- 减少重构风险

### 4. 最终类（Final Class）

使用 `final` 关键字禁止继承：

**原因：**
- 当前设计不支持多态扩展
- 简化类层次结构
- 优化虚函数调用（编译器可去虚化）

## 性能考量

### 1. 内存占用

```cpp
sizeof(ContextImpl) = 1 字节
```

空类优化，实际只占用1字节（C++要求所有对象至少1字节）。

### 2. 构造开销

```cpp
ContextImpl() = default  // 零开销，无操作
```

### 3. 单例访问开销

```cpp
TODO() 耗时 ≈ 1 ns
```

仅返回静态指针，无分支或内存访问。

### 4. 未来扩展的性能影响

**可能添加的成员：**
- 资源缓存：增加内存占用（数 MB）
- 线程池：增加初始化时间（数 ms）
- 统计计数器：增加原子操作开销

## 相关文件

| 文件 | 关系 | 说明 |
|-----|------|------|
| include/core/SkCPUContext.h | 公共接口 | 上下文公共 API |
| src/core/SkCPUContext.cpp | 实现 | 工厂方法和单例实现 |
| src/core/SkCPURecorderImpl.h | 使用者 | 录制器持有上下文指针 |
| src/core/SkResourceCache.h | 未来依赖 | 可能添加的缓存模块 |
