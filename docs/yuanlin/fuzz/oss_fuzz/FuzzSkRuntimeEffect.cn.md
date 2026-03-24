# FuzzSkRuntimeEffect.cpp - SkRuntimeEffect 运行时效果模糊测试

> 源文件: `fuzz/oss_fuzz/FuzzSkRuntimeEffect.cpp`

## 概述

本文件实现了针对 `SkRuntimeEffect`（Skia 运行时着色器效果）的模糊测试。`SkRuntimeEffect` 允许应用程序在运行时通过 SkSL 代码自定义着色器行为。该测试不仅编译 SkSL 着色器，还自动合成所需的 uniform 数据和子着色器，然后将着色器实际应用到画布上进行渲染。测试分别在启用和禁用编译器优化的两种模式下运行，以最大化代码覆盖率。

## 架构位置

该文件位于 `fuzz/oss_fuzz/` 目录下，是 Skia 模糊测试中最全面的 SkSL 相关测试之一。它不仅覆盖编译路径，还覆盖了着色器的实例化、uniform 绑定和实际光栅化渲染，是对 SkRuntimeEffect 端到端安全性的完整验证。

## 主要类与结构体

- **`SkRuntimeEffect`**: 运行时着色器效果核心类
- **`SkRuntimeEffect::Options`**: 编译选项，包含 `forceUnoptimized` 标志
- **`SkRuntimeEffect::Result`**: 编译结果，包含效果对象和错误信息
- **`SkRuntimeEffect::ChildPtr`**: 子着色器/颜色过滤器引用
- **`SkShader`**: 着色器基类
- **`SkPaint`**: 绘图属性
- **`SkSurface` / `SkCanvas`**: 渲染目标和画布

## 公共 API 函数

- **`FuzzSkRuntimeEffect(const uint8_t *data, size_t size)`**: 主入口，分别以优化禁用和启用模式运行测试
- **`FuzzSkRuntimeEffect_Once(shaderText, options)`**: 单次测试执行，编译、实例化并渲染着色器
- **`LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)`**: LibFuzzer 入口点，输入限制 3000 字节

## 内部实现细节

### 双模式测试策略

每个输入被测试两次：
1. **优化禁用模式** (`forceUnoptimized = true`): 禁用内联等优化，暴露函数调用相关的 bug
2. **优化启用模式** (`forceUnoptimized = false`): 测试优化器和内联后的代码路径

这种策略显著提高了覆盖率。默认情况下编译器会内联小到中等函数，这可能隐藏与函数调用相关的 bug。

### 自动输入合成

`FuzzCreateValidInputsForRuntimeEffect()` 自动分析已编译的效果，为其所需的 uniform 和子着色器生成有效输入数据。这避免了模糊测试引擎需要同时生成有效着色器代码和匹配的输入数据的困难。

### 渲染验证

最终将着色器应用到 4x4 的小 Surface 上通过 `drawPaint()` 渲染，触发完整的光栅化管线。

## 依赖关系

- **`include/effects/SkRuntimeEffect.h`**: 运行时效果 API
- **`fuzz/FuzzCommon.h`**: `FuzzCreateValidInputsForRuntimeEffect` 工具函数
- **`include/core/SkCanvas.h` / `SkPaint.h` / `SkShader.h` / `SkSurface.h`**: 渲染 API
- **`include/private/base/SkTArray.h`**: 数组容器
- **`src/gpu/ganesh/GrShaderCaps.h`**: 着色器能力
- **`fuzz/Fuzz.h`**: 模糊测试基础设施

## 设计模式与设计决策

- **双模式测试**: 同一输入运行两次（优化/非优化），以最小的额外成本显著提高覆盖率
- **自动输入合成**: 通过自动生成 uniform 和子着色器，将模糊测试的搜索空间聚焦在着色器代码本身
- **端到端覆盖**: 从源码到像素输出的完整路径，包括编译、实例化和光栅化
- **小 Surface 尺寸**: 4x4 像素的 Surface 足以触发完整的着色器执行，同时最小化像素操作开销
- **结果合并**: 两次测试的结果通过 OR 合并（`result || result`），确保任一模式成功即报告成功

## 性能考量

- 4x4 的 Surface 尺寸将渲染开销降到最低
- 双模式执行使每次测试的耗时大约翻倍，但覆盖率的提升证明了这一成本
- 3000 字节输入限制与其他 SkSL 模糊测试一致
- uniform 数据自动合成避免了无效输入导致的早期退出
- `drawPaint()` 对整个 Surface 着色，确保每个像素都触发着色器执行

### 与纯编译模糊测试的差异

相比 FuzzSKSL2Metal/GLSL/SPIRV/WGSL 等纯编译测试，本测试的独特价值在于：
- 覆盖了 `SkRuntimeEffect::MakeForShader()` 的特定编译路径（比通用 `convertProgram()` 有额外的约束）
- 测试了 uniform 数据绑定和子着色器注入的正确性
- 触发了 CPU 端光栅化着色器的执行路径，而非仅生成代码文本

## 相关文件

- `include/effects/SkRuntimeEffect.h` - SkRuntimeEffect 公共头文件
- `src/core/SkRuntimeEffect.cpp` - SkRuntimeEffect 实现
- `fuzz/FuzzCommon.h` / `fuzz/FuzzCommon.cpp` - 模糊测试公共工具
- `fuzz/oss_fuzz/FuzzSKSL2Metal.cpp` 等 - 其他 SkSL 模糊测试
