# GrSamplerState — GPU 纹理采样器状态

> 源文件: `src/gpu/ganesh/GrSamplerState.h`

## 概述

`GrSamplerState` 表示访问纹理时使用的过滤模式和平铺模式的完整配置。它是一个轻量级值类型，封装了纹理采样的所有关键参数：X/Y 方向的包裹模式 (WrapMode)、过滤模式 (Filter)、多级渐远纹理模式 (MipmapMode) 以及各向异性过滤的最大级别。此类广泛用于 Ganesh 渲染管线中纹理绑定和着色器程序配置。

## 架构位置

```
Skia 绘图调用 (SkSamplingOptions)
    └── GrSamplerState (本文件 - GPU 层采样器状态)
        ├── GrFragmentProcessor (片段处理器纹理采样)
        ├── GrPipeline (渲染管线状态)
        └── GPU 后端采样器对象
            ├── GL: glTexParameteri / glSamplerParameter
            ├── Vulkan: VkSampler
            └── Metal: MTLSamplerState
```

## 主要类与结构体

### GrSamplerState

| 成员 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `fWrapModes[2]` | `WrapMode[2]` | `{kClamp, kClamp}` | X 和 Y 方向的包裹模式 |
| `fFilter` | `Filter` | `kNearest` | 纹理过滤模式 |
| `fMipmapMode` | `MipmapMode` | `kNone` | Mipmap 过滤模式 |
| `fMaxAniso` | `int` | `1` | 各向异性过滤最大级别（1 表示禁用） |

### WrapMode 枚举

| 值 | 描述 |
|----|------|
| `kClamp` | 钳位到边缘：超出 [0,1] 范围时使用边缘像素值 |
| `kRepeat` | 重复平铺：纹理坐标取模运算 |
| `kMirrorRepeat` | 镜像重复：交替翻转平铺 |
| `kClampToBorder` | 钳位到边框：超出范围时使用边框颜色 |

### 类型别名

- `Filter` → `SkFilterMode`（`kNearest` / `kLinear`）
- `MipmapMode` → `SkMipmapMode`（`kNone` / `kNearest` / `kLinear`）

## 公共 API 函数

### 构造函数

| 签名 | 描述 |
|------|------|
| `GrSamplerState()` | 默认构造：Clamp + Nearest + 无 Mipmap |
| `GrSamplerState(WrapMode, Filter, MipmapMode)` | X/Y 使用相同包裹模式 |
| `GrSamplerState(WrapMode, WrapMode, Filter, MipmapMode)` | X/Y 使用不同包裹模式 |
| `GrSamplerState(const WrapMode[2], Filter, MipmapMode)` | 从数组指定包裹模式 |
| `GrSamplerState(Filter)` | 仅指定过滤模式 |
| `GrSamplerState(Filter, MipmapMode)` | 指定过滤和 Mipmap 模式 |

### 静态工厂

```cpp
static constexpr GrSamplerState Aniso(WrapMode wrapX, WrapMode wrapY,
                                       int maxAniso, skgpu::Mipmapped viewIsMipped);
```

创建各向异性过滤采样器。自动将过滤模式设为 `kLinear`，并根据 `viewIsMipped` 参数设置 Mipmap 模式。`maxAniso` 被钳位到 `[1, 1024]` 范围。

### 访问器

| 方法 | 返回 | 描述 |
|------|------|------|
| `wrapModeX()` | `WrapMode` | X 方向包裹模式 |
| `wrapModeY()` | `WrapMode` | Y 方向包裹模式 |
| `isRepeatedX()` | `bool` | X 方向是否为 Repeat 或 MirrorRepeat |
| `isRepeatedY()` | `bool` | Y 方向是否为 Repeat 或 MirrorRepeat |
| `isRepeated()` | `bool` | 任一方向是否重复 |
| `filter()` | `Filter` | 过滤模式 |
| `mipmapMode()` | `MipmapMode` | Mipmap 模式 |
| `mipmapped()` | `skgpu::Mipmapped` | 是否启用 Mipmap（布尔枚举） |
| `maxAniso()` | `int` | 各向异性最大级别 |
| `isAniso()` | `bool` | 是否启用各向异性过滤 (maxAniso > 1) |

### 键生成

```cpp
uint32_t asKey(bool anisoIsOrthogonal) const;
```

将采样器状态编码为 32 位整数键，用于状态缓存查找。`anisoIsOrthogonal` 参数指示底层 API 是否将各向异性过滤视为独立于其他过滤设置的正交参数（如某些 API 中，各向异性隐含线性过滤）。

## 内部实现细节

1. **constexpr 设计**: 所有构造函数和大部分方法均为 `constexpr`，允许在编译时构造和比较采样器状态。

2. **键编码布局**: `asKey()` 使用位打包将所有状态压缩到 32 位：
   - WrapX: 低位开始，`SkNextLog2(4)` = 2 位
   - WrapY: 接着 2 位
   - MaxAniso: `SkNextLog2(1024)` = 10 位
   - Filter: 1 位（仅当非各向异性或正交模式时）
   - MipmapMode: 2 位（同上）
   - 通过 `static_assert` 确保总位数不超过 32。

3. **各向异性键优化**: 当 `fMaxAniso > 1` 且 `anisoIsOrthogonal` 为 false 时，filter 和 mipmapMode 不参与键编码，因为各向异性过滤已隐含这些设置。

4. **相等比较注意**: `operator==` 不比较 `fMaxAniso`，这意味着两个相同 filter/wrap 但不同 aniso 级别的状态会被视为相等。这可能是有意为之，因为 aniso 主要通过 `asKey()` 进行区分。

5. **kMaxMaxAniso 常量**: 设为 1024，远大于任何硬件实际支持的限制，但 WebGPU 以 `unsigned short` 接受此值，所以保持合理范围。

## 依赖关系

- **`include/core/SkSamplingOptions.h`**: `SkFilterMode` 和 `SkMipmapMode` 定义
- **`include/gpu/GpuTypes.h`**: `skgpu::Mipmapped` 枚举
- **`include/private/base/SkTPin.h`**: 值钳位工具函数
- **`src/base/SkMathPriv.h`**: `SkNextLog2` 用于键编码位计算
- **`include/private/base/SkTo.h`**: 安全类型转换

## 设计模式与设计决策

1. **值类型**: 作为轻量级 POD 风格类，支持拷贝、按值传递和 constexpr 构造。无虚函数、无堆分配。

2. **与 Skia 公共类型对齐**: 通过类型别名 `Filter = SkFilterMode` 和 `MipmapMode = SkMipmapMode`，与公共 API 中的采样选项保持一致，便于转换。

3. **平台无关抽象**: 统一表示所有 GPU 后端的采样器状态，由各后端负责将其转换为平台特定的采样器对象。

4. **各向异性过滤特殊处理**: `Aniso()` 工厂方法封装了各向异性过滤的特殊配置逻辑（强制线性过滤、条件 Mipmap），避免使用者错误配置。

## 性能考量

- 类大小约 12 字节（2 * 1 + 1 + 1 + 4 + 填充），适合作为函数参数按值传递。
- `asKey()` 使用位运算编码，开销极低，适合在热路径上频繁调用用于状态缓存查找。
- `constexpr` 构造允许常见采样器配置在编译时完全解析，零运行时开销。
- 各向异性钳位使用 `SkTPin` 避免分支预测失败。

## 相关文件

- `include/core/SkSamplingOptions.h` — Skia 公共采样选项
- `src/gpu/ganesh/GrFragmentProcessor.h` — 使用采样器状态的片段处理器
- `src/gpu/ganesh/gl/GrGLSampler.h` — OpenGL 采样器实现
- `src/gpu/ganesh/vk/GrVkSampler.h` — Vulkan 采样器实现
- `src/gpu/ganesh/mtl/GrMtlSampler.h` — Metal 采样器实现
