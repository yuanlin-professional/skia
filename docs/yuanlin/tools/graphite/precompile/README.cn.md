# tools/graphite/precompile - Graphite 管线预编译测试工具

## 概述

`tools/graphite/precompile` 目录包含了 Graphite 管线预编译系统的测试辅助工具。管线预编译是 Graphite 的一项重要优化特性，允许应用程序在渲染之前预先编译图形管线，从而避免在绘制时出现卡顿（jank）。

本目录的核心文件 `PrecompileEffectFactories.h/.cpp` 提供了一组工厂函数，用于创建普通 API 效果和对应的预编译 API 效果的配对（pair）。这种配对设计是预编译测试的关键：测试框架首先使用预编译 API 版本来生成管线预编译请求，然后使用普通 API 版本进行实际渲染，验证预编译生成的管线确实覆盖了渲染所需的管线。

工厂函数涵盖了三类效果的测试：着色器（Shader）、混合器（Blender）和颜色过滤器（ColorFilter）。每种效果都使用 SkRuntimeEffect（运行时效果）实现，确保预编译路径能够处理自定义着色器代码。

具体来说，`PrecompileFactories` 命名空间提供了：环形着色器（Annulus Shader）用于测试自定义着色器预编译；Src/Dst/Combo 混合器用于测试不同复杂度的混合操作预编译；Double/Half/Combo 颜色过滤器用于测试颜色处理管线的预编译。

这些工具主要用于 Graphite 的 `gr*testprecompile` 和 `gr*testtracking` 测试配置中。

## 目录结构

```
tools/graphite/precompile/
├── PrecompileEffectFactories.h      # 预编译效果工厂声明
└── PrecompileEffectFactories.cpp    # 预编译效果工厂实现
```

## 关键类与函数

### PrecompileFactories 命名空间
- **命名空间**: `skiatest::graphite::PrecompileFactories`
- **功能**: 创建普通 API / 预编译 API 的效果配对

### 类型定义
- `BlenderPair` = `std::pair<sk_sp<SkBlender>, sk_sp<PrecompileBlender>>`
- `ColorFilterPair` = `std::pair<sk_sp<SkColorFilter>, sk_sp<PrecompileColorFilter>>`
- `ShaderPair` = `std::pair<sk_sp<SkShader>, sk_sp<PrecompileShader>>`

### 着色器工厂
- `GetAnnulusShaderCode()` - 获取环形着色器的 SkSL 源代码
- `GetAnnulusShaderEffect()` - 获取环形着色器的 SkRuntimeEffect
- `CreateAnnulusRuntimeShader()` - 创建环形运行时着色器的配对

### 混合器工厂
- `GetSrcBlenderEffect()` / `CreateSrcRuntimeBlender()` - Src 混合器
- `GetDstBlenderEffect()` / `CreateDstRuntimeBlender()` - Dst 混合器
- `GetComboBlenderEffect()` / `CreateComboRuntimeBlender()` - 组合混合器

### 颜色过滤器工厂
- `GetDoubleColorFilterEffect()` / `CreateDoubleRuntimeColorFilter()` - 双倍颜色过滤器
- `GetHalfColorFilterEffect()` / `CreateHalfRuntimeColorFilter()` - 半值颜色过滤器
- `GetComboColorFilterEffect()` / `CreateComboRuntimeColorFilter()` - 组合颜色过滤器

## 依赖关系

- **上游依赖**: `include/core/`（SkBlender、SkColorFilter、SkShader、SkRuntimeEffect）
- **Graphite 依赖**: `include/gpu/graphite/precompile/`（PrecompileBlender、PrecompileColorFilter、PrecompileShader）
- **被引用**: Graphite 预编译测试（`gr*testprecompile` 配置）
- **关联组件**: `tools/graphite/PipelineCallbackHandler.h`（收集预编译键）

## 相关文档与参考

- `tools/graphite/PipelineCallbackHandler.h` - 管线回调处理器
- `include/gpu/graphite/precompile/` - Graphite 预编译公共 API
- `src/gpu/graphite/precompile/` - Graphite 预编译核心实现
- `tools/graphite/UniqueKeyUtils.h` - 管线唯一键工具
