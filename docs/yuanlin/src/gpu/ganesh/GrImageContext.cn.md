# GrImageContext

> 源文件: src/gpu/ganesh/GrImageContext.cpp

## 概述

`GrImageContext` 是 Skia Ganesh GPU 后端中用于图像操作的上下文类。它继承自 `GrContext_Base`,提供了比完整的 `GrDirectContext` 更轻量的上下文实现,专门用于不需要完整渲染能力的图像处理场景,特别是 Promise Image (延迟加载的图像) 的管理。

该实现文件非常简洁,主要包含构造函数、析构函数以及上下文放弃 (abandon) 的逻辑。大部分功能通过继承和组合的方式从基类和成员对象获得。

## 架构位置

`GrImageContext` 位于 Ganesh 上下文层次结构的中间层:

```
GrContext_Base (基础上下文)
    └── GrImageContext (图像上下文)
            └── GrDirectContext (完整渲染上下文)
```

使用场景:
- **Promise Image**: 延迟加载纹理的占位符上下文
- **轻量级图像操作**: 不需要完整 GPU 能力的场景
- **上下文共享**: 多个图像上下文可以共享线程安全代理

与其他模块的关系:
- 持有 `GrContextThreadSafeProxy` 管理线程安全状态
- 被 `GrDirectContext` 继承,扩展为完整上下文
- 支持 Promise Image 的创建和管理

## 主要类与结构体

### 继承关系

```
GrContext_Base
    └── GrImageContext
            └── GrDirectContext
```

### 关键成员变量

继承自 `GrContext_Base`:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fThreadSafeProxy` | `sk_sp<GrContextThreadSafeProxy>` | 线程安全代理 |

## 公共 API 函数

### 构造与析构

```cpp
// 构造函数(受保护)
GrImageContext(sk_sp<GrContextThreadSafeProxy> proxy);

// 析构函数
~GrImageContext();
```

### 上下文管理

```cpp
// 放弃上下文(上下文丢失时调用)
void abandonContext();

// 检查上下文是否已被放弃
bool abandoned();
```

### 工厂方法

```cpp
// 为 Promise Image 创建图像上下文(私有,通过 Priv 访问)
static sk_sp<GrImageContext> MakeForPromiseImage(
    sk_sp<GrContextThreadSafeProxy> tsp);
```

## 内部实现细节

### 构造函数实现

```cpp
GrImageContext::GrImageContext(sk_sp<GrContextThreadSafeProxy> proxy)
    : GrContext_Base(std::move(proxy)) {
}
```

- 接受线程安全代理作为参数
- 转发给基类构造函数
- 使用移动语义避免引用计数开销

### 析构函数实现

```cpp
GrImageContext::~GrImageContext() {}
```

- 空析构函数
- 依赖基类和成员的自动析构
- 线程安全代理的智能指针自动释放

### abandonContext 实现

```cpp
void GrImageContext::abandonContext() {
    fThreadSafeProxy->priv().abandonContext();
}
```

- 委托给线程安全代理的 `priv()` 接口
- 标记上下文为已放弃状态
- 通常在 GPU 上下文丢失时调用

### abandoned 实现

```cpp
bool GrImageContext::abandoned() {
    return fThreadSafeProxy->priv().abandoned();
}
```

- 查询线程安全代理的放弃状态
- 用于检查上下文是否仍然有效
- 在执行 GPU 操作前检查

### MakeForPromiseImage 实现

```cpp
sk_sp<GrImageContext> GrImageContext::MakeForPromiseImage(
    sk_sp<GrContextThreadSafeProxy> tsp) {
    return sk_sp<GrImageContext>(new GrImageContext(std::move(tsp)));
}
```

- 静态工厂方法
- 创建专门用于 Promise Image 的上下文
- 私有方法,通过 `GrImageContextPriv` 访问
- 返回智能指针管理生命周期

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrContext_Base` | 基类,提供基础上下文功能 |
| `GrContextThreadSafeProxy` | 线程安全代理 |
| `GrContextThreadSafeProxyPriv` | 代理的特权接口 |
| `SkRefCnt.h` | 智能指针支持 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| `GrDirectContext` | 继承 `GrImageContext` |
| `GrImageContextPriv` | 提供特权访问 |
| Promise Image 系统 | 使用 `MakeForPromiseImage()` |
| 图像解码器 | 可能使用图像上下文 |

## 设计模式与设计决策

### 设计模式

1. **工厂方法模式 (Factory Method)**
   - `MakeForPromiseImage()` 创建特定类型的上下文
   - 封装构造逻辑
   - 返回智能指针管理生命周期

2. **代理模式 (Proxy)**
   - `fThreadSafeProxy` 代理线程安全操作
   - 分离线程安全逻辑和上下文逻辑
   - 支持跨线程共享

3. **委托模式 (Delegation)**
   - `abandonContext()` 和 `abandoned()` 委托给代理
   - 避免重复实现
   - 集中管理状态

### 关键设计决策

1. **为何需要 GrImageContext?**
   - `GrDirectContext` 包含完整的渲染管线,较重量
   - Promise Image 只需要基础的上下文功能
   - 分离关注点,减少依赖

2. **为何继承 GrContext_Base?**
   - 共享基础上下文功能
   - 保持类型层次的清晰性
   - 支持多态使用

3. **线程安全代理的作用**
   - 上下文本身是单线程的
   - 代理可以在多线程间共享
   - 存储线程安全的配置信息

4. **abandoned 状态的意义**
   - GPU 上下文可能因驱动错误丢失
   - 标记上下文为不可用状态
   - 防止后续操作导致崩溃

5. **MakeForPromiseImage 为何是私有的?**
   - Promise Image 是内部实现细节
   - 普通用户不应直接创建
   - 通过 `GrImageContextPriv` 限制访问

6. **极简实现的合理性**
   - 大部分功能继承自基类
   - 线程安全代理处理状态管理
   - 保持代码简洁和可维护性

## 性能考量

### 轻量级设计

- 相比 `GrDirectContext`,减少了渲染管线的开销
- 适合只需要基础上下文功能的场景
- 减少内存占用

### 移动语义

```cpp
GrImageContext(std::move(proxy))
```

- 避免智能指针的引用计数操作
- 减少原子操作开销

### 委托调用

- `abandonContext()` 和 `abandoned()` 是简单的转发
- 内联优化后无额外开销
- 保持接口的清晰性

### 智能指针管理

- 使用 `sk_sp` 自动管理生命周期
- 避免手动内存管理
- 线程安全的引用计数

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/private/gpu/ganesh/GrImageContext.h` | 头文件 | 类定义 |
| `src/gpu/ganesh/GrContext_Base.h` | 基类 | 基础上下文 |
| `include/gpu/ganesh/GrContextThreadSafeProxy.h` | 依赖 | 线程安全代理 |
| `src/gpu/ganesh/GrContextThreadSafeProxyPriv.h` | 依赖 | 代理特权接口 |
| `src/gpu/ganesh/GrImageContextPriv.h` | 特权 | 特权访问器 |
| `include/gpu/ganesh/GrDirectContext.h` | 派生 | 完整渲染上下文 |
