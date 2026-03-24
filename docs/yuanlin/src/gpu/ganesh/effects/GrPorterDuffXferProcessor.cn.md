# GrPorterDuffXferProcessor

> 源文件: src/gpu/ganesh/effects/GrPorterDuffXferProcessor.h, src/gpu/ganesh/effects/GrPorterDuffXferProcessor.cpp

## 概述

`GrPorterDuffXferProcessor` 是 Ganesh GPU 后端中实现 Porter-Duff 混合模式的传输处理器（Transfer Processor）工厂。Porter-Duff 混合是计算机图形学中最基础且广泛使用的混合算法，定义了如何将源图像与目标图像按特定规则组合，包括常见的 SrcOver、Clear、Multiply 等 15 种标准混合模式。

该模块是 Skia GPU 渲染管线中的关键组件,负责将片段着色器计算的颜色与帧缓冲区中已有的颜色进行混合。它实现了多种优化策略，包括硬件混合加速、LCD 文本渲染优化、双源混合支持等。模块提供了三种处理器实现：基于硬件混合的 `PorterDuffXferProcessor`、基于着色器混合的 `ShaderPDXferProcessor`，以及专门用于 LCD 文本的 `PDLCDXferProcessor`。

## 架构位置

`GrPorterDuffXferProcessor` 位于 Skia GPU 渲染架构的传输处理层：

- **层级**: GPU 渲染后端 -> Ganesh 引擎 -> 传输处理器 (Xfer Processor)
- **模块**: `src/gpu/ganesh/effects/`
- **功能定位**: 实现混合模式的工厂和处理器，连接片段着色器输出与帧缓冲区
- **渲染管线位置**: 渲染管线末端，片段着色之后、写入帧缓冲之前
- **核心责任**: 决定源像素和目标像素如何组合，管理硬件混合状态

在 Ganesh 架构中，传输处理器是渲染管线的最后阶段，与片段处理器协同工作，但职责不同：片段处理器负责计算颜色，传输处理器负责混合颜色。

## 主要类与结构体

### GrPorterDuffXPFactory 类

**继承关系**:
```
GrXPFactory (基类)
    └── GrPorterDuffXPFactory
```

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `fBlendMode` | `SkBlendMode` | 混合模式枚举值 |

**设计特点**:
- 采用享元模式，每种混合模式对应一个全局静态实例
- 禁用虚析构函数警告，因为工厂对象是全局静态的，永不销毁

### PorterDuffXferProcessor 类

基于硬件混合的传输处理器实现：

**继承关系**:
```
GrXferProcessor (基类)
    └── PorterDuffXferProcessor
```

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `fBlendFormula` | `BlendFormula` | 混合公式，定义硬件混合参数 |

### ShaderPDXferProcessor 类

基于着色器的传输处理器实现（用于不支持硬件混合的情况）：

**继承关系**:
```
GrXferProcessor (基类)
    └── ShaderPDXferProcessor
```

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `fXfermode` | `SkBlendMode` | 混合模式 |
| `fBlendUniform` | `UniformHandle` | 混合参数的 Uniform 句柄 |

**特点**: 需要读取目标颜色 (`willReadDstColor=true`)，在着色器中执行混合

### PDLCDXferProcessor 类

专门用于 LCD 文本渲染的优化处理器：

**继承关系**:
```
GrXferProcessor (基类)
    └── PDLCDXferProcessor
```

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `fBlendConstant` | `SkPMColor4f` | 预乘的混合常量颜色 |
| `fAlpha` | `float` | 源颜色的 alpha 值 |
| `fAlphaUniform` | `UniformHandle` | Alpha Uniform 句柄 |

**特点**: 针对 SrcOver + LCD + 常量颜色的特殊优化，避免目标读取

## 公共 API 函数

### GrPorterDuffXPFactory::Get

```cpp
static const GrXPFactory* Get(SkBlendMode blendMode);
```

**功能**: 获取指定混合模式的工厂实例。

**参数**: `blendMode` - Porter-Duff 混合模式枚举值

**返回**: 对应混合模式的全局工厂实例指针

**支持的混合模式**: Clear, Src, Dst, SrcOver, DstOver, SrcIn, DstIn, SrcOut, DstOut, SrcATop, DstATop, Xor, Plus, Modulate, Screen

**实现细节**: 使用 switch-case 返回预定义的全局静态实例，无内存分配开销

### GrPorterDuffXPFactory::MakeSrcOverXferProcessor

```cpp
static sk_sp<const GrXferProcessor> MakeSrcOverXferProcessor(
    const GrProcessorAnalysisColor& color,
    GrProcessorAnalysisCoverage coverage,
    const GrCaps& caps);
```

**功能**: 创建专门优化的 SrcOver 混合处理器（SrcOver 是最常用的混合模式）。

**参数说明**:
- `color`: 颜色分析结果，包含是否透明、是否常量等信息
- `coverage`: 覆盖率分析结果（None, SingleChannel, LCD）
- `caps`: GPU 能力查询接口

**返回**:
- `nullptr` 表示使用全局 `SimpleSrcOverXP()`
- 其他情况返回特定优化的处理器

**优化策略**:
- 非 LCD: 尽量返回 nullptr 使用全局简单实现
- 不透明 + 无覆盖率: 转换为 Src 模式（可禁用混合）
- LCD + 常量颜色: 使用 `PDLCDXferProcessor` 特殊优化
- LCD + 非常量或需要着色器混合: 使用 `ShaderPDXferProcessor`

### GrPorterDuffXPFactory::SimpleSrcOverXP

```cpp
static const GrXferProcessor& SimpleSrcOverXP();
```

**功能**: 返回全局简单 SrcOver 处理器的引用。

**返回**: 全局静态 `PorterDuffXferProcessor` 实例，配置为标准 SrcOver 混合

**使用场景**: 最常见的默认混合情况，避免重复创建对象

**注意事项**: 返回引用而非智能指针，调用者不应管理其生命周期

### GrPorterDuffXPFactory::MakeNoCoverageXP

```cpp
static sk_sp<const GrXferProcessor> MakeNoCoverageXP(SkBlendMode blendMode);
```

**功能**: 创建无覆盖率、非 LCD 的简单混合处理器。

**参数**: `blendMode` - 混合模式

**返回**: 使用硬件混合的 `PorterDuffXferProcessor` 实例

**使用场景**: 简单的不透明混合，无抗锯齿或覆盖率

### GrPorterDuffXPFactory::SrcOverAnalysisProperties

```cpp
static AnalysisProperties SrcOverAnalysisProperties(
    const GrProcessorAnalysisColor& color,
    const GrProcessorAnalysisCoverage& coverage,
    const GrCaps& caps,
    GrClampType clampType);
```

**功能**: 分析 SrcOver 混合的属性，用于渲染管线优化。

**返回**: 属性标志集合，包括是否读取目标、是否忽略输入颜色等

## 内部实现细节

### 工厂模式与单例

`Get` 方法使用享元模式，每种混合模式对应一个全局静态实例：

```cpp
static constexpr const GrPorterDuffXPFactory gSrcOverPDXPF(SkBlendMode::kSrcOver);
static constexpr const GrPorterDuffXPFactory gClearPDXPF(SkBlendMode::kClear);
// ... 其他 13 种混合模式
```

**优点**:
- 零运行时内存分配
- 线程安全（constexpr 静态初始化）
- 指针比较即可判断工厂类型

### 混合公式选择逻辑

`makeXferProcessor` 方法根据条件选择最优实现：

1. **LCD 文本特殊优化**:
   ```cpp
   if (isLCD && fBlendMode == SkBlendMode::kSrcOver && color.isConstant() &&
       !caps.fDualSourceBlendingSupport && !caps.fDstReadInShaderSupport) {
       return PDLCDXferProcessor::Make(fBlendMode, color);
   }
   ```

2. **SrcOver 到 Src 优化**:
   ```cpp
   if (fBlendMode == SkBlendMode::kSrcOver && color.isOpaque() &&
       coverage == kNone && caps.shouldCollapseSrcOverToSrcWhenAble()) {
       return GetBlendFormula(true, false, SkBlendMode::kSrc);
   }
   ```

3. **着色器混合回退**:
   - 需要双源混合但硬件不支持
   - LCD 模式下非 SrcOver 混合
   - Plus 模式下需要饱和度钳制

4. **标准硬件混合**: 使用 `PorterDuffXferProcessor` + `BlendFormula`

### PorterDuffXferProcessor 着色器生成

`append_color_output` 函数根据输出类型生成着色器代码：

```cpp
switch (outputType) {
    case kNone_OutputType:
        fragBuilder->codeAppend("output = half4(0.0);");
        break;
    case kModulate_OutputType:
        fragBuilder->codeAppend("output = inColor * inCoverage;");
        break;
    case kSAModulate_OutputType:
        fragBuilder->codeAppend("output = inColor.a * inCoverage;");
        break;
    case kISAModulate_OutputType:
        fragBuilder->codeAppend("output = (1.0 - inColor.a) * inCoverage;");
        break;
    // ...
}
```

### ShaderPDXferProcessor 目标读取

在不支持硬件混合时，读取帧缓冲区内容并在着色器中混合：

```cpp
std::string blendExpr = GrGLSLBlend::BlendExpression(
    &xp, uniformHandler, &fBlendUniform, srcColor, dstColor, xp.fXfermode);
fragBuilder->codeAppendf("%s = %s;", outColor, blendExpr.c_str());
```

### PDLCDXferProcessor 的 LCD 优化

针对 LCD 文本的特殊情况：

- **前提条件**: SrcOver + 常量颜色 + 无双源混合/目标读取支持
- **优化原理**: 将 RGB 通道烘焙到硬件混合常量，仅用 alpha * coverage 作为片段输出
- **硬件混合设置**:
  - `srcBlend = kConstC` (混合常量)
  - `dstBlend = kISC` (1 - 混合常量)
- **着色器输出**: `output = alpha * coverage`

## 依赖关系

### 依赖的模块

| 模块 | 类型 | 用途 |
|------|------|------|
| `GrXferProcessor` | Ganesh 核心 | 传输处理器基类 |
| `GrXPFactory` | Ganesh 核心 | 传输处理器工厂基类 |
| `SkBlendMode` | Skia 核心 | 混合模式枚举 |
| `BlendFormula` | GPU 通用 | 混合公式表示，跨后端通用 |
| `GrCaps` | Ganesh 能力 | GPU 能力查询 |
| `GrProcessorAnalysisColor` | 分析工具 | 颜色属性分析 |
| `GrProcessorAnalysisCoverage` | 分析工具 | 覆盖率属性分析 |
| `GrGLSLBlend` | GLSL 生成 | 混合表达式生成 |
| `GrGLSLFragmentShaderBuilder` | GLSL 生成 | 片段着色器代码构建 |

### 被依赖的模块

| 模块 | 关系 | 用途 |
|------|------|------|
| `GrPaint` | 上层使用 | 绘制参数包含混合模式 |
| `GrPipeline` | 渲染管线 | 将传输处理器加入管线 |
| `GrOpsTask` | 操作调度 | 根据混合模式创建渲染操作 |
| `GrDrawOp` | 绘制操作 | 使用混合处理器渲染几何 |
| 各种效果处理器 | 效果链 | 传输处理器是效果链的终点 |

## 设计模式与设计决策

### 享元模式

使用全局静态实例共享工厂对象：

- **内存优化**: 15 种混合模式仅创建 15 个对象
- **性能优化**: 无需动态内存分配和释放
- **线程安全**: constexpr 初始化，无竞态条件

### 策略模式

三种处理器实现（PorterDuff, ShaderPD, PDLCD）对应不同策略：

- **硬件混合策略**: 快速但受限于硬件能力
- **着色器混合策略**: 灵活但性能较低
- **LCD 优化策略**: 针对特定场景的极致优化

### 工厂方法模式

`GrXPFactory::makeXferProcessor` 虚函数允许子类自定义创建逻辑：

- **动态选择**: 根据运行时条件选择最优实现
- **扩展性**: 可添加新的混合模式工厂
- **封装**: 隐藏复杂的选择逻辑

### SrcOver 特殊处理

为最常见的 SrcOver 混合提供特殊优化：

- **全局简单实现**: `SimpleSrcOverXP()` 避免重复创建
- **专用工厂方法**: `MakeSrcOverXferProcessor()` 提供定制优化
- **Src 模式转换**: 不透明情况下转为 Src 模式，禁用混合提升性能

### 分析与创建分离

`analysisProperties` 和 `makeXferProcessor` 分离：

- **延迟创建**: 先分析属性，仅在需要时创建处理器
- **管线优化**: 分析结果用于整个管线的优化决策
- **减少对象**: 某些情况下可完全跳过创建

### 硬件抽象

`BlendFormula` 抽象硬件混合参数：

- **跨后端**: 同一公式可用于 OpenGL、Vulkan、Metal
- **语义清晰**: 明确表达混合意图而非硬件细节
- **优化查询**: 预计算的混合公式表，避免运行时计算

## 性能考量

### 硬件混合优先

- **GPU 原生支持**: 固定功能硬件比可编程着色器快
- **带宽节省**: 无需读取目标颜色
- **并行执行**: 混合单元与着色器并行工作

### SrcOver 优化路径

- **全局单例**: `SimpleSrcOverXP()` 无分配开销
- **Src 转换**: 不透明 SrcOver 转为 Src，完全跳过混合阶段
- **快速路径**: 返回 nullptr 表示使用全局实例，减少引用计数开销

### LCD 文本特殊优化

- **避免目标读取**: `PDLCDXferProcessor` 通过巧妙的数学变换避免读取帧缓冲
- **减少着色器计算**: 将 RGB 烘焙到硬件混合常量
- **内存带宽**: 显著减少目标纹理读取的带宽消耗

### 着色器混合代价

- **目标读取**: `ShaderPDXferProcessor` 需要 `willReadDstColor=true`，增加纹理采样
- **ALU 指令**: 混合计算在着色器中执行，占用 ALU 资源
- **寄存器压力**: 需要额外寄存器存储目标颜色
- **使用场景**: 仅在硬件不支持时作为回退方案

### 混合公式缓存

- **预计算表**: `BlendFormula` 通过查表获取，无运行时计算
- **键值优化**: 着色器键仅包含输出类型，减少着色器变体
- **公式复用**: 多个混合模式可能共享相同公式

### 分析属性优化

`AnalysisProperties` 指导管线优化：

- **kUnaffectedByDstValue**: 允许跳过目标加载
- **kIgnoresInputColor**: 允许简化片段处理器
- **kCompatibleWithCoverageAsAlpha**: 允许覆盖率优化
- **kReadsDstInShader**: 提前分配目标纹理

### 双源混合检测

- **能力查询**: 检查 `fDualSourceBlendingSupport` 避免不支持的操作
- **回退策略**: 自动切换到着色器混合
- **性能差异**: 双源混合比着色器混合快，但比单源硬件混合慢

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/ganesh/GrXferProcessor.h` | 基类 | 传输处理器基类定义 |
| `src/gpu/ganesh/GrXPFactory.h` | 基类 | 传输处理器工厂基类 |
| `src/gpu/BlendFormula.h` | 依赖 | 混合公式表示，跨后端通用 |
| `src/gpu/Blend.h` | 依赖 | 混合系数和方程枚举 |
| `include/core/SkBlendMode.h` | 依赖 | Skia 混合模式枚举 |
| `src/gpu/ganesh/GrCaps.h` | 依赖 | GPU 能力查询接口 |
| `src/gpu/ganesh/GrProcessorAnalysis.h` | 依赖 | 颜色和覆盖率分析工具 |
| `src/gpu/ganesh/glsl/GrGLSLBlend.h` | 依赖 | GLSL 混合表达式生成 |
| `src/gpu/ganesh/GrPipeline.h` | 上层使用 | 渲染管线包含传输处理器 |
| `src/gpu/ganesh/GrPaint.h` | 上层使用 | 绘制参数包含混合模式 |
| `src/gpu/ganesh/ops/GrDrawOp.h` | 上层使用 | 绘制操作使用混合 |
