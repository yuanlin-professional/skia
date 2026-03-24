# GrMockCaps - Mock GPU 能力配置

> 源文件: `src/gpu/ganesh/mock/GrMockCaps.h`, `src/gpu/ganesh/mock/GrMockCaps.cpp`

## 概述

`GrMockCaps` 是 Ganesh Mock GPU 后端的能力（Caps）实现，继承自 `GrCaps`。它根据 `GrMockOptions` 配置对象报告 GPU 能力，允许测试在不同的模拟硬件配置下验证 Ganesh 渲染管线的行为。

## 架构位置

```
GrCaps (抽象基类)
    |
    +-- GrGLCaps    (OpenGL 能力)
    +-- GrVkCaps    (Vulkan 能力)
    +-- GrMockCaps  (本文件 - Mock 能力)
```

与 `GrMockGpu` 配对使用，为 Mock GPU 后端提供可定制的能力报告。

## 主要类与结构体

### `GrMockCaps`

继承自 `GrCaps`。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fOptions` | `GrMockOptions` | Mock 配置选项 |

### 常量

```cpp
static const int kMaxSampleCnt = 16;
```

Mock 后端的最大 MSAA 采样数。

## 公共 API 函数

### 构造函数

```cpp
GrMockCaps(const GrContextOptions& contextOptions, const GrMockOptions& options);
```

从 `GrMockOptions` 初始化所有能力字段：MipMap 支持、实例绘制、半浮点顶点属性、缓冲区映射标志、最大纹理/渲染目标尺寸、顶点属性数等。同时初始化 `GrShaderCaps`（整数支持、平面插值、采样器数量等）。

### 格式查询

| 方法 | 说明 |
|------|------|
| `isFormatSRGB()` | 通过 Mock 颜色类型判断 sRGB |
| `isFormatTexturable()` | 查询 Mock 配置的可纹理属性 |
| `isFormatRenderable()` | 查询采样数是否在可渲染范围内 |
| `isFormatAsColorTypeRenderable()` | 排除无 alpha 的 RGB 格式后查询渲染能力 |
| `isFormatCopyable()` | 始终返回 `false` |
| `maxRenderTargetSampleCount()` | 根据 `Renderability` 枚举返回 0/1/16 |
| `getRenderTargetSampleCount()` | 返回满足请求的最小 2 的幂采样数 |

### 像素操作查询

| 方法 | 说明 |
|------|------|
| `supportedWritePixelsColorType()` | 返回表面颜色类型本身 |
| `surfaceSupportsReadPixels()` | 受保护表面不可读取 |

### 其他

| 方法 | 说明 |
|------|------|
| `getWriteSwizzle()` / `onGetReadSwizzle()` | 始终返回 `"rgba"`（无混合） |
| `onGetDefaultBackendFormat()` | 创建 Mock 颜色类型的后端格式 |
| `onAreColorTypeAndFormatCompatible()` | 直接比较颜色类型 |
| `onCanCopySurface()` | 仅在源为受保护而目标非受保护时拒绝 |

## 内部实现细节

### 可渲染性三级模型

```cpp
enum class Renderability { kNo, kNonMSAA, kMSAA };
```

每种颜色类型可独立配置为不可渲染、仅单采样渲染或支持 MSAA 渲染。

### RGB 格式的特殊处理

`isFormatAsColorTypeRenderable` 明确排除了 `RGB_888x`、`RGB_F16F16F16x`、`RGB_101010x` 的可渲染性，因为这些格式缺少 alpha 通道，在混合引用目标 alpha 时会产生未定义行为。

### 压缩格式支持

Mock 后端支持 ETC2、BC1 压缩格式的可配置纹理能力，压缩格式始终不可渲染。

## 依赖关系

- **上游依赖**: `GrCaps`（基类）、`GrMockOptions`（配置）。
- **被依赖**: `GrMockGpu`、Skia 测试框架。

## 设计模式与设计决策

1. **配置驱动**: 所有能力由 `GrMockOptions` 外部提供，支持测试各种硬件配置场景。
2. **构造函数初始化**: 所有能力在构造时一次性设置，不可变。
3. **保守默认值**: 如 `fSupportsProtectedContent = true`、`fSampleLocationsSupport = true` 使 Mock 后端尽可能宽容，减少测试代码中的条件分支。

## 性能考量

作为测试工具类，性能不是关键考虑。所有查询方法都是简单的查表操作或常量返回。

## 相关文件

- `src/gpu/ganesh/mock/GrMockGpu.h` - Mock GPU 实现
- `include/gpu/ganesh/mock/GrMockTypes.h` - `GrMockOptions` 定义
- `src/gpu/ganesh/GrCaps.h` - GPU 能力基类
- `src/gpu/ganesh/GrShaderCaps.h` - 着色器能力
