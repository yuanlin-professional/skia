# SkSLProgramSettings — SkSL 程序编译设置

> 源文件：[`src/sksl/SkSLProgramSettings.h`](../../src/sksl/SkSLProgramSettings.h)

## 概述

SkSLProgramSettings.h 定义了 SkSL 编译器的程序编译设置（`ProgramSettings`）和程序配置（`ProgramConfig`）两个核心结构体。`ProgramSettings` 包含所有影响编译行为的开关和参数，而 `ProgramConfig` 将设置与程序类型绑定，并提供一系列用于判断程序类型的静态辅助方法。

该文件 180 行，是 SkSL 编译器配置系统的核心组件。

## 架构位置

```
SkSL 编译器
  ├── ProgramSettings (编译参数)
  │     ├── 优化设置（内联、死代码消除等）
  │     ├── GLSL/SPIR-V 特定设置
  │     └── 运行时效果设置
  └── ProgramConfig (编译配置)
        ├── ProgramKind（程序类型）
        ├── ProgramSettings（设置实例）
        └── 类型判断辅助函数
```

`ProgramSettings` 和 `ProgramConfig` 在整个 SkSL 编译管线中被广泛使用，从词法分析到代码生成的每个阶段都可能查询这些设置。

## 主要类与结构体

### `ProgramSettings`

编译器设置结构体，所有字段都有默认值：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fFragColorIsInOut` | `bool` | `false` | sk_FragColor 是否声明为 inout（用于 framebuffer-fetch） |
| `fForceHighPrecision` | `bool` | `false` | 强制所有 half 类型为 float |
| `fSharpenTextures` | `bool` | `false` | 对纹理查找的 LOD 添加 -0.5 偏移 |
| `fForceNoRTFlip` | `bool` | `false` | 禁用渲染目标翻转 |
| `fRTFlipOffset` | `int` | `-1` | RT 翻转 uniform 在 uniform 缓冲区中的偏移 |
| `fRTFlipBinding` | `int` | `-1` | RT 翻转 uniform 的 SPIR-V binding 编号 |
| `fRTFlipSet` | `int` | `-1` | RT 翻转 uniform 的 SPIR-V set 编号 |
| `fDefaultUniformSet` | `int` | `0` | 未指定 layout 的 uniform 默认 set |
| `fDefaultUniformBinding` | `int` | `0` | 未指定 layout 的 uniform 默认 binding |
| `fOptimize` | `bool` | `true` | 启用优化器 |
| `fRemoveDeadFunctions` | `bool` | `true` | 移除未调用的函数（需要 fOptimize） |
| `fRemoveDeadVariables` | `bool` | `true` | 移除未使用的变量（需要 fOptimize） |
| `fInlineThreshold` | `int` | `kDefaultInlineThreshold` | 内联阈值（需要 fOptimize） |
| `fForceNoInline` | `bool` | `false` | 强制所有函数添加 noinline 修饰符 |
| `fAllowNarrowingConversions` | `bool` | `false` | 允许到低精度类型的隐式转换 |
| `fValidateSPIRV` | `bool` | `true` | Debug 模式下验证 SPIR-V 输出 |
| `fUseVulkanPushConstantsForGaneshRTAdjust` | `bool` | `false` | 使用 Vulkan push constants |
| `fMaxVersionAllowed` | `Version` | `k100` | 最大允许的 SkSL 版本 |
| `fUseMemoryPool` | `bool` | `true` | 使用内存池分配 IR 节点 |

### `ProgramConfig`

程序完整配置结构体，组合了模块类型、程序类型和设置：

```cpp
struct ProgramConfig {
    ModuleType fModuleType;
    ProgramKind fKind;
    ProgramSettings fSettings;
    SkSL::Version fRequiredSkSLVersion = SkSL::Version::k100;
    // ...
};
```

## 公共 API 函数

### ProgramConfig 成员方法

```cpp
bool isBuiltinCode();
```
- 判断是否在编译 SkSL 内置模块

```cpp
bool enforcesSkSLVersion() const;
```
- 判断是否强制执行 SkSL 版本检查（仅运行时效果和 Mesh 程序）

```cpp
bool strictES2Mode() const;
```
- 判断是否处于严格的 ES2 兼容模式

```cpp
const char* versionDescription() const;
```
- 返回版本指令字符串（如 `"#version 100\n"`）

### ProgramConfig 静态方法

| 方法 | 说明 |
|------|------|
| `IsFragment(kind)` | 判断是否为片段着色器（含 Graphite 变体） |
| `IsVertex(kind)` | 判断是否为顶点着色器（含 Graphite 变体） |
| `IsCompute(kind)` | 判断是否为计算着色器 |
| `IsRuntimeEffect(kind)` | 判断是否为运行时效果（含所有变体和 Mesh） |
| `IsRuntimeShader(kind)` | 判断是否为运行时着色器 |
| `IsRuntimeColorFilter(kind)` | 判断是否为运行时颜色过滤器 |
| `IsRuntimeBlender(kind)` | 判断是否为运行时混合器 |
| `IsMesh(kind)` | 判断是否为自定义 Mesh 程序 |
| `AllowsPrivateIdentifiers(kind)` | 判断是否允许私有标识符 |

## 内部实现细节

### 严格 ES2 模式

`strictES2Mode()` 同时检查三个条件：
1. `fMaxVersionAllowed` 为 `Version::k100`
2. `fRequiredSkSLVersion` 为 `Version::k100`
3. 当前程序类型需要强制版本检查

此模式限制了可用的语言功能，例如要求 `for` 循环必须是完全可展开的。

### 私有标识符访问控制

`AllowsPrivateIdentifiers` 对非 Private 前缀的运行时效果和 Mesh 程序返回 `false`，阻止公共运行时效果访问 SkSL 内部标识符。Private 变体（如 `kPrivateRuntimeShader`）则允许访问。

### 优化选项的依赖关系

`fRemoveDeadFunctions`、`fRemoveDeadVariables` 和 `fInlineThreshold` 都依赖于 `fOptimize = true`。注释指出，即使 `fOptimize` 为 false，常量折叠等用于完全求值常量表达式的优化仍然不会被禁用。

## 依赖关系

- `include/sksl/SkSLVersion.h` — SkSL 版本枚举
- `src/sksl/SkSLDefines.h` — SkSL 常量定义（如 `kDefaultInlineThreshold`）
- `src/sksl/SkSLModule.h` — 模块类型定义
- `src/sksl/SkSLProgramKind.h` — 程序类型枚举
- `<optional>`, `<vector>` — 标准库

## 设计模式与设计决策

- **数据对象模式**：`ProgramSettings` 是纯数据结构，所有字段都有合理的默认值，调用者只需修改需要自定义的部分。
- **类型判断封装**：通过 `ProgramConfig` 的静态方法将程序类型的分类逻辑集中管理，避免在编译器各处散布类型判断。
- **公开/私有运行时效果分离**：通过独立的枚举值区分公开和私有运行时效果，实现细粒度的访问控制。
- **版本强制策略**：仅对运行时效果和 Mesh 程序强制版本检查，GPU 着色器程序不受限制。

## 性能考量

1. **内存池开关**：`fUseMemoryPool` 默认启用，通常可显著加速编译。禁用时可用于内存问题诊断。
2. **优化控制**：`fOptimize`、`fRemoveDeadFunctions`、`fRemoveDeadVariables` 控制编译器优化级别，影响编译时间和输出代码质量的平衡。
3. **内联阈值**：`fInlineThreshold` 控制函数内联的激进程度，阈值越高可能生成更快但更大的代码。
4. **精度控制**：`fForceHighPrecision` 将 half 提升为 float，可能影响 GPU 着色器执行效率。

## 相关文件

- `src/sksl/SkSLProgramKind.h` — 程序类型枚举定义
- `src/sksl/SkSLDefines.h` — 内联阈值等常量定义
- `src/sksl/SkSLModule.h` — 模块类型定义
- `src/sksl/SkSLCompiler.h` — 编译器主类（使用 ProgramConfig）
- `include/sksl/SkSLVersion.h` — SkSL 版本定义
