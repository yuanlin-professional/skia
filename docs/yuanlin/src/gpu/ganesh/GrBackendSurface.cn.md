# GrBackendSurface

> 源文件
> - include/gpu/ganesh/GrBackendSurface.h
> - src/gpu/ganesh/GrBackendSurface.cpp

## 概述

`GrBackendSurface` 是 Ganesh GPU 后端的表面封装系统,包含三个核心类:`GrBackendFormat`、`GrBackendTexture` 和 `GrBackendRenderTarget`。这些类封装了底层图形 API(OpenGL、Vulkan、Metal、Direct3D)的表面对象,提供跨平台的统一接口,用于在 Skia 和客户端代码之间传递 GPU 资源。

该系统使用类型擦除技术(`SkAnySubclass`)隐藏后端特定的实现细节,同时保持类型安全和高性能。这些类是 Skia 与外部 GPU 资源互操作的关键抽象。

## 架构位置

`GrBackendSurface` 位于 Ganesh GPU 后端的资源抽象层:

```
skia/
  include/gpu/ganesh/
    GrBackendSurface.h            # 公共接口
    GrTypes.h                     # 类型定义
  src/gpu/ganesh/
    GrBackendSurface.cpp          # 实现
    GrBackendSurfacePriv.h        # 内部接口
    vk/GrVkBackendSurface.h       # Vulkan 特定实现
    gl/GrGLBackendSurface.h       # OpenGL 特定实现
    mtl/GrMtlBackendSurface.h     # Metal 特定实现
```

这些类被 `SkSurface`、`SkImage` 和 `GrDirectContext` 使用,是 GPU 资源的主要传递媒介。

## 主要类与结构体

### GrBackendFormat

后端格式封装类,描述纹理/渲染目标的像素格式。

**继承关系:**
- 基类: 无
- 派生类: 无(使用组合模式封装后端数据)

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fFormatData` | `AnyFormatData` | 后端特定格式数据(80 字节) |
| `fBackend` | `GrBackendApi` | GPU 后端类型 |
| `fTextureType` | `GrTextureType` | 纹理类型(2D/Rect/External) |
| `fValid` | `bool` | 格式是否有效 |

**关键方法:**

| 方法名 | 返回类型 | 说明 |
|--------|----------|------|
| `backend()` | `GrBackendApi` | 获取后端类型 |
| `textureType()` | `GrTextureType` | 获取纹理类型 |
| `channelMask()` | `uint32_t` | 获取通道掩码 |
| `desc()` | `GrColorFormatDesc` | 获取格式描述 |
| `makeTexture2D()` | `GrBackendFormat` | 转换为 2D 纹理格式 |
| `isValid()` | `bool` | 检查格式是否有效 |

### GrBackendTexture

后端纹理封装类,代表 GPU 纹理资源。

**继承关系:**
- 基类: 无
- 派生类: 无

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fTextureData` | `AnyTextureData` | 后端特定纹理数据(176 字节) |
| `fIsValid` | `bool` | 纹理是否有效 |
| `fWidth` | `int` | 宽度(像素) |
| `fHeight` | `int` | 高度(像素) |
| `fLabel` | `const std::string` | 调试标签 |
| `fMipmapped` | `skgpu::Mipmapped` | 是否有 mipmap |
| `fBackend` | `GrBackendApi` | GPU 后端类型 |
| `fTextureType` | `GrTextureType` | 纹理类型 |

**关键方法:**

| 方法名 | 返回类型 | 说明 |
|--------|----------|------|
| `dimensions()` | `SkISize` | 获取尺寸 |
| `width()`/`height()` | `int` | 获取宽度/高度 |
| `getLabel()` | `std::string_view` | 获取标签 |
| `mipmapped()` | `skgpu::Mipmapped` | 是否有 mipmap |
| `backend()` | `GrBackendApi` | 获取后端类型 |
| `textureType()` | `GrTextureType` | 获取纹理类型 |
| `getBackendFormat()` | `GrBackendFormat` | 获取格式 |
| `setMutableState()` | `void` | 设置可变状态 |
| `isProtected()` | `bool` | 是否受保护 |
| `isValid()` | `bool` | 是否有效 |
| `isSameTexture()` | `bool` | 比较是否同一纹理 |

### GrBackendRenderTarget

后端渲染目标封装类,代表 GPU 渲染表面。

**继承关系:**
- 基类: 无
- 派生类: 无

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fRTData` | `AnyRenderTargetData` | 后端特定渲染目标数据(176 字节) |
| `fIsValid` | `bool` | 渲染目标是否有效 |
| `fFramebufferOnly` | `bool` | 是否仅为帧缓冲 |
| `fWidth` | `int` | 宽度(像素) |
| `fHeight` | `int` | 高度(像素) |
| `fSampleCnt` | `int` | MSAA 采样数 |
| `fStencilBits` | `int` | 模板位数 |
| `fBackend` | `GrBackendApi` | GPU 后端类型 |

**关键方法:**

| 方法名 | 返回类型 | 说明 |
|--------|----------|------|
| `dimensions()` | `SkISize` | 获取尺寸 |
| `width()`/`height()` | `int` | 获取宽度/高度 |
| `sampleCnt()` | `int` | 获取采样数 |
| `stencilBits()` | `int` | 获取模板位数 |
| `backend()` | `GrBackendApi` | 获取后端类型 |
| `isFramebufferOnly()` | `bool` | 是否仅为帧缓冲 |
| `getBackendFormat()` | `GrBackendFormat` | 获取格式 |
| `setMutableState()` | `void` | 设置可变状态 |
| `isProtected()` | `bool` | 是否受保护 |
| `isValid()` | `bool` | 是否有效 |

### 后端数据基类

```cpp
class GrBackendFormatData;
class GrBackendTextureData;
class GrBackendRenderTargetData;
```

这些抽象基类由后端特定实现继承,提供以下方法:

- `copyTo()` - 复制数据到另一个对象
- `equal()` - 比较两个数据对象
- 虚析构函数

## 公共 API 函数

### GrBackendFormat API

#### 构造与复制

```cpp
GrBackendFormat();
```
**功能:** 创建无效的格式对象

```cpp
GrBackendFormat(const GrBackendFormat& that);
GrBackendFormat& operator=(const GrBackendFormat& that);
```
**功能:** 拷贝构造和赋值

#### 操作符

```cpp
bool operator==(const GrBackendFormat& that) const;
bool operator!=(const GrBackendFormat& that) const;
```
**功能:** 比较格式是否相同
**注意:** 无效格式与任何格式都不相等

#### 查询方法

```cpp
uint32_t channelMask() const;
```
**功能:** 获取通道掩码(RGBA 标志位)
**返回:** `SkColorChannelFlag` 的位掩码

```cpp
GrColorFormatDesc desc() const;
```
**功能:** 获取格式描述(位深、编码等)

```cpp
GrBackendFormat makeTexture2D() const;
```
**功能:** 转换为 2D 纹理格式
**特点:** Vulkan 后端会移除 YCbCr 转换信息

#### 调试方法

```cpp
#if defined(SK_DEBUG) || defined(GPU_TEST_UTILS)
SkString toStr() const;
#endif
```
**功能:** 转换为调试字符串

### GrBackendTexture API

#### 构造与复制

```cpp
GrBackendTexture();
```
**功能:** 创建无效的纹理对象

```cpp
GrBackendTexture(const GrBackendTexture& that);
GrBackendTexture& operator=(const GrBackendTexture& that);
```
**功能:** 拷贝构造和赋值
**注意:** 复制的是纹理句柄,非底层数据

#### 状态管理

```cpp
void setMutableState(const skgpu::MutableTextureState& state);
```
**功能:** 设置可变状态(如 Vulkan 布局)
**参数:** `state` - 新的纹理状态
**场景:** 外部修改纹理布局后通知 Skia

#### 查询方法

```cpp
GrBackendFormat getBackendFormat() const;
```
**功能:** 获取纹理格式

```cpp
bool isProtected() const;
```
**功能:** 检查是否为受保护内容(DRM)

```cpp
bool isSameTexture(const GrBackendTexture& that);
```
**功能:** 比较是否指向同一底层纹理
**用途:** 去重和缓存查找

#### 测试方法

```cpp
#if defined(GPU_TEST_UTILS)
static bool TestingOnly_Equals(const GrBackendTexture& t0, const GrBackendTexture& t1);
#endif
```
**功能:** 深度比较两个纹理(测试用)

### GrBackendRenderTarget API

API 与 `GrBackendTexture` 类似,主要区别:

- 增加 `sampleCnt()` 和 `stencilBits()` 查询
- 增加 `isFramebufferOnly()` 检查
- 无 `isSameTexture()` 方法

## 内部实现细节

### 类型擦除存储

所有后端数据使用 `SkAnySubclass` 存储:

```cpp
// GrBackendFormat
inline constexpr static size_t kMaxSubclassSize = 80;
using AnyFormatData = SkAnySubclass<GrBackendFormatData, kMaxSubclassSize>;

// GrBackendTexture
inline constexpr static size_t kMaxSubclassSize = 176;
using AnyTextureData = SkAnySubclass<GrBackendTextureData, kMaxSubclassSize>;

// GrBackendRenderTarget
inline constexpr static size_t kMaxSubclassSize = 176;
using AnyRenderTargetData = SkAnySubclass<GrBackendRenderTargetData, kMaxSubclassSize>;
```

**优势:**
- 避免堆分配,提高性能
- 编译期大小检查
- 隐藏后端类型

### 拷贝实现

拷贝构造和赋值通过 `copyTo()` 方法实现:

```cpp
GrBackendFormat& GrBackendFormat::operator=(const GrBackendFormat& that) {
    if (this != &that) {
        this->~GrBackendFormat();
        new (this) GrBackendFormat(that);
    }
    return *this;
}

GrBackendFormat::GrBackendFormat(const GrBackendFormat& that)
        : fBackend(that.fBackend), fTextureType(that.fTextureType), fValid(that.fValid) {
    if (!fValid) {
        return;
    }
    fFormatData.reset();
    that.fFormatData->copyTo(fFormatData);
}
```

**特点:**
- 使用 placement new 实现赋值
- 调用虚函数 `copyTo()` 复制后端数据
- 无效对象跳过复制

### 格式比较

格式相等需要满足:

1. 两个格式都有效
2. 后端类型相同
3. 后端数据相等(调用虚函数 `equal()`)

```cpp
bool GrBackendFormat::operator==(const GrBackendFormat& that) const {
    if (!fValid || !that.fValid) {
        return false;
    }
    if (fBackend != that.fBackend) {
        return false;
    }
    return fFormatData->equal(that.fFormatData.get());
}
```

### 纹理状态管理

纹理和渲染目标支持可变状态(Vulkan 布局、队列家族):

```cpp
void GrBackendTexture::setMutableState(const skgpu::MutableTextureState& state) {
    fTextureData->setMutableState(state);
}

sk_sp<skgpu::MutableTextureState> GrBackendTexture::getMutableState() const {
    return fTextureData->getMutableState();
}
```

这允许 Skia 和客户端同步纹理状态变化。

### makeTexture2D 实现

转换为 2D 纹理格式:

```cpp
GrBackendFormat GrBackendFormat::makeTexture2D() const {
    GrBackendFormat copy = *this;
    copy.fFormatData->makeTexture2D();  // Vulkan: 移除 YCbCr 转换
    copy.fTextureType = GrTextureType::k2D;
    return copy;
}
```

主要用于 Vulkan,将外部纹理格式转换为普通 2D 纹理。

### 私有模板构造函数

```cpp
template <typename FormatData>
GrBackendFormat(GrTextureType textureType, GrBackendApi api, const FormatData& formatData);
```

**特点:**
- 仅供友元类和工厂函数调用
- 使用 `SkAnySubclass::emplace` 就地构造
- 确保类型安全

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkRefCnt.h` | 智能指针支持 |
| `include/core/SkSize.h` | 尺寸类型 |
| `include/gpu/GpuTypes.h` | GPU 类型定义 |
| `include/gpu/MutableTextureState.h` | 可变状态封装 |
| `include/private/base/SkAnySubclass.h` | 类型擦除容器 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | 内部类型 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| `GrDirectContext` | 创建和更新后端纹理 |
| `SkSurface` | 包装后端表面为 Skia 表面 |
| `SkImage` | 从后端纹理创建图像 |
| `GrContextThreadSafeProxy` | 查询格式能力 |
| 互操作 API | 与外部 GPU 代码交换纹理 |

## 设计模式与设计决策

### 设计模式

1. **桥接模式 (Bridge Pattern)**
   - 公共类是抽象接口
   - 后端数据类是实现接口
   - 后端特定类是具体实现

2. **类型擦除 (Type Erasure)**
   - 使用 `SkAnySubclass` 隐藏后端类型
   - 避免模板导致的代码膨胀
   - 保持 ABI 稳定性

3. **值语义 (Value Semantics)**
   - 支持拷贝构造和赋值
   - 复制的是句柄,非底层资源
   - 适合在容器中存储

### 设计决策

1. **内联存储**
   - 格式 80 字节,纹理/渲染目标 176 字节
   - 避免堆分配,提高性能
   - 大小经过实际测量确定

2. **无效对象模式**
   - 默认构造函数创建无效对象
   - 避免使用可选类型(optional)
   - 简化 API 设计

3. **不可变标签**
   - 纹理标签(`fLabel`)使用 `const std::string`
   - 创建后不可修改
   - 帮助调试和性能分析

4. **可变状态分离**
   - 纹理尺寸、格式等不可变
   - 布局、队列家族等可变
   - 使用 `MutableTextureState` 封装可变部分

5. **比较语义**
   - `isSameTexture()` 比较底层句柄
   - `TestingOnly_Equals()` 深度比较所有字段
   - 不同用途的比较操作分离

## 性能考量

1. **内联存储**
   - 栈上分配,避免堆分配开销
   - 拷贝仅复制 80/176 字节
   - 适合频繁创建和销毁

2. **虚函数最小化**
   - 仅后端数据类使用虚函数
   - 公共类不使用虚函数表
   - 减少间接调用开销

3. **拷贝优化**
   - 拷贝的是句柄,非像素数据
   - 轻量级操作,适合按值传递
   - 避免引用计数开销

4. **格式查询缓存**
   - `channelMask()` 和 `desc()` 可能被频繁调用
   - 后端实现应考虑缓存结果

5. **类型擦除开销**
   - `SkAnySubclass` 避免虚函数表
   - 编译器可以内联 `copyTo()` 和 `equal()` 调用
   - 接近零开销抽象

## 相关文件

| 文件路径 | 说明 |
|----------|------|
| `include/gpu/ganesh/GrBackendSurface.h` | 公共接口 |
| `src/gpu/ganesh/GrBackendSurface.cpp` | 实现 |
| `src/gpu/ganesh/GrBackendSurfacePriv.h` | 内部接口和工厂方法 |
| `src/gpu/ganesh/vk/GrVkBackendSurface.h` | Vulkan 特定实现 |
| `src/gpu/ganesh/gl/GrGLBackendSurface.h` | OpenGL 特定实现 |
| `src/gpu/ganesh/mtl/GrMtlBackendSurface.h` | Metal 特定实现 |
| `include/gpu/MutableTextureState.h` | 可变状态封装 |
| `include/gpu/ganesh/GrDirectContext.h` | 使用后端表面的上下文 |
