# GrMtlUniformHandler

> 源文件
> - src/gpu/ganesh/mtl/GrMtlUniformHandler.h
> - src/gpu/ganesh/mtl/GrMtlUniformHandler.mm

## 概述

`GrMtlUniformHandler` 是 Skia Ganesh Metal 后端的 Uniform 变量管理类，负责在着色器编译过程中管理 Uniform 缓冲区的布局、对齐和偏移计算。该类继承自 `GrGLSLUniformHandler`，复用 GLSL 统一接口，并实现 Metal 特定的内存布局规则。核心功能包括 Uniform 缓冲区对象（UBO）的打包、采样器管理、对齐约束处理，以及着色器声明代码生成。该类确保 CPU 端和 GPU 端的 Uniform 数据布局一致，是 Metal 着色器程序构建的关键组件。

## 架构位置

- **模块层级**：`src/gpu/ganesh/mtl/` - Ganesh Metal 后端
- **继承关系**：`GrMtlUniformHandler` -> `GrGLSLUniformHandler` -> `GrGLSLUniformHandler`（基类）
- **使用者**：`GrMtlPipelineStateBuilder`（着色器编译）
- **协作类**：`GrMtlPipelineState`（运行时 Uniform 上传）

## 主要类与结构体

### GrMtlUniformHandler

```cpp
class GrMtlUniformHandler : public GrGLSLUniformHandler
```

**核心数据成员**：
- `UniformInfoArray fUniforms` - Uniform 变量数组
- `UniformInfoArray fSamplers` - 采样器数组
- `skia_private::TArray<skgpu::Swizzle> fSamplerSwizzles` - 采样器通道重排
- `uint32_t fCurrentUBOOffset` - 当前 UBO 偏移
- `uint32_t fCurrentUBOMaxAlignment` - 最大对齐要求

**常量配置**：
- `kUniformsPerBlock = 8` - 每个块预分配 Uniform 数量
- `kUniformBinding = 0` - Uniform 缓冲区绑定点
- `kUniformBindingCount = 1` - 绑定点数量

### MtlUniformInfo

```cpp
struct MtlUniformInfo : public UniformInfo {
    uint32_t fUBOffset;  // Uniform 在缓冲区中的偏移
};
```

扩展基类 `UniformInfo`，添加 Metal UBO 偏移字段。

## 公共 API 函数

### Uniform 访问

```cpp
const GrShaderVar& getUniformVariable(UniformHandle u) const override;
const char* getUniformCStr(UniformHandle u) const override;
int numUniforms() const override;
UniformInfo& uniform(int idx) override;
```

提供 Uniform 变量的查询接口，支持按句柄或索引访问。

### 采样器管理

```cpp
SamplerHandle addSampler(const GrBackendFormat&, GrSamplerState,
                         const skgpu::Swizzle&, const char* name,
                         const GrShaderCaps*) override;
const char* samplerVariable(SamplerHandle) const override;
skgpu::Swizzle samplerSwizzle(SamplerHandle) const override;
uint32_t samplerVisibility(SamplerHandle) const;
int numSamplers() const;
```

管理纹理采样器，包括名称、Swizzle 和可见性标志。

## 内部实现细节

### 对齐计算

**sksltype_to_alignment_mask 函数**：

根据 SkSL 类型返回对齐掩码（alignment - 1）：
- 标量（`float`, `int`）：0x3（4字节对齐）
- 向量2（`float2`, `int2`）：0x7（8字节对齐）
- 向量3/4（`float3`, `float4`）：0xF（16字节对齐）
- 矩阵2x2：0x7（8字节对齐）
- 矩阵3x3/4x4：0xF（16字节对齐）
- Half 标量：0x1（2字节对齐）
- Half 向量：0x3/0x7（4/8字节对齐）

**检查对齐**：
```cpp
uint32_t aligned = fCurrentUBOOffset & alignmentMask;
if (aligned != 0) {
    fCurrentUBOOffset += alignmentMask - aligned + 1;
}
```

### 大小计算

**sksltype_to_mtl_size 函数**：

返回类型在 Metal 缓冲区中的字节大小：
- `float/int/uint`：4字节
- `float2/int2`：8字节
- `float3/float4/int3/int4`：16字节（注意 float3 填充到16字节）
- `float2x2`：16字节
- `float3x3`：48字节（每行16字节）
- `float4x4`：64字节
- Half 类型：大小减半

### Uniform 添加流程

**internalAddUniformArray 实现**：

1. **对齐当前偏移**：
   - 根据类型获取对齐掩码
   - 更新最大对齐要求
   - 调整 `fCurrentUBOOffset` 到对齐边界

2. **创建 Uniform 信息**：
   ```cpp
   MtlUniformInfo& uni = fUniforms.push_back();
   uni.fVariable = GrShaderVar(name, type, arrayCount);
   uni.fVisibility = visibility;
   uni.fOwner = owner;
   uni.fUBOffset = fCurrentUBOOffset;
   ```

3. **更新偏移**：
   ```cpp
   uint32_t elementSize = sksltype_to_mtl_size(type);
   uint32_t arraySize = elementSize * arrayCount;
   fCurrentUBOOffset += arraySize;
   ```

4. **返回句柄**：
   ```cpp
   return GrGLSLUniformHandler::UniformHandle(fUniforms.count() - 1);
   ```

### 采样器添加

**addSampler 实现**：

```cpp
SamplerHandle GrMtlUniformHandler::addSampler(
        const GrBackendFormat& format, GrSamplerState state,
        const skgpu::Swizzle& swizzle, const char* name,
        const GrShaderCaps* shaderCaps) {
    MtlUniformInfo& info = fSamplers.push_back();
    info.fVariable = GrShaderVar(name, SkSLType::kTexture2DSampler);
    info.fVisibility = kFragment_GrShaderFlag;
    fSamplerSwizzles.push_back(swizzle);
    return GrGLSLUniformHandler::SamplerHandle(fSamplers.count() - 1);
}
```

采样器不占用 UBO 空间，单独管理。

### 着色器声明生成

**appendUniformDecls 实现**：

生成 Metal 着色器中的 Uniform 声明：
```metal
struct Uniforms {
    float4 u_color;
    float4x4 u_matrix;
    // ...
};
```

然后通过 `[[buffer(0)]]` 绑定到着色器函数。

## 依赖关系

**基类**：
- `GrGLSLUniformHandler` - GLSL Uniform 处理器基类

**使用的类型**：
- `GrShaderVar` - 着色器变量表示
- `SkTBlockList<T>` - 块链表容器（高效增长）
- `SkSLType` - Skia 着色器语言类型枚举

**协作类**：
- `GrMtlPipelineStateBuilder` - 着色器构建器（友元类）
- `GrGLSLProgramBuilder` - 程序构建器基类

## 设计模式与设计决策

### 适配器模式

`GrMtlUniformHandler` 继承 `GrGLSLUniformHandler`，复用 GLSL 接口，适配 Metal 后端特定实现。

### 延迟布局计算

在着色器编译期间计算 Uniform 布局，而非运行时，减少 CPU 开销。

### 内存对齐策略

严格遵循 Metal 对齐规则：
- 标量和向量按自然大小对齐
- 向量3填充到向量4
- 矩阵按行对齐，每行作为向量处理

### 块链表优化

使用 `SkTBlockList` 存储 Uniform 信息：
- 减少小对象分配
- 提高缓存局部性
- 支持高效迭代

## 性能考量

### 对齐开销最小化

通过掩码和位运算快速计算对齐：
```cpp
uint32_t aligned = offset & alignmentMask;
if (aligned != 0) {
    offset += alignmentMask - aligned + 1;
}
```

### 预分配策略

`kUniformsPerBlock = 8` 批量预分配，减少动态分配次数。

### 紧凑布局

按顺序打包 Uniform，最小化 UBO 大小和内存浪费。

## 相关文件

**基类**：
- `src/gpu/ganesh/glsl/GrGLSLUniformHandler.h` - GLSL Uniform 处理器

**Metal 后端**：
- `src/gpu/ganesh/mtl/GrMtlPipelineStateBuilder.h` - 管线状态构建器
- `src/gpu/ganesh/mtl/GrMtlPipelineState.h` - 管线状态（运行时）

**工具**：
- `src/gpu/ganesh/GrShaderVar.h` - 着色器变量
- `src/base/SkTBlockList.h` - 块链表容器
