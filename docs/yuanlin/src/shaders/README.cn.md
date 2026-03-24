# src/shaders - Skia 着色器实现

## 概述

`src/shaders` 目录是 Skia 图形库中着色器(Shader)子系统的核心实现所在地。着色器是 Skia 渲染管线中的关键组件,它定义了在绘制图元(primitives)时如何为每个像素生成颜色值。在 Skia 的架构中,着色器通过 `SkShader` 公共接口暴露给用户,而内部实现则通过 `SkShaderBase` 基类构建了一套完整的着色器类型体系。

该目录包含了 Skia 所有内置着色器类型的实现,涵盖纯色着色器、图像着色器、混合着色器、噪声着色器、运行时着色器等多种类型。每种着色器都继承自 `SkShaderBase`,并通过 `appendStages` 方法向 `SkRasterPipeline` 光栅化管线中添加处理阶段(stages),从而实现特定的颜色生成逻辑。这种基于管线的设计使得 Skia 能够高效地将着色器组合在一起,同时保持良好的可扩展性。

着色器系统的另一个重要特性是矩阵变换的传递与累积。`SkShaders::MatrixRec` 类负责在着色器树的遍历过程中管理坐标变换矩阵(CTM、本地矩阵及待处理矩阵)的累积与应用。这种设计避免了为每个矩阵单独执行矩阵乘法的开销,同时还兼容了 Android Framework 所要求的反向矩阵拼接顺序。

着色器还支持序列化与反序列化机制。通过 `SkFlattenable` 基类提供的注册(Register)和工厂(Factory)模式,每种着色器类型都可以被序列化到字节流中,并在之后从字节流中恢复。这对于 `SkPicture` 录制/回放以及跨进程通信至关重要。

此外,该目录还包含一个 `gradients` 子目录,专门存放渐变着色器(Gradient Shader)的实现,包括线性渐变、径向渐变、扫描渐变和锥形渐变四种类型。

## 架构图

```
                          +------------------+
                          |    SkShader      |  (include/core/SkShader.h)
                          |  (公共接口层)      |
                          +--------+---------+
                                   |
                          +--------+---------+
                          |  SkShaderBase    |  (src/shaders/SkShaderBase.h)
                          |  (内部基类)       |
                          |  - uniqueID()    |
                          |  - appendStages()|
                          |  - type()        |
                          |  - asGradient()  |
                          +--------+---------+
                                   |
          +------------------------+-------------------------+
          |            |           |           |             |
  +-------+------+ +--+---+ +-----+----+ +----+-----+ +----+--------+
  |SkColorShader | |SkBlend| |SkImage   | |SkLocal   | |SkGradient   |
  |              | |Shader | |Shader    | |MatrixShdr| |BaseShader   |
  +--------------+ +------+ +----------+ +----------+ +------+------+
                                                              |
  +-------+-------+ +--------+-------+ +-----------+  +------+------+
  |SkPerlinNoise  | |SkPicture       | |SkRuntime  |  |  gradients/ |
  |Shader         | |Shader          | |Shader     |  | (子目录)     |
  +---------------+ +----------------+ +-----------+  +-------------+

  +------------------+ +-------------------+ +---------------------+
  |SkColorFilter     | |SkCoordClamp       | |SkWorkingColorSpace  |
  |Shader            | |Shader             | |Shader               |
  +------------------+ +-------------------+ +---------------------+

  +------------------+ +-------------------+ +---------------------+
  |SkTransformShader | |SkTriColorShader   | |SkEmptyShader        |
  +------------------+ +-------------------+ +---------------------+

  辅助类:
  +------------------+ +-------------------+
  |SkShaders::       | |SkBitmapProcLegacy |
  |MatrixRec         | |Shader             |
  +------------------+ +-------------------+
```

## 目录结构

```
src/shaders/
|-- BUILD.bazel                        # Bazel 构建文件
|-- SkShader.cpp                       # SkShader 公共接口实现
|-- SkShaderBase.h                     # SkShaderBase 基类定义 + MatrixRec
|-- SkShaderBase.cpp                   # SkShaderBase 基类实现
|-- SkColorShader.h / .cpp            # 纯色着色器
|-- SkBlendShader.h / .cpp            # 混合着色器(两个子着色器 + 混合模式)
|-- SkImageShader.h / .cpp            # 图像着色器(最复杂,约 33K 行)
|-- SkLocalMatrixShader.h / .cpp      # 本地矩阵包装着色器 + SkCTMShader
|-- SkColorFilterShader.h / .cpp      # 颜色滤镜包装着色器
|-- SkCoordClampShader.h / .cpp       # 坐标钳制着色器
|-- SkEmptyShader.h / .cpp            # 空着色器(不绘制任何内容)
|-- SkPictureShader.h / .cpp          # SkPicture 图案着色器
|-- SkRuntimeShader.h / .cpp          # 运行时着色器(SkSL 自定义着色器)
|-- SkPerlinNoiseShaderImpl.h / .cpp  # Perlin 噪声着色器实现
|-- SkPerlinNoiseShaderType.h         # Perlin 噪声类型枚举
|-- SkGainmapShader.cpp               # HDR 增益图着色器
|-- SkTransformShader.h / .cpp        # 变换着色器(drawVertices/drawAtlas)
|-- SkTriColorShader.h / .cpp         # 三角形顶点色插值着色器
|-- SkWorkingColorSpaceShader.h / .cpp # 工作色彩空间着色器
|-- SkBitmapProcShader.h / .cpp       # 位图处理着色器(Legacy)
|-- gradients/                         # 渐变着色器子目录
    |-- SkGradientBaseShader.h / .cpp  # 渐变基类
    |-- SkLinearGradient.h / .cpp      # 线性渐变
    |-- SkRadialGradient.h / .cpp      # 径向渐变
    |-- SkSweepGradient.h / .cpp       # 扫描渐变
    |-- SkConicalGradient.h / .cpp     # 锥形(双点)渐变
```

## 关键类与函数

### SkShaderBase (核心基类)

`SkShaderBase` 是所有着色器实现的内部基类,继承自公共接口 `SkShader`。它定义了着色器系统的核心接口:

- **`type()`**: 纯虚函数,返回 `ShaderType` 枚举值,用于类型标识。所有着色器类型通过 `SK_ALL_SHADERS(M)` 宏统一注册,包括 Blend、CTM、Color、ColorFilter、CoordClamp、Empty、GradientBase、Image、LocalMatrix、PerlinNoise、Picture、Runtime、Transform、TriColor、WorkingColorSpace 共 15 种。
- **`appendStages()`**: 纯虚函数,向 `SkRasterPipeline` 添加光栅化阶段。这是着色器最核心的方法,决定了着色器在 CPU 光栅化路径中的行为。
- **`isConstant()`**: 返回着色器是否产生恒定颜色。`SkColorShader` 重写此方法返回 `true`,便于循环提升优化。
- **`asGradient()`**: 如果着色器可表示为渐变,返回对应的 `GradientType` 并填充 `GradientInfo`。
- **`makeContext()` / `Context`**: 传统着色器上下文,用于 `shadeSpan` 逐行着色(Legacy 路径)。
- **`appendRootStages()`**: 根级着色器入口,包装 `appendStages` 并传入 CTM。

辅助函数 `as_SB()` 提供了从 `SkShader*` 到 `SkShaderBase*` 的安全向下转型。

### SkShaders::MatrixRec (矩阵记录)

`MatrixRec` 负责在着色器树遍历过程中累积和管理坐标变换:

- **`fCTM`**: 当前变换矩阵(Canvas Transform Matrix)。
- **`fTotalLocalMatrix`**: 所有本地矩阵的串联(含已应用和未应用的)。
- **`fPendingLocalMatrix`**: 尚未应用到管线中的本地矩阵。
- **`concat(m)`**: 返回新的 MatrixRec,将矩阵 m 追加到待处理和总矩阵中。
- **`apply(rec)`**: 将待处理矩阵的逆应用到 `SkRasterPipeline`,返回已应用状态的 MatrixRec。
- **`applyForFragmentProcessor()`**: GPU Fragment Processor 路径专用,起始坐标已在本地空间。

### SkColorShader

最简单的着色器实现,表示单一 sRGB 颜色。`isConstant()` 返回 `true`,存储的颜色值为扩展 sRGB 格式(`SkColor4f`)。不需要坐标输入。

### SkBlendShader

组合两个子着色器(dst 和 src)并使用指定的 `SkBlendMode` 进行混合。`appendStages` 需要分别执行两个子着色器的管线阶段,然后附加混合操作。

### SkImageShader

最复杂的着色器(实现文件约 33KB),负责将 `SkImage` 映射到绘制区域。核心功能包括:

- 支持 `SkTileMode`(Clamp、Repeat、Mirror、Decal)在 X 和 Y 方向独立设置。
- 支持多种采样方式(`SkSamplingOptions`),包括最近邻、双线性、三次(Mitchell/CatmullRom)。
- 支持子集采样(`MakeSubset`)、原始模式(`MakeRaw`)。
- `CubicResamplerMatrix()` 计算三次重采样核矩阵。
- Legacy 路径通过 `SkBitmapProcLegacyShader::MakeContext` 创建上下文。

### SkLocalMatrixShader 与 SkCTMShader

- **`SkLocalMatrixShader`**: 包装另一个着色器并在其前添加一个本地矩阵变换。`makeWithLocalMatrix()` 创建此类型。`MakeWrapped<T>` 模板方法简化了带本地矩阵的着色器创建。
- **`SkCTMShader`**: 替换 CTM 的特殊着色器,用于 clipShader 场景,保存 clip 时刻的 CTM。

### SkRuntimeShader

基于 `SkRuntimeEffect`(SkSL 运行时效果)的着色器,允许用户通过 SkSL 语言编写自定义着色逻辑。支持 uniform 数据、子着色器、以及调试追踪(`SkSL::DebugTracePriv`)。

### SkPerlinNoiseShader

实现 SVG 规范中的 `feTurbulence` 滤镜效果,支持两种噪声类型:
- **`kFractalNoise`**: 分形噪声,输出 = noise * 0.5 + 0.5
- **`kTurbulence`**: 湍流噪声,输出 = abs(noise)

内部使用 `PaintingData` 结构体管理晶格选择器(`fLatticeSelector`)和噪声数据(`fNoise`),并通过 `StitchData` 支持平铺缝合。

### SkPictureShader

将 `SkPicture` 作为平铺图案使用。先将 Picture 渲染到一个临时 `SkImage` 中,然后通过 `SkImageShader` 进行平铺。`CachedImageInfo` 负责缓存图像信息,避免重复渲染。

### SkWorkingColorSpaceShader

将子着色器的颜色空间从输入色彩空间转换为输出色彩空间。支持在非预乘(unpremul)模式下工作。三个关键参数:`fInputSpace`(输入色彩空间)、`fOutputSpace`(输出色彩空间)、`fWorkInUnpremul`(是否在非预乘空间工作)。

### 其他着色器

- **`SkColorFilterShader`**: 将颜色滤镜(`SkColorFilter`)应用于子着色器输出,同时支持 alpha 缩放。
- **`SkCoordClampShader`**: 将坐标钳制到指定的矩形子集(`fSubset`)内。
- **`SkEmptyShader`**: 空着色器,`appendStages` 始终返回 `false`,不绘制任何内容。
- **`SkTransformShader`**: 在 `drawVertices` 和 `drawAtlas` 中使用,支持每个三角形/四边形独立的纹理坐标变换。矩阵可通过 `update()` 动态更新而无需重建管线。
- **`SkTriColorShader`**: 三角形顶点色插值着色器,用于 `drawVertices`。内部使用 4x3 矩阵(`Matrix43`)进行重心坐标到颜色的映射。
- **`SkGainmapShader`**: HDR 增益图着色器,通过 SkSL 运行时效果将基础图像和增益图合成为 HDR 内容。

## 依赖关系

### 向上依赖(被本目录使用)

| 依赖模块 | 说明 |
|----------|------|
| `include/core/SkShader.h` | 公共着色器接口 |
| `include/core/SkFlattenable.h` | 序列化/反序列化基础设施 |
| `include/core/SkMatrix.h` | 2D 变换矩阵 |
| `include/core/SkColorSpace.h` | 色彩空间管理 |
| `include/core/SkImage.h` | 图像抽象 |
| `include/effects/SkRuntimeEffect.h` | 运行时效果(SkSL) |
| `src/core/SkRasterPipeline.h` | 光栅化管线(CPU 渲染路径) |
| `src/core/SkColorSpaceXformSteps.h` | 色彩空间转换步骤 |
| `src/core/SkArenaAlloc` | 竞技场分配器(高效临时内存分配) |
| `src/core/SkReadBuffer` / `SkWriteBuffer` | 序列化缓冲区 |

### 向下依赖(依赖本目录的模块)

| 依赖模块 | 说明 |
|----------|------|
| `src/gpu/ganesh/` | Ganesh GPU 后端,将着色器转换为 Fragment Processor |
| `src/gpu/graphite/` | Graphite GPU 后端,将着色器转换为 GPU 管线 |
| `src/core/SkDraw.cpp` | CPU 绘制入口 |
| `src/core/SkCanvas.cpp` | 画布操作 |

## 设计模式分析

### 1. 组合模式 (Composite Pattern)

着色器系统大量使用组合模式。许多着色器本身是其他着色器的包装或组合:
- `SkBlendShader` 包含两个子着色器(dst, src)并通过混合模式组合。
- `SkLocalMatrixShader` 包装一个子着色器并添加矩阵变换。
- `SkColorFilterShader` 在子着色器输出上应用颜色滤镜。
- `SkWorkingColorSpaceShader` 在子着色器周围添加色彩空间转换。

这种树形结构允许用户通过嵌套组合构建复杂的着色效果。

### 2. 策略模式 (Strategy Pattern)

`appendStages()` 纯虚方法定义了着色器的"策略接口",每个具体着色器类型实现自己的光栅化管线阶段添加逻辑。渲染引擎不需要知道具体的着色器类型,只需调用统一的 `appendStages` 接口。

### 3. 工厂模式 (Factory Pattern)

通过 `SK_FLATTENABLE_HOOKS` 宏和 `SkRegisterXxxFlattenable()` 函数,每种着色器注册自己的工厂方法(`CreateProc`)用于反序列化。`SkFlattenable` 基础设施维护一个类型名到工厂函数的全局映射表。

### 4. 模板方法模式 (Template Method)

`SkGradientBaseShader::appendStages()` 实现了渐变着色的通用流程(矩阵变换 -> 子类坐标映射 -> tile mode -> 颜色填充),子类通过 `appendGradientStages()` 钩子方法提供特定的坐标映射逻辑。

### 5. 访问者/类型标识模式

`ShaderType` 枚举 + `type()` 虚函数实现了一套类型标识系统,替代了 RTTI。GPU 后端通过 `switch(type())` 将着色器分发到对应的 Fragment Processor 或 Pipeline 构建逻辑。

## 数据流

### CPU 光栅化路径

```
用户调用 SkCanvas::drawRect(paint)
            |
            v
SkDraw::drawRect() 提取 paint.getShader()
            |
            v
SkShaderBase::appendRootStages(rec, ctm)
            |
            v
构造 MatrixRec(ctm), 调用 appendStages(rec, matrixRec)
            |
            v
具体着色器的 appendStages() 实现:
  1. matrixRec.apply(rec) -- 将坐标变换应用到管线
  2. 向 SkRasterPipeline 添加特定操作:
     - SkColorShader: 直接设置常量颜色
     - SkImageShader: 纹理采样阶段
     - SkBlendShader: dst.appendStages + src.appendStages + blend
     - 渐变着色器: 坐标映射 + tile mode + 颜色插值
            |
            v
SkRasterPipeline 按添加顺序依次执行所有阶段
            |
            v
每个像素获得最终的 RGBA 颜色值
```

### 矩阵变换传递流程

```
根着色器接收 CTM
     |
     v
MatrixRec(ctm) 创建
     |
     +-- concat(localMatrix1) --> 新的 MatrixRec
     |                               |
     |                               +-- concat(localMatrix2) --> ...
     |
     +-- apply(rec) --> 向管线注入 seed_shader + matrix 阶段
                        返回 "已应用" 状态的 MatrixRec
```

### 序列化/反序列化流程

```
序列化 (flatten):
  SkShaderBase::flatten(buffer)
    -> 子类 flatten: 写入类型特定数据

反序列化 (CreateProc):
  SkFlattenable::Deserialize(type, data, size)
    -> 查找已注册的 CreateProc
    -> 子类::CreateProc(SkReadBuffer)
    -> 读取数据并重建着色器对象
```

## 相关文档与参考

- **公共 API 头文件**: `include/core/SkShader.h` -- 用户可见的着色器接口
- **渐变公共 API**: `include/effects/SkGradient.h` -- 渐变描述结构体 `SkGradient`
- **运行时效果**: `include/effects/SkRuntimeEffect.h` -- SkSL 运行时着色器 API
- **光栅化管线**: `src/core/SkRasterPipeline.h` -- CPU 渲染的核心管线机制
- **GPU Ganesh 后端**: `src/gpu/ganesh/GrFragmentProcessor.h` -- 着色器到 GPU FP 的转换
- **GPU Graphite 后端**: `src/gpu/graphite/` -- 新一代 GPU 后端的着色器处理
- **Skia 官方文档**: https://skia.org/docs/user/api/skshader/ -- 着色器使用指南
- **锥形渐变设计文档**: https://skia.org/dev/design/conical -- 锥形渐变算法说明
- **SVG 噪声规范**: https://www.w3.org/TR/SVG11/filters.html#feTurbulenceElement -- Perlin 噪声的参考规范
