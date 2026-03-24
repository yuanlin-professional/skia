# GrResourceHandle

> 源文件
> - src/gpu/ganesh/GrResourceHandle.h

## 概述

`GrResourceHandle` 是一个轻量级的模板类,用于表示资源的不透明句柄(opaque handle)。它封装了一个整数索引,提供类型安全的句柄机制,避免直接使用原始指针或整数。通过宏 `GR_DEFINE_RESOURCE_HANDLE_CLASS`,可以方便地为不同类型的资源定义专用的句柄类型。这种设计在 Skia GPU 着色器系统中广泛使用,例如 `UniformHandle` 和 `SamplerHandle`。

## 架构位置

在 Skia GPU 架构中的位置:

```
着色器系统
    ├── UniformHandler
    │   └── UniformHandle (GrResourceHandle 实例)
    ├── VaryingHandler
    │   └── VaryingHandle (GrResourceHandle 实例)
    └── 其他 Handler
        └── 各种 Handle
```

这是一个基础工具类,被着色器编译和资源管理系统广泛使用。

## 主要类与结构体

### 核心模板类

```cpp
template <typename kind> class GrResourceHandle {
public:
    GrResourceHandle(int value);
    GrResourceHandle();

    bool operator==(const GrResourceHandle& other) const;
    bool isValid() const;
    int toIndex() const;

private:
    static const int kInvalid_ResourceHandle = -1;
    int fValue;
};
```

### 宏定义

```cpp
#define GR_DEFINE_RESOURCE_HANDLE_CLASS(name) \
    struct name##Kind {};  \
    using name = GrResourceHandle<name##Kind>;
```

用于快速定义新的句柄类型。

## 公共 API 函数

### 构造函数

```cpp
GrResourceHandle(int value);  // 从索引构造,带有效性检查
GrResourceHandle();           // 构造无效句柄
```

**关键点**:
```cpp
GrResourceHandle(int value) : fValue(value) {
    SkASSERT(this->isValid());  // 确保索引有效(>= 0)
}
```

### 比较操作

```cpp
bool operator==(const GrResourceHandle& other) const {
    return other.fValue == fValue;
}
```

支持句柄相等性比较。

### 有效性检查

```cpp
bool isValid() const {
    return kInvalid_ResourceHandle != fValue;
}
```

判断句柄是否有效(索引 != -1)。

### 索引转换

```cpp
int toIndex() const {
    SkASSERT(this->isValid());
    return fValue;
}
```

将句柄转换回整数索引,使用前必须确保有效。

## 内部实现细节

### 类型安全机制

通过模板参数 `kind` 实现类型区分:

```cpp
// 定义两种不同的句柄类型
GR_DEFINE_RESOURCE_HANDLE_CLASS(UniformHandle);
GR_DEFINE_RESOURCE_HANDLE_CLASS(SamplerHandle);

// 展开后:
struct UniformHandleKind {};
using UniformHandle = GrResourceHandle<UniformHandleKind>;

struct SamplerHandleKind {};
using SamplerHandle = GrResourceHandle<SamplerHandleKind>;
```

**类型安全**:
```cpp
UniformHandle u(0);
SamplerHandle s(1);

u == s;  // 编译错误:类型不匹配
```

### 无效句柄表示

```cpp
static const int kInvalid_ResourceHandle = -1;
```

- 使用 -1 表示无效句柄
- 允许 0 作为有效索引
- 与数组索引自然对应

### 宏展开示例

```cpp
GR_DEFINE_RESOURCE_HANDLE_CLASS(MyHandle);

// 展开为:
struct MyHandleKind {};
using MyHandle = GrResourceHandle<MyHandleKind>;

// 使用:
MyHandle handle(42);
if (handle.isValid()) {
    int index = handle.toIndex();  // 42
    items[index] = ...;
}
```

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖原因 |
|---------|---------|
| `SkTypes.h` | 基础类型和断言 |

### 被依赖的模块

| 模块名称 | 使用方式 | 具体句柄类型 |
|---------|---------|-------------|
| `GrGLSLUniformHandler` | Uniform 资源 | `UniformHandle` |
| `GrGLSLUniformHandler` | 采样器资源 | `SamplerHandle` |
| `GrGLSLVaryingHandler` | Varying 变量 | `VaryingHandle` |
| 各种 Processor | 着色器资源引用 | 多种 Handle |

## 设计模式与设计决策

### 设计模式

1. **类型安全句柄模式** (Type-Safe Handle):
   - 使用模板参数区分类型
   - 编译期类型检查
   - 避免句柄混用

2. **不透明句柄模式** (Opaque Handle):
   - 隐藏内部实现(整数索引)
   - 提供抽象接口
   - 便于未来修改实现

3. **命名类型模式** (Named Type):
   - 通过宏创建语义化的类型
   - 增强代码可读性

### 关键设计决策

**为何使用模板而非继承**:

优点:
- 零运行时开销
- 完全的类型安全
- 不需要虚函数表

vs 继承方案:
```cpp
// 不推荐:运行时开销,可能混用
class ResourceHandle { virtual ~ResourceHandle(); };
class UniformHandle : public ResourceHandle {};
class SamplerHandle : public ResourceHandle {};

ResourceHandle* h = new UniformHandle();  // 可以混用基类指针
```

**为何使用整数索引**:
- 轻量级(4 字节)
- 直接映射到数组索引
- 易于序列化和传递
- 无内存管理开销

vs 指针:
```cpp
// 不推荐:生命周期管理复杂
template <typename T>
class Handle {
    T* ptr;  // 需要管理生命周期
};
```

**为何使用 -1 表示无效**:
- 0 可以作为有效的数组索引
- -1 明确表示"无效"
- 符合 C/C++ 惯例

**为何需要有效性断言**:
```cpp
GrResourceHandle(int value) : fValue(value) {
    SkASSERT(this->isValid());
}
```

- 早期发现错误
- 调试模式下捕获无效句柄
- Release 模式下无开销

**为何需要宏**:
```cpp
#define GR_DEFINE_RESOURCE_HANDLE_CLASS(name)
```

优点:
- 简化定义语法
- 统一命名约定
- 减少重复代码

使用示例:
```cpp
// 一行定义
GR_DEFINE_RESOURCE_HANDLE_CLASS(MyHandle);

// vs 手动定义
struct MyHandleKind {};
using MyHandle = GrResourceHandle<MyHandleKind>;
```

**为何只有相等比较**:
- 句柄主要用于查找和匹配
- 不需要排序(不是有序容器的键)
- 保持接口简洁

**为何 toIndex 需要断言**:
```cpp
int toIndex() const {
    SkASSERT(this->isValid());
    return fValue;
}
```

- 防止使用无效句柄
- 调试时提供清晰的错误信息
- 强制调用者检查有效性

## 性能考量

### 内存占用

- 仅 4 字节(一个 int)
- 与原始整数相同
- 可以按值传递

### 运行时开销

**零开销抽象**:
```cpp
GrResourceHandle<SomeKind> handle(42);
int index = handle.toIndex();
```

编译后:
```asm
mov eax, 42  ; 直接使用整数
```

- 所有方法都内联
- 没有虚函数调用
- 没有额外的间接访问

### 类型安全的编译期检查

```cpp
UniformHandle u = ...;
SamplerHandle s = ...;
u == s;  // 编译错误,零运行时成本
```

- 类型错误在编译期发现
- 不需要运行时类型检查
- RTTI 不需要启用

### 与原始整数的对比

| 特性 | 原始整数 | GrResourceHandle |
|------|---------|-----------------|
| 内存占用 | 4 字节 | 4 字节 |
| 运行时性能 | 无开销 | 无开销 |
| 类型安全 | 无 | 完全 |
| 可读性 | 低 | 高 |
| 错误检测 | 运行时 | 编译期 |

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/glsl/GrGLSLUniformHandler.h` | 使用者 | 定义 UniformHandle 和 SamplerHandle |
| `src/gpu/ganesh/glsl/GrGLSLVarying.h` | 使用者 | 定义 VaryingHandle |
| `src/gpu/ganesh/glsl/GrGLSLFragmentShaderBuilder.h` | 使用者 | 使用各种 Handle |
| `src/gpu/ganesh/glsl/GrGLSLVertexGeoBuilder.h` | 使用者 | 使用各种 Handle |

**在 Skia 中定义的句柄类型**:
- `UniformHandle`: Uniform 变量句柄
- `SamplerHandle`: 采样器句柄
- `VaryingHandle`: Varying 变量句柄
- 其他特定于各 Handler 的句柄

## 使用示例

```cpp
// 定义新的句柄类型
GR_DEFINE_RESOURCE_HANDLE_CLASS(MyResourceHandle);

// 创建句柄
MyResourceHandle handle(0);
MyResourceHandle invalidHandle;  // 无效句柄

// 检查有效性
if (handle.isValid()) {
    int index = handle.toIndex();
    resources[index] = ...;
}

// 比较句柄
if (handle1 == handle2) {
    // 引用同一资源
}

// 类型安全
MyResourceHandle a(0);
OtherResourceHandle b(0);
a == b;  // 编译错误!
```

这个简洁的类提供了强大的类型安全保证,是 Skia GPU 着色器系统的基础构建块。
