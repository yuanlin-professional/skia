# GrShaderCaps

> 源文件
> - src/gpu/ganesh/GrShaderCaps.h
> - src/gpu/ganesh/GrShaderCaps.cpp

## 概述

`GrShaderCaps` 是 Ganesh GPU 后端中用于描述着色器能力和特性的配置类。它继承自 SkSL 的 `ShaderCaps`，扩展了 Ganesh 特定的着色器功能查询，包括硬件特性支持、驱动程序 bug 的变通方案、以及着色器语言扩展信息。该类在着色器代码生成过程中起着关键作用，确保生成的着色器代码能够在目标 GPU 上正确运行。

`GrShaderCaps` 封装了各种 GPU 和驱动程序的差异，为着色器生成器提供统一的能力查询接口。它包含了对特殊功能的支持标志（如帧缓冲读取、双源混合）、精度相关的信息、以及针对特定驱动程序 bug 的变通方案标志。

## 架构位置

`GrShaderCaps` 位于 Ganesh 能力查询系统的核心：

```
GPU 初始化流程
├── GrContextOptions (用户配置)
├── GrGpu (GPU 后端)
│   └── GrCaps (通用能力)
│       └── GrShaderCaps (着色器能力)
│           └── SkSL::ShaderCaps (SkSL 编译器能力)
```

使用流程：
```
着色器生成
├── GrProcessor::emitCode()
│   └── 查询 GrShaderCaps
│       ├── 检查功能支持
│       ├── 应用变通方案
│       └── 生成兼容的着色器代码
```

## 主要类与结构体

### GrShaderCaps

着色器能力描述类。

**继承关系：**
- 父类：`SkSL::ShaderCaps`（SkSL 编译器着色器能力基类）

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fDstReadInShaderSupport` | `bool` | 是否支持在着色器中读取目标纹理 |
| `fPreferFlatInterpolation` | `bool` | 是否优先使用平面插值 |
| `fVertexIDSupport` | `bool` | 是否支持 `gl_VertexID` |
| `fNonconstantArrayIndexSupport` | `bool` | 是否支持非常量数组索引 |
| `fBitManipulationSupport` | `bool` | 是否支持位操作函数（frexp、ldexp 等） |
| `fHalfIs32Bits` | `bool` | half 类型是否实际为 32 位 |
| `fHasLowFragmentPrecision` | `bool` | 片段着色器是否精度较低 |
| `fReducedShaderMode` | `bool` | 是否使用简化的着色器模式 |

**驱动 Bug 变通方案标志：**

| 成员变量 | 说明 |
|---------|------|
| `fRequiresLocalOutputColorForFBFetch` | 帧缓冲读取需要局部输出颜色变量 |
| `fMustObfuscateUniformColor` | 必须混淆 uniform 颜色（Mali GPU bug） |
| `fMustWriteToFragColor` | 必须写入 `gl_FragColor`（Nexus 6 bug） |
| `fAvoidDfDxForGradientsWhenPossible` | 尽可能避免使用 `dFdx`（精度问题） |

**扩展字符串：**

| 成员变量 | 说明 |
|---------|------|
| `fSecondaryOutputExtensionString` | 双源混合扩展名称 |
| `fNoPerspectiveInterpolationExtensionString` | 无透视插值扩展名称 |
| `fSampleVariablesExtensionString` | 采样变量扩展名称 |
| `fFBFetchExtensionString` | 帧缓冲读取扩展名称 |

**其他配置：**

| 成员变量 | 说明 |
|---------|------|
| `fMaxFragmentSamplers` | 片段着色器最大采样器数量 |

## 公共 API 函数

### 构造函数

```cpp
GrShaderCaps()
```

默认构造函数，初始化所有能力标志为 false。实际的能力由各后端在初始化时设置。

### 扩展字符串访问

```cpp
const char* noperspectiveInterpolationExtensionString() const
const char* sampleVariablesExtensionString() const
```

获取特定功能所需的 GLSL 扩展名称。使用前需确保相应的功能支持标志为 true。

### 配置应用

```cpp
void applyOptionsOverrides(const GrContextOptions& options)
```

应用用户提供的配置覆盖。

**处理的选项：**
- `fDisableDriverCorrectnessWorkarounds`: 禁用所有驱动程序变通方案
- `fReducedShaderVariations`: 启用简化着色器模式
- `fSuppressDualSourceBlending`: 禁用双源混合（测试用）
- `fSuppressFramebufferFetch`: 禁用帧缓冲读取（测试用）

### 调试输出

```cpp
void dumpJSON(SkJSONWriter* writer) const
```

将所有能力信息以 JSON 格式输出，用于调试和诊断。仅在 `SK_ENABLE_DUMP_GPU` 启用时可用。

## 内部实现细节

### 配置覆盖应用

`applyOptionsOverrides` 处理用户配置：

```cpp
void GrShaderCaps::applyOptionsOverrides(const GrContextOptions& options) {
    // 禁用驱动变通方案
    if (options.fDisableDriverCorrectnessWorkarounds) {
        // 断言所有变通方案标志应为默认值（未启用）
        SkASSERT(fCanUseVoidInSequenceExpressions);
        SkASSERT(fCanUseMinAndAbsTogether);
        SkASSERT(!fMustForceNegatedAtanParamToFloat);
        // ... 更多断言
    }

    // 简化着色器模式
    if (options.fReducedShaderVariations) {
        fReducedShaderMode = true;
    }

#if defined(GPU_TEST_UTILS)
    // 测试工具：强制禁用某些功能
    if (options.fSuppressDualSourceBlending) {
        fDualSourceBlendingSupport = false;
    }
    if (options.fSuppressFramebufferFetch) {
        fFBFetchSupport = false;
    }
#endif
}
```

**设计要点：**
- 使用断言验证变通方案标志的初始状态
- 测试工具选项仅在 `GPU_TEST_UTILS` 启用时可用
- 简化模式可以减少着色器变体数量，提高编译速度

### JSON 调试输出

```cpp
void GrShaderCaps::dumpJSON(SkJSONWriter* writer) const {
    writer->beginObject();

    writer->appendBool("Shader Derivative Support", fShaderDerivativeSupport);
    writer->appendBool("Dst Read In Shader Support", fDstReadInShaderSupport);
    writer->appendBool("Dual Source Blending Support", fDualSourceBlendingSupport);
    // ... 输出所有能力标志

    writer->appendS32("Max FS Samplers", fMaxFragmentSamplers);

    writer->endObject();
}
```

**用途：**
- 调试 GPU 特性检测问题
- 记录不同设备的能力差异
- 生成能力报告

### 继承的能力

从 `SkSL::ShaderCaps` 继承的能力包括：

| 能力 | 说明 |
|------|------|
| `fShaderDerivativeSupport` | 导数函数支持（dFdx、dFdy） |
| `fDualSourceBlendingSupport` | 双源混合支持 |
| `fIntegerSupport` | 整数运算支持 |
| `fNonsquareMatrixSupport` | 非方阵支持 |
| `fInverseHyperbolicSupport` | 反双曲函数支持 |
| `fFBFetchSupport` | 帧缓冲读取支持 |
| `fUsesPrecisionModifiers` | 是否使用精度修饰符 |
| `fFlatInterpolationSupport` | 平面插值支持 |
| `fNoPerspectiveInterpolationSupport` | 无透视插值支持 |
| `fSampleMaskSupport` | 采样掩码支持 |
| `fExternalTextureSupport` | 外部纹理支持 |
| `fInfinitySupport` | 无穷大支持 |
| `fFloatIs32Bits` | float 是否为 32 位 |
| `fBuiltinFMASupport` | 内建融合乘加支持 |
| `fBuiltinDeterminantSupport` | 内建行列式函数支持 |

## 依赖关系

### 依赖的模块

| 模块 | 关系 | 说明 |
|------|------|------|
| `SkSL::ShaderCaps` | 继承 | SkSL 编译器着色器能力基类 |
| `GrContextOptions` | 配置源 | 用户配置选项 |
| `SkJSONWriter` | 工具 | JSON 输出工具（调试用） |

### 被依赖的模块

| 模块 | 使用方式 | 说明 |
|------|---------|------|
| `GrCaps` | 组合 | 通用能力类持有 GrShaderCaps |
| `GrProcessor` | 查询 | 处理器查询着色器能力 |
| `GrGLSLShaderBuilder` | 查询 | 着色器构建器根据能力生成代码 |
| `GrProgramBuilder` | 查询 | 程序构建器使用能力信息 |
| `SkSL::Compiler` | 配置 | SkSL 编译器使用能力进行优化和变通 |

## 设计模式与设计决策

### 继承扩展模式

继承 `SkSL::ShaderCaps` 并扩展 Ganesh 特定能力：
- **优势**：复用 SkSL 编译器的能力查询系统
- **分层**：SkSL 层负责语言特性，Ganesh 层负责渲染特性
- **一致性**：统一的能力查询接口

### 布尔标志设计

使用独立的布尔变量而非位标志：
- **可读性**：代码中直接使用 `caps.fDstReadInShaderSupport` 更清晰
- **调试**：便于在调试器中查看各项能力
- **扩展性**：添加新能力无需修改位布局

### 扩展字符串封装

将扩展名称封装为成员变量：
```cpp
const char* fNoPerspectiveInterpolationExtensionString = nullptr;
```

**优势：**
- 集中管理扩展信息
- 避免硬编码字符串
- 便于不同后端设置不同的扩展名称

### 变通方案标志

针对驱动程序 bug 设置专门的标志：
- 明确标识问题来源
- 便于跟踪和移除（当驱动更新后）
- 允许用户通过 `fDisableDriverCorrectnessWorkarounds` 禁用

### 配置覆盖机制

提供 `applyOptionsOverrides` 允许用户覆盖自动检测的能力：
- **测试目的**：强制禁用某些功能进行测试
- **性能调优**：启用简化着色器模式
- **调试工具**：绕过驱动 bug 变通方案以定位问题

## 性能考量

### 简化着色器模式

`fReducedShaderMode` 标志用于减少着色器变体：
- 使用更简单的渲染算法
- 减少 uniform 变量的使用
- 降低着色器编译时间和内存占用
- **适用场景**：低端设备、快速原型开发

### 精度信息

`fHalfIs32Bits` 和 `fHasLowFragmentPrecision` 影响精度选择：
- 如果 half 实际为 32 位，使用 float 无性能差异
- 低精度设备上优先使用 mediump/lowp 以提高性能
- 帮助着色器生成器做出正确的精度权衡

### 数组索引支持

`fNonconstantArrayIndexSupport` 影响代码生成策略：
- 不支持时：展开循环或使用分支
- 支持时：使用动态索引，代码更紧凑
- **性能影响**：循环展开可能增加寄存器压力

### 位操作支持

`fBitManipulationSupport` 影响某些算法的实现：
- 支持时：可以使用高效的位操作实现
- 不支持时：使用浮点运算模拟，性能较低

### 帧缓冲读取

`fDstReadInShaderSupport` 决定混合模式的实现方式：
- 支持时：在片段着色器中直接读取目标像素
- 不支持时：使用纹理或多通道渲染
- **性能影响**：帧缓冲读取通常比纹理采样快

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/sksl/SkSLUtil.h` | 父类定义 | SkSL::ShaderCaps 定义 |
| `include/gpu/ganesh/GrContextOptions.h` | 配置源 | 用户配置选项 |
| `src/utils/SkJSONWriter.h` | 工具 | JSON 输出（调试用） |
| `src/gpu/ganesh/GrCaps.h` | 持有者 | 通用能力类 |
| `src/gpu/ganesh/glsl/GrGLSLShaderBuilder.h` | 使用者 | 着色器构建器 |
| `src/gpu/ganesh/GrProcessor.h` | 使用者 | 处理器基类 |
| `src/gpu/ganesh/gl/GrGLCaps.cpp` | 初始化 | OpenGL 后端初始化着色器能力 |
| `src/gpu/ganesh/vk/GrVkCaps.cpp` | 初始化 | Vulkan 后端初始化着色器能力 |
| `src/gpu/ganesh/mtl/GrMtlCaps.mm` | 初始化 | Metal 后端初始化着色器能力 |
