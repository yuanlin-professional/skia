# GrGLShaderStringBuilder

> 源文件
> - src/gpu/ganesh/gl/builders/GrGLShaderStringBuilder.h
> - src/gpu/ganesh/gl/builders/GrGLShaderStringBuilder.cpp

## 概述

`GrGLShaderStringBuilder` 是 Ganesh OpenGL 后端中负责着色器编译和链接的工具模块。该模块提供了一组函数，用于将 SkSL（Skia Shading Language）代码转换为 GLSL，编译着色器对象，并将其附加到程序对象。它还提供了链接状态检查和错误报告功能。该模块是 Ganesh 着色器构建流程的底层基础设施，处理与 OpenGL 驱动的直接交互。

## 架构位置

`GrGLShaderStringBuilder` 位于 Ganesh OpenGL 后端的着色器构建层：

```
Ganesh Program Builder
    ↓
SkSL Compiler (SkSL → GLSL)
    ↓
Shader String Builder (GrGLShaderStringBuilder) ← 当前模块
    ↓
OpenGL Driver (glCompileShader, glLinkProgram)
```

该模块在着色器生成的最后阶段工作，负责将高级的 SkSL 代码转换为 GPU 可执行的二进制程序。

## 主要类与结构体

该模块不包含类定义，提供三个核心函数和一个内联辅助函数：

| 函数名 | 功能描述 |
|--------|----------|
| `skgpu::SkSLToGLSL` | 将 SkSL 代码转换为 GLSL 代码（内联函数） |
| `GrGLCompileAndAttachShader` | 编译并附加着色器到程序 |
| `GrGLCheckLinkStatus` | 检查程序链接状态并报告错误 |

## 公共 API 函数

### skgpu::SkSLToGLSL（内联函数）

```cpp
inline bool SkSLToGLSL(const SkSL::ShaderCaps* caps,
                       const std::string& sksl,
                       SkSL::ProgramKind programKind,
                       const SkSL::ProgramSettings& settings,
                       SkSL::NativeShader* glsl,
                       SkSL::ProgramInterface* outInterface,
                       ShaderErrorHandler* errorHandler);
```

**功能**：将 SkSL 代码转换为 GLSL 代码。

**参数说明**：
- `caps`: 着色器能力查询对象
- `sksl`: 输入的 SkSL 源代码
- `programKind`: 程序类型（顶点着色器、片段着色器等）
- `settings`: 编译设置
- `glsl`: 输出的 GLSL 代码
- `outInterface`: 输出的程序接口信息
- `errorHandler`: 错误处理器

**返回值**：成功返回 `true`，失败返回 `false`。

**实现原理**：通过 `SkSLToBackend` 调用 `SkSL::ToGLSL` 后端生成器。

### GrGLCompileAndAttachShader

```cpp
GrGLuint GrGLCompileAndAttachShader(const GrGLContext& glCtx,
                                    GrGLuint programId,
                                    GrGLenum type,
                                    const SkSL::NativeShader& glsl,
                                    bool shaderWasCached,
                                    GrThreadSafePipelineBuilder::Stats* stats,
                                    GrContextOptions::ShaderErrorHandler* errorHandler);
```

**功能**：编译 GLSL 着色器并附加到程序对象。

**参数说明**：
- `glCtx`: OpenGL 上下文
- `programId`: 目标程序 ID
- `type`: 着色器类型（`GL_VERTEX_SHADER` 或 `GL_FRAGMENT_SHADER`）
- `glsl`: GLSL 源代码
- `shaderWasCached`: 着色器是否来自缓存（用于错误报告）
- `stats`: 统计信息收集器
- `errorHandler`: 错误处理器

**返回值**：成功返回着色器 ID，失败返回 0。

### GrGLCheckLinkStatus

```cpp
bool GrGLCheckLinkStatus(const GrGLGpu* gpu,
                         GrGLuint programID,
                         bool shaderWasCached,
                         GrContextOptions::ShaderErrorHandler* errorHandler,
                         const std::string* sksl[kGrShaderTypeCount],
                         const SkSL::NativeShader glsl[kGrShaderTypeCount]);
```

**功能**：检查程序链接状态，失败时报告详细错误信息。

**参数说明**：
- `gpu`: OpenGL GPU 对象
- `programID`: 程序 ID
- `shaderWasCached`: 着色器是否来自缓存
- `errorHandler`: 错误处理器
- `sksl`: SkSL 源代码数组（用于错误报告）
- `glsl`: GLSL 源代码数组（用于错误报告）

**返回值**：链接成功返回 `true`，失败返回 `false`。

## 内部实现细节

### 着色器编译流程

`GrGLCompileAndAttachShader` 的完整流程：

1. **创建着色器对象**
   ```cpp
   GR_GL_CALL_RET(gli, shaderId, CreateShader(type));
   ```
   调用 `glCreateShader` 创建指定类型的着色器对象。

2. **指定着色器源代码**
   ```cpp
   GR_GL_CALL(gli, ShaderSource(shaderId, 1, &source, &sourceLength));
   ```
   将 GLSL 字符串传递给 OpenGL 驱动。

3. **编译着色器**
   ```cpp
   stats->incShaderCompilations();
   GR_GL_CALL(gli, CompileShader(shaderId));
   ```
   调用 `glCompileShader` 并更新统计计数器。使用 `TRACE_EVENT` 标记编译事件。

4. **检查编译状态**
   ```cpp
   GR_GL_CALL(gli, GetShaderiv(shaderId, GR_GL_COMPILE_STATUS, &compiled));
   ```
   查询编译是否成功。

5. **处理编译错误**
   - 获取错误日志长度
   - 分配缓冲区读取错误信息
   - 调用 `errorHandler->compileError` 报告错误
   - 删除失败的着色器对象并返回 0

6. **附加到程序**
   ```cpp
   GR_GL_CALL(gli, AttachShader(programId, shaderId));
   ```
   将编译成功的着色器附加到程序对象。

**重要注意**：着色器 ID 在此返回，但着色器对象的删除延迟到链接完成后。这是为了规避 Android 模拟器的 GLES2 包装器 bug（会在着色器附加到程序后立即释放其内存）。

### 链接状态检查

`GrGLCheckLinkStatus` 的实现要点：

1. **查询链接状态**
   ```cpp
   GR_GL_CALL(gli, GetProgramiv(programID, GR_GL_LINK_STATUS, &linked));
   ```

2. **构建错误报告**（链接失败时）
   - 拼接 SkSL 代码（如果提供）
   - 拼接 GLSL 代码（如果提供）
   - Debug 构建中添加 "// Vertex SKSL" 等注释
   - Release 构建中省略注释减少输出

3. **获取链接日志**
   ```cpp
   GR_GL_CALL(gli, GetProgramiv(programID, GR_GL_INFO_LOG_LENGTH, &infoLen));
   GR_GL_CALL(gli, GetProgramInfoLog(programID, infoLen+1, &length, (char*)log.get()));
   ```

4. **报告错误**
   ```cpp
   errorHandler->compileError(allShaders.c_str(), errorMsg, shaderWasCached);
   ```
   将完整的着色器源码和错误信息传递给错误处理器。

### Chrome 命令缓冲区兼容性

代码中多处出现读取长度参数的"冗余"调用：
```cpp
GrGLsizei length = GR_GL_INIT_ZERO;
GR_GL_CALL(gli, GetShaderInfoLog(shaderId, infoLen+1, &length, (char*)log.get()));
```

这是为了解决 Chrome 命令缓冲区参数验证的 bug，即使不使用 `length` 也必须提供该参数。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLContext` | 访问 OpenGL 接口和上下文信息 |
| `GrGLInterface` | OpenGL 函数指针表 |
| `SkSL::ToGLSL` | SkSL 到 GLSL 的代码生成器 |
| `SkSLToBackend` | SkSL 编译器后端接口 |
| `GrThreadSafePipelineBuilder::Stats` | 编译统计信息 |
| `GrContextOptions::ShaderErrorHandler` | 错误报告接口 |
| `SkAutoMalloc` | 自动内存管理 |
| `SkTraceEvent` | 性能追踪事件 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| `GrGLProgramBuilder` | 在程序构建过程中调用编译函数 |
| `GrGLGpu` | 着色器编译和程序创建 |
| `GrGLProgram` | 程序对象管理 |

## 设计模式与设计决策

### 函数式设计

该模块采用纯函数设计而非类封装：
- 无状态管理需求
- 每次编译都是独立操作
- 避免不必要的对象创建开销

### 错误处理策略

采用回调式错误处理：
- 通过 `ShaderErrorHandler` 接口报告错误
- 允许不同的使用者自定义错误处理逻辑
- 支持断言、日志、UI 提示等多种错误处理方式

### 统计信息收集

编译计数器 `stats->incShaderCompilations()` 用于：
- 性能分析
- Cache 命中率计算
- 开发调试

### 性能追踪集成

使用 Skia 的追踪系统标记关键事件：
- `TRACE_EVENT0_ALWAYS("skia.shaders", "driver_compile_shader")`
- `ATRACE_ANDROID_FRAMEWORK("checkCompiled")`

这些标记可以被系统性能分析工具（如 Android Systrace）捕获。

### 延迟着色器删除

着色器对象在 `AttachShader` 后不立即删除的原因：
- Android 模拟器 bug 规避
- 保证跨平台兼容性
- 调用者负责在链接后删除

## 性能考量

### 编译时间追踪

通过 `TRACE_EVENT` 标记，可以精确测量：
- 驱动编译时间
- 编译状态查询时间

这对于识别性能瓶颈至关重要。

### 内存管理优化

**错误日志缓冲区**：
- 使用 `SkAutoMalloc` 自动管理内存
- 只在出错时分配
- 离开作用域自动释放

**字符串拼接**：
- 使用 `SkSL::String::appendf` 避免多次内存分配

### Shader Cache 支持

`shaderWasCached` 参数用于区分：
- 首次编译：期望成功，失败是严重错误
- 缓存加载：可能因驱动更新而失败，需要重新编译

这影响错误报告的严重性级别。

### 统计信息收集

`stats->incShaderCompilations()` 用于：
- 监控编译频率
- 评估 cache 效果
- 识别过度编译问题

## 相关文件

| 文件路径 | 关系说明 |
|----------|----------|
| `src/gpu/ganesh/gl/builders/GrGLProgramBuilder.h/cpp` | 调用编译和链接函数 |
| `src/gpu/SkSLToBackend.h` | SkSL 编译器后端框架 |
| `src/sksl/codegen/SkSLGLSLCodeGenerator.h` | GLSL 代码生成器 |
| `src/gpu/ganesh/gl/GrGLContext.h` | OpenGL 上下文封装 |
| `include/gpu/ganesh/gl/GrGLInterface.h` | OpenGL 函数接口 |
| `src/gpu/ganesh/GrThreadSafePipelineBuilder.h` | 管线构建器和统计 |
| `include/gpu/ganesh/GrContextOptions.h` | 上下文选项和错误处理器 |
| `src/core/SkTraceEvent.h` | 性能追踪宏 |
| `src/gpu/ganesh/gl/GrGLUtil.h` | GL 工具函数和宏 |
