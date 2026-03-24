# SkMagnifierImageFilter

> 源文件: `src/effects/imagefilters/SkMagnifierImageFilter.cpp`

## 概述

`SkMagnifierImageFilter` 实现了放大镜图像滤镜效果,在指定的镜头边界(lensBounds)内对输入图像进行非线性放大,并在放大区域边缘通过 inset 参数产生平滑过渡。该滤镜模拟了物理放大镜的视觉效果,中心区域线性放大,边缘区域通过自定义着色器产生渐变扭曲。

## 架构位置

```
SkImageFilter (公共接口)
  └─ SkImageFilter_Base (内部基类)
       └─ SkMagnifierImageFilter (本文件)
            ├─ 输入[0]: 待放大的子滤镜
            ├─ 零 inset 快速路径: applyTransform + applyCrop
            └─ 非零 inset: SkSL 运行时效果 (kMagnifier StableKey)

工厂方法: SkImageFilters::Magnifier(lensBounds, zoomAmount, inset, sampling, input, cropRect)
```

## 主要类与结构体

### `SkMagnifierImageFilter`
- 继承自 `SkImageFilter_Base`，接收一个子滤镜输入
- **成员变量**:
  - `fLensBounds` (`skif::ParameterSpace<SkRect>`): 镜头边界(参数空间)
  - `fZoomAmount` (`float`): 放大倍数(相对值,不属于特定坐标空间)
  - `fInset` (`float`): 边缘过渡区域宽度
  - `fSampling` (`SkSamplingOptions`): 采样选项

## 公共 API 函数

### `SkImageFilters::Magnifier(lensBounds, zoomAmount, inset, sampling, input, cropRect)`
创建放大镜滤镜。验证:
- lensBounds 必须非空、有限
- zoomAmount 必须 > 0
- inset 必须 >= 0
- zoomAmount <= 1 时视为无操作,直接返回输入
- cropRect 仅应用于输入(放大镜基于子输出图像自动限制输出)

## 内部实现细节

### 缩放中心和源矩形计算
`onFilterImage()` 中的核心数学:
1. 计算镜头边界的中心作为初始缩放中心
2. 将镜头边界与期望输出取交集得到可见镜头范围
3. 估算子滤镜的预期输出范围
4. 将缩放中心限制在预期子输出内
5. 计算源矩形: `srcRect = lensBounds * invZoom + center * (1 - invZoom)`
6. 限制最大缩放量以避免半像素被放大到整个镜头

### 自适应裁剪
当放大镜与背景偏移组合使用时,子输出可能不完全覆盖可见镜头区域:
1. 将 zoomXform 映射到可见镜头范围
2. 若预期子输出足够大,通过平移调整源矩形使其完全在子输出内
3. 更新变换矩阵以反映调整后的映射

### 零 Inset 快速路径
当 inset <= 0 时,放大镜退化为简单的矩形到矩形变换:
1. 计算 zoomXform 的逆矩阵
2. 对子输出应用逆变换(从源到镜头映射)
3. 裁剪到镜头边界

### SkSL 放大着色器
`make_magnifier_shader()` 构建非线性放大着色器:
- uniform `lensBounds`: 镜头边界
- uniform `zoomXform`: 缩放变换(平移+缩放,打包为 SkV4)
- uniform `invInset`: inset 的倒数(用于边缘过渡计算)
- child `src`: 源图像着色器

### 矩阵能力限制
声明 `MatrixCapability::kScaleTranslate`。注释说明:由于 zoomAmount 是相对值,在仅支持缩放+平移的情况下,参数空间的缩放矩阵在图层空间中是无操作的,因此 layerZoom == fZoomAmount。

### 输出边界
输出为 lensBounds 与子输出的交集。若无交集则输出为空。

## 依赖关系

- `include/effects/SkRuntimeEffect.h` - 运行时着色器
- `src/core/SkKnownRuntimeEffects.h` - 内置 SkSL 效果
- `src/core/SkImageFilterTypes.h` - FilterResult 和空间类型
- `src/core/SkImageFilter_Base.h` - 滤镜基类

## 设计模式与设计决策

### 双路径实现
零 inset 使用简单变换 + 裁剪,非零 inset 使用 SkSL 着色器。这避免了为简单情况启动着色器管线的开销。

### 自适应源区域
面对不完整的子输出时,自动调整源区域的位置(而非缩放级别),确保可见区域内有有效内容。这对背景偏移等组合场景至关重要。

### 旧格式拒绝
`CreateProc` 直接拒绝旧版放大镜格式(返回 nullptr),因为 Chrome 是唯一已知客户端且不在网页中使用该滤镜。

## 性能考量

- 零 inset 快速路径避免了着色器编译和执行
- 最大缩放量限制(`2 * maxLensSize`)防止极端放大导致的精度问题
- 输入区域限制为镜头边界,避免处理不可见的像素
- `ShaderFlags::kNonTrivialSampling` 确保着色器采样时有足够边界数据
- 运行时着色器使用内置 StableKey 确保编译缓存命中

## 缩放中心自适应算法

放大镜的缩放中心选择是一个多步自适应过程:

1. **初始中心**: 镜头边界的几何中心
2. **约束到子输出**: `expectedChildOutput.clamp(zoomCenter)` 确保中心在可用图像范围内
3. **源矩形计算**: 基于中心和缩放因子计算映射关系
4. **可见区域拟合**: 若子输出不完全覆盖可见镜头:
   - 计算可见镜头对应的源矩形
   - 若子输出足够大,平移源矩形使其完全在子输出内
   - 更新变换矩阵以反映新的映射

这种自适应确保了在背景偏移、部分屏幕外等边缘情况下仍能产生合理的放大效果。

## 零 Inset 与非零 Inset 的渲染差异

**零 Inset** (简单变换路径):
```
子输出 -> 逆 zoomXform 变换 -> 裁剪到镜头边界
```
产生硬边界的放大效果,缩放区域与非缩放区域之间有明显边界。

**非零 Inset** (SkSL 着色器路径):
```
子输出 -> SkSL 着色器 -> 输出
```
着色器在镜头边缘的 inset 范围内进行插值:
- 镜头中心区域: 线性缩放(与零 inset 相同)
- 边缘 inset 区域: 非线性过渡,从缩放回到原始分辨率
- 镜头外部: 不产生输出(被边界裁剪)

## 序列化注意事项

- 旧版放大镜格式被直接拒绝(返回 nullptr),因为 Chrome 是唯一已知客户端
- 新版格式序列化: lensBounds + zoomAmount + inset + sampling + 子滤镜
- cropRect 不序列化(仅作用于输入子滤镜,通过 Crop 滤镜包裹处理)

## 矩阵能力限制的理由

该滤镜声明 `MatrixCapability::kScaleTranslate`,而非 `kComplex`:
- zoomAmount 是相对值(不属于特定坐标空间)
- 在仅缩放+平移的限制下,参数空间的缩放操作在图层空间中是无操作
- 因此 `layerZoom == fZoomAmount`,简化了计算
- 若支持旋转/倾斜,需要对 zoomAmount 进行分解,逻辑更复杂

## 相关文件

- `include/effects/SkImageFilters.h` - 工厂方法声明
- `src/core/SkKnownRuntimeEffects.h` - 内置 SkSL 效果
- `src/sksl/sksl_rt_shader.sksl` - 放大着色器的 SkSL 源码
- `src/core/SkImageFilter_Base.h` - 滤镜基类
- `src/core/SkImageFilterTypes.h` - FilterResult 和空间类型系统
