# GrSkSLFP

> 源文件
> - src/gpu/ganesh/effects/GrSkSLFP.h
> - src/gpu/ganesh/effects/GrSkSLFP.cpp

## 概述

`GrSkSLFP` 是基于 SkSL（Skia Shading Language）定义的片段处理器，允许通过 SkSL 代码动态创建自定义 GPU 效果。该类解析 SkSL 源码，提取 Uniform 和子效果声明，编译为 GPU 着色器代码，并管理运行时参数绑定。支持编译时优化、内联子效果、Uniform 折叠等高级特性，是 Skia 运行时效果（RuntimeEffect）的 GPU 后端核心实现。

## 架构位置

- **模块层级**：`src/gpu/ganesh/effects/` - Ganesh 效果层
- **继承关系**：`GrSkSLFP` -> `GrFragmentProcessor`
- **使用者**：`SkRuntimeEffect`、自定义着色器、图像滤镜
- **编译器**：SkSL 编译器（`SkSL::Compiler`）

## 主要类与结构体

### GrSkSLFP

**静态工厂**：
```cpp
static std::unique_ptr<GrSkSLFP> Make(
    const SkRuntimeEffect*, const char* name,
    std::unique_ptr<GrFragmentProcessor> inputFP,
    sk_sp<const SkData> uniforms);
```

**核心功能**：
- 解析 SkSL 代码
- 编译为 GLSL/Metal 着色器
- 管理 Uniform 数据
- 绑定子效果（采样器）

## 内部实现细节

### SkSL 编译流程

1. **解析**：SkSL 源码 -> AST（抽象语法树）
2. **语义分析**：类型检查、符号解析
3. **优化**：常量折叠、死代码消除、内联
4. **代码生成**：AST -> GLSL/MSL/SPIR-V

### Uniform 管理

**Uniform 布局**：
- 按 SkSL 声明顺序排列
- 遵循目标平台对齐规则
- 打包到 Uniform 缓冲区

**运行时绑定**：
- 从 `sk_sp<const SkData>` 读取 Uniform 值
- 复制到 GPU 缓冲区

### 子效果处理

**采样器**：
- SkSL 中的 `shader` 类型映射为采样器
- 创建子 `GrFragmentProcessor`
- 链接到主效果

**内联优化**：
- 简单子效果内联到主着色器
- 减少纹理采样和函数调用

### 编译时优化

**常量传播**：
- 编译时已知的 Uniform 直接替换
- 简化表达式计算

**死代码消除**：
- 移除未使用的变量和分支
- 减少着色器指令数

## 设计模式与设计决策

### 解释器模式

SkSL 作为领域特定语言（DSL），解释为 GPU 着色器代码。

### 延迟编译

仅在首次使用时编译着色器，支持运行时效果。

### 数据驱动

Uniform 和子效果通过数据配置，代码与数据分离。

## 性能考量

### 编译缓存

编译后的着色器缓存复用，避免重复编译。

### 内联优化

简单子效果内联减少采样和函数调用开销。

### Uniform 批处理

批量上传 Uniform 减少 API 调用。

## 相关文件

- `src/sksl/SkSLCompiler.h` - SkSL 编译器
- `src/gpu/ganesh/GrFragmentProcessor.h` - 片段处理器基类
- `src/core/SkRuntimeEffect.h` - 运行时效果公共接口
