# GrDefaultGeoProcFactory

> 源文件
> - src/gpu/ganesh/GrDefaultGeoProcFactory.h
> - src/gpu/ganesh/GrDefaultGeoProcFactory.cpp

## 概述

`GrDefaultGeoProcFactory` 是 Skia Ganesh 渲染引擎中的默认几何处理器工厂，负责创建标准的几何处理器（Geometry Processor）。几何处理器是 GPU 渲染管线中的核心组件，负责顶点变换、颜色处理、纹理坐标计算等基础图形处理操作。该工厂提供了一套灵活的配置接口，通过不同的参数组合创建满足各种渲染需求的几何处理器。

这个工厂采用了工厂模式设计，通过命名空间封装了创建几何处理器的静态方法，支持颜色属性、覆盖度属性、局部坐标等多种配置选项，并能处理设备空间和视图空间的坐标转换。

## 架构位置

`GrDefaultGeoProcFactory` 位于 Skia GPU 渲染架构的几何处理层：

```
Skia GPU Rendering Pipeline
├── GrContext (渲染上下文)
├── GrRenderTargetContext (渲染目标)
├── GrOp (图形操作)
│   └── Geometry Processor Layer (几何处理层)
│       ├── GrDefaultGeoProcFactory ← 当前模块
│       ├── DefaultGeoProc (具体实现)
│       └── GrGeometryProcessor (基类)
└── GLSL Code Generation (着色器代码生成)
```

该模块在渲染管线中承担以下职责：
- 为大多数标准绘制操作提供默认的顶点处理逻辑
- 处理顶点位置变换、颜色插值、纹理坐标计算
- 生成对应的 GLSL 顶点和片段着色器代码

## 主要类与结构体

### 核心类

| 类名 | 继承关系 | 作用 |
|-----|---------|------|
| `GrDefaultGeoProcFactory` | 无（命名空间） | 工厂类，提供静态创建方法 |
| `DefaultGeoProc` | `GrGeometryProcessor` | 具体的几何处理器实现 |
| `DefaultGeoProc::Impl` | `GrGeometryProcessor::ProgramImpl` | 着色器程序实现 |

### 配置结构体

#### Color 结构体
```cpp
struct Color {
    enum Type {
        kPremulGrColorUniform_Type,      // 预乘颜色uniform
        kPremulGrColorAttribute_Type,    // 预乘颜色属性
        kPremulWideColorAttribute_Type,  // 宽色域颜色属性
    };
    Type fType;
    SkPMColor4f fColor;
};
```

#### Coverage 结构体
```cpp
struct Coverage {
    enum Type {
        kSolid_Type,                    // 固定覆盖度
        kUniform_Type,                  // uniform覆盖度
        kAttribute_Type,                // 属性覆盖度
        kAttributeTweakAlpha_Type,      // 调整alpha的属性覆盖度
        kAttributeUnclamped_Type,       // 未钳位的属性覆盖度
    };
    Type fType;
    uint8_t fCoverage;
};
```

#### LocalCoords 结构体
```cpp
struct LocalCoords {
    enum Type {
        kUnused_Type,        // 不使用局部坐标
        kUsePosition_Type,   // 使用位置作为局部坐标
        kHasExplicit_Type,   // 显式提供局部坐标
    };
    Type fType;
    const SkMatrix* fMatrix;
};
```

### DefaultGeoProc 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fInPosition` | `Attribute` | 输入位置属性 |
| `fInColor` | `Attribute` | 输入颜色属性 |
| `fInLocalCoords` | `Attribute` | 输入局部坐标属性 |
| `fInCoverage` | `Attribute` | 输入覆盖度属性 |
| `fViewMatrix` | `SkMatrix` | 视图变换矩阵 |
| `fLocalMatrix` | `SkMatrix` | 局部坐标变换矩阵 |
| `fColor` | `SkPMColor4f` | 颜色值 |
| `fCoverage` | `uint8_t` | 覆盖度值 |
| `fFlags` | `uint32_t` | 配置标志位 |

### 配置标志位

| 标志位 | 数值 | 说明 |
|-------|------|------|
| `kColorAttribute_GPFlag` | 0x1 | 使用颜色属性 |
| `kColorAttributeIsWide_GPFlag` | 0x2 | 宽色域颜色属性 |
| `kLocalCoordAttribute_GPFlag` | 0x4 | 使用局部坐标属性 |
| `kCoverageAttribute_GPFlag` | 0x8 | 使用覆盖度属性 |
| `kCoverageAttributeTweak_GPFlag` | 0x10 | 调整alpha的覆盖度 |
| `kCoverageAttributeUnclamped_GPFlag` | 0x20 | 未钳位的覆盖度 |

## 公共 API 函数

### Make
```cpp
static GrGeometryProcessor* Make(
    SkArenaAlloc* arena,
    const Color& color,
    const Coverage& coverage,
    const LocalCoords& localCoords,
    const SkMatrix& viewMatrix);
```
创建标准的几何处理器实例，在视图空间中处理顶点位置。

**参数说明：**
- `arena`: 内存分配器
- `color`: 颜色配置
- `coverage`: 覆盖度配置
- `localCoords`: 局部坐标配置
- `viewMatrix`: 视图变换矩阵

### MakeForDeviceSpace
```cpp
static GrGeometryProcessor* MakeForDeviceSpace(
    SkArenaAlloc* arena,
    const Color& color,
    const Coverage& coverage,
    const LocalCoords& localCoords,
    const SkMatrix& viewMatrix);
```
创建用于设备空间的几何处理器，顶点位置已经在设备空间中，但仍需计算正确的局部坐标。

**特点：**
- 期望输入的顶点位置已在设备空间
- 需要反转视图矩阵来计算局部坐标
- 如果视图矩阵不可逆，返回 `nullptr`

## 内部实现细节

### 着色器代码生成

`DefaultGeoProc::Impl` 类负责生成顶点和片段着色器代码：

#### 顶点着色器逻辑
1. **位置变换**：将输入位置通过视图矩阵变换到裁剪空间
2. **颜色处理**：
   - 如果使用顶点颜色属性，直接传递
   - 如果使用uniform颜色，从uniform读取
   - 如果启用覆盖度调整，将覆盖度乘以颜色的alpha通道
3. **局部坐标计算**：
   - 如果提供显式局部坐标，直接使用
   - 否则使用位置通过局部矩阵变换得到

#### 片段着色器逻辑
1. **颜色输出**：接收顶点着色器插值的颜色
2. **覆盖度处理**：
   - 固定覆盖度：输出常量值
   - Uniform覆盖度：从uniform读取
   - 属性覆盖度：接收顶点着色器插值值
   - 未钳位覆盖度：在片段着色器中执行饱和度钳位

### Key 生成策略

```cpp
void addToKey(const GrShaderCaps& caps, skgpu::KeyBuilder* b) const override {
    uint32_t key = fFlags;
    key |= fCoverage == 0xff      ?  0x80 : 0;
    key |= fLocalCoordsWillBeRead ? 0x100 : 0;
    // 添加矩阵key
    key = ProgramImpl::AddMatrixKeys(caps, key, fViewMatrix, ...);
    b->add32(key);
}
```

Key 用于缓存和查找已编译的着色器程序，包含：
- 所有配置标志位
- 覆盖度是否为完全不透明
- 是否需要读取局部坐标
- 视图矩阵和局部矩阵的类型信息

### 内存管理

使用 `SkArenaAlloc` 进行内存分配，所有几何处理器实例的生命周期由 arena 管理，无需手动释放。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `GrGeometryProcessor` | 基类，定义几何处理器接口 |
| `SkArenaAlloc` | 内存分配器 |
| `SkMatrix` | 矩阵变换 |
| `GrGLSLVertexBuilder` | 顶点着色器代码构建 |
| `GrGLSLFragmentBuilder` | 片段着色器代码构建 |
| `GrGLSLVaryingHandler` | 顶点到片段的varying变量处理 |
| `GrGLSLUniformHandler` | Uniform变量处理 |
| `GrGLSLProgramDataManager` | 程序数据管理 |
| `skgpu::KeyBuilder` | 着色器缓存key构建 |

### 被依赖的模块

| 模块 | 使用方式 |
|-----|---------|
| `GrOp` 子类 | 创建几何处理器用于绘制操作 |
| `GrDrawOp` | 标准绘制操作的几何处理器提供者 |
| `GrFillRectOp` | 矩形填充操作 |
| `GrStrokeOp` | 描边操作 |
| 各种绘制pipeline | 作为默认几何处理器使用 |

## 设计模式与设计决策

### 工厂模式
使用命名空间提供静态工厂方法，而不是传统的工厂类，简化了接口：
```cpp
namespace GrDefaultGeoProcFactory {
    GrGeometryProcessor* Make(...);
    GrGeometryProcessor* MakeForDeviceSpace(...);
}
```

### 策略模式
通过 `Color`、`Coverage`、`LocalCoords` 结构体封装不同的配置策略，允许灵活组合：
- 颜色可以是uniform或顶点属性
- 覆盖度可以是固定值、uniform或顶点属性
- 局部坐标可以不使用、使用位置或显式提供

### 位标志优化
使用位标志 (`GPFlag`) 紧凑地表示处理器配置，提高了key生成和比较效率。

### 模板方法模式
`GrGeometryProcessor::ProgramImpl` 定义了着色器生成的框架，`DefaultGeoProc::Impl` 实现具体步骤。

### 设计决策

1. **分离配置和实现**：工厂接口接受高层配置结构体，内部转换为低层位标志
2. **支持设备空间顶点**：`MakeForDeviceSpace` 支持已变换的顶点，用于特定优化场景
3. **覆盖度灵活性**：提供多种覆盖度模式，支持不同的抗锯齿和混合需求
4. **宽色域支持**：通过 `kPremulWideColorAttribute_Type` 支持高精度颜色

## 性能考量

### 着色器变体管理
通过精心设计的key系统，最小化着色器编译次数：
- 相同配置的处理器共享编译的程序
- Key包含所有影响着色器代码的因素

### Uniform vs 属性
- **Uniform颜色/覆盖度**：适用于整个绘制批次使用相同值的场景，节省带宽
- **属性颜色/覆盖度**：适用于每个顶点需要不同值的场景，提高灵活性

### 矩阵优化
- 缓存上一次的矩阵值，避免不必要的uniform更新
- 使用 `SkMatrix::InvalidMatrix()` 初始化，确保首次设置

### Arena 分配
使用arena分配器避免频繁的内存分配和释放，提高缓存局部性。

### 条件编译
在着色器中根据标志位有条件地生成代码，避免执行不需要的操作：
```cpp
if (tweakAlpha) {
    vertBuilder->codeAppendf("color = color * %s;", gp.fInCoverage.name());
}
```

### 饱和度钳位策略
`kAttributeUnclamped_Type` 允许在片段着色器中延迟钳位操作，某些GPU上可能更高效。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrGeometryProcessor.h` | 基类 | 几何处理器抽象基类 |
| `src/gpu/ganesh/glsl/GrGLSLVertexGeoBuilder.h` | 使用 | 顶点着色器构建器 |
| `src/gpu/ganesh/glsl/GrGLSLFragmentShaderBuilder.h` | 使用 | 片段着色器构建器 |
| `src/gpu/ganesh/glsl/GrGLSLProgramDataManager.h` | 使用 | 程序数据管理 |
| `src/gpu/ganesh/GrOp.h` | 被使用 | 图形操作基类 |
| `src/gpu/ganesh/ops/GrFillRectOp.cpp` | 被使用 | 矩形填充操作实现 |
| `src/gpu/ganesh/GrProcessorUnitTest.h` | 测试 | 单元测试支持 |
| `src/base/SkArenaAlloc.h` | 依赖 | Arena内存分配器 |
| `include/core/SkMatrix.h` | 依赖 | 矩阵变换 |
