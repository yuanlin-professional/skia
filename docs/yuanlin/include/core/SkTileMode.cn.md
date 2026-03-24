# SkTileMode

> 源文件: `include/core/SkTileMode.h`

## 概述
SkTileMode 定义了 Skia 中 shader(着色器)在其原始边界之外绘制时的平铺模式枚举。该枚举控制纹理、渐变和其他 shader 效果如何在边界外扩展,是图形渲染中处理边界条件的核心机制,广泛用于纹理映射、渐变填充和图像滤镜等场景。

## 架构位置
SkTileMode 位于 Skia 核心(core)模块,是着色器(SkShader)和图像滤镜(SkImageFilter)子系统的基础枚举。它被所有类型的 shader(包括图像 shader、渐变 shader)和需要处理边界行为的组件(如模糊滤镜、卷积滤镜)使用。

## 主要枚举类型

### SkTileMode
定义 shader 的边界平铺行为。

**枚举值**:

#### kClamp
```
/**
 *  Replicate the edge color if the shader draws outside of its
 *  original bounds.
 */
kClamp
```
- **说明**: 边缘颜色拉伸模式
- **行为**: 超出原始边界时,重复使用边缘的颜色值
- **视觉效果**: 边缘颜色向外延伸,形成"拉伸"效果
- **使用场景**:
  - 避免边缘出现突变
  - 渐变需要固定端点颜色时
  - 单张图片居中显示,边缘不需要重复

#### kRepeat
```
/**
 *  Repeat the shader's image horizontally and vertically.
 */
kRepeat
```
- **说明**: 重复平铺模式
- **行为**: 在水平和垂直方向上重复 shader 的图像
- **视觉效果**: 创建无缝重复的图案
- **使用场景**:
  - 纹理贴图(如地板、墙纸)
  - 背景图案
  - 需要无限扩展的图案

#### kMirror
```
/**
 *  Repeat the shader's image horizontally and vertically, alternating
 *  mirror images so that adjacent images always seam.
 */
kMirror
```
- **说明**: 镜像重复模式
- **行为**: 水平和垂直方向上重复,但相邻图像以镜像方式交替
- **视觉效果**: 相邻图像镜像对称,确保接缝处平滑过渡
- **使用场景**:
  - 创建对称图案
  - 需要平滑接缝的重复纹理
  - 万花筒效果

#### kDecal
```
/**
 *  Only draw within the original domain, return transparent-black everywhere else.
 */
kDecal
```
- **说明**: 边界裁剪模式
- **行为**: 仅在原始区域内绘制,超出部分返回透明黑色
- **视觉效果**: 清晰的边界,外部完全透明
- **使用场景**:
  - 严格限制绘制区域
  - 不希望边界外有任何内容
  - 图像裁剪和蒙版操作

**辅助定义**:
```cpp
kLastTileMode = kDecal  // 最后一个枚举值(用于迭代和验证)

static constexpr int kSkTileModeCount =
    static_cast<int>(SkTileMode::kLastTileMode) + 1;  // 枚举总数 = 4
```

## 视觉示意图

假设有一个 2x2 的原始图像 [A],各模式效果如下:

```
kClamp:
┌─────────────┐
│ AAAAAAAAAAA │  边缘颜色拉伸
│ AAAAAAAAAAA │
│ AA[Image]AA │
│ AAAAAAAAAAA │
│ AAAAAAAAAAA │
└─────────────┘

kRepeat:
┌─────────────┐
│ [A][A][A][A]│  直接重复
│ [A][A][A][A]│
│ [A][A][A][A]│
└─────────────┘

kMirror:
┌─────────────┐
│ [A][Ā][A][Ā]│  镜像交替(Ā表示镜像)
│ [Ā][A][Ā][A]│
│ [A][Ā][A][Ā]│
└─────────────┘

kDecal:
┌─────────────┐
│ ░░░░░░░░░░░ │  透明区域
│ ░░░[A]░░░░░ │  仅原始区域可见
│ ░░░░░░░░░░░ │
└─────────────┘
```

## 使用场景详解

### 纹理映射
在 SkShader::MakeImage() 中使用:
```cpp
// 创建重复平铺的背景纹理
auto shader = SkImage::makeShader(SkTileMode::kRepeat, SkTileMode::kRepeat);
```

### 渐变填充
在 SkGradient::MakeLinear() 等中使用:
```cpp
// 线性渐变,边缘颜色拉伸
auto gradient = SkGradient::MakeLinear(points, colors, nullptr, 2,
                                        SkTileMode::kClamp);
```

### 图像滤镜
在 SkImageFilters::Blur() 等中使用:
```cpp
// 模糊滤镜,边界使用 decal 模式避免边缘渗色
auto filter = SkImageFilters::Blur(sigmaX, sigmaY, SkTileMode::kDecal, nullptr);
```

### 卷积滤镜
在 SkImageFilters::MatrixConvolution() 中控制边界采样:
```cpp
// 锐化滤镜,边界使用 clamp 模式
auto sharpen = SkImageFilters::MatrixConvolution(kernelSize, kernel, gain, bias,
                                                  offset, SkTileMode::kClamp, ...);
```

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/core/SkTypes.h | 基础类型定义 |

### 被依赖的模块
| 模块 | 用途 |
|------|------|
| include/core/SkShader.h | Shader 的平铺模式参数 |
| include/effects/SkGradient.h | 渐变 shader 的边界行为 |
| include/effects/SkImageFilters.h | 图像滤镜的边界处理 |
| src/shaders/SkImageShader.h | 图像 shader 的实现 |
| src/gpu/ganesh/GrTextureEffect.h | GPU 纹理采样的 wrap mode 映射 |

## 设计模式与设计决策

### 枚举类型选择
使用 `enum class` 而非普通 enum,提供类型安全:
- 避免隐式转换为 int
- 防止命名空间污染
- 编译时类型检查

### 命名一致性
枚举值命名遵循 OpenGL/Vulkan 的惯例(Clamp、Repeat、Mirror),降低图形程序员的学习成本。

### kDecal 的特殊性
kDecal 模式相对较新,不是所有图形 API 都原生支持。Skia 在某些后端上需要通过 shader 逻辑模拟此行为。

## 性能考量

### GPU 实现
不同平台对平铺模式的硬件支持:
- **Clamp/Repeat/Mirror**: 大多数 GPU 原生支持(通过纹理采样器状态)
- **Decal**: 部分 GPU 不支持,需要 shader 中手动检查边界

### 性能排序(从快到慢)
1. **kRepeat**: 通常最快,硬件直接支持
2. **kClamp**: 硬件支持,性能接近 Repeat
3. **kMirror**: 需要额外计算,但大多数硬件优化良好
4. **kDecal**: 可能需要条件分支,性能稍慢

### 缓存影响
kRepeat 和 kMirror 可能导致更好的纹理缓存命中率,因为会重复访问相同的纹理区域。

## 平台相关说明

### OpenGL 映射
```
kClamp  -> GL_CLAMP_TO_EDGE
kRepeat -> GL_REPEAT
kMirror -> GL_MIRRORED_REPEAT
kDecal  -> GL_CLAMP_TO_BORDER (alpha=0) 或 shader 模拟
```

### Vulkan 映射
```
kClamp  -> VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE
kRepeat -> VK_SAMPLER_ADDRESS_MODE_REPEAT
kMirror -> VK_SAMPLER_ADDRESS_MODE_MIRRORED_REPEAT
kDecal  -> VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_BORDER
```

### Metal 映射
```
kClamp  -> MTLSamplerAddressModeClampToEdge
kRepeat -> MTLSamplerAddressModeRepeat
kMirror -> MTLSamplerAddressModeMirrorRepeat
kDecal  -> MTLSamplerAddressModeClampToZero (或 shader 模拟)
```

## 相关文件
| 文件 | 关系 |
|------|------|
| include/core/SkShader.h | 使用 SkTileMode 作为参数 |
| include/effects/SkGradient.h | 渐变的平铺模式 |
| include/effects/SkImageFilters.h | 滤镜边界处理 |
| src/shaders/SkImageShader.cpp | 图像 shader 的平铺实现 |
| src/gpu/ganesh/effects/GrTextureEffect.cpp | GPU 纹理效果的 wrap mode 实现 |
| include/core/SkSamplingOptions.h | 与采样选项配合使用 |
