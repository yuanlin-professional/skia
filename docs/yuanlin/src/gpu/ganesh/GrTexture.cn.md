# GrTexture

> 源文件: src/gpu/ganesh/GrTexture.h, src/gpu/ganesh/GrTexture.cpp

## 概述

`GrTexture` 是 Ganesh GPU 后端中表示纹理资源的核心抽象类。它虚继承自 `GrSurface`，代表了 GPU 上实际的纹理对象。该类封装了纹理的基本属性（如纹理类型、mipmap 状态）和操作（如标记 mipmap 脏、计算 scratch key 等），是 Skia GPU 渲染管线中纹理管理的基础。

纹理可以独立存在（仅用于采样），也可以与渲染目标结合（用于渲染到纹理）。该类通过虚函数接口定义了与后端相关的操作，具体实现由各个 GPU 后端（GL、Vulkan、Metal 等）提供。

## 架构位置

`GrTexture` 位于 Skia 的 GPU 资源管理层次结构中：

```
Skia GPU 资源层次
└── GrGpuResource            # GPU 资源基类
    └── GrSurface            # 表面资源（虚基类）
        └── GrTexture        # 纹理资源（本类）
            ├── GrGLTexture      # OpenGL 实现
            ├── GrVkTexture      # Vulkan 实现
            ├── GrMtlTexture     # Metal 实现
            └── GrD3DTexture     # Direct3D 实现
```

该类可以与 `GrRenderTarget` 组合使用，形成可渲染纹理（通过菱形继承）。

## 主要类与结构体

### 继承关系

```
GrGpuResource
    ↑
    │ (虚继承)
GrSurface
    ↑
    │ (虚继承)
GrTexture
```

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fTextureType | GrTextureType | 纹理类型（2D、外部、矩形等） |
| fMipmapStatus | GrMipmapStatus | Mipmap 状态（未分配、脏、有效） |
| fMaxMipmapLevel | int | 最大 mipmap 级别数 |

### 重要类型定义

**GrMipmapStatus 枚举**：
- `kNotAllocated`: 未分配 mipmap
- `kDirty`: Mipmap 已分配但内容过时
- `kValid`: Mipmap 已分配且内容有效

**GrTextureType 枚举**：
- `k2D`: 标准 2D 纹理
- `kExternal`: 外部纹理（如相机流）
- `kRectangle`: 矩形纹理（非标准化坐标）

## 公共 API 函数

### 类型转换

```cpp
GrTexture* asTexture() override
const GrTexture* asTexture() const override
```
返回自身，用于类型识别和向下转型。

### 后端接口

```cpp
virtual GrBackendTexture getBackendTexture() const = 0
```
获取后端特定的纹理句柄（纯虚函数）。

```cpp
virtual void textureParamsModified() = 0
```
通知 Skia 纹理参数（如过滤模式、环绕模式）被外部修改。

### 资源窃取

```cpp
static bool StealBackendTexture(sk_sp<GrTexture>,
                               GrBackendTexture*,
                               SkImages::BackendTextureReleaseProc*)
```
从唯一拥有且无待处理 IO 的 `GrTexture` 中窃取底层资源，并删除该 `GrTexture` 对象。

### 纹理属性查询

```cpp
GrTextureType textureType() const
bool hasRestrictedSampling() const
skgpu::Mipmapped mipmapped() const
bool mipmapsAreDirty() const
GrMipmapStatus mipmapStatus() const
int maxMipmapLevel() const
```

### Mipmap 状态管理

```cpp
void markMipmapsDirty()
void markMipmapsClean()
```

### Scratch Key 计算

```cpp
static void ComputeScratchKey(const GrCaps& caps,
                              const GrBackendFormat& format,
                              SkISize dimensions,
                              GrRenderable,
                              int sampleCnt,
                              skgpu::Mipmapped,
                              GrProtected,
                              skgpu::ScratchKey* key)
```

## 内部实现细节

### 构造函数

```cpp
GrTexture(GrGpu*, const SkISize&, GrProtected,
         GrTextureType, GrMipmapStatus, std::string_view label)
```

实现逻辑：
1. 调用基类 `GrSurface` 构造函数
2. 初始化纹理类型和 mipmap 状态
3. 根据 mipmap 状态计算最大 mipmap 级别（使用 `SkMipmap::ComputeLevelCount`）
4. 如果是外部纹理，设置为只读状态

### Mipmap 管理

**markMipmapsDirty()**:
- 只在状态为 `kValid` 时才标记为 `kDirty`
- 避免 `kNotAllocated` 状态被错误标记

**markMipmapsClean()**:
- 断言 mipmap 已分配
- 设置状态为 `kValid`

### GPU 内存大小计算

```cpp
size_t onGpuMemorySize() const
```
使用 `GrSurface::ComputeSize` 计算，参数包括：
- 后端格式
- 纹理尺寸
- 颜色采样数（对于纹理总是 1）
- 是否包含 mipmap

### Scratch Key 生成

`ComputeScratchKey()` 生成 5 个 32 位整数的键：
- `[0]`: 宽度
- `[1]`: 高度
- `[2]`: 格式键低 32 位
- `[3]`: 格式键高 32 位
- `[4]`: 打包的标志位（mipmapped、protected、renderable、sampleCnt）

压缩 ID 布局（第 5 个元素）：
```
位 [0]    : mipmapped (1 bit)
位 [1]    : protected (1 bit)
位 [2]    : renderable (1 bit)
位 [3-31] : sampleCnt (29 bits)
```

### 资源窃取实现

`StealBackendTexture()` 流程：
1. 检查纹理是否唯一持有（`unique()`）
2. 调用子类的 `onStealBackendTexture()` 获取后端句柄
3. 移除 unique key 和 scratch key
4. 释放纹理对象，资源缓存会自动清理

## 依赖关系

### 依赖的模块

| 模块 | 依赖关系 | 说明 |
|-----|---------|------|
| GrSurface | 继承 | 表面资源基类 |
| GrGpu | 使用 | GPU 接口，用于查询能力 |
| GrCaps | 使用 | 硬件能力查询 |
| GrResourceCache | 使用 | 资源缓存管理 |
| SkMipmap | 使用 | Mipmap 级别计算 |
| GrBackendTexture | 使用 | 跨 API 的纹理表示 |

### 被依赖的模块

| 模块 | 使用方式 | 说明 |
|-----|---------|------|
| GrTextureProxy | 代理 | 纹理的延迟实例化代理 |
| GrRenderTarget | 组合 | 可渲染纹理 |
| GrTextureResource | 使用 | 纹理资源管理器 |
| 各后端实现 | 继承 | GL/Vulkan/Metal/D3D 纹理 |

## 设计模式与设计决策

### 虚继承设计

采用虚继承 `GrSurface` 以支持菱形继承：
```
        GrSurface
        ↗       ↖
   GrTexture  GrRenderTarget
        ↖       ↗
    GrTextureRenderTarget
```

这允许一个对象同时作为纹理和渲染目标，避免基类重复。

### 模板方法模式

定义纯虚函数接口，由子类实现后端特定操作：
- `getBackendTexture()`: 获取后端句柄
- `onStealBackendTexture()`: 窃取后端资源
- `textureParamsModified()`: 参数修改通知

### 状态管理策略

**Mipmap 状态三态机**：
```
kNotAllocated ──allocate──> kDirty ──generate──> kValid
                               ↑                     │
                               └──────modify─────────┘
```

### 外部纹理特殊处理

外部纹理（`GrTextureType::kExternal`）在构造时自动设置为只读：
```cpp
if (textureType == GrTextureType::kExternal) {
    this->setReadOnly();
}
```

这是因为外部纹理通常来自摄像头、视频解码器等，不应被 Skia 修改。

## 性能考量

### Scratch Key 优化

- 压缩的格式不计算 scratch key（通过 `isFormatCompressed()` 检查）
- Scratch key 用于快速查找可复用的纹理资源
- 键生成非常高效，只涉及位操作

### Mipmap 懒生成

- Mipmap 标记为脏而不是立即重新生成
- 实际生成推迟到渲染时批量处理
- 减少不必要的重复生成

### 内存占用计算

`onGpuMemorySize()` 提供准确的内存占用信息：
- 用于预算管理
- 帮助资源缓存做出驱逐决策
- 考虑所有 mipmap 级别

### 资源生命周期管理

- 通过引用计数自动管理生命周期
- 支持资源窃取避免不必要的复制
- 与缓存系统集成，支持自动清理

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/gpu/ganesh/GrSurface.h | 基类 | 表面资源基类 |
| src/gpu/ganesh/GrTextureProxy.h | 代理 | 纹理延迟实例化代理 |
| src/gpu/ganesh/GrRenderTarget.h | 组合 | 可渲染表面 |
| src/gpu/ganesh/gl/GrGLTexture.h | 子类 | OpenGL 纹理实现 |
| src/gpu/ganesh/vk/GrVkTexture.h | 子类 | Vulkan 纹理实现 |
| src/gpu/ganesh/mtl/GrMtlTexture.h | 子类 | Metal 纹理实现 |
| src/gpu/ganesh/GrGpu.h | 使用 | GPU 接口 |
| src/gpu/ganesh/GrResourceCache.h | 使用 | 资源缓存 |
| include/gpu/ganesh/GrBackendSurface.h | 使用 | 后端表面表示 |
