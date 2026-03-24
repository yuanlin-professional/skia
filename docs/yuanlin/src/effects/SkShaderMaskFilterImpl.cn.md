# SkShaderMaskFilterImpl - 着色器遮罩滤镜

> 源文件: `src/effects/SkShaderMaskFilterImpl.h`, `src/effects/SkShaderMaskFilterImpl.cpp`

## 概述

SkShaderMaskFilterImpl 是 SkShaderMaskFilter 的具体实现类。它将一个 SkShader 应用为遮罩滤镜，通过 SrcIn 混合模式将着色器输出与已有的 alpha 遮罩相乘。这允许用渐变、图像或任意着色器来调制文本或形状的透明度。

## 架构位置

```
SkMaskFilter (公共接口)
  └── SkMaskFilterBase (内部基类)
        └── SkShaderMaskFilterImpl (着色器遮罩滤镜)

SkShaderMaskFilter (公共工厂类)
```

- **类型标识**: `SkMaskFilterBase::Type::kShader`
- **公共 API**: `SkShaderMaskFilter::Make(sk_sp<SkShader>)`

## 主要类与结构体

### SkShaderMaskFilterImpl
**成员变量**:
- `fShader` (sk_sp<SkShader>): 关联的着色器

**方法**:
- `getFormat()` — 返回 `SkMask::kA8_Format`
- `filterMask()` — 应用着色器到遮罩
- `computeFastBounds()` — 边界不变（*dst = src）
- `asABlur()` — 返回 false（不是模糊滤镜）
- `asImageFilter()` — 转换为图像滤镜表示
- `shader()` — 获取关联着色器

## 公共 API 函数

```cpp
static sk_sp<SkMaskFilter> SkShaderMaskFilter::Make(sk_sp<SkShader> shader);
```
创建着色器遮罩滤镜。shader 为 nullptr 时返回 nullptr。

## 内部实现细节

### filterMask
1. 仅接受 A8 格式输入
2. 分配目标遮罩并拷贝源遮罩的 alpha 数据
3. 在 alpha 数据上创建 SkBitmap（A8 格式）
4. 创建带着色器的 SkPaint，使用 `SkBlendMode::kSrcIn`
5. 在位图上创建 SkCanvas
6. 应用 CTM 变换并调用 `drawPaint`

**核心技巧**: `SkBlendMode::kSrcIn` 使得着色器仅在遮罩已有覆盖的区域绘制，实现 alpha 调制效果。

### asImageFilter
转换为 `SkImageFilters::Blend(kDstIn, shader_filter, nullptr)` 表示。返回的 bool 为 false 表示不影响着色属性。

### rect_memcpy
辅助函数，按行拷贝矩形区域（处理不同 rowBytes 的情况）。

### 序列化
- `flatten`: 写入 fShader
- `CreateProc`: 读取 shader 并调用 Make

### Flattenable 注册
同时注册当前名称 "SkShaderMaskFilterImpl" 和旧名称 "SkShaderMF"。

## 依赖关系

- `SkMaskFilterBase` — 遮罩滤镜基类
- `SkShader` — 着色器接口
- `SkCanvas` — 绘制着色器到遮罩
- `SkBitmap` — A8 位图包装
- `SkImageFilters` — asImageFilter 转换
- `SkBlendMode` — SrcIn / DstIn 混合模式

## 设计模式与设计决策

1. **SrcIn 混合**: 巧妙利用混合模式实现着色器与遮罩的 alpha 调制
2. **Canvas 绘制**: 通过在遮罩上创建 Canvas 来执行着色器，复用了 Skia 的完整绘制管线
3. **向后兼容**: 注册旧名称 "SkShaderMF" 确保旧 SKP 文件能正确反序列化

## 性能考量

- filterMask 需要创建临时 Canvas 和位图，有一定的初始化开销
- 着色器绘制复用 Skia 管线，性能取决于着色器的复杂度
- computeFastBounds 直接传递边界（着色器不改变几何范围）

## 相关文件

- `include/effects/SkShaderMaskFilter.h` — 公共 API
- `src/core/SkMaskFilterBase.h` — 遮罩滤镜基类
- `include/core/SkShader.h` — 着色器接口
- `include/effects/SkImageFilters.h` — 图像滤镜
