# SkMatrixTransformImageFilter

> 源文件: `src/effects/imagefilters/SkMatrixTransformImageFilter.cpp`

## 概述

`SkMatrixTransformImageFilter` 实现了对图像滤镜输出应用矩阵变换的功能。它对子滤镜的输出图像施加一个参数空间的变换矩阵,并使用指定的采样选项进行重采样。该滤镜也是 `SkImageFilters::Offset()` 的底层实现,偏移操作被转化为平移矩阵变换。

## 架构位置

```
SkImageFilter (公共接口)
  └─ SkImageFilter_Base (内部基类)
       └─ SkMatrixTransformImageFilter (本文件)
            └─ 输入[0]: 待变换的子滤镜

工厂方法:
  SkImageFilters::MatrixTransform(matrix, sampling, input)
  SkImageFilters::Offset(dx, dy, input, cropRect)  // 委托给 MatrixTransform
```

## 主要类与结构体

### `SkMatrixTransformImageFilter`
- 继承自 `SkImageFilter_Base`,接收一个子滤镜输入
- **成员变量**:
  - `fTransform` (`skif::ParameterSpace<SkMatrix>`): 参数空间中的变换矩阵
  - `fSampling` (`SkSamplingOptions`): 重采样选项
- **构造时优化**: 预调用 `getType()` 缓存矩阵类型信息,确保后续多线程调用的安全性

## 公共 API 函数

### `SkImageFilters::MatrixTransform(transform, sampling, input) -> sk_sp<SkImageFilter>`
创建矩阵变换滤镜。若矩阵不可逆则返回 nullptr。

### `SkImageFilters::Offset(dx, dy, input, cropRect) -> sk_sp<SkImageFilter>`
创建偏移滤镜。内部实现为:
1. 创建 `SkMatrix::Translate(dx, dy)` 的 MatrixTransform(使用最近邻采样)
2. 若提供了 cropRect,在外层包裹 Crop 滤镜

## 内部实现细节

### 滤镜核心逻辑
`onFilterImage()` 的工作流程:
1. 计算所需输入区域(通过逆变换期望输出)
2. 获取子滤镜在所需区域的输出
3. 将参数空间变换映射到图层空间
4. 调用 `childOutput.applyTransform(context, transform, fSampling)`

### 输入区域计算
`requiredInput()` 方法:
1. 将 `fTransform` 映射到图层空间
2. 对期望输出应用逆变换,得到所需输入矩形
3. 若采样不是最近邻,额外扩展 1 像素(为双线性/双三次核提供边缘数据)

### 输出边界计算
`onGetOutputLayerBounds()`:
- 获取子滤镜的输出边界
- 使用图层空间变换映射该边界
- 若子输出无界,则变换后也无界

### 序列化兼容性
注册了多个旧名称的反序列化:
- `SkMatrixImageFilter` (旧版矩阵滤镜名)
- `SkOffsetImageFilter` / `SkOffsetImageFilterImpl` (旧版偏移滤镜)
- `LegacyOffsetCreateProc` 处理旧格式的偏移数据(SkPoint)

### 采样版本兼容
旧版 SKP 使用 FilterQuality,新版使用 `SkSamplingOptions`。`CreateProc` 根据版本号选择正确的反序列化方式。

## 依赖关系

- `include/core/SkMatrix.h` - 变换矩阵
- `include/core/SkSamplingOptions.h` - 采样选项
- `src/core/SkImageFilterTypes.h` - FilterResult 和空间类型
- `src/core/SkImageFilter_Base.h` - 滤镜基类
- `src/core/SkSamplingPriv.h` - 采样选项版本兼容转换
- `src/core/SkPicturePriv.h` - SKP 版本常量

## 设计模式与设计决策

### 变换组合
变换矩阵存储在参数空间中,在 `onFilterImage()` 时通过 `mapping.paramToLayer()` 映射到图层空间。这确保了变换正确地响应画布的 CTM。

### Offset 作为 MatrixTransform 的特例
将偏移操作统一为平移矩阵变换,减少了代码重复和维护负担。偏移使用最近邻采样以匹配历史行为(旧版实现会四舍五入到像素)。

### 矩阵能力
声明 `MatrixCapability::kComplex`,支持任意复杂变换。这是因为该滤镜本身就是处理变换的,无论 CTM 多复杂都能正确处理。

### 可逆性检查
工厂方法中要求变换矩阵可逆,因为 `requiredInput()` 需要逆变换来计算所需输入区域。

## 性能考量

- 采样选项选择影响质量/性能平衡:最近邻最快但有锯齿,双线性/双三次更平滑但需要额外像素
- 非最近邻采样时额外请求 1 像素边界,确保核函数有足够数据
- 变换矩阵类型在构造时预缓存(`getType()`),避免运行时竞争
- `applyTransform` 可能延迟实际变换到最终绘制时,与其他操作合并

## Offset 与 MatrixTransform 的关系

`SkImageFilters::Offset(dx, dy, input, cropRect)` 的实现等价于:
```
MatrixTransform(Translate(dx, dy), kNearest, input) + 可选 Crop(cropRect)
```

关键决策:
- **使用最近邻采样**: 匹配旧版 Offset 的历史行为(旧版实现会将偏移向量四舍五入到图层空间像素)
- **cropRect 仅作用于输出**: 旧版 cropRect 语义是限制偏移后的输出范围

## 版本兼容性

- `SkMatrixImageFilter` -> 重命名为 `SkMatrixTransformImageFilter`
- `SkOffsetImageFilter` / `SkOffsetImageFilterImpl` -> 统一为 MatrixTransform 的平移特例
- 采样选项从 FilterQuality 枚举迁移到 SkSamplingOptions (`kMatrixImageFilterSampling_Version`)
- `LegacyOffsetCreateProc` 处理旧版偏移格式(存储为 SkPoint)

## 边界计算详解

输入边界计算链:
```
desiredOutput
  -> inverseTransform(desiredOutput)     // 逆变换得到所需输入区域
  -> outset(1, 1)                        // 非最近邻采样的额外像素
  -> getChildInputLayerBounds(...)       // 递归到子滤镜
```

输出边界计算链:
```
contentBounds
  -> getChildOutputLayerBounds(...)      // 子滤镜的输出
  -> transform(childOutput)             // 正向变换得到最终输出
```

## 构造时预缓存

构造函数中的关键行:
```cpp
(void) static_cast<const SkMatrix&>(fTransform).getType();
```
强制计算并缓存矩阵类型标志。这是因为 `SkMatrix::getType()` 内部使用延迟计算模式,首次调用会写入缓存字段。在多线程环境中,如果不预缓存,多个线程同时首次调用 `getType()` 可能产生数据竞争。

## 相关文件

- `include/effects/SkImageFilters.h` - 工厂方法声明
- `src/core/SkImageFilter_Base.h` - 滤镜基类
- `src/core/SkImageFilterTypes.h` - FilterResult 和空间类型系统
- `src/effects/imagefilters/SkCropImageFilter.cpp` - Offset 使用的裁剪滤镜
- `src/core/SkPicturePriv.h` - SKP 版本常量
