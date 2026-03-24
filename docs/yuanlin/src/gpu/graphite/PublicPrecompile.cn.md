# PublicPrecompile — Graphite 管线预编译

> 源文件: `src/gpu/graphite/PublicPrecompile.cpp`

## 概述

本文件实现了 Skia Graphite GPU 后端的管线预编译 (pipeline precompilation) 功能。管线预编译允许应用在实际绘制之前提前编译 GPU 图形管线，避免首次使用时的编译卡顿 (jank)。它遍历所有可能的渲染器 (Renderer)、绘制类型 (DrawType)、覆盖模式 (Coverage) 和绘制选项 (PaintOptions) 的组合，为每个有效组合创建图形管线编译任务。

## 架构位置

```
应用层
    └── Precompile() 公共 API (本文件)
        ├── PrecompileCombinations() — 组合遍历
        │   └── PaintOptions::buildCombinations() — 生成 paint 键
        └── compile() — 单个管线编译
            ├── RendererProvider::renderers() — 遍历所有渲染器
            ├── RenderStep — 遍历渲染步骤
            └── ResourceProvider::createGraphicsPipelineHandle() + startPipelineCreationTask()
                └── 异步管线编译
```

## 主要类与结构体

本文件不定义新类，但涉及的核心类型：

| 类型 | 描述 |
|------|------|
| `PrecompileContext` | 预编译上下文，提供字典、渲染器等服务 |
| `PaintOptions` | 绘制选项组合描述 |
| `RenderPassProperties` | 渲染通道属性（目标颜色类型、MSAA、深度模板等） |
| `DrawTypeFlags` | 绘制类型位标志 |
| `Coverage` | 覆盖类型（None、SingleChannel、LCD） |
| `UniquePaintParamsID` | 唯一的绘制参数标识符 |
| `RenderPassDesc` | 渲染通道描述 |
| `GraphicsPipelineHandle` | 图形管线句柄 |

## 公共 API 函数

### Precompile()

```cpp
void Precompile(PrecompileContext* precompileContext,
                const PaintOptions& options,
                DrawTypeFlags drawTypes,
                SkSpan<const RenderPassProperties> renderPassProperties);
```

主预编译入口。对每个渲染通道属性组合：

1. **纹理信息创建**: 通过 `getDefaultSampledTextureInfo()` 获取目标颜色类型的纹理信息
2. **Write Swizzle 计算**: 验证颜色类型与格式的兼容性
3. **LoadOp 变体**: 某些平台 (Dawn) 的 LoadOp 影响 MSAA 管线，需要额外组合
4. **RenderPassDesc 构建**: 包含纹理信息、LoadOp、StoreOp、MSAA、深度模板等
5. **分类编译**: 不同绘制类型有不同的编译策略

### 绘制类型分类处理

| 绘制类型 | 特殊处理 |
|----------|----------|
| 通用形状 | Coverage::None 和 SingleChannel，无 primitiveBlender |
| NonSimpleShape | 额外编译 CoverBounds_InverseCover 管线 |
| BitmapText_Color | 清除 shader 选项，启用 primitiveBlender |
| BitmapText_LCD / SDFText_LCD | LCD 覆盖模式，无 primitiveBlender |
| DrawVertices | 有/无 primitiveBlender 两种变体 |
| DropShadows | 分析型(带 Coverage) + 几何型(带 Gaussian 颜色滤镜) |

### PrecompileCombinations()

```cpp
void PrecompileCombinations(const RendererProvider*, ResourceProvider*,
                             const PaintOptions&, const KeyContext&,
                             DrawTypeFlags, bool withPrimitiveBlender,
                             Coverage, const RenderPassDesc&);
```

遍历 `PaintOptions` 的所有有效组合，对每个组合调用 `compile()`。

## 内部实现细节

### compile() 匿名函数

对于每个生成的 `UniquePaintParamsID`：
1. 遍历所有注册的渲染器
2. 过滤匹配绘制类型、primitiveBlender 和覆盖类型的渲染器
3. 对渲染器的每个渲染步骤 (RenderStep)：
   - 着色步骤使用 paintID，非着色步骤使用 Invalid ID
   - 创建 `GraphicsPipelineHandle`（标记为 `kForPrecompilation`）
   - 启动异步管线编译任务

### LoadOp 变体处理

```
if (rpp.fRequiresMSAA &&
    !caps->msaaRenderToSingleSampledSupport() &&
    caps->loadOpAffectsMSAAPipelines())
```

在需要 MSAA 但不支持 "render to single sampled" 且 LoadOp 影响管线的平台上（如 Dawn/WebGPU），需要为 LoadOp::kClear 和 LoadOp::kLoad 分别编译管线。

### DropShadow 特殊处理

阴影绘制需要两种管线：
- **分析型**: 使用单通道覆盖，标准混合
- **几何型**: 使用 Compose(Blend(kModulate), Gaussian()) 颜色滤镜，primitiveBlender 模式为 kDst，跳过颜色变换

### 颜色 Emoji 文本

```cpp
tmp.setShaders({});  // 着色器不影响最终颜色
```

ARGB 文本已包含颜色信息，不需要着色器处理，但需要 primitiveBlender。

## 依赖关系

**Graphite 核心**:
- `src/gpu/graphite/Caps.h` — GPU 能力查询
- `src/gpu/graphite/Renderer.h`, `RendererProvider.h` — 渲染器注册表
- `src/gpu/graphite/ResourceProvider.h` — 管线创建
- `src/gpu/graphite/GraphicsPipelineDesc.h` — 管线描述
- `src/gpu/graphite/PipelineCreationTask.h` — 异步编译任务

**键和字典**:
- `src/gpu/graphite/KeyContext.h` — 键生成上下文
- `src/gpu/graphite/RuntimeEffectDictionary.h` — 运行时效果字典
- `src/gpu/graphite/UniquePaintParamsID.h` — 绘制参数唯一 ID

**预编译**:
- `include/gpu/graphite/precompile/Precompile.h` — 公共声明
- `src/gpu/graphite/precompile/PaintOptionsPriv.h` — PaintOptions 组合生成
- `src/gpu/graphite/PrecompileInternal.h` — 内部预编译工具

## 设计模式与设计决策

1. **组合爆炸管理**: 通过 `PaintOptions::buildCombinations()` 回调模式，将绘制选项的笛卡尔积展开推迟到需要时，避免一次性生成过多组合。

2. **分类处理策略**: 不同绘制类型有不同的覆盖模式、primitiveBlender 需求和着色器配置。文件将这些特殊情况显式处理而非使用通用路径，确保生成最小化的有效管线集合。

3. **异步编译**: `startPipelineCreationTask()` 触发的管线编译是异步的，不阻塞调用线程。`kForPrecompilation` 标志允许资源提供者优化编译调度。

4. **平台差异抽象**: 通过 `Caps` 查询（如 `loadOpAffectsMSAAPipelines()`）处理平台差异，使预编译逻辑对具体后端透明。

## 性能考量

- **预编译目的**: 将管线编译从渲染热路径移到启动或加载阶段，消除首帧卡顿。
- **组合数量控制**: 通过绘制类型过滤、渲染器匹配等机制限制编译数量，避免不必要的编译浪费。
- **异步编译**: 管线编译任务可并行执行，充分利用多核 CPU。
- **跳过无效组合**: `WriteSwizzleForColorType` 失败时跳过该颜色类型，避免编译运行时不会出现的管线。
- **LoadOp 优化**: 大多数平台只需编译一个 LoadOp 变体，仅在必要时（Dawn MSAA）才编译两个。

## 相关文件

- `include/gpu/graphite/precompile/Precompile.h` — 公共 API 声明
- `include/gpu/graphite/PrecompileContext.h` — 预编译上下文
- `src/gpu/graphite/precompile/PaintOptionsPriv.h` — PaintOptions 组合生成
- `src/gpu/graphite/Renderer.h` — 渲染器定义
- `src/gpu/graphite/GraphicsPipeline.h` — 图形管线
- `src/gpu/graphite/PipelineCreationTask.h` — 管线创建任务
- `src/gpu/graphite/PrecompileInternal.h` — 内部预编译工具
