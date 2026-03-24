# GrGLVertexArray

> 源文件
> - src/gpu/ganesh/gl/GrGLVertexArray.h
> - src/gpu/ganesh/gl/GrGLVertexArray.cpp

## 概述

`GrGLVertexArray` 是 Ganesh OpenGL 后端中用于管理 OpenGL 顶点数组对象（VAO）的核心类。它封装了 VAO 的生命周期管理，并通过追踪顶点数组状态来避免冗余的 GL 调用，从而优化渲染性能。该模块包含两个主要类：`GrGLAttribArrayState` 用于跟踪顶点属性数组的状态，`GrGLVertexArray` 用于表示和管理完整的 VAO 对象。这两个类协同工作，为 Ganesh 提供高效的顶点数据绑定机制。

## 架构位置

`GrGLVertexArray` 位于 Ganesh GPU 后端的 OpenGL 层，处于以下架构位置：

```
Ganesh Core (GrGpu)
    ↓
OpenGL Backend (GrGLGpu)
    ↓
Vertex Management (GrGLVertexArray) ← 当前模块
    ↓
OpenGL API (glVertexAttribPointer, glBindVertexArray)
```

该模块是 OpenGL 渲染管线中顶点输入阶段的关键组件，负责配置顶点着色器的输入数据布局。

## 主要类与结构体

### GrGLAttribArrayState

**功能**：追踪和设置顶点属性数组状态。

**继承关系**：无基类，独立类。

**关键成员变量**：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fAttribArrayStates` | `STArray<16, AttribArrayState>` | 存储所有顶点属性的状态 |
| `fNumEnabledArrays` | `int` | 当前启用的属性数组数量 |
| `fPrimitiveRestartEnabled` | `GrPrimitiveRestart` | 图元重启状态 |
| `fEnableStateIsValid` | `bool` | 启用状态是否有效 |

### AttribArrayState（内部结构体）

**功能**：跟踪单个顶点属性的 GL 状态。

**关键成员变量**：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fVertexBufferUniqueID` | `GrGpuResource::UniqueID` | 关联的顶点缓冲区 ID |
| `fUsingCpuBuffer` | `bool` | 是否使用 CPU 缓冲区 |
| `fCPUType` | `GrVertexAttribType` | CPU 端的属性类型 |
| `fGPUType` | `SkSLType` | GPU 端的着色器类型 |
| `fStride` | `GrGLsizei` | 顶点步幅 |
| `fOffset` | `const GrGLvoid*` | 属性数据偏移 |
| `fDivisor` | `int` | 实例化除数 |

### GrGLVertexArray

**功能**：表示一个 OpenGL VAO 对象，管理其生命周期和状态。

**继承关系**：无基类。

**关键成员变量**：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fID` | `GrGLuint` | OpenGL VAO ID |
| `fAttribArrays` | `GrGLAttribArrayState` | 属性数组状态追踪器 |
| `fIndexBufferUniqueID` | `GrGpuResource::UniqueID` | 关联的索引缓冲区 ID |

## 公共 API 函数

### GrGLAttribArrayState::set

```cpp
void set(GrGLGpu* gpu, int attribIndex, const GrBuffer* vertexBuffer,
         GrVertexAttribType cpuType, SkSLType gpuType,
         GrGLsizei stride, size_t offsetInBytes, int divisor = 0);
```

**功能**：启用并配置指定索引的顶点属性。

**参数说明**：
- `gpu`: OpenGL GPU 对象
- `attribIndex`: 属性索引（对应着色器中的 location）
- `vertexBuffer`: 顶点缓冲区
- `cpuType`: CPU 端数据类型（如 Float2, UByte4_norm）
- `gpuType`: GPU 端着色器类型（如 float2, vec4）
- `stride`: 顶点步幅（字节数）
- `offsetInBytes`: 属性在缓冲区中的偏移
- `divisor`: 实例化除数（0=每顶点，1=每实例）

### GrGLAttribArrayState::enableVertexArrays

```cpp
void enableVertexArrays(const GrGLGpu* gpu, int enabledCount,
                        GrPrimitiveRestart enablePrimitiveRestart = GrPrimitiveRestart::kNo);
```

**功能**：启用前 N 个顶点属性数组，禁用其余的。

**参数说明**：
- `enabledCount`: 需要启用的属性数量
- `enablePrimitiveRestart`: 是否启用图元重启

### GrGLVertexArray::bind

```cpp
GrGLAttribArrayState* bind(GrGLGpu* gpu);
```

**功能**：绑定此 VAO，返回其状态追踪器。

**返回值**：成功时返回 `GrGLAttribArrayState*`，失败时返回 `nullptr`。

### GrGLVertexArray::bindWithIndexBuffer

```cpp
GrGLAttribArrayState* bindWithIndexBuffer(GrGLGpu* gpu, const GrBuffer* indexBuffer);
```

**功能**：绑定 VAO 并同时绑定索引缓冲区。

**参数说明**：
- `indexBuffer`: 索引缓冲区对象

### GrGLVertexArray::invalidateCachedState

```cpp
void invalidateCachedState();
```

**功能**：使缓存的状态失效，强制下次设置时重新配置。

## 内部实现细节

### 属性布局映射

`attrib_layout` 函数将 Ganesh 的 `GrVertexAttribType` 映射到 OpenGL 的 GL 类型：

**浮点类型**：
- `kFloat_GrVertexAttribType` → `{false, 1, GL_FLOAT}`
- `kHalf4_GrVertexAttribType` → `{false, 4, GL_HALF_FLOAT}`

**整数类型**：
- `kInt2_GrVertexAttribType` → `{false, 2, GL_INT}`
- `kByte4_GrVertexAttribType` → `{false, 4, GL_BYTE}`

**归一化类型**：
- `kUByte4_norm_GrVertexAttribType` → `{true, 4, GL_UNSIGNED_BYTE}`

返回的 `AttribLayout` 包含：
- `fNormalized`: 是否归一化到 [0,1]
- `fCount`: 分量数量（1-4）
- `fType`: GL 类型常量

### 状态追踪与优化

`GrGLAttribArrayState::set` 实现了智能状态追踪：

1. **缓冲区变更检测**：
   - CPU 缓冲区：直接使用指针地址
   - GPU 缓冲区：通过 `uniqueID` 比对

2. **属性配置变更检测**：
   - 比较 CPU 类型、GPU 类型、步幅、偏移
   - 只有发生变化才调用 GL API

3. **调用正确的 GL 函数**：
   - 浮点类型：`glVertexAttribPointer`
   - 整数类型：`glVertexAttribIPointer`（需要整数支持）

4. **实例化配置**：
   - 使用 `glVertexAttribDivisor` 设置实例化除数
   - 仅在支持实例化且除数改变时调用

### 启用状态管理

`enableVertexArrays` 函数优化了属性启用/禁用操作：

1. **增量更新**：
   - 如果状态有效，只更新变化的部分
   - 如果状态无效，完全重新配置

2. **启用新属性**：
   - 从 `fNumEnabledArrays` 到 `enabledCount` 调用 `glEnableVertexAttribArray`

3. **禁用多余属性**：
   - 从 `enabledCount` 到之前的数量调用 `glDisableVertexAttribArray`

4. **图元重启控制**：
   - 根据参数启用或禁用 `GL_PRIMITIVE_RESTART_FIXED_INDEX`

### VAO 绑定逻辑

`GrGLVertexArray::bindWithIndexBuffer` 的实现：

1. 调用 `bind()` 绑定 VAO
2. 检查索引缓冲区类型：
   - CPU 缓冲区：解绑 `GL_ELEMENT_ARRAY_BUFFER`
   - GPU 缓冲区：绑定并缓存 ID

3. 利用 VAO 特性：索引缓冲区绑定会被 VAO 记住

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLGpu` | 访问 GL 接口和能力查询 |
| `GrBuffer` | 顶点和索引缓冲区抽象 |
| `GrCpuBuffer` | CPU 端缓冲区 |
| `GrGpuBuffer` | GPU 端缓冲区 |
| `GrGLBuffer` | GL 缓冲区封装 |
| `GrCaps` | GPU 能力查询 |
| `SkSLType` | 着色器类型定义 |
| `GrVertexAttribType` | 顶点属性类型枚举 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| `GrGLGpu` | 在绘制前配置顶点输入 |
| `GrGLOpsRenderPass` | 渲染通道中设置顶点数据 |
| `GrGLProgram` | 程序对象管理 VAO |

## 设计模式与设计决策

### 状态追踪模式

采用缓存-比对-更新的模式：
- **缓存**：保存上次设置的所有参数
- **比对**：新参数与缓存比对
- **更新**：仅在变化时调用 GL API

这种设计避免了大量冗余的 GL 调用，显著提升性能。

### 分离的状态管理

`GrGLAttribArrayState` 与 `GrGLVertexArray` 分离的原因：
- `GrGLAttribArrayState` 也用于追踪 VAO 0（默认 VAO）的状态
- 允许统一的接口处理有无 VAO 的情况
- 代码复用性更强

### 延迟验证机制

通过 `fEnableStateIsValid` 标志实现延迟验证：
- `invalidate()` 只标记状态无效
- 实际的 GL 调用延迟到下次 `set()` 或 `enableVertexArrays()` 时

这种设计减少了不必要的 GL 调用，特别是在状态频繁失效的场景。

### 类型双重映射

同时存储 `fCPUType` 和 `fGPUType` 的原因：
- CPU 类型决定了 GL 函数的参数（count, type, normalized）
- GPU 类型决定了使用哪个 GL 函数（float vs integer）
- 两者组合才能完整描述数据传输

## 性能考量

### 状态追踪开销

**内存开销**：
- 每个属性：约 32 字节（AttribArrayState）
- 16 个属性：512 字节（栈上分配）

**收益**：
- 避免重复的 `glVertexAttribPointer` 调用
- 避免重复的 `glEnableVertexAttribArray` 调用
- VAO 切换后无需重新配置

### GL 调用优化

**冗余消除**：
- 顶点缓冲区绑定：通过 `uniqueID` 比对
- 索引缓冲区绑定：VAO 已记住绑定
- 属性启用状态：增量更新

**批量操作**：
- `enableVertexArrays` 一次性处理所有启用/禁用

### VAO 的性能优势

使用 VAO 的收益：
- 属性配置只需设置一次
- 快速切换不同的顶点布局
- 减少驱动验证开销

### CPU 缓冲区支持

支持 `GrCpuBuffer`（使用客户端指针）：
- 小数据避免 GPU 上传开销
- 动态数据避免缓冲区同步

## 相关文件

| 文件路径 | 关系说明 |
|----------|----------|
| `src/gpu/ganesh/gl/GrGLGpu.h/cpp` | 主要使用者，管理 VAO 池 |
| `src/gpu/ganesh/GrBuffer.h` | 缓冲区抽象基类 |
| `src/gpu/ganesh/gl/GrGLBuffer.h/cpp` | GL 缓冲区实现 |
| `src/gpu/ganesh/GrCpuBuffer.h` | CPU 端缓冲区 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | 顶点属性类型定义 |
| `src/gpu/ganesh/gl/GrGLDefines.h` | GL 常量定义 |
| `src/gpu/ganesh/GrCaps.h` | GPU 能力查询 |
| `src/gpu/ganesh/gl/GrGLUtil.h` | GL 工具函数 |
| `include/gpu/ganesh/gl/GrGLInterface.h` | GL 函数接口 |
