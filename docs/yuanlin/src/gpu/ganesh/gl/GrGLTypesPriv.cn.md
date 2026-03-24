# GrGLTypesPriv

> 源文件
> - src/gpu/ganesh/gl/GrGLTypesPriv.h
> - src/gpu/ganesh/gl/GrGLTypesPriv.cpp

## 概述

`GrGLTypesPriv` 提供了 Skia Ganesh OpenGL 后端的私有类型定义和工具类。该模块包含纹理参数管理类 `GrGLTextureParameters`、后端纹理信息封装类 `GrGLBackendTextureInfo` 以及纹理规格结构体 `GrGLTextureSpec`。这些类型用于管理 OpenGL 纹理的状态、参数和元数据。

核心组件 `GrGLTextureParameters` 跟踪纹理参数的时间戳，并区分采样器可覆盖状态（如过滤模式、包装模式）和非采样器状态（如 mipmap 级别、swizzle）。这种设计允许在使用采样器对象时优化状态管理。

## 架构位置

```
GrGLTextureParameters (纹理参数管理)
    ├── SamplerOverriddenState (采样器覆盖的状态)
    └── NonsamplerState (非采样器状态)

GrGLBackendTextureInfo (后端纹理信息)
    ├── GrGLTextureInfo (GL纹理信息)
    └── GrGLTextureParameters (参数引用)

GrGLTextureSpec (纹理规格)
    ├── fTarget (GL目标)
    └── fFormat (GL格式)
```

这些类型在 OpenGL 纹理管理层提供参数状态跟踪和验证功能。

## 主要类与结构体

### GrGLTextureParameters

**继承关系:**
- 继承自: `SkNVRefCnt<GrGLTextureParameters>`

**类型定义:**

| 类型名 | 定义 | 说明 |
|--------|------|------|
| `ResetTimestamp` | `uint64_t` | 重置时间戳类型 |

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fSamplerOverriddenState` | `SamplerOverriddenState` | 采样器可覆盖的状态 |
| `fNonsamplerState` | `NonsamplerState` | 非采样器状态 |
| `fResetTimestamp` | `ResetTimestamp` | 重置时间戳 |

### SamplerOverriddenState 结构体

可被采样器对象覆盖的纹理参数：

| 成员变量 | 类型 | 默认值 | 说明 |
|---------|------|--------|------|
| `fMinFilter` | `GrGLenum` | `GR_GL_NEAREST_MIPMAP_LINEAR` | 缩小过滤 |
| `fMagFilter` | `GrGLenum` | `GR_GL_LINEAR` | 放大过滤 |
| `fWrapS` | `GrGLenum` | `GR_GL_REPEAT` | S 轴包装模式 |
| `fWrapT` | `GrGLenum` | `GR_GL_REPEAT` | T 轴包装模式 |
| `fMinLOD` | `GrGLfloat` | `-1000.f` | 最小 LOD |
| `fMaxLOD` | `GrGLfloat` | `1000.f` | 最大 LOD |
| `fMaxAniso` | `GrGLfloat` | `1.f` | 最大各向异性 |
| `fBorderColorInvalid` | `bool` | `false` | 边界颜色是否失效 |

### NonsamplerState 结构体

不被采样器对象影响的纹理参数：

| 成员变量 | 类型 | 默认值 | 说明 |
|---------|------|--------|------|
| `fBaseMipMapLevel` | `GrGLint` | `0` | 基础 mipmap 级别 |
| `fMaxMipmapLevel` | `GrGLint` | `1000` | 最大 mipmap 级别 |
| `fSwizzleIsRGBA` | `bool` | `true` | Swizzle 是否为 RGBA |

### GrGLBackendTextureInfo

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fInfo` | `GrGLTextureInfo` | GL 纹理信息（ID、格式等） |
| `fParams` | `sk_sp<GrGLTextureParameters>` | 纹理参数引用 |

### GrGLTextureSpec

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fTarget` | `GrGLenum` | GL 纹理目标 |
| `fFormat` | `GrGLenum` | GL 纹理格式 |

## 公共 API 函数

### GrGLTextureParameters

**构造与初始化:**
- `GrGLTextureParameters()` - 默认构造，时间戳设为过期

**访问器:**
- `ResetTimestamp resetTimestamp() const` - 获取重置时间戳
- `const SamplerOverriddenState& samplerOverriddenState() const` - 获取采样器状态
- `const NonsamplerState& nonsamplerState() const` - 获取非采样器状态

**状态管理:**
- `void invalidate()` - 使所有状态失效
- `void set(const SamplerOverriddenState*, const NonsamplerState&, ResetTimestamp)` - 设置状态

### SamplerOverriddenState

- `SamplerOverriddenState()` - 构造，使用 OpenGL 默认值
- `void invalidate()` - 使状态失效

### NonsamplerState

- `NonsamplerState()` - 构造，使用 OpenGL 默认值
- `void invalidate()` - 使状态失效

### GrGLBackendTextureInfo

- `GrGLBackendTextureInfo(const GrGLTextureInfo&, sk_sp<GrGLTextureParameters>)` - 构造
- `const GrGLTextureInfo& info() const` - 获取纹理信息
- `GrGLTextureParameters* parameters() const` - 获取参数指针
- `sk_sp<GrGLTextureParameters> refParameters() const` - 获取参数引用
- `bool isProtected() const` - 是否为受保护纹理

### 工具函数

- `GrGLSurfaceInfo GrGLTextureSpecToSurfaceInfo(const GrGLTextureSpec&, uint32_t sampleCount, uint32_t levelCount, skgpu::Protected)` - 将纹理规格转换为表面信息

## 内部实现细节

### 状态默认值初始化

```cpp
GrGLTextureParameters::SamplerOverriddenState::SamplerOverriddenState()
        // OpenGL 默认值
        : fMinFilter(GR_GL_NEAREST_MIPMAP_LINEAR)
        , fMagFilter(GR_GL_LINEAR)
        , fWrapS(GR_GL_REPEAT)
        , fWrapT(GR_GL_REPEAT)
        , fMinLOD(-1000.f)
        , fMaxLOD(1000.f)
        , fMaxAniso(1.f)
        , fBorderColorInvalid(false) {}

GrGLTextureParameters::NonsamplerState::NonsamplerState()
        // OpenGL 默认值
        : fBaseMipMapLevel(0), fMaxMipmapLevel(1000), fSwizzleIsRGBA(true) {}
```

### 状态失效

```cpp
void GrGLTextureParameters::SamplerOverriddenState::invalidate() {
    fMinFilter = ~0U;           // 无效值
    fMagFilter = ~0U;
    fWrapS = ~0U;
    fWrapT = ~0U;
    fMinLOD = SK_ScalarNaN;     // NaN 表示失效
    fMaxLOD = SK_ScalarNaN;
    fMaxAniso = -1.f;           // 负值表示失效
    fBorderColorInvalid = true;
}

void GrGLTextureParameters::NonsamplerState::invalidate() {
    fSwizzleIsRGBA = false;
    fBaseMipMapLevel = ~0;      // 无效值
    fMaxMipmapLevel = ~0;
}

void GrGLTextureParameters::invalidate() {
    fSamplerOverriddenState.invalidate();
    fNonsamplerState.invalidate();
}
```

### 状态设置

```cpp
void GrGLTextureParameters::set(const SamplerOverriddenState* samplerState,
                                const NonsamplerState& nonsamplerState,
                                ResetTimestamp currTimestamp) {
    if (samplerState) {
        fSamplerOverriddenState = *samplerState;
    }
    fNonsamplerState = nonsamplerState;
    fResetTimestamp = currTimestamp;
}
```

### 纹理规格转换

```cpp
GrGLSurfaceInfo GrGLTextureSpecToSurfaceInfo(const GrGLTextureSpec& glSpec,
                                             uint32_t sampleCount,
                                             uint32_t levelCount,
                                             GrProtected isProtected) {
    GrGLSurfaceInfo info;
    // 共享信息
    info.fSampleCount = sampleCount;
    info.fLevelCount = levelCount;
    info.fProtected = isProtected;

    // GL 特定信息
    info.fTarget = glSpec.fTarget;
    info.fFormat = glSpec.fFormat;

    return info;
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLTypes` | GL 基础类型 |
| `GrGLDefines` | GL 常量定义 |
| `SkRefCnt` | 引用计数 |
| `SkScalar` | 标量类型（NaN） |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrGLTexture` | 使用 `GrGLTextureParameters` 管理状态 |
| `GrGLGpu` | 使用参数设置纹理状态 |
| `GrBackendTexture` | 通过 `GrGLBackendTextureInfo` 导出 |

## 设计模式与设计决策

### 1. 时间戳机制

使用时间戳跟踪参数有效性：

```cpp
using ResetTimestamp = uint64_t;
static constexpr ResetTimestamp kExpiredTimestamp = 0;
```

**优势**:
- 快速验证参数是否过期
- 无需逐个检查参数
- 支持批量失效

### 2. 状态分离

采样器状态与非采样器状态分开：

```cpp
struct SamplerOverriddenState { ... };  // 可被采样器对象覆盖
struct NonsamplerState { ... };         // 总是生效
```

**原因**:
- 使用采样器对象时，某些状态来自采样器而非纹理
- 避免不必要的状态设置

### 3. 可选采样器状态

```cpp
void set(const SamplerOverriddenState* samplerState,  // 可为 nullptr
         const NonsamplerState& nonsamplerState,
         ResetTimestamp currTimestamp) {
    if (samplerState) {
        fSamplerOverriddenState = *samplerState;
    }
    // ...
}
```

**优势**: 使用采样器对象时可跳过采样器状态设置

### 4. 不可复制值类型

使用 `SkNVRefCnt`（非虚引用计数）：

```cpp
class GrGLTextureParameters : public SkNVRefCnt<GrGLTextureParameters> { ... };
```

**优势**: 轻量级引用计数，无虚函数开销

## 性能考量

### 1. 时间戳快速验证

```cpp
if (params->resetTimestamp() == currentTimestamp) {
    // 参数有效，跳过设置
}
```

避免逐参数比较。

### 2. 批量失效

```cpp
void invalidate() {
    fSamplerOverriddenState.invalidate();
    fNonsamplerState.invalidate();
}
```

一次调用使所有状态失效。

### 3. 最小化内存占用

```cpp
// SamplerOverriddenState: ~36 字节
// NonsamplerState: ~12 字节
// 总计: ~56 字节（包含时间戳和对齐）
```

### 4. 引用计数共享

多个纹理可共享同一参数对象：

```cpp
sk_sp<GrGLTextureParameters> params = ...;
texture1->setParameters(params);
texture2->setParameters(params);  // 共享
```

## 时间戳溢出处理

```cpp
// 使用 uint64_t
// 假设每帧重置一次，60fps
// 溢出时间: 2^64 / 60 / 60 / 24 / 365 ≈ 9.7 billion years
```

实际上不会溢出。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/gpu/ganesh/gl/GrGLTypes.h` | 依赖 | 公共 GL 类型 |
| `src/gpu/ganesh/gl/GrGLDefines.h` | 依赖 | GL 常量定义 |
| `src/gpu/ganesh/gl/GrGLTexture.h` | 使用者 | 纹理类 |
| `src/gpu/ganesh/gl/GrGLGpu.h` | 使用者 | GPU 接口 |
| `include/gpu/ganesh/GrBackendSurface.h` | 使用者 | 后端表面类型 |
| `include/core/SkRefCnt.h` | 依赖 | 引用计数基类 |
