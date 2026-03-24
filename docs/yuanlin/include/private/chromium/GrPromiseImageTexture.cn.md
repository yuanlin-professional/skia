# GrPromiseImageTexture

> 源文件: `include/private/chromium/GrPromiseImageTexture.h`

## 概述

GrPromiseImageTexture 是 Ganesh 渲染引擎中用于实现 Promise Image 机制的纹理包装类。它封装了 GrBackendTexture，并通过引用计数管理纹理的生命周期，确保在 PromiseImageTextureFulfillProc 返回实例后，底层纹理在对应的 ReleaseProc 调用前保持有效。

## 架构位置

本类位于 Skia 的 Ganesh GPU 后端子系统，专为 Chromium 的 Promise Image 系统设计。Promise Image 允许应用在纹理实际可用之前创建 SkImage，延迟实际纹理的填充（fulfill）直到渲染时刻，是跨进程纹理共享的关键机制。

## 主要类与结构体

### GrPromiseImageTexture

Promise Image 纹理包装类，继承自 SkNVRefCnt，提供非虚拟引用计数。

**继承关系**: SkNVRefCnt&lt;GrPromiseImageTexture&gt; → GrPromiseImageTexture

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fBackendTexture | GrBackendTexture | 后端纹理对象 |

## 公共 API 函数

### `Make()`

```cpp
static sk_sp<GrPromiseImageTexture> Make(const GrBackendTexture& backendTexture)
```

- **功能**: 创建 GrPromiseImageTexture 实例的工厂方法
- **参数**: `backendTexture` - 后端纹理对象（OpenGL、Vulkan、Metal 等）
- **返回值**:
  - 如果 `backendTexture` 有效，返回智能指针
  - 如果无效，返回 nullptr
- **用途**: 将外部创建的后端纹理包装为 Promise Image 纹理

### `backendTexture()`

```cpp
GrBackendTexture backendTexture() const
```

- **功能**: 获取底层的后端纹理对象
- **返回值**: GrBackendTexture 对象（按值返回）
- **用途**: 访问实际的纹理资源

### 析构函数

```cpp
~GrPromiseImageTexture()
```

- **功能**: 销毁 Promise Image 纹理对象
- **注意**: 析构时不会自动销毁 `fBackendTexture`，纹理的生命周期由外部管理

### 禁用的操作

```cpp
GrPromiseImageTexture() = delete;
GrPromiseImageTexture(const GrPromiseImageTexture&) = delete;
GrPromiseImageTexture(GrPromiseImageTexture&&) = delete;
GrPromiseImageTexture& operator=(const GrPromiseImageTexture&) = delete;
GrPromiseImageTexture& operator=(GrPromiseImageTexture&&) = delete;
```

- **功能**: 禁用默认构造、拷贝和移动操作
- **原因**: 强制使用工厂方法 `Make()`，确保对象正确初始化

## 内部实现细节

### 私有构造函数

```cpp
explicit GrPromiseImageTexture(const GrBackendTexture& backendTexture)
```

实际构造函数是私有的，只能通过 `Make()` 工厂方法调用，这种设计：
- 允许在构造前验证输入
- 支持构造失败时返回 nullptr
- 隐藏实现细节

### 非虚拟引用计数

继承自 `SkNVRefCnt`（Non-Virtual RefCnt），而非 `SkRefCnt`，这意味着：
- 析构函数不是虚函数
- 减少了虚函数表的开销
- 不能通过基类指针正确地多态销毁（但这不是问题，因为没有派生类）

### 纹理所有权语义

GrPromiseImageTexture 不拥有 `fBackendTexture`，它只是一个观察者：
- 创建时接受外部纹理
- 析构时不销毁纹理
- 纹理的实际生命周期由 fulfill/release 回调管理

### 简单的数据结构

整个类只包含一个成员变量 `fBackendTexture`，非常轻量级，适合频繁创建和传递。

## Promise Image 系统上下文

### Fulfill 回调

当 Skia 需要纹理时，调用用户提供的 `PromiseImageTextureFulfillProc`：

```cpp
typedef sk_sp<GrPromiseImageTexture> (*PromiseImageTextureFulfillProc)(void* context);
```

回调返回 `GrPromiseImageTexture` 实例，表明纹理已准备好。

### Release 回调

当 Skia 完成纹理使用后，调用 `PromiseImageTextureReleaseProc`：

```cpp
typedef void (*PromiseImageTextureReleaseProc)(void* context);
```

此时应用可以安全地销毁或重用底层纹理。

### 生命周期约束

从 fulfill 回调返回到 release 回调之间，`GrBackendTexture` 必须保持有效，这通过引用计数保证：
- Skia 持有 `sk_sp<GrPromiseImageTexture>`
- 引用计数确保对象在使用期间不被销毁
- 应用需要确保底层纹理资源的有效性

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| SkRefCnt | 引用计数基类 |
| SkNVRefCnt | 非虚拟引用计数基类 |
| GrBackendSurface | 后端纹理抽象 |
| SkTypes | 基本类型定义 |

### 被依赖的模块

- Promise Image 创建 API（如 `SkImage::MakePromiseTexture`）
- Chromium 的跨进程纹理共享机制
- GPU 后端的纹理导入路径

## 设计模式与设计决策

### 工厂模式

使用静态 `Make()` 方法代替公共构造函数，优点：
- 构造前验证输入
- 支持返回 nullptr 表示失败
- 保持接口简洁

### RAII 部分应用

虽然使用智能指针管理对象生命周期，但不管理底层纹理资源，这是一种"轻量级 RAII"：
- 管理包装对象的生命周期
- 不管理被包装资源的生命周期
- 避免了所有权的复杂性

### 不可变对象

对象创建后无法修改（除了通过引用计数），所有操作都是 const，这带来：
- 线程安全的读取
- 简化了并发控制
- 避免了状态不一致

### 轻量级包装

整个类只是 `GrBackendTexture` 的薄包装，没有额外的逻辑或状态，保持了高性能。

## 性能考量

### 零开销抽象

除了引用计数，GrPromiseImageTexture 几乎没有额外开销：
- 成员变量只有一个 `fBackendTexture`
- 无虚函数调用
- `backendTexture()` 返回副本，但 GrBackendTexture 通常只包含句柄

### 智能指针传递

使用 `sk_sp` 传递，支持高效的移动语义，避免不必要的引用计数修改。

### 延迟纹理创建

Promise Image 机制允许推迟纹理创建直到实际需要，减少了：
- 内存占用
- 纹理创建开销
- GPU 资源锁定时间

### 跨进程效率

在 Chromium 中，纹理可以在一个进程创建，通过句柄传递到另一个进程，GrPromiseImageTexture 包装了这些句柄，避免了纹理数据的跨进程拷贝。

## 平台相关说明

### 跨后端支持

GrBackendTexture 支持多种 GPU 后端：
- OpenGL/GLES: 纹理 ID
- Vulkan: VkImage 和相关信息
- Metal: MTLTexture
- Dawn/WebGPU: WGPUTexture

GrPromiseImageTexture 对这些差异透明，提供统一接口。

### Chromium 集成

专为 Chromium 设计，但可在其他需要跨线程或跨进程纹理共享的环境中使用。

## 使用示例

```cpp
// 创建后端纹理（例如 OpenGL）
GrBackendTexture backendTex(width, height, GrMipMapped::kNo, glInfo);

// 包装为 Promise Image 纹理
sk_sp<GrPromiseImageTexture> promiseTex = GrPromiseImageTexture::Make(backendTex);

if (promiseTex) {
    // 在 fulfill 回调中返回
    return promiseTex;
}

// 失败处理
return nullptr;
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/gpu/ganesh/GrBackendSurface.h` | 后端纹理定义 |
| `include/core/SkImage.h` | Promise Image API |
| `include/core/SkRefCnt.h` | 引用计数基类 |
| `src/image/SkImage_GpuBase.h` | GPU Image 实现 |
| `src/gpu/ganesh/GrPromiseImageHelper.h` | Promise Image 辅助工具 |
