# GrMockTexture

> 源文件
> - src/gpu/ganesh/mock/GrMockTexture.h

## 概述

`GrMockTexture` 是 Skia 图形库中 Mock 后端的纹理、渲染目标和混合对象的实现,提供了三个类:`GrMockTexture`(纹理)、`GrMockRenderTarget`(渲染目标)和 `GrMockTextureRenderTarget`(混合对象)。这些类用于测试 Skia 的纹理管理和渲染管线,而无需真实的 GPU 资源。

## 架构位置

```
Skia Graphics Library
└── src/gpu/ganesh/
    ├── GrTexture              (纹理基类)
    ├── GrRenderTarget         (渲染目标基类)
    └── mock/
        ├── GrMockTexture      (Mock纹理) ← 当前文件
        ├── GrMockRenderTarget (Mock渲染目标)
        └── GrMockTextureRenderTarget (混合对象)
```

## 主要类与结构体

### GrMockTexture

Mock 纹理实现,继承自 `GrTexture`。

**继承关系:**
- `GrSurface` -> `GrTexture` -> `GrMockTexture`

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fInfo` | `GrMockTextureInfo` | 纹理配置信息 |

**构造函数:**

```cpp
// 预算纹理
GrMockTexture(GrMockGpu* gpu, skgpu::Budgeted budgeted,
              SkISize dimensions, GrMipmapStatus mipmapStatus,
              const GrMockTextureInfo& info, std::string_view label);

// 包装外部纹理
GrMockTexture(GrMockGpu* gpu, SkISize dimensions,
              GrMipmapStatus mipmapStatus, const GrMockTextureInfo& info,
              GrWrapCacheable cacheable, GrIOType ioType,
              std::string_view label);
```

**公共方法:**

| 方法 | 返回类型 | 说明 |
|-----|---------|------|
| `getBackendTexture()` | `GrBackendTexture` | 获取后端纹理句柄 |
| `backendFormat()` | `GrBackendFormat` | 获取后端格式 |
| `textureParamsModified()` | `void` | 纹理参数修改通知(空操作) |

### GrMockRenderTarget

Mock 渲染目标实现,继承自 `GrRenderTarget`。

**继承关系:**
- `GrSurface` -> `GrRenderTarget` -> `GrMockRenderTarget`

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fInfo` | `GrMockRenderTargetInfo` | 渲染目标配置信息 |

**构造函数:**

```cpp
// 预算渲染目标
GrMockRenderTarget(GrMockGpu* gpu, skgpu::Budgeted budgeted,
                   SkISize dimensions, int sampleCnt,
                   const GrMockRenderTargetInfo& info,
                   std::string_view label);

// 包装外部渲染目标
GrMockRenderTarget(GrMockGpu* gpu, Wrapped,
                   SkISize dimensions, int sampleCnt,
                   const GrMockRenderTargetInfo& info,
                   std::string_view label);
```

**公共方法:**

| 方法 | 返回类型 | 说明 |
|-----|---------|------|
| `canAttemptStencilAttachment()` | `bool` | 检查是否可附加模板缓冲(始终返回 true) |
| `completeStencilAttachment()` | `bool` | 完成模板附件(始终返回 true) |
| `onGpuMemorySize()` | `size_t` | 计算 GPU 内存占用 |
| `getBackendRenderTarget()` | `GrBackendRenderTarget` | 获取后端渲染目标 |
| `backendFormat()` | `GrBackendFormat` | 获取后端格式 |

### GrMockTextureRenderTarget

同时作为纹理和渲染目标的混合对象。

**继承关系:**
- 多重继承: `GrMockTexture` + `GrMockRenderTarget`

**构造函数:**

```cpp
// 内部创建
GrMockTextureRenderTarget(GrMockGpu* gpu, skgpu::Budgeted budgeted,
                          SkISize dimensions, int sampleCnt,
                          GrMipmapStatus mipmapStatus,
                          const GrMockTextureInfo& texInfo,
                          const GrMockRenderTargetInfo& rtInfo,
                          std::string_view label);

// 包装可渲染后端纹理
GrMockTextureRenderTarget(GrMockGpu* gpu, SkISize dimensions,
                          int sampleCnt, GrMipmapStatus mipmapStatus,
                          const GrMockTextureInfo& texInfo,
                          const GrMockRenderTargetInfo& rtInfo,
                          GrWrapCacheable cacheable,
                          std::string_view label);
```

**重写方法:**

```cpp
GrTexture* asTexture() override { return this; }
GrRenderTarget* asRenderTarget() override { return this; }
const GrTexture* asTexture() const override { return this; }
const GrRenderTarget* asRenderTarget() const override { return this; }
```

## 内部实现细节

### 内存占用计算

#### GrMockRenderTarget::onGpuMemorySize
```cpp
size_t onGpuMemorySize() const override {
    int numColorSamples = this->numSamples();
    if (numColorSamples > 1) {
        ++numColorSamples;  // MSAA 需额外的解析缓冲区
    }
    return GrSurface::ComputeSize(
        this->backendFormat(), this->dimensions(),
        numColorSamples, skgpu::Mipmapped::kNo);
}
```

#### GrMockTextureRenderTarget::onGpuMemorySize
```cpp
size_t onGpuMemorySize() const override {
    int numColorSamples = this->numSamples();
    if (numColorSamples > 1) {
        ++numColorSamples;
    }
    return GrSurface::ComputeSize(
        this->backendFormat(), this->dimensions(),
        numColorSamples, this->mipmapped());  // 包含 mipmap
}
```

### 资源生命周期

所有类都实现了以下生命周期方法:
```cpp
void onRelease() override {
    INHERITED::onRelease();
}

void onAbandon() override {
    INHERITED::onAbandon();
}

void onSetLabel() override {}  // 空实现
```

### 混合对象的菱形继承问题

`GrMockTextureRenderTarget` 通过显式路径选择避免歧义:
```cpp
void onAbandon() override {
    GrRenderTarget::onAbandon();
    GrMockTexture::onAbandon();
}

void onRelease() override {
    GrRenderTarget::onRelease();
    GrMockTexture::onRelease();
}

// 避免 MSVC 的"通过支配继承"警告
void computeScratchKey(skgpu::ScratchKey* key) const override {
    GrTexture::computeScratchKey(key);
}
```

### 后端对象创建

```cpp
GrBackendTexture GrMockTexture::getBackendTexture() const {
    return GrBackendTextures::MakeMock(
        this->width(), this->height(),
        this->mipmapped(), fInfo);
}

GrBackendRenderTarget GrMockRenderTarget::getBackendRenderTarget() const {
    int numStencilBits = 0;
    if (GrAttachment* stencil = this->getStencilAttachment()) {
        numStencilBits = GrBackendFormatStencilBits(stencil->backendFormat());
    }
    return GrBackendRenderTargets::MakeMock(
        this->width(), this->height(),
        this->numSamples(), numStencilBits, fInfo);
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `GrTexture` | 纹理基类 |
| `GrRenderTarget` | 渲染目标基类 |
| `GrSurface` | 表面基类 |
| `GrMockGpu` | Mock GPU 管理器 |
| `GrBackendSurface` | 后端表面抽象 |
| `GrAttachment` | 附件管理 |

### 被依赖的模块

| 模块 | 使用场景 |
|-----|---------|
| `GrMockGpu` | 创建纹理和渲染目标 |
| 单元测试 | 测试纹理/渲染目标生命周期 |
| `GrMockOpsRenderPass` | 使用渲染目标 |

## 设计模式与设计决策

### 空对象模式
所有方法提供最小实现,满足接口要求但不执行实际 GPU 操作。

### 多重继承设计
`GrMockTextureRenderTarget` 使用多重继承同时具备纹理和渲染目标特性,需要特别处理:
- 显式调用基类方法
- 解决方法歧义
- 特别处理虚基类 `GrSurface`

### 构造函数模板
提供预算版和包装版构造函数,满足不同资源管理需求。

### 只读纹理支持
```cpp
if (ioType == kRead_GrIOType) {
    this->setReadOnly();  // 标记为只读
}
```

## 性能考量

### 零开销实现
- 无实际 GPU 资源分配
- 内存占用计算为模拟值
- 所有状态更新为空操作

### 测试效率
- 快速创建/销毁
- 无驱动调用开销
- 适合批量测试

### 内存占用模拟
提供真实的内存占用计算,便于测试内存管理逻辑。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrTexture.h` | 基类 | 纹理抽象 |
| `src/gpu/ganesh/GrRenderTarget.h` | 基类 | 渲染目标抽象 |
| `src/gpu/ganesh/GrSurface.h` | 基类 | 表面抽象 |
| `src/gpu/ganesh/mock/GrMockGpu.h` | 管理者 | Mock GPU 实现 |
| `include/gpu/ganesh/mock/GrMockTypes.h` | 类型 | Mock 配置类型 |
| `include/gpu/ganesh/GrBackendSurface.h` | 接口 | 后端表面类型 |
| `src/gpu/ganesh/GrAttachment.h` | 协作 | 模板附件管理 |
