# GrPromiseImageTexture

> 源文件
> - src/gpu/ganesh/GrPromiseImageTexture.cpp

## 概述

`GrPromiseImageTexture` 是 Ganesh GPU 后端中用于支持 Chrome 的 Promise Image 功能的简单包装类。它封装了一个 `GrBackendTexture`,代表一个由客户端通过 Promise 回调提供的纹理。

Promise Image 是一种允许客户端在异步回调中提供纹理数据的机制,主要用于跨进程或跨线程的纹理共享场景,特别是 Chrome 浏览器中的 GPU 进程架构。

该类的设计极其简洁:
- 仅包含一个 `GrBackendTexture` 成员
- 提供简单的构造和析构
- 无复杂的生命周期管理
- 作为纯数据容器使用

## 架构位置

`GrPromiseImageTexture` 在 Chrome 集成架构中的位置:

```
Chrome 渲染进程
    ↓
Promise 回调
    ↓
GrPromiseImageTexture (包装后端纹理)
    ↓
GrBackendTexture (跨 API 的纹理描述)
    ↓
Ganesh GPU 后端 (使用纹理)
    ↓
实际 GPU 资源
```

它是 Chrome 特定功能,通过 `include/private/chromium/` 路径暴露。

## 主要类与结构体

### GrPromiseImageTexture 类

**继承关系**:
- 无继承关系,独立的包装类

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fBackendTexture | GrBackendTexture | 包装的后端纹理 |

注意:成员变量的定义在头文件 `include/private/chromium/GrPromiseImageTexture.h` 中,实现文件仅包含构造和析构函数。

## 公共 API 函数

### 构造函数

```cpp
GrPromiseImageTexture::GrPromiseImageTexture(const GrBackendTexture& backendTexture) {
    SkASSERT(backendTexture.isValid());
    fBackendTexture = backendTexture;
}
```

接受一个有效的 `GrBackendTexture` 并存储它。使用断言确保输入纹理有效。

### 析构函数

```cpp
GrPromiseImageTexture::~GrPromiseImageTexture() {}
```

默认析构函数,无特殊清理逻辑。`GrBackendTexture` 的析构由其自身管理。

### 访问器

虽然在提供的源文件中未显示,但头文件中应该提供:

```cpp
const GrBackendTexture& backendTexture() const;
```

用于获取包装的后端纹理。

## 内部实现细节

### 简单包装设计

该类极其简单,仅执行以下操作:
1. 验证输入纹理的有效性
2. 存储纹理引用的拷贝

### 无所有权管理

`GrPromiseImageTexture` 不拥有底层 GPU 资源:
- `GrBackendTexture` 本身是一个描述符,不持有 GPU 资源
- 实际的 GPU 资源生命周期由客户端(Chrome)管理
- Promise 回调确保纹理在使用期间有效

### 跨 API 兼容性

通过 `GrBackendTexture` 支持多个图形 API:
- OpenGL/OpenGL ES
- Vulkan
- Metal
- Direct3D
- Dawn

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| GrBackendTexture | 包装的后端纹理描述符 |
| SkAssert | 断言验证 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| Chrome Promise Image API | 通过 Promise 回调提供 GrPromiseImageTexture |
| GrProxyProvider | 使用 Promise 纹理创建代理 |
| SkImage 相关代码 | 创建基于 Promise 的图像 |

## 设计模式与设计决策

### 包装器模式(Wrapper Pattern)

简单包装 `GrBackendTexture`,提供类型安全和语义清晰的接口。

### 值语义

虽然类本身通过指针传递(通常在 `sk_sp` 中),但它包装的 `GrBackendTexture` 使用值语义,便于拷贝和传递。

### 最小化设计

类设计极简:
- 无虚函数(无虚表开销)
- 无复杂状态管理
- 仅作为数据容器

### Chrome 特定接口

放置在 `include/private/chromium/` 下,明确标识为 Chrome 特定功能,不是通用 Skia API 的一部分。

### 断言验证

使用断言而非异常或错误返回,符合 Skia 的错误处理风格,假设调用者提供正确输入。

## 性能考量

### 零开销抽象

该类仅是一个包装,编译器可以完全优化掉额外的抽象层。

### 避免不必要拷贝

`GrBackendTexture` 是轻量级的描述符(通常包含句柄和元数据),拷贝开销很小。

### 无虚函数调用

直接访问成员变量,无虚函数查找开销。

### 内联友好

简单的构造函数可以内联,减少函数调用开销。

## Promise Image 使用场景

### Chrome GPU 进程架构

在 Chrome 中,渲染进程和 GPU 进程分离:
1. 渲染进程记录绘制命令(DDL)
2. 纹理数据在 GPU 进程中
3. 使用 Promise Image 机制桥接两个进程
4. Promise 回调在 GPU 进程执行时提供纹理

### 跨线程纹理共享

允许在一个线程创建纹理,在另一个线程使用:
1. 线程 A:创建 Promise Image,记录绘制
2. 线程 B:实例化 Promise,提供纹理
3. 线程 B:执行绘制

### 延迟纹理加载

支持异步纹理加载:
1. 创建 Promise Image 占位符
2. 开始异步加载纹理数据
3. 加载完成后,Promise 回调提供纹理
4. 延迟的绘制操作使用实际纹理

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| include/private/chromium/GrPromiseImageTexture.h | 头文件 | 类定义和公共接口 |
| include/gpu/ganesh/GrBackendSurface.h | 依赖 | 后端纹理定义 |
| src/gpu/ganesh/GrProxyProvider.h/cpp | 使用者 | 创建 Promise 纹理代理 |
| src/image/SkImage_GaneshYUVAPromise.cpp | 使用者 | Promise YUVA 图像 |
| include/gpu/ganesh/GrContextThreadSafeProxy.h | 相关 | 线程安全上下文代理 |

## 总结

`GrPromiseImageTexture` 是一个极简的包装类,专门为 Chrome 的 Promise Image 功能设计。它的简洁性是有意为之,因为:

1. **单一职责**:仅负责包装后端纹理
2. **Chrome 特定**:不是通用 Skia 功能
3. **性能优先**:零开销的薄包装层
4. **清晰语义**:类型系统明确表示这是一个 Promise 纹理

尽管代码量很少(仅 15 行),但它在 Chrome 的 GPU 架构中扮演着重要角色,实现了跨进程和跨线程的高效纹理共享机制。
