# FuzzImageFilterDeserialize (OSS-Fuzz)

> 源文件: fuzz/oss_fuzz/FuzzImageFilterDeserialize.cpp

## 概述

测试图像滤镜的反序列化和应用。图像滤镜用于模糊、阴影、色彩调整等效果,其反序列化涉及复杂的对象图和参数验证。

## 架构位置

测试 `include/core/SkImageFilter.h` 的反序列化功能。

## 主要类与结构体

### FuzzImageFilterDeserialize 函数

```cpp
void FuzzImageFilterDeserialize(const uint8_t *data, size_t size)
```

流程:
1. 创建 24x24 位图和 canvas
2. 反序列化滤镜: `SkImageFilter::Deserialize(data, size)`
3. 应用滤镜到 paint
4. 使用滤镜渲染图像: `canvas.drawImage(..., &paint)`

### LLVMFuzzerTestOneInput

最大 10024 字节,使用可移植字体确保一致性。

## 内部实现细节

### 滤镜类型

可能反序列化的滤镜:
- SkBlurImageFilter (模糊)
- SkDropShadowImageFilter (阴影)
- SkColorFilterImageFilter (色彩)
- SkMergeImageFilter (合并)
- SkMatrixTransformImageFilter (变换)
- 组合滤镜(滤镜树)

### 安全性测试

- 验证滤镜参数范围
- 防止无限递归(滤镜树)
- 检测内存泄漏
- 验证 GPU 资源管理

## 依赖关系

- `include/effects/`: 各种图像滤镜实现
- `src/core/SkFlattenable.cpp`: 反序列化基础

## 设计模式与设计决策

**实际使用测试**: 不仅反序列化,还实际应用滤镜,确保完整功能正常。

## 性能考量

某些滤镜(如复杂模糊)计算密集,需要超时保护。

## 相关文件

- `src/effects/imagefilters/`: 滤镜实现
- `tests/ImageFilterTest.cpp`: 单元测试

该 fuzzer 发现了多个滤镜反序列化和应用中的安全问题,对 Skia 的稳定性至关重要。
