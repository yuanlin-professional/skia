# GrGLProgramBuilder

> 源文件
> - src/gpu/ganesh/gl/builders/GrGLProgramBuilder.h
> - src/gpu/ganesh/gl/builders/GrGLProgramBuilder.cpp

## 概述

`GrGLProgramBuilder` 是 Ganesh OpenGL 后端中负责构建完整着色器程序的核心类。它协调整个着色器编译流程，从 SkSL 代码生成到 GLSL 编译、链接，再到 uniform 和顶点属性绑定。该类还负责持久化缓存的管理，支持程序二进制缓存和源代码缓存，显著提升着色器编译性能。`GrGLProgramBuilder` 是 Ganesh 着色器基础设施的顶层组织者，整合了 uniform 管理、varying 管理、代码生成等多个子系统。

## 架构位置

`GrGLProgramBuilder` 位于 Ganesh 着色器构建系统的顶层：

```
GrDirectContext
    ↓
GrThreadSafePipelineBuilder
    ↓
GrGLProgramBuilder ← 当前模块
    ├─ GrGLSLProgramBuilder (基类)
    ├─ GrGLUniformHandler
    ├─ GrGLVaryingHandler
    └─ GrGLShaderStringBuilder
         ↓
    OpenGL Program Object
```

该模块是着色器构建流程的总控制器，连接高层的程序描述和底层的 GL 对象创建。

## 主要类与结构体

### GrGLPrecompiledProgram

**功能**：封装预编译的程序信息。

**关键成员变量**：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fProgramID` | `GrGLuint` | OpenGL 程序 ID |
| `fInterface` | `SkSL::Program::Interface` | 程序接口信息 |

### GrGLProgramBuilder

**功能**：构建 OpenGL 着色器程序的主控类。

**继承关系**：
- 基类：`GrGLSLProgramBuilder`

**关键成员变量**：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fGpu` | `GrGLGpu*` | OpenGL GPU 对象 |
| `fVaryingHandler` | `GrGLVaryingHandler` | Varying 变量管理器 |
| `fUniformHandler` | `GrGLUniformHandler` | Uniform 变量管理器 |
| `fAttributes` | `std::unique_ptr<GrGLProgram::Attribute[]>` | 顶点属性数组 |
| `fVertexAttributeCnt` | `int` | 顶点属性数量 |
| `fInstanceAttributeCnt` | `int` | 实例属性数量 |
| `fVertexStride` | `size_t` | 顶点步幅 |
| `fInstanceStride` | `size_t` | 实例步幅 |
| `fCached` | `sk_sp<SkData>` | 从缓存加载的数据 |

## 公共 API 函数

### CreateProgram（静态方法）

```cpp
static sk_sp<GrGLProgram> CreateProgram(GrDirectContext* dContext,
                                        const GrProgramDesc& desc,
                                        const GrProgramInfo& programInfo,
                                        const GrGLPrecompiledProgram* precompiledProgram = nullptr);
```

**功能**：创建着色器程序的主入口函数。

**参数说明**：
- `dContext`: Direct Context 对象
- `desc`: 程序描述符（用作缓存 key）
- `programInfo`: 程序信息（包含处理器和状态）
- `precompiledProgram`: 可选的预编译程序（跳过编译步骤）

**返回值**：成功返回 `GrGLProgram` 智能指针，失败返回 `nullptr`。

**流程**：
1. 创建 `GrGLProgramBuilder` 实例
2. 尝试从持久化缓存加载
3. 调用 `emitAndInstallProcs()` 生成 SkSL 代码
4. 调用 `finalize()` 完成编译和链接

### PrecompileProgram（静态方法）

```cpp
static bool PrecompileProgram(GrDirectContext* dContext,
                              GrGLPrecompiledProgram* precompiledProgram,
                              const SkData& cachedData);
```

**功能**：从缓存数据预编译程序。

**参数说明**：
- `dContext`: Direct Context 对象
- `precompiledProgram`: 输出参数，存储编译结果
- `cachedData`: 缓存的着色器数据

**返回值**：成功返回 `true`，失败返回 `false`。

**用途**：
- 在后台预热着色器缓存
- 减少首次渲染的延迟

## 内部实现细节

### 程序构建流程

`CreateProgram` 的完整流程：

1. **环境设置**
   ```cpp
   GrAutoLocaleSetter als("C");  // 确保数字格式一致
   TRACE_EVENT0_ALWAYS("skia.shaders", "shader_compile");
   ```

2. **缓存查询**
   ```cpp
   auto persistentCache = dContext->priv().getPersistentCache();
   if (persistentCache && !precompiledProgram) {
       builder.fCached = persistentCache->load(*key);
   }
   ```

3. **代码生成**
   ```cpp
   if (!builder.emitAndInstallProcs()) {
       return nullptr;
   }
   ```
   调用基类方法生成 SkSL 代码。

4. **最终化**
   ```cpp
   return builder.finalize(precompiledProgram);
   ```

### finalize 实现细节

`finalize` 是最复杂的函数，处理多种缓存场景：

**1. 创建程序对象**
```cpp
GrGLuint programID;
if (precompiledProgram) {
    programID = precompiledProgram->fProgramID;
} else {
    GL_CALL_RET(programID, CreateProgram());
}
```

**2. 缓存命中处理**

**程序二进制缓存（kGLPB_Tag）**：
- 直接调用 `glProgramBinary` 加载二进制
- 检查链接状态
- 成功则跳过编译步骤

**GLSL 源码缓存（kGLSL_Tag）**：
- 加载预编译的 GLSL 代码
- 跳过 SkSL → GLSL 转换
- 仍需调用 `glCompileShader`

**SkSL 源码缓存（kSKSL_Tag）**：
- 加载 SkSL 源码（用于工具覆盖）
- 完整执行编译流程

**3. 缓存未命中处理**

```cpp
// 片段着色器编译
if (!skgpu::SkSLToGLSL(...)) {
    cleanup_program(fGpu, programID, shadersToDelete);
    return nullptr;
}
if (!this->compileAndAttachShaders(...)) {
    cleanup_program(fGpu, programID, shadersToDelete);
    return nullptr;
}

// 顶点着色器编译
// ... 类似流程
```

**4. 属性和 Uniform 绑定**

```cpp
this->computeCountsAndStrides(programID, geomProc, true);
this->bindProgramResourceLocations(programID);
```

**5. 程序链接**

```cpp
GL_CALL(LinkProgram(programID));
if (!GrGLCheckLinkStatus(...)) {
    cleanup_program(fGpu, programID, shadersToDelete);
    return nullptr;
}
```

**6. 存储到缓存**

```cpp
if (!cached && !precompiledProgram) {
    this->storeShaderInCache(interface, programID, glsl, isSkSL, &settings);
}
```

### 缓存存储策略

`storeShaderInCache` 支持两种缓存格式：

**程序二进制缓存**（最快）：
```cpp
GrGLsizei length = 0;
GL_CALL(GetProgramiv(programID, GL_PROGRAM_BINARY_LENGTH, &length));
GrGLenum binaryFormat;
GL_CALL(GetProgramBinary(programID, length, &length, &binaryFormat, binary.get()));
```
存储格式：
- 版本号
- `kGLPB_Tag` 标签
- `SkSL::Program::Interface`
- 二进制格式
- 二进制数据

**源代码缓存**：
存储内容：
- `kGLSL_Tag` 或 `kSKSL_Tag` 标签
- GLSL/SkSL 源代码
- 程序接口
- 元数据（属性名称、设置等）

### 属性绑定

`computeCountsAndStrides` 函数处理顶点属性：

```cpp
auto addAttr = [&](int i, const auto& a) {
    fAttributes[i].fCPUType = a.cpuType();
    fAttributes[i].fGPUType = a.gpuType();
    fAttributes[i].fOffset = *a.offset();
    fAttributes[i].fLocation = i;
    if (bindAttribLocations) {
        GL_CALL(BindAttribLocation(programID, i, a.name()));
    }
};
```

属性位置按顺序分配：
- 顶点属性：0 到 `vertexAttributeCnt-1`
- 实例属性：从 `vertexAttributeCnt` 开始

### 片段输出绑定

`bindProgramResourceLocations` 绑定片段着色器输出：

```cpp
if (caps.bindFragDataLocationSupport()) {
    GL_CALL(BindFragDataLocation(programID, 0,
                                 GrGLSLFragmentShaderBuilder::DeclaredColorOutputName()));
    if (fFS.hasSecondaryOutput()) {
        GL_CALL(BindFragDataLocationIndexed(programID, 0, 1,
                              GrGLSLFragmentShaderBuilder::DeclaredSecondaryColorOutputName()));
    }
}
```

- 主颜色输出：location 0
- 次要输出（双源混合）：location 0, index 1

### PrecompileProgram 实现

该函数支持离线预编译：

1. **解析缓存数据**（仅支持 SkSL 格式）
2. **编译着色器**（Lambda 表达式封装）
3. **绑定属性和输出**
4. **链接程序**
5. **存储结果**

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLSLProgramBuilder` | 基类，提供代码生成框架 |
| `GrGLUniformHandler` | Uniform 变量管理 |
| `GrGLVaryingHandler` | Varying 变量管理 |
| `GrGLShaderStringBuilder` | 着色器编译和链接 |
| `GrPersistentCacheUtils` | 持久化缓存序列化 |
| `GrGLGpu` | OpenGL GPU 接口 |
| `GrGeometryProcessor` | 几何处理器（定义顶点属性） |
| `skgpu::SkSLToGLSL` | SkSL 到 GLSL 转换 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| `GrGLGpu` | 创建和管理程序对象 |
| `GrThreadSafePipelineBuilder` | 多线程着色器编译 |
| `GrDirectContext` | 上下文级别的程序创建 |

## 设计模式与设计决策

### Builder 模式

类名体现了 Builder 模式：
- 逐步构建复杂的程序对象
- 分离构建过程和表示
- 支持多种配置和选项

### 缓存分层策略

三级缓存优先级：
1. **程序二进制**（最快，免编译）
2. **GLSL 源码**（跳过 SkSL 编译）
3. **SkSL 源码**（完整流程）

这种设计最大化了不同场景下的性能。

### 错误处理和清理

使用 RAII 和显式清理函数：
```cpp
cleanup_program(fGpu, programID, shadersToDelete);
```
确保错误路径不泄漏 GL 资源。

### 统计和追踪

集成多种监控机制：
- **TRACE_EVENT**：性能追踪
- **Stats**：编译计数统计
- **ShaderErrorHandler**：错误报告

### Locale 保护

```cpp
GrAutoLocaleSetter als("C");
```
确保浮点数格式化一致，避免不同 locale 下的着色器不兼容。

### 延迟着色器删除

着色器在链接后才删除：
```cpp
cleanup_shaders(fGpu, shadersToDelete);
```
避免 Android 模拟器的 bug（见 `GrGLShaderStringBuilder`）。

## 性能考量

### 缓存命中率优化

**程序二进制缓存**：
- 完全跳过编译和链接
- 加载时间 < 1ms
- 最高性能收益

**源代码缓存**：
- 跳过 SkSL 编译器
- 节省约 50% 编译时间

**统计追踪**：
```cpp
TRACE_EVENT0_ALWAYS("skia.shaders", "cache_hit");
TRACE_EVENT0_ALWAYS("skia.shaders", "cache_miss");
```

### 程序二进制提示

```cpp
GL_CALL(ProgramParameteri(programID, GR_GL_PROGRAM_BINARY_RETRIEVABLE_HINT, GR_GL_TRUE));
```
提示驱动保留可检索的二进制，提升缓存效率。

### 编译时间追踪

```cpp
TRACE_EVENT0_ALWAYS("skia.shaders", "shader_compile");
TRACE_EVENT0_ALWAYS("skia.shaders", "driver_link_program");
```
精确测量编译各阶段耗时。

### 预编译支持

`PrecompileProgram` 允许：
- 后台线程预编译
- 启动时预热缓存
- 减少首帧延迟

### 避免冗余绑定

```cpp
this->resolveProgramResourceLocations(programID, usedProgramBinaries);
```
使用二进制时强制查询 uniform 位置，避免状态不同步。

## 相关文件

| 文件路径 | 关系说明 |
|----------|----------|
| `src/gpu/ganesh/glsl/GrGLSLProgramBuilder.h/cpp` | 基类，代码生成框架 |
| `src/gpu/ganesh/gl/builders/GrGLShaderStringBuilder.h/cpp` | 着色器编译工具 |
| `src/gpu/ganesh/gl/GrGLUniformHandler.h/cpp` | Uniform 管理 |
| `src/gpu/ganesh/gl/GrGLVaryingHandler.h` | Varying 管理 |
| `src/gpu/ganesh/gl/GrGLProgram.h/cpp` | 程序对象 |
| `src/gpu/ganesh/gl/GrGLGpu.h/cpp` | OpenGL GPU 接口 |
| `src/gpu/ganesh/GrPersistentCacheUtils.h/cpp` | 缓存序列化工具 |
| `src/gpu/ganesh/GrThreadSafePipelineBuilder.h` | 多线程构建器 |
| `src/gpu/SkSLToBackend.h` | SkSL 编译器后端 |
| `include/gpu/ganesh/GrContextOptions.h` | 上下文选项 |
