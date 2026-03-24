# GrGLUniformHandler

> 源文件
> - src/gpu/ganesh/gl/GrGLUniformHandler.h
> - src/gpu/ganesh/gl/GrGLUniformHandler.cpp

## 概述

`GrGLUniformHandler` 是 Skia Ganesh OpenGL 后端中负责管理着色器 uniform 变量的类。它继承自 `GrGLSLUniformHandler`，专门处理 OpenGL 程序的 uniform 声明、位置绑定和采样器管理。该类在着色器编译过程中收集所有 uniform 信息，并在程序链接后绑定或查询 uniform 位置。

该类的核心职责是：1) 在着色器构建阶段注册和命名 uniform 变量；2) 管理纹理采样器的绑定；3) 生成着色器源码中的 uniform 声明；4) 处理 uniform 位置的绑定或查询。

## 架构位置

```
GrGLSLUniformHandler (抽象基类)
    └── GrGLUniformHandler (GL具体实现)

调用链:
GrGLProgramBuilder -> GrGLUniformHandler -> GL uniform binding
```

该类是 `GrGLProgramBuilder` 的组成部分，负责着色器程序构建过程中的 uniform 管理。

## 主要类与结构体

### GrGLUniformHandler

**继承关系:**
- 继承自: `GrGLSLUniformHandler`

**关键常量:**

| 常量名 | 值 | 说明 |
|--------|---|------|
| `kUniformsPerBlock` | 8 | 每个块的 uniform 数量 |

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fUniforms` | `UniformInfoArray` | Uniform 信息数组 |
| `fSamplers` | `UniformInfoArray` | 采样器信息数组 |
| `fSamplerSwizzles` | `skia_private::TArray<skgpu::Swizzle>` | 采样器 swizzle 配置 |

### 类型别名

```cpp
typedef GrGLProgramDataManager::GLUniformInfo GLUniformInfo;
typedef GrGLProgramDataManager::UniformInfoArray UniformInfoArray;
```

## 公共 API 函数

### 访问器
- `const GrShaderVar& getUniformVariable(UniformHandle u) const` - 获取 uniform 变量
- `const char* getUniformCStr(UniformHandle u) const` - 获取 uniform 名称字符串
- `int numUniforms() const` - 获取 uniform 数量
- `UniformInfo& uniform(int idx)` - 获取可变 uniform 信息
- `const UniformInfo& uniform(int idx) const` - 获取不可变 uniform 信息

### Sampler 管理
- `const char* samplerVariable(SamplerHandle handle) const` - 获取采样器变量名
- `skgpu::Swizzle samplerSwizzle(SamplerHandle handle) const` - 获取采样器 swizzle

### 着色器生成
- `void appendUniformDecls(GrShaderFlags visibility, SkString*) const` - 追加 uniform 声明

### 位置绑定（仅限 GrGLProgramBuilder 使用）
- `void bindUniformLocations(GrGLuint programID, const GrGLCaps& caps)` - 绑定 uniform 位置
- `void getUniformLocations(GrGLuint programID, const GrGLCaps& caps, bool force)` - 查询 uniform 位置

## 内部实现细节

### Uniform 注册

```cpp
UniformHandle GrGLUniformHandler::internalAddUniformArray(
                                                   const GrProcessor* owner,
                                                   uint32_t visibility,
                                                   SkSLType type,
                                                   const char* name,
                                                   bool mangleName,
                                                   int arrayCount,
                                                   const char** outName) {
    SkASSERT(name && strlen(name));
    SkASSERT(valid_name(name));
    SkASSERT(0 != visibility);

    // 处理名称前缀
    char prefix = 'u';
    if ('u' == name[0] || !strncmp(name, GR_NO_MANGLE_PREFIX, strlen(GR_NO_MANGLE_PREFIX))) {
        prefix = '\0';  // 已有前缀或不需要混淆
    }
    SkString resolvedName = fProgramBuilder->nameVariable(prefix, name, mangleName);

    // 创建 uniform 信息
    GLUniformInfo tempInfo;
    tempInfo.fVariable = GrShaderVar{std::move(resolvedName),
                                     type,
                                     GrShaderVar::TypeModifier::Uniform,
                                     arrayCount};
    tempInfo.fVisibility = visibility;
    tempInfo.fOwner      = owner;
    tempInfo.fRawName    = SkString(name);
    tempInfo.fLocation   = -1;  // 初始位置未知

    fUniforms.push_back(tempInfo);

    if (outName) {
        *outName = fUniforms.back().fVariable.c_str();
    }
    return GrGLSLUniformHandler::UniformHandle(fUniforms.count() - 1);
}
```

### 采样器添加

```cpp
SamplerHandle GrGLUniformHandler::addSampler(
        const GrBackendFormat& backendFormat,
        GrSamplerState,
        const skgpu::Swizzle& swizzle,
        const char* name,
        const GrShaderCaps* shaderCaps) {
    SkASSERT(name && strlen(name));

    constexpr char prefix = 'u';
    SkString mangleName = fProgramBuilder->nameVariable(prefix, name, true);

    GrTextureType type = backendFormat.textureType();

    GLUniformInfo tempInfo;
    tempInfo.fVariable = GrShaderVar{std::move(mangleName),
                                     SkSLCombinedSamplerTypeForTextureType(type)};
    tempInfo.fVisibility = kFragment_GrShaderFlag;  // 采样器仅在片段着色器中
    tempInfo.fOwner      = nullptr;
    tempInfo.fRawName    = SkString(name);
    tempInfo.fLocation   = -1;

    fSamplers.push_back(tempInfo);
    fSamplerSwizzles.push_back(swizzle);
    SkASSERT(fSamplers.count() == fSamplerSwizzles.size());

    return GrGLSLUniformHandler::SamplerHandle(fSamplers.count() - 1);
}
```

### 着色器声明生成

```cpp
void GrGLUniformHandler::appendUniformDecls(GrShaderFlags visibility, SkString* out) const {
    // 生成 uniform 声明
    for (const UniformInfo& uniform : fUniforms.items()) {
        if (uniform.fVisibility & visibility) {
            uniform.fVariable.appendDecl(fProgramBuilder->shaderCaps(), out);
            out->append(";");
        }
    }

    // 生成采样器声明
    for (const UniformInfo& sampler : fSamplers.items()) {
        if (sampler.fVisibility & visibility) {
            sampler.fVariable.appendDecl(fProgramBuilder->shaderCaps(), out);
            out->append(";\n");
        }
    }
}
```

### Uniform 位置绑定

```cpp
void GrGLUniformHandler::bindUniformLocations(GrGLuint programID, const GrGLCaps& caps) {
    if (caps.bindUniformLocationSupport()) {
        int currUniform = 0;

        // 绑定普通 uniform
        for (GLUniformInfo& uniform : fUniforms.items()) {
            GL_CALL(BindUniformLocation(programID, currUniform, uniform.fVariable.c_str()));
            uniform.fLocation = currUniform;
            ++currUniform;
        }

        // 绑定采样器
        for (GLUniformInfo& sampler : fSamplers.items()) {
            GL_CALL(BindUniformLocation(programID, currUniform, sampler.fVariable.c_str()));
            sampler.fLocation = currUniform;
            ++currUniform;
        }
    }
}
```

### Uniform 位置查询

```cpp
void GrGLUniformHandler::getUniformLocations(GrGLuint programID, const GrGLCaps& caps, bool force) {
    if (!caps.bindUniformLocationSupport() || force) {
        // 查询普通 uniform 位置
        for (GLUniformInfo& uniform : fUniforms.items()) {
            GrGLint location;
            GL_CALL_RET(location, GetUniformLocation(programID, uniform.fVariable.c_str()));
            uniform.fLocation = location;
        }

        // 查询采样器位置
        for (GLUniformInfo& sampler : fSamplers.items()) {
            GrGLint location;
            GL_CALL_RET(location, GetUniformLocation(programID, sampler.fVariable.c_str()));
            sampler.fLocation = location;
        }
    }
}
```

### 名称验证

```cpp
bool valid_name(const char* name) {
    // 禁止未知的 "sk_" 前缀名称
    if (!strncmp(name, GR_NO_MANGLE_PREFIX, strlen(GR_NO_MANGLE_PREFIX))) {
        return !strcmp(name, SkSL::Compiler::RTADJUST_NAME);  // 仅允许特定名称
    }
    return true;
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLSLProgramBuilder` | 程序构建器 |
| `GrGLProgramBuilder` | GL 程序构建器 |
| `GrGLGpu` | GPU 接口 |
| `GrGLCaps` | OpenGL 能力查询 |
| `GrGLProgramDataManager` | Uniform 数据类型 |
| `GrShaderVar` | 着色器变量描述 |
| `skgpu::Swizzle` | 纹理通道重排 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrGLProgramBuilder` | 使用该类管理 uniform |
| `GrGLProgram` | 通过 `GrGLProgramDataManager` 间接使用 |

## 设计模式与设计决策

### 1. 块列表存储

使用 `SkTBlockList` 存储 uniform 信息：

```cpp
UniformInfoArray fUniforms;  // typedef SkTBlockList<GLUniformInfo>
```

**优势**:
- 元素在内存中稳定（不会因扩容而移动）
- 允许返回引用和指针
- 高效的迭代和追加

### 2. 名称混淆策略

可选的名称混淆以避免冲突：

```cpp
char prefix = 'u';
if ('u' == name[0] || !strncmp(name, GR_NO_MANGLE_PREFIX, strlen(GR_NO_MANGLE_PREFIX))) {
    prefix = '\0';  // 跳过混淆
}
SkString resolvedName = fProgramBuilder->nameVariable(prefix, name, mangleName);
```

**场景**:
- `mangleName=true`: 为处理器添加唯一前缀
- `mangleName=false`: 保持原始名称（如内置 uniform）

### 3. 位置绑定双路径

支持两种位置获取方式：

```cpp
// 方式 1: 显式绑定（推荐，支持时使用）
if (caps.bindUniformLocationSupport()) {
    GL_CALL(BindUniformLocation(programID, currUniform, name));
}

// 方式 2: 查询（回退方案）
else {
    GL_CALL_RET(location, GetUniformLocation(programID, name));
}
```

### 4. 采样器特殊处理

采样器与普通 uniform 分开管理：

```cpp
UniformInfoArray fUniforms;   // 普通 uniform
UniformInfoArray fSamplers;   // 采样器
skia_private::TArray<skgpu::Swizzle> fSamplerSwizzles;  // 采样器 swizzle
```

**原因**:
- 采样器有特殊的类型系统
- 需要额外的 swizzle 信息
- 总是仅在片段着色器中可见

## 性能考量

### 1. 块大小优化

```cpp
static const int kUniformsPerBlock = 8;
```

平衡内存开销和分配频率。

### 2. 显式位置绑定

优先使用 `glBindUniformLocation`：

```cpp
if (caps.bindUniformLocationSupport()) {
    // 显式绑定，避免查询
}
```

**优势**: 避免字符串查找，提高链接性能

### 3. 内联存储

使用 `SkTBlockList` 而非 `std::vector`：

**优势**: 避免引用失效，减少重新分配

### 4. 最小化 GL 调用

批量绑定所有 uniform 位置：

```cpp
for (GLUniformInfo& uniform : fUniforms.items()) {
    GL_CALL(BindUniformLocation(...));  // 单次遍历
}
```

## Uniform 命名约定

### 1. 自动前缀

```cpp
char prefix = 'u';  // 'u' for uniforms
```

生成的名称如：`uColor`, `uMatrix` 等

### 2. 处理器混淆

```cpp
// 原始名称: "color"
// 处理器 0: "ucolor_Stage0"
// 处理器 1: "ucolor_Stage1"
```

### 3. 保留名称

```cpp
// sk_RTAdjust: 保留，不混淆
// 其他 sk_*: 禁止
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/glsl/GrGLSLUniformHandler.h` | 基类 | 平台无关的 uniform 处理器 |
| `src/gpu/ganesh/gl/builders/GrGLProgramBuilder.h` | 使用者 | GL 程序构建器 |
| `src/gpu/ganesh/gl/GrGLProgramDataManager.h` | 类型定义 | Uniform 数据类型 |
| `src/gpu/ganesh/gl/GrGLGpu.h` | 依赖 | GPU 接口 |
| `src/gpu/ganesh/gl/GrGLCaps.h` | 依赖 | 能力查询 |
| `src/gpu/ganesh/GrShaderVar.h` | 依赖 | 着色器变量 |
| `src/gpu/Swizzle.h` | 依赖 | 纹理通道重排 |
