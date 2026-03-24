# GrSurfaceCharacterization

> 源文件: src/gpu/ganesh/GrSurfaceCharacterization.cpp

## 概述

`GrSurfaceCharacterization` 是 Ganesh GPU 后端中用于描述渲染表面特性的类，主要用于 Deferred Display List（DDL）场景。它封装了创建和验证 GPU surface 所需的所有关键属性，包括尺寸、格式、采样数、mipmap 状态等，使得可以在不实际创建 surface 的情况下验证兼容性和创建占位符。

该类是 Chromium 私有 API 的一部分（`include/private/chromium/GrSurfaceCharacterization.h`），主要用于跨线程渲染场景，允许在一个线程上记录渲染命令，在另一个线程上执行。它通过特征描述（characterization）实现了"契约式编程"，确保最终的 surface 满足预期的规格。

## 架构位置

`GrSurfaceCharacterization` 位于 Ganesh GPU 后端的高层抽象接口：

- **主要用户**: Chromium 的 viz compositor（合成器）
- **使用场景**: DDL（Deferred Display List）、跨线程渲染、预分配验证
- **依赖对象**: `GrContextThreadSafeProxy`（线程安全的 context 代理）
- **验证目标**: `GrSurface` 和 `GrSurfaceProxy`
- **相关类**: `SkDeferredDisplayList`、`SkDeferredDisplayListRecorder`

该类是实现延迟渲染和线程隔离的关键组件，使得渲染命令记录和执行可以完全分离。

## 主要类与结构体

### GrSurfaceCharacterization 类

该类没有显式的继承关系，是一个独立的值类型。

**关键成员变量（从头文件推断）:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fContextInfo` | `sk_sp<GrContextThreadSafeProxyPriv>` | 线程安全的 context 信息 |
| `fCacheMaxResourceBytes` | `size_t` | 资源缓存最大字节数 |
| `fImageInfo` | `SkImageInfo` | 图像信息（宽高、色彩类型、alpha 类型、色彩空间） |
| `fBackendFormat` | `GrBackendFormat` | GPU 后端格式 |
| `fOrigin` | `GrSurfaceOrigin` | Surface 原点位置 |
| `fSampleCnt` | `int` | 采样数（MSAA） |
| `fIsTextureable` | `Textureable` | 是否可作为纹理 |
| `fIsMipmapped` | `skgpu::Mipmapped` | 是否有 mipmap |
| `fUsesGLFBO0` | `UsesGLFBO0` | 是否使用 OpenGL FBO 0 |
| `fVkRTSupportsInputAttachment` | `VkRTSupportsInputAttachment` | Vulkan input attachment 支持 |
| `fVulkanSecondaryCBCompatible` | `VulkanSecondaryCBCompatible` | Vulkan 次级命令缓冲兼容性 |
| `fIsProtected` | `GrProtected` | 是否受保护内存 |
| `fSurfaceProps` | `SkSurfaceProps` | Surface 属性 |

### 嵌套枚举类型

- `Textureable`: 表示是否可作为纹理（`kYes` / `kNo`）
- `UsesGLFBO0`: 表示是否使用 OpenGL 的默认帧缓冲
- `VkRTSupportsInputAttachment`: Vulkan 特定的 input attachment 支持
- `VulkanSecondaryCBCompatible`: Vulkan 次级命令缓冲兼容性

## 公共 API 函数

### 验证方法

```cpp
void validate() const  // DEBUG 模式下验证特征的一致性和有效性
```

验证逻辑包括：
- 颜色类型和后端格式兼容性
- 采样数的可渲染性
- Mipmap 和 Textureable 的依赖关系
- 后端特定标志的一致性（GL、Vulkan）

### 比较方法

```cpp
bool operator==(const GrSurfaceCharacterization& other) const
```

比较所有关键属性：
- Context 信息
- 缓存大小
- Origin
- ImageInfo（包含尺寸、色彩类型等）
- 后端格式
- 采样数
- 各种标志
- Surface 属性

### 变体创建方法

#### createResized
```cpp
GrSurfaceCharacterization createResized(int width, int height) const
```

创建不同尺寸的特征描述：
- 验证新尺寸是否在 GPU 限制内
- 保持其他所有属性不变
- 返回新的特征对象（如果失败返回无效对象）

#### createColorSpace
```cpp
GrSurfaceCharacterization createColorSpace(sk_sp<SkColorSpace> cs) const
```

创建不同色彩空间的特征描述：
- 只修改色彩空间
- 保持其他所有属性不变

#### createBackendFormat
```cpp
GrSurfaceCharacterization createBackendFormat(SkColorType colorType,
                                              const GrBackendFormat& backendFormat) const
```

创建不同后端格式和色彩类型的特征描述：
- 同时修改色彩类型和后端格式
- 需要确保两者兼容

#### createFBO0
```cpp
GrSurfaceCharacterization createFBO0(bool usesGLFBO0) const
```

创建 FBO0 特征描述：
- 只适用于 OpenGL 后端
- 不能与 Textureable、Vulkan 标志同时使用
- 用于渲染到默认帧缓冲

### 查询方法

```cpp
bool isValid() const  // 检查特征是否有效
SkColorType colorType() const  // 从 ImageInfo 获取色彩类型
// ... 其他属性访问器
```

## 内部实现细节

### 验证逻辑（validate 方法）

在 DEBUG 模式下执行的完整性检查：

1. **可渲染性验证**:
```cpp
GrColorType grCT = SkColorTypeToGrColorType(this->colorType());
SkASSERT(fSampleCnt && caps->isFormatAsColorTypeRenderable(grCT, fBackendFormat, fSampleCnt));
```

2. **格式兼容性**:
```cpp
SkASSERT(caps->areColorTypeAndFormatCompatible(grCT, fBackendFormat));
```

3. **Mipmap 和 Textureable 依赖**:
```cpp
SkASSERT(skgpu::Mipmapped::kNo == fIsMipmapped || Textureable::kYes == fIsTextureable);
```
Mipmap 只对纹理有意义。

4. **Textureable 和 FBO0 互斥**:
```cpp
SkASSERT(Textureable::kNo == fIsTextureable || UsesGLFBO0::kNo == fUsesGLFBO0);
```
FBO0（默认帧缓冲）不能作为纹理。

5. **后端特定标志验证**:
- `UsesGLFBO0` 只能用于 OpenGL
- Vulkan 特定标志只能用于 Vulkan
- Vulkan 次级命令缓冲与 input attachment 互斥
- Textureable 与 Vulkan 次级命令缓冲互斥

### 相等性比较实现

```cpp
bool operator==(const GrSurfaceCharacterization& other) const {
    if (!this->isValid() || !other.isValid()) {
        return false;  // 无效对象不相等
    }
    if (fContextInfo != other.fContextInfo) {
        return false;  // Context 必须相同
    }
    return /* 逐个比较所有成员 */;
}
```

使用"短路"优化，Context 不同时立即返回。

### createResized 实现

```cpp
GrSurfaceCharacterization createResized(int width, int height) const {
    const GrCaps* caps = fContextInfo->priv().caps();
    if (!caps) {
        return GrSurfaceCharacterization();  // 无效
    }
    if (width <= 0 || height <= 0 ||
        width > caps->maxRenderTargetSize() ||
        height > caps->maxRenderTargetSize()) {
        return GrSurfaceCharacterization();  // 超出限制
    }
    return GrSurfaceCharacterization(/* 复制所有参数，只修改尺寸 */);
}
```

关键点：
- 验证尺寸合法性
- 使用 `caps->maxRenderTargetSize()` 检查 GPU 限制
- 通过 `fImageInfo.makeWH(width, height)` 创建新的 ImageInfo

### createColorSpace 实现

```cpp
return GrSurfaceCharacterization(
    fContextInfo,
    fCacheMaxResourceBytes,
    fImageInfo.makeColorSpace(std::move(cs)),  // 只修改色彩空间
    fBackendFormat,
    /* ... 其他参数保持不变 ... */
);
```

使用 `SkImageInfo::makeColorSpace()` 创建新的 ImageInfo。

### createBackendFormat 实现

```cpp
SkImageInfo newII = fImageInfo.makeColorType(colorType);
return GrSurfaceCharacterization(
    /* ... */,
    newII,
    backendFormat,  // 新的后端格式
    /* ... */
);
```

同时修改色彩类型和后端格式，确保两者匹配。

### createFBO0 实现

```cpp
if (fIsTextureable == Textureable::kYes ||
    fVkRTSupportsInputAttachment == VkRTSupportsInputAttachment::kYes ||
    fVulkanSecondaryCBCompatible == VulkanSecondaryCBCompatible::kYes) {
    return GrSurfaceCharacterization();  // 不兼容的配置
}
```

严格检查互斥条件，避免创建无效的 FBO0 特征。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `GrContextThreadSafeProxy` | 线程安全的 context 访问 |
| `GrCaps` | 查询 GPU 能力和限制 |
| `GrBackendFormat` | 后端格式描述 |
| `SkImageInfo` | 图像信息（尺寸、色彩） |
| `SkColorSpace` | 色彩空间管理 |
| `GrTypesPriv` | 内部类型定义 |

### 被依赖的模块

| 模块 | 使用场景 |
|-----|---------|
| `SkDeferredDisplayListRecorder` | 创建 DDL 时提供特征描述 |
| `SkDeferredDisplayList` | 验证执行环境 |
| `SkSurface` | 从现有 surface 提取特征 |
| Chromium viz compositor | 跨线程渲染协调 |

## 设计模式与设计决策

### 值语义设计

`GrSurfaceCharacterization` 采用值语义：
- 可拷贝和移动
- 不使用指针或引用成员（除了 `sk_sp`）
- 适合跨线程传递

**优势:**
- 线程安全（拷贝后独立）
- 易于存储和传输
- 无生命周期管理问题

### 不可变性（Immutability）

特征创建后不可修改，只能通过 `create*()` 方法创建新对象：
- **优势**: 线程安全、易于推理、防止意外修改
- **实现**: 没有 setter 方法，只有创建新对象的工厂方法

### 契约式验证

通过 `validate()` 和 `operator==` 实现契约验证：
- **记录端**: 使用特征描述录制命令
- **执行端**: 验证实际 surface 是否匹配特征
- **保证**: 录制的命令在执行端有效

### 后端无关设计

虽然包含后端特定标志（GL、Vulkan），但设计是后端中立的：
- 使用 `GrBackendFormat` 抽象后端格式
- 后端特定标志只在相应后端有效
- 验证逻辑检查后端一致性

### 懒验证策略

`validate()` 只在 DEBUG 模式下执行：
- **开发阶段**: 捕获配置错误
- **发布版本**: 无性能开销
- **信任机制**: 假设外部输入已验证

### 工厂方法模式

所有变体创建都使用工厂方法（`create*`）：
- 封装复杂的构造逻辑
- 验证参数有效性
- 返回有效或无效对象（无异常）

## 性能考量

### 轻量级对象

特征对象相对轻量：
- 主要是值类型成员
- 只有一个智能指针（`fContextInfo`）
- 适合按值传递和存储

### 引用计数共享

`fContextInfo` 使用 `sk_sp` 智能指针：
- 多个特征对象可以共享同一个 context 信息
- 避免重复创建 context 代理
- 线程安全的引用计数

### 验证成本

`validate()` 只在 DEBUG 模式下运行：
- 发布版本无开销
- 开发时提供完整性检查
- 使用断言而非异常（零开销）

### 比较优化

`operator==` 使用短路优化：
```cpp
if (fContextInfo != other.fContextInfo) {
    return false;  // 立即返回
}
```
最常见的不匹配情况（不同 context）快速返回。

### 创建方法效率

`create*()` 方法：
- 最小化验证成本（只检查必要条件）
- 返回值优化（RVO）
- 失败时返回无效对象而非抛异常

### 内存布局

成员按以下顺序：
1. 智能指针（对齐要求高）
2. 大对象（`SkImageInfo`）
3. 值类型（格式、枚举）

良好的内存对齐减少填充。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/private/chromium/GrSurfaceCharacterization.h` | 头文件 | 类定义 |
| `src/gpu/ganesh/GrContextThreadSafeProxy.h` | 依赖 | 线程安全 context |
| `src/gpu/ganesh/GrCaps.h` | 依赖 | GPU 能力查询 |
| `include/gpu/ganesh/GrBackendSurface.h` | 依赖 | 后端格式 |
| `include/core/SkImageInfo.h` | 依赖 | 图像信息 |
| `include/core/SkDeferredDisplayList.h` | 使用者 | DDL 执行 |
| `include/core/SkDeferredDisplayListRecorder.h` | 使用者 | DDL 录制 |
| `include/core/SkSurface.h` | 相关 | Surface 提取特征 |
| `src/gpu/ganesh/GrSurface.h` | 验证目标 | 实际 GPU surface |
