# GaussianBlurEffect

> 源文件: modules/skottie/src/effects/GaussianBlurEffect.cpp

## 概述

GaussianBlurEffect 模块实现了高斯模糊效果,支持水平、垂直和双向模糊,以及边缘像素重复选项。该效果对应 Adobe After Effects 的高斯模糊效果,是视频后期制作中最常用的模糊工具。

## 架构位置

```
modules/skottie/
  └── src/
      └── effects/
          ├── GaussianBlurEffect.cpp   # 高斯模糊实现
          ├── Effects.h                # 效果接口
          └── MotionTileEffect.cpp     # 其他图像效果
```

## 主要类与结构体

### GaussianBlurEffectAdapter

```cpp
class GaussianBlurEffectAdapter final : public AnimatablePropertyContainer
```

**核心成员:**
- `fBlur` - `sksg::BlurImageFilter` 模糊滤镜
- `fImageFilterEffect` - `sksg::ImageFilterEffect` 效果节点
- `fBlurriness` - 模糊强度
- `fDimensions` - 模糊方向(1=双向, 2=水平, 3=垂直)
- `fRepeatEdge` - 边缘重复模式(0=关闭, 1=开启)

## 公共 API 函数

### attachGaussianBlurEffect

```cpp
sk_sp<sksg::RenderNode> EffectBuilder::attachGaussianBlurEffect(
    const skjson::ArrayValue& jprops,
    sk_sp<sksg::RenderNode> layer) const
```

**属性索引:**
```cpp
enum : size_t {
    kBlurriness_Index = 0,  // 模糊强度
    kDimensions_Index = 1,  // 模糊方向
    kRepeatEdge_Index = 2,  // 边缘重复
};
```

## 内部实现细节

### 模糊方向映射

```cpp
static constexpr SkVector kDimensionsMap[] = {
    { 1, 1 }, // 1 -> 水平和垂直
    { 1, 0 }, // 2 -> 仅水平
    { 0, 1 }, // 3 -> 仅垂直
};
```

### Sigma 计算

```cpp
const auto sigma = fBlurriness * kBlurSizeToSigma;
fBlur->setSigma({ sigma * kDimensionsMap[dim_index].x(),
                  sigma * kDimensionsMap[dim_index].y() });
```

### 边缘重复处理

```cpp
// 边缘重复意味着两件事:
// - 模糊使用 kClamp 平铺模式
// - 输出裁剪到内容大小
fBlur->setTileMode(repeat_edge ? SkTileMode::kClamp : SkTileMode::kDecal);

static_cast<sksg::ImageFilterEffect*>(fImageFilterEffect.get())->setCropping(
    repeat_edge ? sksg::ImageFilterEffect::Cropping::kContent
                : sksg::ImageFilterEffect::Cropping::kNone);
```

## 依赖关系

- `SkTileMode` - 平铺模式(Clamp/Decal)
- `sksg::BlurImageFilter` - 模糊图像滤镜
- `sksg::ImageFilterEffect` - 图像滤镜效果包装器
- `EffectBinder` - 属性绑定器

## 设计模式与设计决策

### 分离的 X/Y Sigma

通过独立的 X/Y sigma 值支持方向性模糊,使用方向映射表简化参数计算。

### 条件裁剪

边缘重复模式触发内容裁剪,防止模糊扩展超出原始边界。

## 性能考量

### 单次 Sigma 计算

预计算 sigma 值并一次性设置,避免重复的浮点运算。

### 索引边界检查

```cpp
const auto dim_index = SkTPin<size_t>(static_cast<size_t>(fDimensions),
                                      1, std::size(kDimensionsMap)) - 1;
```

使用 `SkTPin` 确保数组访问安全,防止越界。

## 相关文件

- `modules/sksg/include/SkSGRenderEffect.h` - 渲染效果节点
- `include/core/SkTileMode.h` - 平铺模式定义
- `modules/skottie/src/effects/Effects.h` - 效果构建器
