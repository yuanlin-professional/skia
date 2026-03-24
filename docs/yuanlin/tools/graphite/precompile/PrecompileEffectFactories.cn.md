# PrecompileEffectFactories

> 源文件: `tools/graphite/precompile/PrecompileEffectFactories.h`, `tools/graphite/precompile/PrecompileEffectFactories.cpp`

## 概述

PrecompileEffectFactories 是 Skia Graphite 预编译测试框架中的效果工厂模块。它提供了一组工厂函数，每个函数同时创建一个标准 API 效果对象和对应的 Precompile API 效果对象，形成配对（pair）。这些配对用于验证 Graphite 预编译系统能够正确地为运行时效果预先编译着色器管线。

Graphite 的预编译系统允许应用在实际使用前预先编译所需的着色器组合，避免运行时的着色器编译卡顿（jank）。

## 架构位置

```
Graphite 预编译测试
  +-- PrecompileFactories  (效果配对工厂) <-- 本文件
  +-- PrecompileRuntimeEffects (运行时效果预编译 API)
  +-- SkRuntimeEffect (标准运行时效果 API)
```

## 主要类与结构体

### 命名空间
`skiatest::graphite::PrecompileFactories`

### 类型别名
- `BlenderPair`: `pair<sk_sp<SkBlender>, sk_sp<PrecompileBlender>>`
- `ColorFilterPair`: `pair<sk_sp<SkColorFilter>, sk_sp<PrecompileColorFilter>>`
- `ShaderPair`: `pair<sk_sp<SkShader>, sk_sp<PrecompileShader>>`

## 公共 API 函数

### Shader 工厂

| 函数 | 说明 |
|------|------|
| `GetAnnulusShaderCode()` | 获取环形着色器 SkSL 源码 |
| `GetAnnulusShaderEffect()` | 获取/缓存环形着色器效果 |
| `CreateAnnulusRuntimeShader()` | 创建 Shader 配对 |

### Blender 工厂

| 函数 | 说明 |
|------|------|
| `GetSrcBlenderEffect()` / `CreateSrcRuntimeBlender()` | 源混合器（返回 src） |
| `GetDstBlenderEffect()` / `CreateDstRuntimeBlender()` | 目标混合器（返回 dst） |
| `GetComboBlenderEffect()` / `CreateComboRuntimeBlender()` | 组合混合器（混合 src 和 dst 子混合器） |

### ColorFilter 工厂

| 函数 | 说明 |
|------|------|
| `GetDoubleColorFilterEffect()` / `CreateDoubleRuntimeColorFilter()` | 双倍颜色过滤器（`2*c`） |
| `GetHalfColorFilterEffect()` / `CreateHalfRuntimeColorFilter()` | 半值颜色过滤器（`0.5*c`） |
| `GetComboColorFilterEffect()` / `CreateComboRuntimeColorFilter()` | 组合颜色过滤器（混合两个子过滤器） |

## 内部实现细节

### SkRuntimeEffect 缓存
所有 `Get*Effect()` 函数使用局部静态变量缓存编译后的 SkRuntimeEffect，通过 `SkMakeRuntimeEffect` 工具宏创建，避免重复编译。

### 配对创建模式
每个 `Create*` 函数遵循相同模式：
1. 获取缓存的 SkRuntimeEffect
2. 创建标准 API 对象（如 `effect->makeShader(uniforms, children)`）
3. 创建对应的 Precompile API 对象（如 `PrecompileRuntimeEffects::MakePrecompileShader(effect)`）
4. 返回 `{标准对象, 预编译对象}` 配对

### 组合效果（Combo）
组合混合器和组合颜色过滤器使用子效果作为 uniform children。例如 ComboBlender：
```
blendFrac * a.eval(src, dst) + (1 - blendFrac) * b.eval(src, dst)
```
其中 a 和 b 分别是 SrcBlender 和 DstBlender。

Precompile 版本需要传入子效果的预编译表示，确保预编译系统能够正确地展开效果图。

### 命名策略
大多数效果通过 `options.fName` 设置名称，但 HalfColorFilter 故意省略名称以测试默认名称场景。

## 依赖关系

- **Skia 核心**: `SkRuntimeEffect`, `SkShader`, `SkBlender`, `SkColorFilter`, `SkData`
- **Graphite 预编译**: `PrecompileShader`, `PrecompileBlender`, `PrecompileColorFilter`, `PrecompileRuntimeEffect`
- **内部**: `SkRuntimeEffectPriv` (SkMakeRuntimeEffect 宏)

## 设计模式与设计决策

1. **配对工厂模式**: 每个工厂同时产出标准和预编译两个对象，确保它们代表相同的效果
2. **静态缓存**: SkRuntimeEffect 通过局部静态变量缓存，线程安全且全局共享
3. **效果图测试**: 通过 Combo 效果测试具有子效果（children）的复合效果预编译
4. **缺省名称测试**: HalfColorFilter 故意省略名称，验证预编译系统对未命名效果的处理

## 性能考量

- SkRuntimeEffect 编译仅在首次调用时发生，后续调用直接复用
- 预编译对象在测试期间使用，实际预编译发生在着色器管线构建时

## 相关文件

- `include/effects/SkRuntimeEffect.h` - 运行时效果 API
- `include/gpu/graphite/precompile/PrecompileRuntimeEffect.h` - 预编译运行时效果 API
- `include/gpu/graphite/precompile/PrecompileShader.h` - 预编译 Shader
- `include/gpu/graphite/precompile/PrecompileBlender.h` - 预编译 Blender
- `include/gpu/graphite/precompile/PrecompileColorFilter.h` - 预编译 ColorFilter
