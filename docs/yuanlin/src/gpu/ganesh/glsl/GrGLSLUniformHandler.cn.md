# GrGLSLUniformHandler

> 源文件
> - src/gpu/ganesh/glsl/GrGLSLUniformHandler.h
> - src/gpu/ganesh/glsl/GrGLSLUniformHandler.cpp

## 概述

`GrGLSLUniformHandler` 是 Ganesh GLSL 层中管理 uniform 变量的抽象基类。它提供了添加、查询和管理着色器 uniform 的统一接口，支持跨不同着色器阶段的可见性控制、名称混淆（name mangling）、数组 uniform 等功能。该类是着色器构建系统中 uniform 管理的核心抽象，为 OpenGL、Vulkan、Metal 等不同后端提供一致的接口。

## 架构位置

```
GrGLSLProgramBuilder
    ↓
GrGLSLUniformHandler (抽象基类) ← 当前模块
    ↓
后端特定实现 (GrGLUniformHandler, GrVkUniformHandler, etc.)
    ↓
着色器代码生成
```

该模块位于 GLSL 抽象层，是着色器构建流程中 uniform 管理的接口定义。

## 主要类与结构体

### GrGLSLBuiltinUniformHandles

**功能**：存储内置 uniform 的句柄。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fRTAdjustmentUni` | `UniformHandle` | 渲染目标调整 uniform |
| `fRTFlipUni` | `UniformHandle` | 渲染目标翻转 uniform（用于 dFdy, sk_Clockwise, sk_FragCoord） |
| `fDstTextureCoordsUni` | `UniformHandle` | 目标纹理坐标 uniform（启用目标纹理读回时） |

### UniformInfo

**功能**：存储单个 uniform 的完整信息。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fVariable` | `GrShaderVar` | 着色器变量描述 |
| `fVisibility` | `uint32_t` | 可见性标志位（哪些着色器阶段可访问） |
| `fOwner` | `const GrProcessor*` | 拥有该 uniform 的处理器 |
| `fRawName` | `SkString` | 原始名称（未混淆） |

### GrGLSLUniformHandler

**功能**：uniform 管理的抽象基类。

**继承关系**：
- 纯虚基类，由后端特定类继承

**关键成员变量**：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fProgramBuilder` | `GrGLSLProgramBuilder*` | 程序构建器指针（不拥有） |

**类型别名**：

| 别名 | 实际类型 | 说明 |
|------|----------|------|
| `UniformHandle` | `GrGLSLProgramDataManager::UniformHandle` | Uniform 句柄 |
| `SamplerHandle` | 资源句柄类型 | 采样器句柄 |

## 公共 API 函数

### addUniform

```cpp
UniformHandle addUniform(const GrProcessor* owner,
                         uint32_t visibility,
                         SkSLType type,
                         const char* name,
                         const char** outName = nullptr);
```

**功能**：添加单个 uniform 变量。

**参数说明**：
- `owner`: 拥有该 uniform 的处理器（用于查找和管理）
- `visibility`: 可见性标志（`kVertex_GrShaderFlag` | `kFragment_GrShaderFlag` 等）
- `type`: SkSL 类型（不能是组合采样器类型）
- `name`: uniform 名称（会被混淆）
- `outName`: 输出参数，返回混淆后的最终名称

**返回值**：uniform 句柄，用于后续设置数据。

### addUniformArray

```cpp
UniformHandle addUniformArray(const GrProcessor* owner,
                              uint32_t visibility,
                              SkSLType type,
                              const char* name,
                              int arrayCount,
                              const char** outName = nullptr);
```

**功能**：添加 uniform 数组。

**参数说明**：
- `arrayCount`: 数组大小（0 表示非数组）
- 其他参数同 `addUniform`

### getUniformVariable

```cpp
virtual const GrShaderVar& getUniformVariable(UniformHandle u) const = 0;
```

**功能**：通过句柄获取 uniform 的着色器变量描述。

### getUniformCStr

```cpp
virtual const char* getUniformCStr(UniformHandle u) const = 0;
```

**功能**：快捷方式，获取 uniform 的名称字符串。

### getUniformMapping

```cpp
GrShaderVar getUniformMapping(const GrProcessor& owner, SkString rawName) const;
```

**功能**：查找指定处理器添加的 uniform（按原始名称）。

**返回值**：
- 找到：返回对应的 `GrShaderVar`
- 未找到：返回类型为 `kVoid` 的变量

**实现**：
```cpp
for (int i = this->numUniforms() - 1; i >= 0; i--) {
    const UniformInfo& u = this->uniform(i);
    if (u.fOwner == &owner && u.fRawName == rawName) {
        return u.fVariable;
    }
}
return GrShaderVar();  // kVoid 类型
```

从后向前遍历（最近添加的优先），匹配 owner 和原始名称。

### liftUniformToVertexShader

```cpp
GrShaderVar liftUniformToVertexShader(const GrProcessor& owner, SkString rawName);
```

**功能**：查找 uniform 并将其提升到顶点着色器可见。

**用途**：
- 某些计算需要在顶点着色器中进行
- 动态调整 uniform 的可见性

**实现**：
```cpp
for (int i = this->numUniforms() - 1; i >= 0; i--) {
    UniformInfo& u = this->uniform(i);
    if (u.fOwner == &owner && u.fRawName == rawName) {
        u.fVisibility |= kVertex_GrShaderFlag;  // 添加顶点着色器可见性
        return u.fVariable;
    }
}
return GrShaderVar();
```

**注意**：注释说明返回 void 变量比断言更好，因为采样矩阵的处理逻辑：
- Uniform 采样矩阵：通过此函数查找
- 常量采样矩阵：查找不到，推断为常量

## 内部实现细节

### 名称混淆机制

```cpp
#define GR_NO_MANGLE_PREFIX "sk_"
```

**规则**：
- 以 `sk_` 开头的名称不混淆（内置变量）
- 其他名称会被混淆以避免冲突

**混淆检查**：
```cpp
bool mangle = strncmp(name, GR_NO_MANGLE_PREFIX, strlen(GR_NO_MANGLE_PREFIX));
```

### 纯虚函数接口

子类必须实现的函数：

**Uniform 管理**：
- `internalAddUniformArray`: 实际添加 uniform 的实现
- `getUniformVariable`: 获取变量
- `getUniformCStr`: 获取名称
- `numUniforms`: uniform 数量
- `uniform(int idx)`: 访问 uniform 信息

**采样器管理**：
- `samplerVariable`: 获取采样器变量名
- `samplerSwizzle`: 获取采样器 swizzle
- `addSampler`: 添加采样器
- `inputSamplerVariable`: 输入采样器变量（可选）
- `inputSamplerSwizzle`: 输入采样器 swizzle（可选）
- `addInputSampler`: 添加输入采样器（可选）

**代码生成**：
- `appendUniformDecls`: 生成 uniform 声明代码

### 后备实现

输入采样器相关函数有默认实现（触发断言）：
```cpp
virtual const char* inputSamplerVariable(SamplerHandle) const {
    SkDEBUGFAIL("Trying to get input sampler from unsupported backend");
    return nullptr;
}
```

不是所有后端都支持输入采样器（如输入附件）。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLSLProgramDataManager` | Uniform 句柄定义 |
| `GrShaderVar` | 着色器变量描述 |
| `GrProcessor` | 处理器基类 |
| `GrResourceHandle` | 资源句柄宏 |
| `SkSLType` | SkSL 类型系统 |
| `skgpu::Swizzle` | 颜色通道重排 |
| `GrBackendFormat` | 后端纹理格式 |
| `GrSamplerState` | 采样器状态 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| `GrGLSLProgramBuilder` | 程序构建时管理 uniform |
| `GrProcessor` 子类 | 添加自定义 uniform |
| 后端特定实现 | GL, Vulkan, Metal 等 |

## 设计模式与设计决策

### 抽象工厂模式

`GrGLSLUniformHandler` 作为抽象接口：
- 定义 uniform 管理的通用操作
- 各后端提供具体实现
- 上层代码无需关心后端差异

### 句柄模式

使用 `UniformHandle` 而非直接指针：
- 类型安全
- 后端可以自由选择存储方式
- 支持延迟绑定

### 名称混淆

自动混淆名称避免冲突：
- 多个处理器可能使用相同的 uniform 名称
- 混淆后的名称保证唯一
- 内置变量（`sk_` 前缀）不混淆

### 可见性位域

使用位域表示可见性：
```cpp
uint32_t visibility = kVertex_GrShaderFlag | kFragment_GrShaderFlag;
```

优点：
- 紧凑表示
- 高效的位运算
- 易于添加/修改可见性

### 所有权追踪

每个 uniform 记录其 owner：
- 支持按处理器查找
- 调试时追踪来源
- 生命周期管理

## 性能考量

### 查找效率

`getUniformMapping` 和 `liftUniformToVertexShader` 使用线性搜索：
- 从后向前遍历（最近添加的优先，提高缓存命中率）
- Uniform 数量通常较少（<100）
- 主要在构建时调用，运行时无开销

### 内存布局

`UniformInfo` 结构体：
- 约 60 字节（取决于 `SkString` 实现）
- 通常以数组形式存储
- 内存局部性良好

### Uniform 更新

运行时通过 `GrGLSLProgramDataManager` 更新：
- 使用句柄直接访问
- 无需名称查找
- 高效的批量更新

## 相关文件

| 文件路径 | 关系说明 |
|----------|----------|
| `src/gpu/ganesh/glsl/GrGLSLProgramBuilder.h` | 使用该类管理 uniform |
| `src/gpu/ganesh/glsl/GrGLSLProgramDataManager.h` | 运行时 uniform 更新 |
| `src/gpu/ganesh/gl/GrGLUniformHandler.h/cpp` | OpenGL 特定实现 |
| `src/gpu/ganesh/GrShaderVar.h` | 着色器变量描述 |
| `src/gpu/ganesh/GrProcessor.h` | 处理器基类 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | 着色器标志定义 |
| `src/core/SkSLTypeShared.h` | SkSL 类型定义 |
