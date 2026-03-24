# GrSurfaceCharacterization

> 源文件: `include/private/chromium/GrSurfaceCharacterization.h`

## 概述

GrSurfaceCharacterization 封装了 Ganesh 渲染引擎进行内部渲染决策所需的所有表面特性信息。该类是延迟显示列表（DDL）系统的核心组件，用于在记录绘制命令时提供完整的表面配置参数，确保命令可以在稍后安全地回放到真实表面上。

## 架构位置

本类位于 Skia 的 Ganesh GPU 后端子系统中，专为 Chromium 的 DDL（Deferred Display List）架构设计。它连接了 GrDeferredDisplayListRecorder（录制器）、GrDeferredDisplayList（显示列表）和 SkSurface（表面）之间的配置信息传递链。

## 主要类与结构体

### GrSurfaceCharacterization

表面特性描述类，包含了表面的所有关键属性信息。

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fContextInfo | sk_sp&lt;GrContextThreadSafeProxy&gt; | 上下文线程安全代理 |
| fCacheMaxResourceBytes | size_t | 缓存的最大资源字节数 |
| fImageInfo | SkImageInfo | 图像信息（尺寸、颜色类型等） |
| fBackendFormat | GrBackendFormat | 后端格式（OpenGL/Vulkan 等） |
| fOrigin | GrSurfaceOrigin | 表面原点（顶部或底部） |
| fSampleCnt | int | 多重采样数量 |
| fIsTextureable | Textureable | 是否可用作纹理 |
| fIsMipmapped | skgpu::Mipmapped | 是否启用 Mipmap |
| fUsesGLFBO0 | UsesGLFBO0 | 是否使用 OpenGL 的 FBO0 |
| fVkRTSupportsInputAttachment | VkRTSupportsInputAttachment | Vulkan 渲染目标是否支持输入附件 |
| fVulkanSecondaryCBCompatible | VulkanSecondaryCBCompatible | 是否兼容 Vulkan 二级命令缓冲区 |
| fIsProtected | skgpu::Protected | 是否为受保护内存 |
| fSurfaceProps | SkSurfaceProps | 表面属性 |

### 枚举类型

**Textureable**
- `kNo`: 不可用作纹理
- `kYes`: 可用作纹理

**UsesGLFBO0**
- `kNo`: 不使用默认帧缓冲区
- `kYes`: 使用 OpenGL 的默认帧缓冲区（FBO0）

**VkRTSupportsInputAttachment**
- `kNo`: Vulkan 渲染目标不支持输入附件
- `kYes`: 支持输入附件，允许高级混合在着色器中直接读取目标值

**VulkanSecondaryCBCompatible**
- `kNo`: 不兼容 Vulkan 二级命令缓冲区
- `kYes`: 兼容二级命令缓冲区模式

## 公共 API 函数

### 构造函数

```cpp
GrSurfaceCharacterization()
```

- **功能**: 创建一个无效的默认特性对象
- **初始状态**: 所有成员设置为默认值，`isValid()` 返回 false

### `createResized()`

```cpp
GrSurfaceCharacterization createResized(int width, int height) const
```

- **功能**: 创建一个新的特性对象，仅改变宽度和高度
- **参数**:
  - `width`: 新的宽度
  - `height`: 新的高度
- **返回值**: 新的特性对象，其他属性保持不变
- **用途**: 用于处理表面尺寸变化的场景

### `createColorSpace()`

```cpp
GrSurfaceCharacterization createColorSpace(sk_sp<SkColorSpace>) const
```

- **功能**: 创建一个新的特性对象，仅替换颜色空间
- **参数**: 新的颜色空间对象
- **返回值**: 具有新颜色空间的特性对象
- **用途**: 支持动态切换颜色空间

### `createBackendFormat()`

```cpp
GrSurfaceCharacterization createBackendFormat(SkColorType colorType,
                                              const GrBackendFormat& backendFormat) const
```

- **功能**: 创建一个新的特性对象，替换后端格式和颜色类型
- **参数**:
  - `colorType`: 新的颜色类型
  - `backendFormat`: 新的后端格式
- **返回值**: 具有新格式的特性对象
- **注意**: 必须同时提供颜色类型以正确解释新格式

### `createFBO0()`

```cpp
GrSurfaceCharacterization createFBO0(bool usesGLFBO0) const
```

- **功能**: 创建一个新的特性对象，仅改变 FBO0 使用标志
- **参数**: `usesGLFBO0` - 是否使用 OpenGL 的默认帧缓冲区
- **返回值**: 具有新 FBO0 设置的特性对象
- **平台**: 仅适用于 OpenGL 后端

### 查询方法

```cpp
bool isValid() const
```

- **功能**: 检查特性对象是否有效
- **返回值**: 颜色类型不为 `kUnknown_SkColorType` 时返回 true

```cpp
GrContextThreadSafeProxy* contextInfo() const
sk_sp<GrContextThreadSafeProxy> refContextInfo() const
```

- **功能**: 获取上下文信息（裸指针或智能指针）
- **返回值**: 上下文的线程安全代理

```cpp
size_t cacheMaxResourceBytes() const
```

- **功能**: 获取缓存的最大资源字节数
- **返回值**: 字节数

```cpp
const SkImageInfo& imageInfo() const
const GrBackendFormat& backendFormat() const
GrSurfaceOrigin origin() const
SkISize dimensions() const
int width() const
int height() const
SkColorType colorType() const
int sampleCount() const
```

- **功能**: 获取各种表面属性
- **返回值**: 对应的属性值

```cpp
bool isTextureable() const
bool isMipMapped() const
bool usesGLFBO0() const
bool vkRTSupportsInputAttachment() const
bool vulkanSecondaryCBCompatible() const
skgpu::Protected isProtected() const
```

- **功能**: 查询布尔类型的特性标志
- **返回值**: 对应的布尔值

```cpp
SkColorSpace* colorSpace() const
sk_sp<SkColorSpace> refColorSpace() const
const SkSurfaceProps& surfaceProps() const
```

- **功能**: 获取颜色空间和表面属性
- **返回值**: 对应的对象引用或指针

### 运算符重载

```cpp
bool operator==(const GrSurfaceCharacterization& other) const
bool operator!=(const GrSurfaceCharacterization& other) const
```

- **功能**: 比较两个特性对象是否相等
- **返回值**: 相等返回 true

## 内部实现细节

### 私有构造函数

完整的构造函数被声明为私有，只有友元类（如 SkSurface_Ganesh、GrVkSecondaryCBDrawContext 等）可以调用，确保特性对象只能通过正确的途径创建。

### Dynamic MSAA 限制

在构造函数和 `set()` 方法中，如果 `surfaceProps` 包含 `kDynamicMSAA_Flag` 标志，会将对象重置为无效状态，因为 DDL 当前不支持动态 MSAA。

```cpp
if (surfaceProps.flags() & SkSurfaceProps::kDynamicMSAA_Flag) {
    *this = {};  // 重置为无效状态
}
```

### set() 方法

提供了一个私有的 `set()` 方法，允许友元类批量设置所有属性，避免多次拷贝。

### 验证机制

在调试模式下，构造函数和 `set()` 方法会调用 `validate()` 进行一致性检查：

```cpp
SkDEBUGCODE(this->validate());
```

### 默认值设计

默认构造函数的初始化值：
- `fOrigin`: kBottomLeft_GrSurfaceOrigin（OpenGL 传统）
- `fSampleCnt`: 0（无多重采样）
- `fIsTextureable`: Textureable::kYes（默认可纹理化）
- `fIsMipmapped`: skgpu::Mipmapped::kYes（默认启用 Mipmap）

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| SkColorSpace | 颜色空间管理 |
| SkColorType | 颜色类型定义 |
| SkImageInfo | 图像信息封装 |
| SkRefCnt | 智能指针基类 |
| SkSize | 尺寸表示 |
| SkSurfaceProps | 表面属性 |
| GrBackendSurface | 后端表面抽象 |
| GrContextThreadSafeProxy | 线程安全上下文代理 |
| GrTypes | Ganesh 类型定义 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| GrDeferredDisplayListRecorder | 使用特性对象配置录制器 |
| GrDeferredDisplayList | 存储特性对象用于回放验证 |
| SkSurface_Ganesh | 创建和验证表面特性 |
| GrVkSecondaryCBDrawContext | Vulkan 二级命令缓冲区配置 |

## 设计模式与设计决策

### 值语义设计

GrSurfaceCharacterization 采用值语义，支持拷贝和移动，使得特性对象可以方便地传递和存储：

```cpp
GrSurfaceCharacterization(const GrSurfaceCharacterization&) = default;
GrSurfaceCharacterization(GrSurfaceCharacterization&&) = default;
```

### 不可变变体模式

提供了 `createResized()`, `createColorSpace()` 等方法创建新的变体，而不是修改现有对象，这种设计：
- 保证了线程安全
- 避免了意外修改
- 支持函数式编程风格

### 友元类控制

通过友元机制限制对象的创建和修改权限，确保特性对象只能从有效的表面或上下文中派生。

### 强类型枚举

使用 `enum class` 定义枚举类型（如 `Textureable::kYes`），提高了类型安全性，避免了隐式转换。

## 性能考量

### 轻量级拷贝

虽然包含多个成员，但大部分是基本类型或智能指针，拷贝开销较小，适合按值传递。

### 智能指针共享

`fContextInfo` 和颜色空间使用智能指针，避免了昂贵的深拷贝，多个特性对象可以共享同一上下文信息。

### 内联访问器

大部分查询方法在头文件中定义为内联函数，避免了函数调用开销。

### 延迟验证

验证逻辑只在调试模式下执行，不影响发布版本的性能。

## 平台相关说明

### OpenGL 特定

- `fUsesGLFBO0`: 指示是否绘制到窗口系统提供的默认帧缓冲区
- `createFBO0()`: 用于在 FBO 和 FBO0 之间切换

### Vulkan 特定

- `fVkRTSupportsInputAttachment`: 标记 VkImage 是否带有 `VK_IMAGE_USAGE_INPUT_ATTACHMENT_BIT`，用于优化高级混合
- `fVulkanSecondaryCBCompatible`: 指示是否包装原始 Vulkan 二级命令缓冲区

### 跨平台抽象

`GrBackendFormat` 提供了统一的后端格式抽象，隐藏了不同 API 的差异。

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/private/chromium/GrDeferredDisplayList.h` | DDL 存储特性对象 |
| `include/private/chromium/GrDeferredDisplayListRecorder.h` | 录制器接受特性对象 |
| `include/private/chromium/GrVkSecondaryCBDrawContext.h` | Vulkan 二级 CB 使用特性 |
| `include/core/SkSurface.h` | 表面创建特性对象 |
| `include/gpu/ganesh/GrBackendSurface.h` | 后端格式定义 |
| `include/gpu/ganesh/GrContextThreadSafeProxy.h` | 线程安全上下文代理 |
| `include/core/SkImageInfo.h` | 图像信息封装 |
