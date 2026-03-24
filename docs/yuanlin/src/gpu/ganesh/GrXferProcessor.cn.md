# GrXferProcessor

> 源文件
> - `src/gpu/ganesh/GrXferProcessor.h`
> - `src/gpu/ganesh/GrXferProcessor.cpp`

## 概述

`GrXferProcessor` 是 Ganesh GPU 渲染管线中负责最终颜色混合和输出的核心组件。它控制片段着色器输出的源颜色与帧缓冲中目标颜色的混合方式,并管理固定功能混合状态或执行可编程的混合着色器代码。

该模块的设计围绕两种工作模式:
- **Dst Read 模式**: 在着色器中读取目标颜色,执行可编程混合,基类自动处理覆盖率
- **No Dst Read 模式**: 使用固定功能混合或双源混合,子类完全控制混合状态和覆盖率处理

`GrXferProcessor` 通过 `GrXPFactory` 工厂类动态创建,允许在了解完整绘制状态后选择最优的混合策略。

## 架构位置

```
Ganesh 渲染管线
├── GrPaint                    # 高层绘制状态
├── GrPipeline                 # 完整的渲染管线配置
│   ├── GrFragmentProcessor[]  # 颜色和覆盖率处理器链
│   └── GrXferProcessor        # 【本模块】最终混合处理器
│       ├── ProgramImpl        # GPU 着色器代码生成器
│       └── GrXPFactory        # 工厂类,决策和创建 XP
├── GrProgramInfo              # 程序构建信息
└── GPU 后端 (GL/Metal/Vulkan) # 硬件 API 调用层
```

`GrXferProcessor` 位于渲染管线的最终阶段,接收所有 fragment processor 处理后的颜色和覆盖率,执行与帧缓冲的混合操作。

## 主要类与结构体

### GrXferProcessor

继承自 `GrProcessor` 和 `GrNonAtomicRef`,是所有混合处理器的抽象基类。

**关键成员变量**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fWillReadDstColor` | `bool` | 是否在着色器中读取目标颜色 |
| `fIsLCD` | `bool` | 是否处理 LCD 子像素覆盖率 |

**公共方法**

| 方法 | 说明 |
|------|------|
| `addToKey()` | 生成唯一键用于着色器缓存 |
| `makeProgramImpl()` | 创建着色器代码生成器(纯虚函数) |
| `xferBarrierType()` | 返回所需的内存屏障类型 |
| `getBlendInfo()` | 获取固定功能混合状态 |
| `willReadDstColor()` | 查询是否读取目标颜色 |
| `hasSecondaryOutput()` | 查询是否使用双源混合 |
| `isLCD()` | 查询是否为 LCD 覆盖率 |
| `isEqual()` | 比较两个处理器是否等价 |

### GrXferProcessor::ProgramImpl

负责生成实际的 GPU 着色器代码,处理两种混合路径:
1. **固定功能混合**: 通过 `emitOutputsForBlendState()` 输出颜色
2. **着色器混合**: 通过 `emitBlendCodeForDstRead()` 读取目标并混合

**核心方法**

| 方法 | 说明 |
|------|------|
| `emitCode()` | 生成完整的混合着色器代码 |
| `setData()` | 更新 uniform 变量 |
| `DefaultCoverageModulation()` | 默认的覆盖率调制实现 |
| `emitOutputsForBlendState()` | 子类实现:无 dst read 时的混合(虚函数) |
| `emitBlendCodeForDstRead()` | 子类实现:有 dst read 时的混合(虚函数) |
| `emitWriteSwizzle()` | 应用输出通道重排列 |

**EmitArgs 结构体**

封装着色器生成所需的上下文信息:

| 字段 | 类型 | 说明 |
|------|------|------|
| `fXPFragBuilder` | `GrGLSLXPFragmentBuilder*` | 片段着色器构建器 |
| `fUniformHandler` | `GrGLSLUniformHandler*` | Uniform 变量管理器 |
| `fShaderCaps` | `const GrShaderCaps*` | 着色器能力查询 |
| `fXP` | `const GrXferProcessor&` | 当前 XP 实例 |
| `fInputColor` | `const char*` | 输入颜色变量名 |
| `fInputCoverage` | `const char*` | 输入覆盖率变量名 |
| `fOutputPrimary` | `const char*` | 主输出颜色变量名 |
| `fOutputSecondary` | `const char*` | 次输出颜色变量名(双源混合) |
| `fDstTextureSamplerHandle` | `SamplerHandle` | 目标纹理采样器句柄 |
| `fDstTextureOrigin` | `GrSurfaceOrigin` | 目标纹理坐标原点 |
| `fWriteSwizzle` | `const skgpu::Swizzle&` | 输出通道映射 |

### GrXPFactory

工厂基类,负责分析绘制状态并创建最优的 `GrXferProcessor` 实例。

**关键枚举:AnalysisProperties**

| 属性位 | 说明 |
|--------|------|
| `kReadsDstInShader` | 需要在着色器中读取目标颜色 |
| `kCompatibleWithCoverageAsAlpha` | 可将覆盖率作为 alpha 处理 |
| `kIgnoresInputColor` | 忽略输入颜色(如 clear 操作) |
| `kRequiresDstTexture` | 需要目标纹理(当不支持 framebuffer fetch) |
| `kRequiresNonOverlappingDraws` | 要求绘制区域不重叠 |
| `kUsesNonCoherentHWBlending` | 使用非相干硬件混合 |
| `kUnaffectedByDstValue` | 目标值不影响输出(如 Src 模式) |

**静态方法**

| 方法 | 说明 |
|------|------|
| `MakeXferProcessor()` | 创建 XP 实例 |
| `GetAnalysisProperties()` | 分析绘制属性并返回标志位集合 |
| `FromBlendMode()` | 从 `SkBlendMode` 获取对应的工厂 |

**纯虚方法**

| 方法 | 说明 |
|------|------|
| `makeXferProcessor()` | 子类实现:创建具体的 XP |
| `analysisProperties()` | 子类实现:返回分析属性 |

### GrXferBarrierType

内存屏障类型枚举:

| 值 | 说明 |
|----|------|
| `kNone_GrXferBarrierType` | 无需屏障 |
| `kTexture_GrXferBarrierType` | 纹理屏障(读写同一纹理时) |
| `kBlend_GrXferBarrierType` | 混合扩展所需屏障 |

## 公共 API 函数

### GrXferProcessor 核心 API

```cpp
// 添加缓存键(用于着色器程序缓存)
void addToKey(const GrShaderCaps& caps, skgpu::KeyBuilder* b) const;

// 创建着色器代码生成器
virtual std::unique_ptr<ProgramImpl> makeProgramImpl() const = 0;

// 查询所需的内存屏障类型
virtual GrXferBarrierType xferBarrierType(const GrCaps& caps) const;

// 获取固定功能混合状态(仅在 !willReadDstColor() 时有效)
skgpu::BlendInfo getBlendInfo() const;

// 查询是否读取目标颜色
bool willReadDstColor() const;

// 查询是否使用双源混合
bool hasSecondaryOutput() const;

// 查询是否为 LCD 覆盖率
bool isLCD() const;

// 比较两个 XP 是否等价
bool isEqual(const GrXferProcessor& that) const;
```

### GrXPFactory 工厂 API

```cpp
// 创建 XP 实例(静态方法,处理 nullptr 工厂的默认行为)
static sk_sp<const GrXferProcessor> MakeXferProcessor(
    const GrXPFactory* factory,
    const GrProcessorAnalysisColor& color,
    GrProcessorAnalysisCoverage coverage,
    const GrCaps& caps,
    GrClampType clampType
);

// 分析绘制属性
static AnalysisProperties GetAnalysisProperties(
    const GrXPFactory* factory,
    const GrProcessorAnalysisColor& color,
    const GrProcessorAnalysisCoverage& coverage,
    const GrCaps& caps,
    GrClampType clampType
);

// 从混合模式获取工厂(返回静态 Porter-Duff 或自定义工厂)
static const GrXPFactory* FromBlendMode(SkBlendMode mode);
```

### ProgramImpl 着色器生成 API

```cpp
// 生成完整的混合着色器代码
void emitCode(const EmitArgs& args);

// 更新 uniform 数据
void setData(const GrGLSLProgramDataManager& pdm, const GrXferProcessor& xp);

// 默认覆盖率调制实现(静态辅助方法)
static void DefaultCoverageModulation(
    GrGLSLXPFragmentBuilder* fragBuilder,
    const char* srcCoverage,
    const char* dstColor,
    const char* outColor,
    const char* outColorSecondary,
    const GrXferProcessor& proc
);
```

## 内部实现细节

### 着色器代码生成逻辑

`ProgramImpl::emitCode()` 的核心流程(第 117-173 行):

**1. 无 Dst Read 路径**:
```cpp
if (!args.fXP.willReadDstColor()) {
    adjust_for_lcd_coverage(args.fXPFragBuilder, args.fInputCoverage, args.fXP);
    this->emitOutputsForBlendState(args);
}
```
- 处理 LCD 覆盖率调整(取 RGB 通道最大值作为 alpha)
- 调用子类的 `emitOutputsForBlendState()` 输出最终颜色

**2. 有 Dst Read 路径**:
```cpp
else {
    // 从 framebuffer fetch 或纹理采样获取 dstColor
    const char* dstColor = fragBuilder->dstColor();

    // 优化:覆盖率为零时提前丢弃片段
    if (args.fDstTextureSamplerHandle.isValid()) {
        if (args.fInputCoverage) {
            fragBuilder->codeAppendf(
                "if (all(lessThanEqual(%s.rgb, half3(0)))) { discard; }",
                args.fInputCoverage);
        }
    }

    // 调用子类的混合代码生成
    this->emitBlendCodeForDstRead(...);
}
```

### LCD 覆盖率处理

针对 LCD 亚像素渲染的特殊处理(第 105-115 行):

```cpp
static void adjust_for_lcd_coverage(GrGLSLXPFragmentBuilder* fragBuilder,
                                    const char* srcCoverage,
                                    const GrXferProcessor& proc) {
    if (srcCoverage && proc.isLCD()) {
        // 将 RGB 覆盖率转换为单一 alpha 值(取最大值)
        fragBuilder->codeAppendf("%s.a = max(max(%s.r, %s.g), %s.b);",
                                 srcCoverage, srcCoverage, srcCoverage, srcCoverage);
    }
}
```

这确保在不使用着色器混合时,LCD 覆盖率能正确应用到 alpha 通道。

### 默认覆盖率调制

`DefaultCoverageModulation()` 实现标准的覆盖率插值(第 194-217 行):

```cpp
void ProgramImpl::DefaultCoverageModulation(...) {
    if (srcCoverage) {
        if (proc.isLCD()) {
            // LCD 模式:使用目标 alpha 和输出 alpha 进行插值
            fragBuilder->codeAppendf("half3 lerpRGB = mix(%s.aaa, %s.aaa, %s.rgb);",
                                     dstColor, outColor, srcCoverage);
        }
        // 标准覆盖率混合公式:src * coverage + dst * (1 - coverage)
        fragBuilder->codeAppendf("%s = %s * %s + (half4(1.0) - %s) * %s;",
                                 outColor, srcCoverage, outColor, srcCoverage, dstColor);
        if (proc.isLCD()) {
            // LCD alpha 取 RGB 插值结果的最大值
            fragBuilder->codeAppendf("%s.a = max(max(lerpRGB.r, lerpRGB.b), lerpRGB.g);", outColor);
        }
    }
}
```

### 工厂分析逻辑

`GrXPFactory::GetAnalysisProperties()` 根据能力决策实现策略(第 51-73 行):

```cpp
AnalysisProperties GrXPFactory::GetAnalysisProperties(...) {
    AnalysisProperties result;
    if (factory) {
        result = factory->analysisProperties(color, coverage, caps, clampType);
    } else {
        // nullptr 工厂默认使用 SrcOver 混合
        result = GrPorterDuffXPFactory::SrcOverAnalysisProperties(...);
    }

    // 无覆盖率时自动兼容 coverage-as-alpha
    if (coverage == GrProcessorAnalysisCoverage::kNone) {
        result |= AnalysisProperties::kCompatibleWithCoverageAsAlpha;
    }

    // 不支持 shader dst read 时强制使用纹理
    if ((result & AnalysisProperties::kReadsDstInShader) &&
        !caps.shaderCaps()->fDstReadInShaderSupport) {
        result |= AnalysisProperties::kRequiresDstTexture |
                  AnalysisProperties::kRequiresNonOverlappingDraws;
    }
    return result;
}
```

### 键生成策略

`addToKey()` 生成缓存键时包含公共状态(第 42-47 行):

```cpp
void GrXferProcessor::addToKey(const GrShaderCaps& caps, skgpu::KeyBuilder* b) const {
    b->addBool(this->willReadDstColor(), "willReadDstColor");
    b->addBool(fIsLCD, "isLCD");
    this->onAddToKey(caps, b);  // 子类添加特定键
}
```

### 输出重排列

`emitWriteSwizzle()` 处理非标准颜色通道映射(第 175-188 行):

```cpp
void ProgramImpl::emitWriteSwizzle(...) {
    if (skgpu::Swizzle::RGBA() != swizzle) {
        x->codeAppendf("%s = %s.%s;", outColor, outColor, swizzle.asString().c_str());
        if (outColorSecondary) {
            x->codeAppendf("%s = %s.%s;",
                           outColorSecondary, outColorSecondary, swizzle.asString().c_str());
        }
    }
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrProcessor` | 基类,提供处理器通用框架 |
| `GrNonAtomicRef` | 非原子引用计数基类 |
| `GrCaps` / `GrShaderCaps` | 查询 GPU 能力 |
| `GrProcessorAnalysis` | 颜色和覆盖率分析结果 |
| `GrGLSLXPFragmentBuilder` | 片段着色器代码构建器 |
| `GrGLSLUniformHandler` | Uniform 变量管理 |
| `skgpu::KeyBuilder` | 着色器程序缓存键构建 |
| `skgpu::Blend` / `skgpu::BlendInfo` | 混合模式和状态定义 |
| `skgpu::Swizzle` | 通道重排列 |
| `GrPorterDuffXPFactory` | 默认 Porter-Duff 混合实现 |
| `GrCustomXfermode` | 自定义混合模式实现 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|----------|
| `GrPipeline` | 持有 `GrXferProcessor` 并在渲染时使用 |
| `GrPaint` | 通过 `GrXPFactory` 创建 XP |
| `GrProgramInfo` | 使用 XP 生成完整的 GPU 程序 |
| `GrGLProgram` | 调用 `ProgramImpl::setData()` 更新 uniform |
| `GrVkPipeline` | 从 `getBlendInfo()` 获取固定功能混合状态 |
| `GrMtlPipelineState` | 使用 XP 配置 Metal 渲染管线 |
| `GrDrawOp` | 间接通过 `GrPaint` 使用 XP |

## 设计模式与设计决策

### 1. 模板方法模式

`ProgramImpl::emitCode()` 定义着色器生成框架,子类实现具体混合逻辑:
- **模板方法**: `emitCode()`
- **Hook 方法**: `emitOutputsForBlendState()` 和 `emitBlendCodeForDstRead()`

### 2. 抽象工厂模式

`GrXPFactory` 是抽象工厂:
- **产品**: `GrXferProcessor` 及其子类
- **具体工厂**: `GrPorterDuffXPFactory`、`GrCustomXfermode` 等
- **工厂方法**: `makeXferProcessor()` 和 `analysisProperties()`

### 3. 策略模式

通过不同的 `GrXPFactory` 实现不同的混合策略:
- **Porter-Duff 策略**: 标准 alpha 混合
- **自定义策略**: 高级混合模式(如 screen, multiply 等)
- **上下文**: `GrPaint` 持有工厂指针

### 4. 双分派

`isEqual()` 方法实现双分派:
```cpp
bool isEqual(const GrXferProcessor& that) const {
    if (this->classID() != that.classID()) return false;  // 类型检查
    if (this->fWillReadDstColor != that.fWillReadDstColor) return false;
    if (fIsLCD != that.fIsLCD) return false;
    return this->onIsEqual(that);  // 子类虚函数
}
```

### 5. Null Object 模式

`GrXPFactory::FromBlendMode()` 返回 `nullptr` 表示默认的 SrcOver 混合:
```cpp
static const GrXPFactory* FromBlendMode(SkBlendMode mode) {
    if (SkBlendMode_AsCoeff(mode, nullptr, nullptr)) {
        const GrXPFactory* result = GrPorterDuffXPFactory::Get(mode);
        SkASSERT(result);
        return result;
    }
    return GrCustomXfermode::Get(mode);
}
```

### 6. 关注点分离

- **XP**: 负责混合逻辑和状态查询
- **ProgramImpl**: 负责着色器代码生成
- **XPFactory**: 负责分析和决策

### 7. 编译时多态

`GrXPFactory` 使用 `constexpr` 构造函数和静态工厂,允许编译期实例化:
```cpp
constexpr GrXPFactory() {}
```

## 性能考量

### 1. 固定功能混合优先

当不需要读取目标颜色时,使用硬件固定功能混合:
- 避免 framebuffer fetch 或纹理采样的带宽消耗
- 利用 GPU 的专用混合单元,比着色器实现快数倍

### 2. 着色器程序缓存

通过 `addToKey()` 生成唯一键:
- 相同状态的绘制调用复用已编译的着色器程序
- 避免重复编译相同的混合代码

### 3. 提前丢弃优化

在 dst read 路径中提前丢弃零覆盖率片段(第 139-142 行):
```cpp
if (all(lessThanEqual(coverage.rgb, half3(0)))) {
    discard;  // 跳过后续混合计算和内存写入
}
```

### 4. 延迟决策

`GrXPFactory` 在管线构建时才创建 `GrXferProcessor`:
- 根据完整绘制状态选择最优混合策略
- 避免创建不必要的处理器实例

### 5. 非原子引用计数

继承 `GrNonAtomicRef` 而非 `SkRefCnt`:
- XP 仅在单线程(GPU 记录线程)使用
- 避免原子操作的同步开销

### 6. LCD 覆盖率优化

仅在需要时调整 LCD 覆盖率:
```cpp
if (srcCoverage && proc.isLCD()) {
    // 仅当有覆盖率且为 LCD 模式时执行
}
```

### 7. 静态常量优化

工厂实例通常为静态 `constexpr` 对象:
- 零运行时开销
- 避免动态分配

### 8. 局部变量优化

使用局部 `outColor` 变量在某些 GPU 上提高性能(第 145-152 行):
```cpp
bool needsLocalOutColor = args.fShaderCaps->fRequiresLocalOutputColorForFBFetch;
if (needsLocalOutColor) {
    fragBuilder->codeAppendf("half4 %s;", outColor);
    // ... 混合到局部变量
    fragBuilder->codeAppendf("%s = %s;", args.fOutputPrimary, outColor);
}
```

## 相关文件

| 文件路径 | 关系说明 |
|----------|----------|
| `src/gpu/ganesh/GrPipeline.h` | 包含并使用 XP 配置渲染管线 |
| `src/gpu/ganesh/GrPaint.h` | 持有 `GrXPFactory` 指针 |
| `src/gpu/ganesh/GrProcessor.h` | XP 的基类 |
| `src/gpu/ganesh/GrNonAtomicRef.h` | 引用计数基类 |
| `src/gpu/ganesh/GrProcessorAnalysis.h` | 分析结果类型定义 |
| `src/gpu/ganesh/effects/GrPorterDuffXferProcessor.h` | Porter-Duff 混合实现 |
| `src/gpu/ganesh/effects/GrCustomXfermode.h` | 自定义混合模式实现 |
| `src/gpu/ganesh/glsl/GrGLSLXPFragmentBuilder.h` | 片段着色器构建器 |
| `src/gpu/ganesh/glsl/GrGLSLUniformHandler.h` | Uniform 管理接口 |
| `src/gpu/ganesh/glsl/GrGLSLFragmentShaderBuilder.h` | 通用片段着色器构建工具 |
| `src/gpu/ganesh/GrCaps.h` | GPU 能力查询 |
| `src/gpu/ganesh/GrShaderCaps.h` | 着色器能力查询 |
| `src/gpu/KeyBuilder.h` | 缓存键构建工具 |
| `src/gpu/Blend.h` | 混合系数和状态定义 |
| `src/gpu/Swizzle.h` | 通道重排列工具 |
| `include/core/SkBlendMode.h` | Skia 混合模式枚举 |
