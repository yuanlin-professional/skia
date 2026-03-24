# GrSPIRVUniformHandler

> 源文件
> - src/gpu/ganesh/GrSPIRVUniformHandler.h
> - src/gpu/ganesh/GrSPIRVUniformHandler.cpp

## 概述

`GrSPIRVUniformHandler` 是专门用于 SPIR-V 着色器的 uniform 变量管理器,负责处理着色器中的常量数据布局。它采用标准的描述符集(descriptor set)和绑定点(binding)布局:将所有 uniform 打包到第 0 个描述符集的 uniform buffer 中,将采样器和纹理放在第 1 个描述符集中。该类实现了 std140 布局规范,确保数据对齐符合 SPIR-V 和 Vulkan 规范,主要用于 Vulkan、Dawn 和 Direct3D 后端。

## 架构位置

在 Skia GPU 着色器编译流水线中的位置:

```
GrGLSLProgramBuilder
    ├── GrSPIRVUniformHandler
    │   ├── Uniform Buffer(Set 0, Binding 0)
    │   └── Sampler/Texture(Set 1,多个 Binding)
    ├── 顶点着色器
    ├── 片段着色器
    └── 生成 SPIR-V 代码
```

## 主要类与结构体

### 核心类

| 类名 | 继承关系 | 作用 |
|------|---------|------|
| `GrSPIRVUniformHandler` | `GrGLSLUniformHandler` | SPIR-V uniform 管理器 |
| `GrSPIRVUniformHandler::SPIRVUniformInfo` | `UniformInfo` | 扩展的 uniform 信息,包含 UBO 偏移 |

### 关键成员变量

| 成员变量 | 类型 | 作用 |
|---------|------|------|
| `fUniforms` | `UniformInfoArray` | 所有 uniform 的信息 |
| `fSamplers` | `UniformInfoArray` | 所有采样器的信息 |
| `fSamplerSwizzles` | `TArray<skgpu::Swizzle>` | 采样器的颜色通道混洗 |
| `fCurrentUBOOffset` | `uint32_t` | 当前 UBO 偏移位置 |
| `fRTFlipOffset` | `uint32_t` | RenderTarget 翻转参数的偏移 |

### 常量定义

```cpp
static constexpr int kUniformDescriptorSet = 0;          // Uniform 在第 0 个描述符集
static constexpr int kSamplerTextureDescriptorSet = 1;   // 采样器在第 1 个描述符集
static constexpr int kUniformBinding = 0;                // Uniform buffer 绑定点
static constexpr size_t kUniformsPerBlock = 8;          // 块列表大小
```

## 公共 API 函数

### 查询函数

```cpp
const GrShaderVar& getUniformVariable(UniformHandle u) const override;
const char* getUniformCStr(UniformHandle u) const override;
uint32_t getRTFlipOffset() const;  // 获取 RT 翻转参数偏移
```

### 采样器相关

```cpp
const char* samplerVariable(SamplerHandle handle) const override;
skgpu::Swizzle samplerSwizzle(SamplerHandle handle) const override;
```

### 代码生成

```cpp
void appendUniformDecls(GrShaderFlags visibility, SkString* out) const override;
```

生成 SPIR-V 格式的 uniform 声明代码。

### 统计函数

```cpp
int numUniforms() const override;
UniformInfo& uniform(int idx) override;
const UniformInfo& uniform(int idx) const override;
```

## 内部实现细节

### std140 布局规范实现

**对齐计算**:
```cpp
uint32_t sksltype_to_alignment_mask(SkSLType type)
```

返回对齐掩码(实际对齐 = 掩码 + 1):

| 类型 | 对齐(字节) | 示例 |
|------|-----------|------|
| `short/ushort` | 2 | 0x1 |
| `int/uint/float` | 4 | 0x3 |
| `vec2/ivec2` | 8 | 0x7 |
| `vec3/vec4/mat2` | 16 | 0xF |
| `mat3/mat4` | 16 | 0xF |

**大小计算**:
```cpp
uint32_t sksltype_to_size(SkSLType type)
```

返回类型的字节大小:
- 标量:按实际大小(`float` 4 字节,`short` 2 字节)
- 向量:元素大小 × 元素数量
- 矩阵:特殊处理,`mat2x2` 占用 8 个 float(std140 规则)

**偏移计算**:
```cpp
uint32_t get_ubo_offset(uint32_t* currentOffset, SkSLType type, int arrayCount)
```

核心逻辑:
1. 获取类型的对齐掩码
2. 如果是数组或 mat2x2,强制 16 字节对齐
3. 计算填充以满足对齐要求
4. 返回对齐后的偏移
5. 更新当前偏移指针

数组处理:
```cpp
if (arrayCount) {
    uint32_t elementSize = std::max<uint32_t>(16, sksltype_to_size(type));
    *currentOffset = uniformOffset + elementSize * arrayCount;
}
```

每个数组元素至少占用 16 字节(std140 规则)。

### Uniform 添加

```cpp
UniformHandle internalAddUniformArray(
    const GrProcessor* owner,
    uint32_t visibility,
    SkSLType type,
    const char* name,
    bool mangleName,
    int arrayCount,
    const char** outName) override
```

步骤:
1. 生成变量名(可选 mangle)
2. 计算 UBO 偏移
3. 创建带 `layout(offset = N)` 的 `GrShaderVar`
4. 填充 `SPIRVUniformInfo` 结构
5. 加入 `fUniforms` 数组
6. 返回 handle

### 采样器添加

```cpp
SamplerHandle addSampler(
    const GrBackendFormat& backendFormat,
    GrSamplerState samplerState,
    const skgpu::Swizzle& swizzle,
    const char* name,
    const GrShaderCaps* caps) override
```

特点:
- 每个采样器占用 2 个连续绑定点(sampler 和 texture)
- 使用 `direct3d` 布局限定符(兼容 D3D)
- 设置为 `set = 1`
- 绑定点:sampler 在偶数,texture 在奇数

布局字符串示例:
```
layout(direct3d, set = 1, sampler = 0, texture = 1)
```

### 代码生成

```cpp
void appendUniformDecls(GrShaderFlags visibility, SkString* out) const
```

生成的代码结构:

**采样器声明**(直接输出):
```glsl
layout(direct3d, set = 1, sampler = 0, texture = 1) uniform sampler2D uSampler0;
layout(direct3d, set = 1, sampler = 2, texture = 3) uniform sampler2D uSampler1;
```

**Uniform buffer 声明**(包裹在 buffer 块中):
```glsl
layout (set = 0, binding = 0) uniform UniformBuffer
{
    layout(offset = 0) vec4 uColor;
    layout(offset = 16) mat4 uTransform;
};
```

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖原因 |
|---------|---------|
| `GrGLSLUniformHandler` | 基类 |
| `GrGLSLProgramBuilder` | 程序构建上下文 |
| `GrShaderVar` | 变量表示 |
| `SkSLType` | 类型系统 |
| `GrBackendFormat` | 后端格式 |
| `skgpu::Swizzle` | 颜色通道混洗 |

### 被依赖的模块

| 模块名称 | 使用方式 |
|---------|---------|
| `GrVkPipelineStateBuilder` | Vulkan 管线构建 |
| `GrDawnProgramBuilder` | Dawn 程序构建 |
| `GrD3DPipelineStateBuilder` | Direct3D 管线构建 |

## 设计模式与设计决策

### 设计模式

1. **分离布局模式**:
   - Uniform 和采样器使用不同的描述符集
   - 允许独立更新和优化

2. **std140 标准布局**:
   - 严格遵循 OpenGL std140 规范
   - 保证跨平台兼容性

3. **块列表分配** (`SkTBlockList`):
   - 避免动态数组的重新分配
   - 保持指针稳定性

### 关键设计决策

**为何使用两个描述符集**:
- 描述符集 0:所有 uniform 打包到单个 buffer
  - 减少 binding 数量
  - 提高更新效率
- 描述符集 1:采样器和纹理分开
  - 允许灵活绑定不同纹理
  - 符合 GPU 最佳实践

**为何采用 std140 布局**:
- 跨平台兼容性好
- 规范明确,易于实现
- 虽然有空间浪费,但换取兼容性值得

**为何分离 sampler 和 texture**:
```glsl
layout(direct3d, set = 1, sampler = 0, texture = 1)
```
- 某些 API(如 D3D12)要求分离
- 提供更大的灵活性
- 可以共享采样器或纹理

**为何数组元素最少 16 字节**:
```cpp
uint32_t elementSize = std::max<uint32_t>(16, sksltype_to_size(type));
```
- std140 规范要求
- 保证对齐和跨平台一致性

**为何需要 getRTFlipOffset**:
- Vulkan 坐标系与 OpenGL 不同
- 需要在着色器中翻转 Y 坐标
- 提供偏移允许动态更新翻转参数

## 性能考量

### 空间效率

**优点**:
- 所有 uniform 在单个 buffer 中
- 减少描述符集数量

**缺点**:
- std140 布局有填充开销
- 例如:`vec3` 后面有 4 字节填充
- 数组元素最少 16 字节,小类型浪费空间

### 时间复杂度

| 操作 | 复杂度 |
|------|--------|
| 添加 uniform | O(1) |
| 添加 sampler | O(1) |
| 生成声明代码 | O(n) |
| 查询 uniform | O(1) |

### 更新效率

**批量更新**:
- 所有 uniform 在连续内存中
- 可以一次性更新整个 buffer
- 减少 API 调用次数

**分离更新**:
- 采样器可以独立于 uniform buffer 更新
- 支持动态纹理切换

### 优化权衡

**空间 vs 兼容性**:
- std140 浪费空间,但保证兼容
- std430 更紧凑,但支持有限
- 选择 std140 优先兼容性

**描述符集数量**:
- 使用两个集合是折中方案
- 更多集合更灵活但开销大
- 当前设计平衡了灵活性和效率

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/glsl/GrGLSLUniformHandler.h` | 基类 | Uniform 处理抽象接口 |
| `src/gpu/ganesh/GrShaderVar.h` | 使用 | 变量表示 |
| `src/gpu/ganesh/GrSPIRVVaryingHandler.h` | 姊妹类 | Varying 处理器 |
| `src/gpu/ganesh/vk/GrVkPipelineStateBuilder.cpp` | 使用者 | Vulkan 后端 |
| `src/gpu/ganesh/dawn/GrDawnProgramBuilder.cpp` | 使用者 | Dawn 后端 |
| `src/gpu/ganesh/d3d/GrD3DPipelineStateBuilder.cpp` | 使用者 | D3D 后端 |
| `src/core/SkSLTypeShared.h` | 依赖 | SkSL 类型定义 |
