# AtlasInstancedHelper

> 源文件
> - src/gpu/ganesh/ops/AtlasInstancedHelper.h
> - src/gpu/ganesh/ops/AtlasInstancedHelper.cpp

## 概述

`AtlasInstancedHelper` 是 Skia Ganesh GPU 后端中用于实例化渲染的辅助类，专门用于处理基于图集（Atlas）的路径遮罩裁剪。该类封装了在实例化的 `GrGeometryProcessor` 中对图集路径遮罩进行裁剪所需的所有步骤，包括顶点属性设置、着色器代码注入、uniform 数据管理等。通过将多个相似的几何体批量渲染到同一个图集纹理中，可以显著提高渲染性能。

该类主要服务于需要使用图集进行路径渲染的场景，如文本渲染、小路径渲染等，通过实例化技术减少 draw call 数量，提升批处理效率。

## 架构位置

`AtlasInstancedHelper` 位于 Skia 的 GPU 渲染管线中，具体在 Ganesh 后端的操作（ops）层。它作为几何处理器的辅助工具，处理实例化渲染中的图集相关逻辑：

```
Skia 架构层次:
├── 公共 API 层
├── 核心图形库层
└── GPU 后端层
    └── Ganesh 后端
        ├── GrContext
        ├── GrRenderTargetContext
        ├── GrOpsTask
        └── GrOp 操作层 ← AtlasInstancedHelper 位于此处
            ├── GrGeometryProcessor
            └── 各种具体操作（文本、路径等）
```

该类与 `GrGeometryProcessor`、`GrSurfaceProxy`、着色器构建器等组件紧密协作，在 GPU 管线的几何处理阶段发挥作用。

## 主要类与结构体

### AtlasInstancedHelper 类

该类不继承自其他类，是一个独立的辅助工具类。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fAtlasProxy` | `sk_sp<GrSurfaceProxy>` | 指向图集纹理的代理对象，管理图集资源 |
| `fAtlasSwizzle` | `skgpu::Swizzle` | 图集纹理的颜色通道重排配置 |
| `fShaderFlags` | `ShaderFlags` | 着色器标志位，控制渲染行为 |

### ShaderFlags 枚举

| 标志位 | 值 | 说明 |
|-------|-----|------|
| `kNone` | 0 | 无特殊标志 |
| `kInvertCoverage` | 1 << 0 | 反转覆盖率，用于镂空效果 |
| `kCheckBounds` | 1 << 1 | 检查边界，防止超出图集范围 |

### Instance 结构体

封装单个实例的数据，用于批量渲染：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fLocationInAtlas` | `SkIPoint16` | 路径在图集中的位置（左上角坐标） |
| `fPathDevIBounds` | `SkIRect` | 路径在设备空间的整数边界框 |
| `fTransposedInAtlas` | `bool` | 路径在图集中是否被转置 |

## 公共 API 函数

### 构造与配置

```cpp
AtlasInstancedHelper(GrSurfaceProxyView atlasView, ShaderFlags shaderFlags)
```
构造函数，接收图集视图和着色器标志。要求图集必须是 Top-Left 原点。

```cpp
GrSurfaceProxy* proxy() const
```
获取图集代理对象的指针。

```cpp
const skgpu::Swizzle& atlasSwizzle() const
```
获取图集的颜色通道重排配置。

```cpp
bool isCompatible(const AtlasInstancedHelper& helper)
```
检查两个 helper 是否可以批量渲染在一起（图集代理和标志位必须匹配）。

### 着色器相关

```cpp
void getKeyBits(KeyBuilder* b) const
```
向着色器键值构建器添加唯一标识此 helper 的位信息，用于着色器缓存。

```cpp
void appendInstanceAttribs(
    skia_private::TArray<GrGeometryProcessor::Attribute>* instanceAttribs) const
```
向实例属性数组添加必要的顶点属性（位置信息和可选的大小信息）。

```cpp
void injectShaderCode(const GrGeometryProcessor::ProgramImpl::EmitArgs&,
                      const GrShaderVar& devCoord,
                      GrGLSLUniformHandler::UniformHandle* atlasAdjustUniformHandle) const
```
向顶点和片段着色器注入代码，实现图集坐标转换和覆盖率计算。

```cpp
void setUniformData(const GrGLSLProgramDataManager&,
                   const GrGLSLUniformHandler::UniformHandle& atlasAdjustUniformHandle) const
```
在绘制前设置 uniform 变量，传递图集的尺寸调整系数。

### 数据写入

```cpp
void writeInstanceData(VertexWriter* instanceWriter, const Instance*) const
```
将实例数据写入顶点缓冲区，格式化为着色器所需的属性数据。

## 内部实现细节

### 图集坐标转换机制

该类实现了从设备坐标到图集纹理坐标的转换：

1. **编码转置信息**：使用负数 x 坐标表示路径在图集中被转置，同时加 1 以避免零值无法取反
2. **坐标计算**：
   ```glsl
   atlasCoord = devCoord - devTopLeft
   if (transposed) atlasCoord = atlasCoord.yx
   atlasCoord += atlasTopLeft
   ```
3. **归一化**：通过 `atlasAdjust` uniform（1/width, 1/height）将像素坐标转换为纹理坐标

### 边界检查优化

当 `kCheckBounds` 标志启用时：
- 顶点着色器额外输出图集边界信息（`atlasBounds`）
- 片段着色器在纹理采样前检查坐标是否在边界内
- 超出边界的像素覆盖率设为 0，避免采样到相邻图集元素

### 覆盖率反转

当 `kInvertCoverage` 标志启用时，将 alpha 覆盖率反转（`1 - atlasCoverage`），用于实现路径的镂空效果。

### 实例数据打包

`writeInstanceData` 将实例信息紧凑打包为 float4（或 float4 + float2）：
- `locations.x`：带符号的图集 x 坐标（负数表示转置）
- `locations.y`：图集 y 坐标
- `locations.zw`：设备空间的路径左上角坐标
- `sizeInAtlas`（可选）：路径在图集中的尺寸

## 依赖关系

### 依赖的模块

| 模块 | 依赖关系 | 说明 |
|------|---------|------|
| `GrSurfaceProxy` | 强依赖 | 管理图集纹理资源 |
| `GrGeometryProcessor` | 强依赖 | 提供几何处理器接口和属性系统 |
| `GrGLSLShaderBuilder` | 强依赖 | 用于注入着色器代码 |
| `skgpu::Swizzle` | 强依赖 | 处理纹理通道重排 |
| `VertexWriter` | 强依赖 | 写入实例数据到顶点缓冲区 |
| `KeyBuilder` | 强依赖 | 构建着色器键值用于缓存 |

### 被依赖的模块

| 模块 | 依赖类型 | 说明 |
|------|---------|------|
| `AtlasTextOp` | 使用 | 文本渲染操作使用此 helper 处理字形图集 |
| `AtlasPathRenderer` | 使用 | 路径渲染器使用此 helper 处理路径图集 |
| `DrawAtlasOp` | 使用 | 图集绘制操作的核心辅助工具 |
| 各种实例化 GrGeometryProcessor | 使用 | 通过此 helper 实现图集裁剪功能 |

## 设计模式与设计决策

### 1. 辅助类模式（Helper Pattern）

将图集实例化渲染的复杂逻辑封装到独立的辅助类中，避免在多个 `GrGeometryProcessor` 子类中重复代码。这种设计提高了代码复用性和可维护性。

### 2. 标志位配置模式

使用 `ShaderFlags` 枚举控制着色器的可选功能：
- **优点**：编译时确定着色器变体，避免运行时分支
- **实现**：通过 `getKeyBits` 将标志位编码到着色器键值中

### 3. 数据驱动的着色器生成

通过 `injectShaderCode` 根据配置动态生成着色器代码，而不是使用多个独立的着色器程序，减少了着色器数量。

### 4. 仅支持 Top-Left 原点

设计决策：强制要求图集使用 Top-Left 原点（通过断言检查），简化了坐标转换逻辑，因为大多数图集场景都使用这种约定。

### 5. 紧凑的数据编码

使用负数编码转置状态（`-x - 1`）是一个巧妙的空间优化，避免额外的 attribute 传递，充分利用了 GPU 的浮点数符号位。

### 6. 延迟 uniform 设置

uniform 数据（`atlasAdjust`）在 `setUniformData` 中设置，而不是在构造时，这允许图集尺寸在后续阶段确定（例如动态图集分配）。

## 性能考量

### 1. 实例化渲染优化

通过批量处理多个实例，将多个 draw call 合并为单个实例化绘制，显著减少 CPU-GPU 通信开销。

### 2. 最小化顶点属性

基础配置只使用 4 个浮点数（float4），仅在需要边界检查时才添加额外的 2 个浮点数，减少了顶点缓冲区带宽占用。

### 3. 着色器变体管理

通过 2 个标志位生成有限数量的着色器变体（最多 4 种组合），避免了运行时分支的性能损失，同时限制了着色器数量。

### 4. 纹理采样优化

- 使用 `kCanBeFlat` 插值模式传递边界信息，减少插值计算
- 边界检查在片段着色器中进行，避免超出范围的纹理采样

### 5. 坐标转换效率

使用 `atlasAdjust` uniform 一次性完成像素坐标到纹理坐标的转换，避免在每个顶点/片段中重复除法运算。

### 6. 图集兼容性检查

`isCompatible` 方法允许运行时高效判断是否可以批处理，通过简单的指针和标志位比较完成。

### 7. 内存对齐

使用 `SkIPoint16` 存储图集位置，相比 `int` 节省 50% 空间，对于大量实例特别有效。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/ops/AtlasTextOp.h/cpp` | 使用者 | 文本渲染操作，使用此 helper 处理字形图集 |
| `src/gpu/ganesh/ops/AtlasPathRenderer.h/cpp` | 使用者 | 基于图集的路径渲染器 |
| `src/gpu/ganesh/ops/DrawAtlasOp.h/cpp` | 使用者 | 通用图集绘制操作 |
| `src/gpu/ganesh/GrGeometryProcessor.h` | 接口 | 提供几何处理器基类和属性系统 |
| `src/gpu/ganesh/GrSurfaceProxy.h` | 依赖 | 图集纹理的代理管理 |
| `src/gpu/ganesh/glsl/GrGLSLShaderBuilder.h` | 依赖 | 着色器代码生成工具 |
| `src/gpu/BufferWriter.h` | 依赖 | 顶点数据写入工具 |
| `src/core/SkIPoint16.h` | 依赖 | 16 位整数点类型，节省内存 |
