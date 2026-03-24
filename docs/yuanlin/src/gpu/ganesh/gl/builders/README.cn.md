# builders/ - GL 着色器程序构建器

## 概述

`builders/` 目录包含 OpenGL 着色器程序的构建、编译和链接逻辑。它负责将 Skia 内部的渲染管线描述（`GrProgramInfo`）转化为可执行的 GL 着色器程序（`GrGLProgram`）。这是 Ganesh GL 后端中着色器管理的核心模块。

该目录的核心类 `GrGLProgramBuilder` 继承自 `GrGLSLProgramBuilder`，协调了从 SkSL 到 GLSL 的编译、GL shader 对象的创建、程序链接、属性定位和二进制缓存等完整流程。

## 文件分类索引

### 1. 程序构建 — Program Builder

| 文件 | 说明 |
|------|------|
| GrGLProgramBuilder.h / GrGLProgramBuilder.cpp | GL 着色器程序构建器（SkSL→GLSL 编译、链接、缓存） |

### 2. 着色器编译工具 — Shader Compilation

| 文件 | 说明 |
|------|------|
| GrGLShaderStringBuilder.h / GrGLShaderStringBuilder.cpp | Shader 编译与链接工具函数 |

## 关键类

### GrGLProgramBuilder

继承自 `GrGLSLProgramBuilder`，是 GL 着色器程序的工厂类。

**核心静态方法：**
```cpp
// 创建着色器程序（可选使用预编译缓存）
static sk_sp<GrGLProgram> CreateProgram(GrDirectContext*,
                                         const GrProgramDesc&,
                                         const GrProgramInfo&,
                                         const GrGLPrecompiledProgram* = nullptr);

// 预编译着色器（用于程序二进制缓存）
static bool PrecompileProgram(GrDirectContext*, GrGLPrecompiledProgram*, const SkData&);
```

**内部流程：**
1. 通过 `GrGLSLProgramBuilder` 基类生成 SkSL 着色器代码
2. 调用 `skgpu::SkSLToGLSL()` 将 SkSL 转换为 GLSL
3. `compileAndAttachShaders()` 编译 GLSL 并附加到 GL 程序
4. `computeCountsAndStrides()` 计算顶点属性布局
5. `finalize()` 链接程序并提取 Uniform 位置
6. 可选地将编译结果缓存为程序二进制（`storeShaderInCache`）

### GrGLPrecompiledProgram

一个轻量结构体，持有预编译的 GL 程序 ID 和 SkSL 程序接口信息，用于跳过编译阶段直接使用已缓存的程序二进制。

### 工具函数

`GrGLShaderStringBuilder.h` 中定义了关键的编译和链接辅助函数：

```cpp
// SkSL到GLSL的转换函数
inline bool SkSLToGLSL(const SkSL::ShaderCaps* caps,
                        const std::string& sksl,
                        SkSL::ProgramKind programKind,
                        const SkSL::ProgramSettings& settings,
                        SkSL::NativeShader* glsl, ...);

// 编译并附加单个shader到程序
GrGLuint GrGLCompileAndAttachShader(const GrGLContext& glCtx,
                                     GrGLuint programId,
                                     GrGLenum type,
                                     const SkSL::NativeShader& glsl, ...);

// 检查程序链接状态
bool GrGLCheckLinkStatus(const GrGLGpu* gpu, GrGLuint programID, ...);
```

## 依赖关系

- **上游：** `GrGLGpu::ProgramCache` 调用 `GrGLProgramBuilder::CreateProgram()` 创建程序
- **下游：** 依赖 `src/gpu/ganesh/glsl/` 中的 GLSL 代码生成器和 `src/sksl/` 中的 SkSL 编译器
- **产出：** 生成 `GrGLProgram` 实例，供 `GrGLGpu` 在渲染时使用

## 数据流

```
GrProgramInfo + GrProgramDesc
        |
        v
GrGLProgramBuilder::CreateProgram()
        |
        +-- GrGLSLProgramBuilder 生成 SkSL 代码
        |
        +-- SkSLToGLSL() 转换为 GLSL
        |
        +-- glCreateShader() + glCompileShader()
        |
        +-- glAttachShader() + glLinkProgram()
        |
        +-- 提取 Uniform 位置 / 属性布局
        |
        v
    GrGLProgram (可直接用于绘制)
```
