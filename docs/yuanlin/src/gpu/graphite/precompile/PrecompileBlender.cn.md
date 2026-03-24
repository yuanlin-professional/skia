# PrecompileBlender

> 源文件: include/gpu/graphite/precompile/PrecompileBlender.h, src/gpu/graphite/precompile/PrecompileBlender.cpp

## 概述

`PrecompileBlender` 是 Skia Graphite 预编译系统中表示混合器（Blender）的抽象类，对应运行时 API 中的 `SkBlender` 类。它封装了各种混合操作的预编译变体，包括基于 `SkBlendMode` 的简单混合、算术混合以及自定义运行时效果混合器。该模块是预编译绘制管线的关键组件之一。

主要功能：
- 提供混合器的抽象表示
- 支持 SkBlendMode 模式混合
- 支持算术混合（Arithmetic）
- 管理 Porter-Duff、HSLC 和其他混合模式的合并优化
- 生成混合器的 Key 用于着色器代码查找

## 架构位置

`PrecompileBlender` 在预编译系统中的位置：

```
预编译层次：
PrecompileBase (基类)
    ├── PrecompileShader
    ├── PrecompileColorFilter
    ├── PrecompileBlender (本模块)
    └── PrecompileImageFilter

使用流程：
Client → PrecompileBlenders::Mode/Arithmetic → PrecompileBlender
                                                      ↓
                                            PaintOptions::setBlenders
                                                      ↓
                                            buildCombinations
                                                      ↓
                                            AddBlendMode(keyContext)
```

## 主要类与结构体

### PrecompileBlender

混合器预编译抽象基类。

**继承关系**
```
PrecompileBase (基类)
    ↑
PrecompileBlender (本模块)
    ↑
PrecompileBlendModeBlender (内部实现类)
```

**关键成员**
- 无额外成员变量（继承自 `PrecompileBase`）
- 虚函数 `asBlendMode()` 用于提取简单混合模式

### PrecompileBlendModeBlender

实现 SkBlendMode 混合的内部类。

**继承关系**
- 继承自 `PrecompileBlender`

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fBlendMode` | `SkBlendMode` | 具体的混合模式 |

### PrecompileBlenderList

管理多个混合器选项的辅助类。

**继承关系**
- 独立类，无继承

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fHasPorterDuffBlender` | `bool` | 是否包含 Porter-Duff 混合 |
| `fHasHSLCBlender` | `bool` | 是否包含 HSLC 混合 |
| `fFixedBlenderEffects` | `std::vector<sk_sp<PrecompileBlender>>` | 固定混合效果列表 |
| `fNumCombos` | `int` | 总组合数 |

## 公共 API 函数

### PrecompileBlender 类

**类型查询**
```cpp
PrecompileBlenderPriv priv();
const PrecompileBlenderPriv priv() const;
```
提供私有接口访问。

### PrecompileBlenders 命名空间

**工厂函数**

```cpp
sk_sp<PrecompileBlender> Mode(SkBlendMode blendMode);
```
创建基于 SkBlendMode 的混合器预编译对象。

```cpp
sk_sp<PrecompileBlender> Arithmetic();
```
创建算术混合器的预编译对象（对应 `SkBlenders::Arithmetic`）。

## 内部实现细节

### PrecompileBlendModeBlender 实现

**混合模式提取**：
```cpp
std::optional<SkBlendMode> asBlendMode() const final {
    return fBlendMode;
}
```

**Key 生成**：
```cpp
void addToKey(const KeyContext& keyContext, int desiredCombination) const final {
    SkASSERT(desiredCombination == 0); // 混合模式只有一个组合
    AddBlendMode(keyContext, fBlendMode);
}
```

### 算术混合器实现

```cpp
sk_sp<PrecompileBlender> PrecompileBlenders::Arithmetic() {
    const SkRuntimeEffect* arithmeticEffect =
            GetKnownRuntimeEffect(SkKnownRuntimeEffects::StableKey::kArithmetic);

    return PrecompileRuntimeEffects::MakePrecompileBlender(sk_ref_sp(arithmeticEffect));
}
```
使用内置的运行时效果实现算术混合。

### PrecompileBlenderList 构造逻辑

**从 PrecompileBlender 列表构造**：
```cpp
PrecompileBlenderList::PrecompileBlenderList(SkSpan<const sk_sp<PrecompileBlender>> blenders) {
    for (const auto& b : blenders) {
        if (!b) {
            // null 等价于 kSrcOver
            fHasPorterDuffBlender = true;
        } else if (b->priv().asBlendMode().has_value()) {
            SkBlendMode bm = b->priv().asBlendMode().value();

            SkSpan<const float> coeffs = skgpu::GetPorterDuffBlendConstants(bm);
            if (!coeffs.empty()) {
                // Porter-Duff 模式（可用固定系数表示）
                fHasPorterDuffBlender = true;
            } else if (bm >= SkBlendMode::kHue) {
                // HSLC 模式（Hue, Saturation, Color, Luminosity）
                fHasHSLCBlender = true;
            } else {
                // 其他固定混合模式（无简化片段）
                fFixedBlenderEffects.push_back(b);
                fNumCombos++;
            }
        } else {
            // 运行时混合器（总是固定的）
            fFixedBlenderEffects.push_back(b);
            fNumCombos += b->priv().numCombinations();
        }
    }

    // 确保至少有一个混合器（默认 Porter-Duff）
    if (!fHasPorterDuffBlender && !fHasHSLCBlender && fFixedBlenderEffects.empty()) {
        fHasPorterDuffBlender = true;
    }

    if (fHasPorterDuffBlender) fNumCombos++;
    if (fHasHSLCBlender) fNumCombos++;
}
```

**混合模式分类**：
- **Porter-Duff**：可用固定系数表示的模式（kSrcOver, kDstOver, kSrc, kDst 等）
- **HSLC**：基于色调/饱和度/颜色/亮度的模式（kHue, kSaturation, kColor, kLuminosity）
- **固定模式**：其他不可简化的混合模式（kPlus, kModulate, kScreen 等）
- **运行时混合器**：自定义 RuntimeEffect 混合器

### 选项选择算法

```cpp
std::pair<sk_sp<PrecompileBlender>, int> PrecompileBlenderList::selectOption(
        int desiredCombination) const {
    SkASSERT(desiredCombination >= 0 && desiredCombination < this->numCombinations());

    if (fHasPorterDuffBlender) {
        if (desiredCombination == 0) {
            // 使用 kSrcOver 作为 Porter-Duff 代表
            return {PrecompileBlenders::Mode(SkBlendMode::kSrcOver), 0};
        } else {
            desiredCombination--;
        }
    }

    if (fHasHSLCBlender) {
        if (desiredCombination == 0) {
            // 使用 kHue 作为 HSLC 代表
            return {PrecompileBlenders::Mode(SkBlendMode::kHue), 0};
        } else {
            desiredCombination--;
        }
    }

    if (!fFixedBlenderEffects.empty()) {
        auto [option, childCombination] =
                PrecompileBase::SelectOption<PrecompileBlender>(fFixedBlenderEffects,
                                                                desiredCombination);
        return {option, childCombination};
    }

    SkUNREACHABLE;
}
```

### 混合模式合并策略

多个 Porter-Duff 模式合并为一个组合，因为它们在着色器中使用相同的代码路径，只是系数不同：

```
输入：{ kSrcOver, kDstOver, kSrc, kDst, kSrcIn, ... }
         ↓ 合并
输出：{ [Porter-Duff Group], [HSLC Group], [Fixed Modes] }
```

这种合并显著减少了需要编译的着色器变体数量。

## 依赖关系

**依赖的模块**

| 模块 | 用途 |
|------|------|
| `PrecompileBase` | 预编译基类 |
| `SkRuntimeEffect` | 运行时效果支持 |
| `PrecompileRuntimeEffect` | 运行时效果预编译 |
| `SkKnownRuntimeEffects` | 内置运行时效果 |
| `KeyHelpers` | Key 生成辅助函数 |
| `Blend` | 混合模式常量和工具 |
| `PaintParams` | 绘制参数 |

**被依赖的模块**

- `PaintOptions`：管理混合器选项
- `PrecompileColorFilter`：某些颜色滤镜内部使用混合器
- `PrecompileShader`：某些着色器可能包含混合操作

## 设计模式与设计决策

### 策略模式

`PrecompileBlender` 作为抽象策略，不同的子类（BlendMode、Arithmetic、RuntimeEffect）实现不同的混合策略。

### 工厂模式

`PrecompileBlenders` 命名空间提供工厂函数，隐藏具体实现类：
```cpp
PrecompileBlenders::Mode(SkBlendMode::kSrcOver)  // 返回 PrecompileBlendModeBlender
PrecompileBlenders::Arithmetic()                  // 返回 RuntimeEffect 混合器
```

### 组合优化策略

通过 `PrecompileBlenderList` 将相似的混合模式分组，减少着色器变体：
- Porter-Duff 组：使用相同着色器代码，不同 uniform
- HSLC 组：使用相同着色器代码
- 固定模式：各自独立的着色器代码

### 空对象模式

`nullptr` 被解释为默认混合器（kSrcOver），简化客户端代码。

### 类型提取模式

`asBlendMode()` 方法允许从抽象类型中提取具体的 BlendMode，用于优化路径。

### 组合数计算

每个混合器类型只有一个组合（desiredCombination 总是 0），简化了组合管理。

## 性能考量

### 着色器变体减少

通过合并 Porter-Duff 和 HSLC 模式，将 30+ 个混合模式减少到约 3-5 个着色器变体。

### 内联 Key 生成

`AddBlendMode` 是内联函数，直接写入 Key 缓冲区，避免函数调用开销。

### 智能指针优化

使用 `sk_sp` 管理生命周期，避免不必要的引用计数操作。

### 编译时常量

混合模式枚举是编译时常量，允许编译器优化 switch 语句。

### 运行时效果缓存

`GetKnownRuntimeEffect` 返回缓存的 RuntimeEffect 实例，避免重复解析和编译。

### 调试断言

使用 `SkASSERT(desiredCombination == 0)` 在调试版本验证，生产版本无开销。

### 向量预留

`PrecompileBlenderList` 构造时预估空间，减少动态扩容。

### 跳过空检查

`if (!b)` 快速处理 null 情况，避免虚函数调用。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `include/gpu/graphite/precompile/PrecompileBase.h` | 基类 | 预编译基类定义 |
| `src/gpu/graphite/precompile/PrecompileBlenderPriv.h` | 相关 | 私有访问接口 |
| `include/gpu/graphite/precompile/PrecompileRuntimeEffect.h` | 依赖 | 运行时效果预编译 |
| `src/core/SkKnownRuntimeEffects.h` | 依赖 | 内置运行时效果 |
| `src/gpu/Blend.h` | 依赖 | 混合模式工具 |
| `src/gpu/graphite/KeyHelpers.h` | 依赖 | Key 生成辅助 |
| `include/gpu/graphite/precompile/PaintOptions.h` | 使用方 | 绘制选项管理 |
| `include/effects/SkRuntimeEffect.h` | 依赖 | 运行时效果基础 |
