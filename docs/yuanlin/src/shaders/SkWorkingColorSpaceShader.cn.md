# SkWorkingColorSpaceShader - 工作色彩空间着色器

> 源文件:
> - `src/shaders/SkWorkingColorSpaceShader.h`
> - `src/shaders/SkWorkingColorSpaceShader.cpp`

## 概述

SkWorkingColorSpaceShader 是一个着色器包装类，用于在指定的工作色彩空间中执行子着色器的计算。它在子着色器执行前将坐标/颜色从目标色彩空间转换到输入色彩空间，在子着色器执行后将结果从输出色彩空间转换回目标色彩空间。这使得着色器可以在与渲染目标不同的色彩空间中工作，同时确保最终输出的颜色正确。

## 架构位置

```
Skia 着色器系统
├── SkShader (公共 API)
│   └── SkShaderBase (内部基类)
│       └── SkWorkingColorSpaceShader (本模块 - 色彩空间转换包装)
│           ├── 输入色彩空间转换 (dst -> input)
│           ├── 子着色器执行
│           └── 输出色彩空间转换 (output -> dst)
├── SkColorSpaceXformSteps (色彩空间转换)
└── SkRasterPipeline (光栅管线)
```

## 主要类与结构体

### `SkWorkingColorSpaceShader`
- 继承自 `SkShaderBase`，`final` 类不可继续派生。
- **成员变量**:
  - `fShader` (sk_sp\<SkShader\>): 被包装的子着色器。
  - `fInputSpace` (sk_sp\<SkColorSpace\>): 输入色彩空间（子着色器的工作空间）。可为 null，表示使用目标色彩空间。
  - `fOutputSpace` (sk_sp\<SkColorSpace\>): 输出色彩空间。可为 null，表示使用输入色彩空间。
  - `fWorkInUnpremul` (bool): 是否在非预乘 alpha 模式下工作（尚未公开到公共 API）。

## 公共 API 函数

### `Make` (静态工厂方法)
```cpp
static sk_sp<SkShader> Make(sk_sp<SkShader> shader,
                            sk_sp<SkColorSpace> inputCS,
                            sk_sp<SkColorSpace> outputCS,
                            bool workInUnpremul);
```
- **功能**: 创建工作色彩空间着色器。
- **优化**: 当 inputCS、outputCS 和 workInUnpremul 都为 null/false 时，直接返回原始着色器（无额外转换开销）。

### `workingSpace`
```cpp
std::tuple<sk_sp<SkColorSpace>, sk_sp<SkColorSpace>, SkAlphaType>
workingSpace(sk_sp<SkColorSpace> dstCS, SkAlphaType dstAT) const;
```
- **功能**: 根据目标色彩空间计算实际的输入/输出色彩空间和工作 Alpha 类型。
- **规则**:
  - null `fInputSpace` 使用 `dstCS`。
  - null `fOutputSpace` 使用 `inputSpace`。
  - `fWorkInUnpremul` 为 true 时使用 `kUnpremul_SkAlphaType`，否则使用 `dstAT`。

### 其他方法
- `shader()`: 获取子着色器。
- `type()`: 返回 `ShaderType::kWorkingColorSpace`。

## 内部实现细节

### appendStages 实现
```
目标色彩空间 --[dstToInput]--> 输入色彩空间 --[子着色器执行]--> 输出色彩空间 --[outputToDst]--> 目标色彩空间
```

1. 确定目标色彩空间（null 时默认为 sRGB）。
2. 通过 `workingSpace()` 计算实际的输入/输出色彩空间和工作 Alpha 类型。
3. 创建 `SkColorSpaceXformSteps` 用于 dst->input 和 output->dst 的转换。
4. 转换画笔颜色到工作色彩空间（用于 alpha-only 图像着色器引用画笔颜色的场景）。
5. 创建工作状态的 `SkStageRec`，将输入色彩空间传递给子着色器。
6. 执行子着色器的 `appendStages()`。
7. 将 output->dst 的转换追加到管线。

### 序列化/反序列化
- `flatten()`: 写入子着色器、`workInUnpremul` 标记、输入和输出色彩空间数据。
- `CreateProc()`: 从缓冲区读取并重建着色器。支持向后兼容旧版本 (`kWorkingColorSpaceOutput` 之前的版本)。

### 向后兼容
旧版本格式（`legacyWorkingCS`）:
- 不支持 `workInUnpremul`。
- 只有输入色彩空间（非空），没有输出色彩空间。
- 新版本增加了输出色彩空间和 unpremul 工作模式的支持。

## 依赖关系

- `include/core/SkColorSpace.h`: 色彩空间。
- `include/core/SkShader.h`: 着色器基类。
- `src/shaders/SkShaderBase.h`: 着色器内部基类。
- `src/core/SkColorSpaceXformSteps.h`: 色彩空间转换步骤。
- `src/core/SkEffectPriv.h`: 效果私有工具。
- `src/core/SkReadBuffer.h` / `SkWriteBuffer.h`: 序列化。
- `src/base/SkArenaAlloc.h`: Arena 分配器。

## 设计模式与设计决策

1. **装饰器模式**: 包装子着色器，在其前后添加色彩空间转换逻辑。
2. **Null 即默认**: null 的输入/输出色彩空间分别表示"使用目标空间"和"使用输入空间"，简化了常见用例。
3. **无输入到输出转换**: 假设子着色器负责从输入到输出的转换（或两者相同），减少冗余转换。
4. **Unpremul 工作模式**: 为需要在非预乘 alpha 空间工作的着色器提供支持，但尚未公开到公共 API。
5. **向后兼容**: 反序列化代码处理旧版本格式，确保版本升级时不会丢失数据。

## 性能考量

1. **短路优化**: 当不需要任何转换时，`Make()` 直接返回原始着色器，避免不必要的包装层。
2. **管线效率**: 色彩空间转换以 `SkColorSpaceXformSteps` 的形式追加到 SkRasterPipeline，利用 SIMD 加速。
3. **画笔颜色预转换**: 在管线构建时一次性转换画笔颜色，避免逐像素重复转换。

## 相关文件

- `src/shaders/SkShaderBase.h/.cpp`: 着色器内部基类。
- `src/core/SkColorSpaceXformSteps.h/.cpp`: 色彩空间转换实现。
- `include/core/SkColorSpace.h`: 色彩空间类。
- `src/core/SkRasterPipeline.h`: 光栅管线。
