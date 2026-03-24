# BlackAndWhiteEffect - Skottie 黑白效果

> 源文件: `modules/skottie/src/effects/BlackAndWhiteEffect.cpp`

## 概述

BlackAndWhiteEffect 实现了 After Effects 中的"Black & White"（黑白）效果。该效果将彩色图像转换为灰度图像，同时允许独立控制六种基色（红、黄、绿、青、蓝、品红）对最终亮度的贡献权重。实现基于 SkRuntimeEffect 运行时颜色滤镜，通过色相六分体（Hue Hexagon）上的权重分解来计算最终亮度。

## 架构位置

该文件位于 Skottie 效果子系统中（`skottie::internal` 命名空间），使用 `DiscardableAdapterBase` 将 Lottie 属性映射到 `sksg::ExternalColorFilter` 场景图节点。

```
AnimationBuilder
  └── EffectBuilder::attachBlackAndWhiteEffect()
        └── BlackAndWhiteAdapter (DiscardableAdapterBase)
              └── sksg::ExternalColorFilter
                    └── SkRuntimeEffect (颜色滤镜)
```

## 主要类与结构体

### `BlackAndWhiteAdapter`
- 继承自 `DiscardableAdapterBase<BlackAndWhiteAdapter, sksg::ExternalColorFilter>`
- 持有一个预编译的 `SkRuntimeEffect` 实例
- 管理 6 个标量动画属性（`fCoeffs[6]`），分别对应 R/Y/G/C/B/M 六种颜色的权重

### 属性索引枚举
- `kReds_Index = 0`
- `kYellows_Index = 1`
- `kGreens_Index = 2`
- `kCyans_Index = 3`
- `kBlues_Index = 4`
- `kMagentas_Index = 5`
- TODO：`kTint_Index = 6` 和 `kTintColor_Index = 7` 尚未实现

## 公共 API 函数

### `EffectBuilder::attachBlackAndWhiteEffect()`
```cpp
sk_sp<sksg::RenderNode> EffectBuilder::attachBlackAndWhiteEffect(
    const skjson::ArrayValue& jprops, sk_sp<sksg::RenderNode> layer) const;
```
- **功能**：将黑白效果附加到目标图层

## 内部实现细节

### SkSL 颜色滤镜着色器

```glsl
uniform half kR, kY, kG, kC, kB, kM;

half4 main(half4 c) {
    half m = min(min(c.r, c.g), c.b);

    half dr = c.r - m, dg = c.g - m, db = c.b - m;

    // 二次色权重
    half wy = min(dr, dg);  // 黄 = min(R过量, G过量)
    half wc = min(dg, db);  // 青 = min(G过量, B过量)
    half wm = min(db, dr);  // 品红 = min(B过量, R过量)

    // 原色权重
    half wr = dr - wy - wm;  // 红
    half wg = dg - wy - wc;  // 绿
    half wb = db - wc - wm;  // 蓝

    // 最终亮度
    half l = m + kR*wr + kY*wy + kG*wg + kC*wc + kB*wb + kM*wm;
    return half4(l, l, l, c.a);
}
```

### 色相六分体算法

该算法是本实现的核心，灵感来自信号处理领域的黑白滤镜实现：

1. **提取最小分量** `m`：作为灰度基底
2. **计算色差** `dr, dg, db`：每个分量超出最小值的部分
3. **二次色权重**：通过相邻原色差值的最小值确定（黄=min(dr,dg)，青=min(dg,db)，品红=min(db,dr)）
4. **原色权重**：从色差中减去二次色贡献后的剩余

关键数学性质：
- 至少一个 `(dr, dg, db)` 为 0（因为 m 是最小值）
- 至少两个原色权重和两个二次色权重为 0
- 这相当于在色相六分体上无分支地选择了当前颜色所在的扇区

### onSync 方法

将 6 个系数从百分比归一化为 [0, 1] 范围，打包为结构体通过 `SkData::MakeWithCopy` 传递给运行时效果：

```cpp
struct { float normalized_coeffs[6]; } coeffs = {
    fCoeffs[0] / 100, fCoeffs[1] / 100, ..., fCoeffs[5] / 100
};
```

### 效果编译（make_effect）

使用单例模式缓存编译后的 `SkRuntimeEffect`：
```cpp
static const SkRuntimeEffect* effect =
    SkRuntimeEffect::MakeForColorFilter(SkString(BLACK_AND_WHITE_EFFECT)).effect.release();
```

## 依赖关系

- **Skia 核心**：`SkData`
- **Skia 效果**：`SkRuntimeEffect`（运行时颜色滤镜）
- **Skottie 内部**：`Adapter.h`（`DiscardableAdapterBase`）、`Effects.h`（`EffectBinder`）
- **SkSG**：`SkSGColorFilter.h`（`ExternalColorFilter`）

## 设计模式与设计决策

1. **无分支色相分解**：通过 min/max 运算代替条件判断实现色相扇区选择，非常适合 GPU 着色器的 SIMD 执行模型。

2. **运行时颜色滤镜**：使用 `SkRuntimeEffect::MakeForColorFilter` 而非 `MakeForShader`，因为黑白效果是纯粹的逐像素颜色变换。

3. **效果单例**：SkSL 编译开销较大，通过静态局部变量确保只编译一次。

4. **结构化 uniform 传递**：将 6 个系数打包为连续内存块，通过 `SkData::MakeWithCopy` 一次性设置所有 uniform。

5. **未完成的功能**：Tint 和 TintColor 参数已预留索引但尚未实现，留有扩展空间。

## 性能考量

- SkSL 着色器在 GPU 上逐像素并行执行，无分支操作确保了 SIMD 效率
- 运行时效果通过单例模式缓存，避免重复编译
- 仅在属性变化时重新创建颜色滤镜（通过 DiscardableAdapterBase 的失效检测）
- 6 个 uniform 值通过单次 `SkData::MakeWithCopy` 传递，最小化内存分配
- `ExternalColorFilter` 节点利用场景图的失效传播机制避免不必要的重绘

## 补充说明

### 色相六分体权重分解示例

以纯黄色 `(1.0, 1.0, 0.0)` 为例：
- `m = min(1, 1, 0) = 0`
- `dr = 1, dg = 1, db = 0`
- `wy = min(1, 1) = 1`（黄色权重 = 1）
- `wc = min(1, 0) = 0`
- `wm = min(0, 1) = 0`
- `wr = 1 - 1 - 0 = 0`
- `wg = 1 - 1 - 0 = 0`
- `wb = 0 - 0 - 0 = 0`
- 最终亮度 = `0 + kY * 1`，即完全由黄色系数控制

### 中间色处理

对于非纯色（如橙色 `(1.0, 0.5, 0.0)`）：
- `m = 0, dr = 1, dg = 0.5, db = 0`
- `wy = min(1, 0.5) = 0.5`（50% 黄色权重）
- `wr = 1 - 0.5 - 0 = 0.5`（50% 红色权重）
- 最终亮度 = `kR * 0.5 + kY * 0.5`

这种分解确保了颜色之间的平滑过渡。

### 未实现功能

代码中预留了 Tint（着色）功能的属性索引：
- `kTint_Index = 6`：着色强度
- `kTintColor_Index = 7`：着色颜色

着色功能会在灰度输出上叠加一个色调偏移，类似于照片中的棕褐色调效果。

## 相关文件

- `modules/skottie/src/effects/Effects.h` - EffectBuilder 定义
- `modules/skottie/src/Adapter.h` - DiscardableAdapterBase 基类
- `include/effects/SkRuntimeEffect.h` - SkRuntimeEffect API
- `modules/sksg/include/SkSGColorFilter.h` - ExternalColorFilter 节点
- `modules/skottie/src/effects/TritoneEffect.cpp` - 另一个颜色风格化效果
- `modules/skottie/src/effects/BrightnessContrastEffect.cpp` - 另一个使用 SkRuntimeEffect 的颜色效果
