# SkColorFilterShader - 颜色滤镜着色器

> 源文件:
> - `src/shaders/SkColorFilterShader.h`
> - `src/shaders/SkColorFilterShader.cpp`

## 概述

SkColorFilterShader 是一个组合着色器，它将一个颜色滤镜 (SkColorFilter) 应用到另一个着色器的输出之上，并可选地应用一个 alpha 缩放因子。当用户调用 `SkShader::makeWithColorFilter()` 时，就会创建此类型的着色器。它在着色器管线中先执行子着色器，然后对结果应用 alpha 缩放和颜色滤镜。

## 架构位置

```
Skia 着色器系统
├── SkShader (公共 API)
│   └── SkShaderBase (内部基类)
│       └── SkColorFilterShader (本模块 - 颜色滤镜组合)
│           ├── 子着色器执行
│           ├── Alpha 缩放
│           └── SkColorFilter 应用
├── SkColorFilter / SkColorFilterBase
└── SkRasterPipeline (光栅管线)
```

## 主要类与结构体

### `SkColorFilterShader`
- 继承自 `SkShaderBase`。
- **成员变量**:
  - `fShader` (sk_sp\<SkShader\>): 被滤镜处理的子着色器。
  - `fFilter` (sk_sp\<SkColorFilterBase\>): 应用的颜色滤镜。
  - `fAlpha` (float): Alpha 缩放因子 (0.0 到 1.0)。

## 公共 API 函数

### `Make` (静态工厂方法)
```cpp
static sk_sp<SkShader> Make(sk_sp<SkShader> shader, float alpha, sk_sp<SkColorFilter> filter);
```
- **功能**: 创建颜色滤镜着色器。
- **短路优化**:
  - 如果 `shader` 为 null，返回 nullptr。
  - 如果 `filter` 为 null，直接返回原始 shader。

### 访问器
- `shader()`: 获取子着色器。
- `filter()`: 获取颜色滤镜。
- `alpha()`: 获取 alpha 缩放因子。
- `type()`: 返回 `ShaderType::kColorFilter`。

## 内部实现细节

### appendStages 实现
管线构建的三个阶段：
1. **子着色器执行**: 调用 `as_SB(fShader)->appendStages(rec, mRec)`。
2. **Alpha 缩放**: 如果 `fAlpha != 1.0f`，追加 `SkRasterPipelineOp::scale_1_float` 操作。alpha 值存储在 arena 分配器中。
3. **颜色滤镜应用**: 调用 `fFilter->appendStages(rec, isOpaque)`。`isOpaque` 参数基于子着色器的不透明性和 alpha 值计算。

### isOpaque 判断
```cpp
bool isOpaque() const override {
    return fShader->isOpaque() && fAlpha == 1.0f && as_CFB(fFilter)->isAlphaUnchanged();
}
```
仅当子着色器不透明、alpha 为 1.0、且滤镜不改变 alpha 通道时，组合着色器才被标记为不透明。

### 序列化/反序列化
- `flatten()`: 写入子着色器和颜色滤镜。带有 `SkASSERT(fAlpha == 1.0f)` 断言，因为公共 API `makeWithColorFilter()` 不暴露 alpha 参数。
- `CreateProc()`: 读取着色器和滤镜，alpha 固定为 1.0f。

### alpha 参数的特殊性
虽然类内部支持 alpha 参数，但公共 API `SkShader::makeWithColorFilter()` 始终传入 1.0f。alpha 参数的存在可能是为了内部优化或未来扩展。序列化时断言 alpha 为 1.0f，反序列化也硬编码为 1.0f。

## 依赖关系

- `include/core/SkColorFilter.h`: 颜色滤镜公共接口。
- `include/core/SkShader.h`: 着色器公共接口。
- `src/shaders/SkShaderBase.h`: 着色器内部基类。
- `src/effects/colorfilters/SkColorFilterBase.h`: 颜色滤镜内部基类（`as_CFB`, `as_CFB_sp`）。
- `src/core/SkRasterPipeline.h`: 光栅管线。
- `src/core/SkRasterPipelineOpList.h`: 管线操作枚举。
- `src/core/SkReadBuffer.h` / `SkWriteBuffer.h`: 序列化。
- `src/base/SkArenaAlloc.h`: Arena 分配器。
- `src/core/SkEffectPriv.h`: `SkStageRec` 定义。

## 设计模式与设计决策

1. **组合模式**: 将着色器和颜色滤镜组合为一个新的着色器。
2. **短路优化**: 工厂方法在不需要创建包装器时直接返回原始着色器。
3. **管线式处理**: 着色器、alpha 缩放和滤镜按顺序追加到光栅管线中，最大化 SIMD 处理效率。
4. **公共/内部 API 分离**: alpha 参数虽然在内部支持，但公共 API 不暴露此功能，保持了接口的简洁性。

## 性能考量

1. **最小化包装**: 当滤镜为 null 时不创建包装对象。
2. **管线操作效率**: alpha 缩放使用单个 `scale_1_float` 管线操作，当 alpha 为 1.0 时完全跳过。
3. **不透明性传播**: `isOpaque()` 的正确实现允许后续的混合优化。
4. **Arena 分配**: alpha 值存储在 `rec.fAlloc` 中，避免堆分配。

## 相关文件

- `src/shaders/SkShaderBase.h/.cpp`: 着色器基类。
- `src/effects/colorfilters/SkColorFilterBase.h/.cpp`: 颜色滤镜基类。
- `include/core/SkShader.h`: `makeWithColorFilter()` 方法定义。
- `src/core/SkRasterPipeline.h`: 光栅管线。
