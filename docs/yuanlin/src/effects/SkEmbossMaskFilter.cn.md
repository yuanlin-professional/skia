# SkEmbossMaskFilter - 浮雕遮罩滤镜

> 源文件: `src/effects/SkEmbossMaskFilter.h`, `src/effects/SkEmbossMaskFilter.cpp`

## 概述

SkEmbossMaskFilter 创建 3D 浮雕效果的遮罩滤镜。它通过指定光源方向和模糊量，将 alpha 遮罩解释为高度图，计算漫反射和镜面反射光照，生成具有立体感的视觉效果。

该滤镜由两阶段组成：首先使用高斯模糊生成平滑的高度图，然后由 SkEmbossMask 执行实际的光照计算。同时支持转换为图像滤镜表示（通过 SkImageFilters 的光照和混合操作链），用于 GPU 加速渲染。

## 架构位置

```
SkMaskFilter (公共接口)
  └── SkMaskFilterBase (内部基类)
        └── SkEmbossMaskFilter
              └── SkEmbossMask::Emboss() (光照计算)
```

- **类型标识**: `SkMaskFilterBase::Type::kEmboss`
- **GPU 路径**: 通过 `asImageFilter()` 转换为图像滤镜链

## 主要类与结构体

### SkEmbossMaskFilter
**Light 结构体**:
- `fDirection[3]` (SkScalar): 光源方向（归一化的 x,y,z）
- `fPad` (uint16_t): 对齐填充
- `fAmbient` (uint8_t): 环境光强度（0-255）
- `fSpecular` (uint8_t): 镜面反射指数（4.4 定点格式）

**成员变量**:
- `fLight` (Light): 光照参数
- `fBlurSigma` (SkScalar): 模糊 sigma 值

## 公共 API 函数

```cpp
static sk_sp<SkMaskFilter> Make(SkScalar blurSigma, const Light& light);
```
创建浮雕滤镜。自动归一化光源方向。blurSigma 必须为正有限值。

### 旧版 API（条件编译）
```cpp
// SK_SUPPORT_LEGACY_EMBOSSMASKFILTER
static sk_sp<SkMaskFilter> SkBlurMaskFilter::MakeEmboss(
    SkScalar blurSigma, const SkScalar direction[3],
    SkScalar ambient, SkScalar specular);
```

## 内部实现细节

### filterMask（CPU 路径）
1. 仅接受 A8 格式输入
2. 使用 `SkBlurMask::BoxBlur` 以 `kInner_SkBlurStyle` 生成模糊遮罩
3. 将格式设为 k3D_Format
4. 分配三平面内存（alpha + multiply + additive）
5. 将原始模糊结果拷贝到 alpha 平面
6. 通过矩阵变换光源方向
7. 恢复 XY 分量长度（Z 分量可能被矩阵变换破坏）
8. 调用 `SkEmbossMask::Emboss` 计算 multiply 和 additive 平面
9. 用原始 alpha 覆盖模糊后的 alpha

### asImageFilter（GPU 路径）
将浮雕效果转换为图像滤镜链：

```
finalFilter = ambientDiffuseColor + specular
            = srcColor * (ambient + diffuse) + specularHighlight

where:
  coverageBlurred = Blur(sigma, sigma, input)
  diffuse = DistantLitDiffuse(direction, white, surfaceScale, kd=1, coverageBlurred)
  ambient = Shader(ambientColor)
  ambientdiffuse = Plus(diffuse, ambient)
  ambientdiffuseColor = Modulate(srcColor, ambientdiffuse)
  specular = LegacySpecular(direction, white, surfaceScale, ks=1, shininess, coverageBlurred)
  final = Plus(ambientdiffuseColor, specular)
  result = DstIn(final, original_coverage)
```

**关键参数**:
- surfaceScale = -255/32（负值匹配旧版法线方向）
- shininess = (specular >> 4) + 1
- 返回 `{filter, true}`，true 表示此滤镜影响着色属性

### LegacySpecular（声明在 .h 中）
自定义的镜面反射计算，与 SkImageFilters::DistantLitSpecular 不同。使用 `(2*dot(L,N) - Lz) * Lz` 的反射公式，定义在 SkLightingImageFilter.cpp 中。

### 序列化
- `flatten`: 写入 Light 结构体（pad 清零确保缓存兼容）和 blurSigma
- `CreateProc`: 读取 Light 和 sigma，调用 Make

## 依赖关系

- `SkMaskFilterBase` — 遮罩滤镜基类
- `SkEmbossMask` — 光照计算
- `SkBlurMask` — 高斯模糊
- `SkImageFilters` — GPU 路径的图像滤镜链
- `SkPoint3` — 3D 向量（光源方向归一化）
- `SkShaders` — 颜色着色器（环境光、源颜色）

## 设计模式与设计决策

1. **双路径设计**: CPU 路径使用 SkEmbossMask 直接计算，GPU 路径通过 asImageFilter 转换
2. **光源归一化**: Make 中自动归一化光源方向，确保一致性
3. **负 surfaceScale**: 匹配旧版法线方向（"朝向"显示器而非朝向用户）
4. **Pad 清零**: 序列化时清零 pad 字段确保字体缓存查找的确定性
5. **着色影响**: asImageFilter 返回 true 表示此滤镜修改了颜色（不仅仅是透明度）

## 性能考量

- CPU 路径: BoxBlur + 逐像素光照计算，适合小遮罩
- GPU 路径: 通过图像滤镜链实现，利用 GPU 并行计算
- 镜面反射的幂运算在 CPU 路径中是循环实现，GPU 路径使用内置 pow
- 矩阵变换光源方向确保在非均匀缩放下仍然正确

## 相关文件

- `src/effects/SkEmbossMask.h` — 光照计算实现
- `src/core/SkBlurMask.h` — 高斯模糊
- `include/effects/SkImageFilters.h` — 图像滤镜
- `src/effects/SkLightingImageFilter.cpp` — LegacySpecular 实现
- `include/effects/SkBlurMaskFilter.h` — 旧版 API（条件编译）
