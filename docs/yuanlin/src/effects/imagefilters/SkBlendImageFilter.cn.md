# SkBlendImageFilter

> 源文件: `src/effects/imagefilters/SkBlendImageFilter.cpp`

## 概述

`SkBlendImageFilter` 实现了图像滤镜层面的混合(Blend)操作,将背景和前景两个输入图像滤镜的结果通过指定的混合模式或自定义混合器(Blender)进行合成。该滤镜支持标准的 Porter-Duff 混合模式、高级混合模式、自定义运行时混合器以及算术混合(Arithmetic Blending),是 Skia 图像合成管线的核心组件。

## 架构位置

```
SkImageFilter (公共接口)
  └─ SkImageFilter_Base (内部基类)
       └─ SkBlendImageFilter (本文件)
            ├─ 输入[0]: 背景 (kBackground)
            ├─ 输入[1]: 前景 (kForeground)
            └─ 混合方式: SkBlender / SkBlendMode / Arithmetic

工厂方法:
  SkImageFilters::Blend(SkBlendMode, ...)
  SkImageFilters::Blend(sk_sp<SkBlender>, ...)
  SkImageFilters::Arithmetic(k1, k2, k3, k4, ...)
```

## 主要类与结构体

### `SkBlendImageFilter`
- 继承自 `SkImageFilter_Base`,接收两个输入滤镜
- **成员变量**:
  - `fBlender` (`sk_sp<SkBlender>`): 混合器对象,非空(src-over 也用显式 blender 表示)
  - `fArithmeticCoefficients` (`std::optional<SkV4>`): 算术混合系数 (k1, k2, k3, k4),仅用于 Arithmetic 变体
  - `fEnforcePremul` (`bool`): 是否强制预乘 alpha(仅 Arithmetic 变体序列化需要)

### `make_blend()` (内部辅助函数)
统一的创建函数,处理以下优化:
- `kSrc` 模式 -> 直接返回前景(加裁剪)
- `kDst` 模式 -> 直接返回背景(加裁剪)
- `kClear` 模式 -> 返回 `SkImageFilters::Empty()`

## 公共 API 函数

### `SkImageFilters::Blend(SkBlendMode, background, foreground, cropRect)`
使用标准混合模式创建混合滤镜。

### `SkImageFilters::Blend(sk_sp<SkBlender>, background, foreground, cropRect)`
使用自定义混合器创建混合滤镜。null 混合器被转换为 `kSrcOver`。

### `SkImageFilters::Arithmetic(k1, k2, k3, k4, enforcePMColor, background, foreground, cropRect)`
创建算术混合滤镜,公式为: `result = k1*FG*BG + k2*FG + k3*BG + k4`。内部使用 `SkBlenders::Arithmetic` 创建运行时混合器,同时保存系数用于边界分析和序列化。

## 内部实现细节

### 滤镜核心逻辑
`onFilterImage()` 的工作流程:
1. 通过 `onGetOutputLayerBounds()` 预计算最大可能输出,限制两个子滤镜的求值范围
2. 将最大输出与期望输出取交集
3. 收集背景和前景子滤镜输出
4. 使用 `FilterResult::Builder::eval()` 回调调用 `makeBlendShader()`

### 智能混合着色器创建
`makeBlendShader()` 处理了 null 着色器的情况:
- 两个输入均为 null 且不影响透明黑色 -> 返回 null(跳过求值)
- 仅一个输入为 null,且混合系数允许 -> 直接返回非 null 的那个着色器
- 否则用 `SkShaders::Color(SK_ColorTRANSPARENT)` 替换 null 着色器

### 精确的输出边界分析
`onGetOutputLayerBounds()` 包含详尽的六种输出边界情况分析:
1. **无输出**: k=(0,0,0,0) 或 (kZero, kZero)
2. **交集(FG∩BG)**: k=(非零,0,0,0) 或 (kZero|kDA, kZero|kSA)
3. **仅前景**: k=(0,非零,0,0) 或 src 系数非零且 dst 为零
4. **仅背景**: k=(0,0,非零,0) 或 dst 系数非零且 src 为零
5. **并集(FG∪BG)**: 高级混合模式或两者系数都非零
6. **无限**: k=(任意,任意,任意,非零) 或非算术运行时混合器

### 序列化格式
使用三种标记值区分混合类型:
- 标准混合模式: 直接写入 `SkBlendMode` 枚举值
- 算术混合: 写入 `kArithmetic_SkBlendMode` 哨兵值,后跟 k1-k4 系数和 enforcePremul
- 自定义混合器: 写入 `kCustom_SkBlendMode`,后跟 blender flattenable 数据

### 向后兼容
注册了多个旧名称的反序列化回调:
- `SkXfermodeImageFilter_Base`, `SkXfermodeImageFilterImpl` (旧版混合)
- `ArithmeticImageFilterImpl`, `SkArithmeticImageFilter` (旧版算术混合)

## 依赖关系

- `include/core/SkBlendMode.h` / `SkBlender.h` - 混合模式和混合器
- `include/effects/SkBlenders.h` - `SkBlenders::Arithmetic` 工厂方法
- `src/core/SkBlendModePriv.h` - `SkBlendMode_AsCoeff` 系数分解
- `src/core/SkBlenderBase.h` - `as_BB()` 内部转换
- `src/core/SkImageFilterTypes.h` - FilterResult 和空间类型
- `src/core/SkRectPriv.h` - 无限边界工具

## 设计模式与设计决策

### 统一混合抽象
所有混合操作(Porter-Duff、高级混合、算术、自定义)统一为 `SkBlender` 接口,简化了内部处理逻辑。算术系数额外保存用于更精确的边界分析。

### 创建时优化
工厂方法中对 `kSrc`/`kDst`/`kClear` 三种退化情况进行了优化,避免创建不必要的混合滤镜。

### 边界精度与可检查性的权衡
- Porter-Duff 模式:通过系数分解精确确定边界
- 算术混合:通过系数分析精确确定边界
- 高级混合:利用 alpha 通道为 src-over 的特性,推断为并集边界
- 自定义运行时混合器:悲观估计为无限边界

## 性能考量

- 边界预计算可以限制子滤镜的求值范围,减少不必要的像素处理
- `makeBlendShader` 中的 null 着色器优化避免了不必要的混合计算
- `computeFastBounds()` 的逻辑与 `onGetOutputLayerBounds()` 重复(代码注释中标注了这一技术债务)
- 对于简单混合模式,系数分析路径是轻量级的 O(1) 操作
- 算术混合系数的保存使得边界分析不需要运行时检查 blender 的行为
- Porter-Duff 系数分解通过 `SkBlendMode_AsCoeff` 实现,覆盖 12 种标准混合模式

## 混合模式分类与边界行为

| 混合模式类型 | 透明黑色影响 | 输出边界 | 示例 |
|------------|------------|---------|------|
| kSrc/kDst/kClear | - | 创建时优化为简单滤镜 | - |
| Porter-Duff (两系数零) | 否 | 有界 | kSrcIn, kDstIn |
| Porter-Duff (一系数零) | 否 | 前景或背景之一 | kSrcATop, kDstATop |
| Porter-Duff (两系数非零) | 否 | 前景和背景并集 | kSrcOver, kScreen |
| 高级混合 | 否 | 前景和背景并集 | kOverlay, kMultiply |
| Arithmetic (k3=0) | 否 | 取决于 k1,k2,k3 | k1*FG*BG+k2*FG+k3*BG |
| Arithmetic (k3!=0) | 是 | 无界 | 全局偏移 |
| 自定义运行时 | 是 | 无界 | 任意 SkSL |

## 版本兼容性

该滤镜经历了多次名称和格式变更:
- `SkXfermodeImageFilter_Base` / `SkXfermodeImageFilterImpl` -> 统一为 `SkBlendImageFilter`
- `ArithmeticImageFilterImpl` / `SkArithmeticImageFilter` -> 合并到 Blend 的 Arithmetic 变体
- 版本 `kCombineBlendArithmeticFilters` 标记了新旧格式的分界

## 创建时优化总结

工厂方法 `make_blend()` 在创建时执行以下优化:
- `kSrc` -> 直接返回前景滤镜(+ 可选裁剪)
- `kDst` -> 直接返回背景滤镜(+ 可选裁剪)
- `kClear` -> 返回 `SkImageFilters::Empty()`
- null blender -> 转换为 `SkBlender::Mode(kSrcOver)`

这些优化避免了为退化情况创建不必要的滤镜节点。

## 相关文件

- `include/effects/SkImageFilters.h` - 工厂方法声明
- `include/effects/SkBlenders.h` - 算术混合器工厂
- `src/core/SkBlendModePriv.h` - 混合模式系数分析
- `src/core/SkImageFilter_Base.h` - 滤镜基类
- `src/core/SkImageFilterTypes.h` - FilterResult 和空间类型系统
