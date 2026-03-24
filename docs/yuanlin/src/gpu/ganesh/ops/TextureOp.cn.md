# TextureOp

> 源文件
> - src/gpu/ganesh/ops/TextureOp.h
> - src/gpu/ganesh/ops/TextureOp.cpp

## 概述

`TextureOp` 是 Skia Ganesh GPU 后端中用于绘制纹理矩形的核心操作类，负责将纹理映射到任意四边形区域并进行渲染。该操作支持颜色调制、过滤、Mipmap、子集约束、颜色空间变换等高级功能，并能够智能合并多个纹理绘制调用以提高批处理效率。作为 Skia 中最常用的 GPU 操作之一，`TextureOp` 的实现经过高度优化，内存布局紧凑，合并逻辑复杂，以实现最佳性能。

## 架构位置

`TextureOp` 位于 Skia GPU 渲染管线的以下位置：

- **模块层级**：`src/gpu/ganesh/ops/` - Ganesh GPU 操作层
- **继承关系**：`TextureOpImpl` 继承自 `GrMeshDrawOp`
- **命名空间**：`skgpu::ganesh`
- **接口层**：`TextureOp` 提供静态工厂方法作为公共接口
- **实现层**：`TextureOpImpl` 封装在匿名命名空间中作为私有实现
- **依赖组件**：
  - 上层调用：`SurfaceDrawContext`、`SkGpuDevice`
  - 同层依赖：`FillRectOp`、`QuadPerEdgeAA`
  - 底层依赖：`GrTextureEffect`、`GrGeometryProcessor`

## 主要类与结构体

### TextureOp（公共接口类）

```cpp
class TextureOp
```

**核心职责**：
- 提供纹理绘制操作的公共静态工厂方法
- 封装纹理渲染的参数和配置选项

**关键成员**：
- `enum class Saturate` - 控制颜色饱和度限制（0..1 范围）
- `Make()` - 创建单个纹理四边形绘制操作
- `AddTextureSetOps()` - 批量添加纹理集合操作

### TextureOpImpl（私有实现类）

```cpp
class TextureOpImpl final : public GrMeshDrawOp
```

**核心数据成员**：
- `GrQuadBuffer<ColorSubsetAndAA> fQuads` - 四边形缓冲区，存储所有待渲染的四边形数据
- `sk_sp<GrColorSpaceXform> fTextureColorSpaceXform` - 颜色空间变换
- `Desc* fDesc` - 绘制描述符，存储顶点规格、程序信息等
- `Metadata fMetadata` - 紧凑的元数据（8字节），包含过滤、AA、颜色类型等标志
- `ViewCountPair fViewCountPairs[]` - 可变长度数组，存储纹理代理和四边形计数

### Metadata 结构体

```cpp
struct Metadata
```

**紧凑位域设计**（总大小 8 字节）：
- `skgpu::Swizzle fSwizzle` - 颜色通道重排（2字节）
- `uint16_t fProxyCount` - 代理计数
- `uint16_t fTotalQuadCount` - 总四边形数量
- `uint16_t fFilter : 2` - 过滤模式
- `uint16_t fMipmapMode : 2` - Mipmap 模式
- `uint16_t fAAType : 2` - 抗锯齿类型
- `uint16_t fColorType : 2` - 颜色类型
- `uint16_t fSubset : 1` - 是否使用子集约束
- `uint16_t fSaturate : 1` - 是否饱和颜色
- `uint16_t fUnused : 6` - 预留位

### ColorSubsetAndAA 结构体

```cpp
struct ColorSubsetAndAA
```

**每个四边形的元数据**：
- `SkPMColor4f fColor` - 预乘颜色
- `SkRect fSubsetRect` - 子集约束矩形
- `unsigned fAAFlags : 4` - 四边形边缘 AA 标志

### Desc 结构体

```cpp
struct Desc
```

**绘制描述符**（在准备阶段创建）：
- `VertexSpec fVertexSpec` - 顶点规格
- `GrProgramInfo* fProgramInfo` - 程序信息
- `sk_sp<const GrBuffer> fIndexBuffer` - 索引缓冲区
- `sk_sp<const GrBuffer> fVertexBuffer` - 顶点缓冲区
- `char* fPrePreparedVertices` - 预准备的顶点数据（DDL 使用）

### BatchSizeLimiter 类

```cpp
class TextureOp::BatchSizeLimiter
```

**批量大小限制器**：
- 将大型纹理集合绘制分解为多个可管理的操作
- 遵守索引缓冲区和资源限制
- 根据 AA 类型动态调整批次大小

## 公共 API 函数

### Make

```cpp
static GrOp::Owner Make(
    GrRecordingContext*,
    GrSurfaceProxyView,
    SkAlphaType srcAlphaType,
    sk_sp<GrColorSpaceXform>,
    GrSamplerState::Filter,
    GrSamplerState::MipmapMode,
    const SkPMColor4f&,
    Saturate,
    SkBlendMode,
    GrAAType,
    DrawQuad*,
    const SkRect* subset)
```

**功能**：创建单个纹理四边形绘制操作

**智能降级优化**：
1. **子集检查**：如果子集包含整个纹理，移除子集约束
2. **过滤优化**：调用 `FilterAndMipmapHaveNoEffect()` 检测是否需要过滤
3. **混合模式路由**：
   - `SkBlendMode::kSrcOver`：返回优化的 `TextureOpImpl`
   - 其他混合模式：回退到 `FillRectOp` + 片段处理器链

### AddTextureSetOps

```cpp
static void AddTextureSetOps(
    SurfaceDrawContext*,
    const GrClip*,
    GrRecordingContext*,
    GrTextureSetEntry[],
    int cnt,
    int proxyRunCnt,
    GrSamplerState::Filter,
    GrSamplerState::MipmapMode,
    Saturate,
    SkBlendMode,
    GrAAType,
    SkCanvas::SrcRectConstraint,
    const SkMatrix& viewMatrix,
    sk_sp<GrColorSpaceXform>)
```

**功能**：批量添加纹理集合操作

**三级决策路径**：
1. **单操作回退**：不支持动态状态或非 src-over 混合，每个条目创建独立操作
2. **单批次路径**：条目数量小于限制，创建单个 `TextureOpImpl`
3. **分块批处理**：使用 `BatchSizeLimiter` 将大集合分解为多个批次

### FilterAndMipmapHaveNoEffect

```cpp
std::tuple<bool, bool> FilterAndMipmapHaveNoEffect(
    const GrQuad& srcQuad,
    const GrQuad& dstQuad)
```

**功能**：判断过滤和 Mipmap 是否有实际效果

**判断逻辑**：
- **非轴对齐**：始终需要过滤和 Mipmap
- **轴对齐矩形**：
  - 过滤：源和目标尺寸不同，或小数部分不对齐
  - Mipmap：源尺寸大于目标尺寸（缩小采样）
- **轴对齐四边形**：边长相同且顶点整数对齐时无需过滤

## 内部实现细节

### 坐标归一化机制

**proxy_normalization_params 函数**：
```cpp
struct NormalizationParams {
    float fIW;       // 1/width 或 1.0（矩形纹理）
    float fInvH;     // 1/height 或 1.0，底部原点时取反
    float fYOffset;  // 顶部原点为0，底部原点为归一化高度
};
```

**功能**：统一处理不同纹理类型和原点配置
- **矩形纹理**（`GrTextureType::kRectangle`）：使用像素坐标，iw=ih=1.0
- **2D纹理**：使用归一化坐标，iw=1/width, ih=1/height
- **底部原点**：Y 轴翻转（ih 取反），添加高度偏移

### 子集约束内缩

**normalize_and_inset_subset 函数**：
```cpp
SkRect normalize_and_inset_subset(
    GrSamplerState::Filter filter,
    const NormalizationParams& params,
    const SkRect* subsetRect)
```

**内缩策略**：
- **最近邻过滤**：内缩到像素中心（floor 对齐）
- **线性过滤**：内缩 `GrTextureEffect::kLinearInset`（0.5像素）
- **中心固定**：确保内缩后矩形不会翻转，最小不超过矩形中心
- **Y 轴翻转**：底部原点时交换 top 和 bottom 以保持排序

**安全跳过子集判断**（`safe_to_ignore_subset_rect`）：
1. 无 AA + 最近邻过滤 + 双轴对齐 + 子集包含局部边界
2. 局部边界内缩 0.5 像素后仍在子集内

### 操作合并逻辑

**onCombineIfPossible 实现**：

**合并条件检查**（必须全部满足）：
1. 无预准备描述符（DDL 记录的操作不合并）
2. 子集模式相同
3. 颜色空间变换相同
4. AA 类型兼容（可升级到 kCoverage）
5. 合并后四边形总数不溢出
6. 饱和度模式相同
7. 过滤模式相同
8. Mipmap 模式相同
9. Swizzle 相同

**合并结果类型**：
- `kMerged`：相同代理，直接合并四边形
- `kMayChain`：不同代理但兼容，使用动态状态链接
- `kCannotCombine`：不满足合并条件

**AA 升级传播**：合并时如果需要升级 AA 类型，调用 `propagateCoverageAAThroughoutChain()` 将覆盖 AA 传播到整个操作链。

### 顶点填充流程

**FillInVertices 静态函数**：
```cpp
static void FillInVertices(
    const GrCaps& caps,
    TextureOpImpl* texOp,
    Desc* desc,
    char* vertexData)
```

**流程**：
1. 创建 `QuadPerEdgeAA::Tessellator` 细分器
2. 遍历操作链中的所有操作
3. 对每个操作遍历其所有代理
4. 对每个代理的每个四边形调用 `tessellator.append()`
5. 细分器将四边形转换为顶点数据写入缓冲区

**W0 裁剪**：在 `appendQuad()` 中调用 `GrQuadUtils::ClipToW0()` 裁剪到 W=0 平面，避免透视除法问题。

### 批次分解策略

**BatchSizeLimiter 使用场景**：
- 条目总数超过 `MaxNumNonAAQuads()` 或 `MaxNumAAQuads()`
- 动态状态支持且混合模式为 src-over

**分解算法**：
1. **kNone/kMSAA**：简单按 `MaxNumNonAAQuads()` 切分
2. **kCoverage**：
   - 扫描条目累积 AA 状态
   - 遇到 AA 标志时升级为 kCoverage
   - 达到对应限制时切分批次
   - 允许部分批次降级为 kNone

### 预准备路径（DDL）

**onPrePrepareDraws 流程**：
1. 在记录时 Arena 中分配 `Desc`
2. 调用 `characterize()` 确定顶点规格
3. 调用 `allocatePrePreparedVertices()` 预分配顶点内存
4. 调用 `FillInVertices()` 填充顶点数据
5. 调用 `INHERITED::onPrePrepareDraws()` 创建并注册 `GrProgramInfo`

**flush 时路径**：
- `onPrepareDraws()`：直接在 flush Arena 分配描述符
- 如有预准备顶点：`memcpy` 复制到 GPU 缓冲区
- 否则：现场调用 `FillInVertices()`

## 依赖关系

**核心依赖**：
- `GrMeshDrawOp` - 基类
- `QuadPerEdgeAA` - 四边形抗锯齿顶点生成
- `GrQuad`, `GrQuadBuffer` - 四边形几何表示
- `GrTextureEffect` - 纹理采样片段处理器

**渲染管线依赖**：
- `GrGeometryProcessor` - 几何着色器
- `GrProgramInfo` - 程序配置信息
- `GrMeshDrawTarget` - 网格绘制目标
- `GrOpFlushState` - 操作刷新状态

**资源管理依赖**：
- `GrSurfaceProxyView` - 纹理代理视图
- `GrColorSpaceXform` - 颜色空间变换
- `GrResourceProvider` - 索引缓冲区获取

**回退路径依赖**：
- `FillRectOp` - 复杂混合模式回退

## 设计模式与设计决策

### Pimpl 模式（私有实现）

`TextureOp` 作为公共接口类，将复杂的实现细节封装在匿名命名空间的 `TextureOpImpl` 中，保持接口清晰稳定。

### 工厂方法模式

所有对象创建通过静态 `Make()` 方法，而非直接构造，允许返回优化的替代实现（如 `FillRectOp`）。

### 内存布局优化

**紧凑位域**：`Metadata` 结构体使用位域压缩多个标志到 8 字节
**变长数组技巧**：`fViewCountPairs[1]` 声明为单元素数组，实际通过 `MakeWithExtraMemory` 分配额外内存，避免额外指针开销

**历史原因**：注释强调"增加 TextureOp 大小会导致意外性能退化"，因此极度重视内存紧凑性。

### 策略模式（批处理策略）

根据不同场景选择不同批处理策略：
- 单操作独立绘制
- 单批次聚合绘制
- 分块批处理绘制

### 渐进式优化决策

**多级检查降级**：
1. 在 `Make()` 阶段检查过滤必要性
2. 在构造函数中检查子集必要性
3. 在 `AddTextureSetOps()` 中逐四边形检查过滤和子集

### 防御性编程

- **W0 裁剪**：防止透视除法异常
- **中心固定内缩**：防止子集矩形翻转
- **溢出检查**：`CombinedQuadCountWillOverflow()` 防止计数器溢出

## 性能考量

### 内存紧凑性

- `Metadata` 仅 8 字节，存储 10+ 个状态标志
- `ViewCountPair` 内联分配，避免额外堆分配和指针解引用
- 描述符延迟分配，仅在准备阶段创建

### 批处理与合并

**操作合并**：相同配置的绘制调用合并为单个操作，减少状态切换和绘制调用
**动态状态链接**：不同纹理但兼容的操作链接在一起，通过动态状态数组在单次绘制中切换纹理
**索引缓冲区共享**：使用 `QuadPerEdgeAA::GetIndexBuffer()` 获取共享索引缓冲区

### 顶点数据生成

**预准备路径**：DDL 记录时预填充顶点数据，flush 时直接 `memcpy`，避免重复计算
**现场生成路径**：即时模式直接在 GPU 缓冲区中生成顶点，无中间拷贝

### 过早优化避免

**FilterAndMipmapHaveNoEffect**：避免在不必要时使用过滤和 Mipmap，减少采样器负载
**子集跳过**：安全情况下跳过昂贵的纹理坐标钳位计算

### 分支预测友好

**快速路径优先**：常见场景（src-over 混合、单批次）放在判断前面
**早期返回**：不满足条件立即返回，避免深层嵌套

## 相关文件

**几何处理**：
- `src/gpu/ganesh/geometry/GrQuad.h` - 四边形表示
- `src/gpu/ganesh/geometry/GrQuadBuffer.h` - 四边形缓冲区
- `src/gpu/ganesh/geometry/GrQuadUtils.h` - 四边形工具函数
- `src/gpu/ganesh/ops/QuadPerEdgeAA.h` - 四边形边缘抗锯齿

**相关操作**：
- `src/gpu/ganesh/ops/FillRectOp.h/cpp` - 填充矩形操作（回退路径）
- `src/gpu/ganesh/ops/GrMeshDrawOp.h` - 网格绘制操作基类

**效果与处理器**：
- `src/gpu/ganesh/effects/GrTextureEffect.h` - 纹理效果片段处理器
- `src/gpu/ganesh/effects/GrBlendFragmentProcessor.h` - 混合片段处理器
- `src/gpu/ganesh/GrColorSpaceXform.h` - 颜色空间变换

**基础设施**：
- `src/gpu/ganesh/GrSurfaceProxyView.h` - 表面代理视图
- `src/gpu/ganesh/GrResourceProvider.h` - 资源提供者
- `src/gpu/ganesh/SurfaceDrawContext.h` - 表面绘制上下文
