# MtlGraphicsPipeline -- Metal 图形管线

> 源文件:
> - `src/gpu/graphite/mtl/MtlGraphicsPipeline.h`
> - `src/gpu/graphite/mtl/MtlGraphicsPipeline.mm`

## 概述

MtlGraphicsPipeline 是 Graphite Metal 后端的图形管线实现,继承自 `GraphicsPipeline` 基类。它将着色器编译、顶点描述、混合状态、深度模板状态等组装为 Metal 的 `MTLRenderPipelineState` 对象。与 Vulkan 不同,Metal 的深度模板状态和模板引用值独立于管线状态对象,因此也一并管理。

## 架构位置

```
GraphicsPipeline (抽象基类)
  -> MtlGraphicsPipeline  <-- 本模块
       -> id<MTLRenderPipelineState> (渲染管线状态)
       -> id<MTLDepthStencilState> (深度模板状态)
```

## 主要类与结构体

### MtlGraphicsPipeline

关键缓冲区索引常量:

| 常量 | 值 | 用途 |
|------|-----|------|
| `kIntrinsicUniformBufferIndex` | 0 | 内置 uniform |
| `kCombinedUniformIndex` | 1 | 合并 paint/renderstep uniform |
| `kStaticDataBufferIndex` | 2 | 静态顶点数据 |
| `kAppendDataBufferIndex` | 3 | 追加顶点/实例数据 |
| `kGradientBufferIndex` | 4 | 渐变存储缓冲区 |

```cpp
class MtlGraphicsPipeline final : public GraphicsPipeline {
    sk_cfp<id<MTLRenderPipelineState>> fPipelineState;
    sk_cfp<id<MTLDepthStencilState>> fDepthStencilState;
    uint32_t fStencilReferenceValue;
};
```

## 公共 API 函数

### Make -- 常规管线创建
```cpp
static sk_sp<MtlGraphicsPipeline> Make(const MtlSharedContext*, const RuntimeEffectDictionary*,
    const UniqueKey&, const GraphicsPipelineDesc&, const RenderPassDesc&,
    SkEnumBitMask<PipelineCreationFlags>, uint32_t compilationID);
```
完整流程: ShaderInfo 生成 -> SkSL 编译为 MSL -> MTLLibrary 创建 -> 管线状态组装。

### MakeLoadMSAAPipeline -- MSAA 加载管线
```cpp
static sk_sp<MtlGraphicsPipeline> MakeLoadMSAAPipeline(const MtlSharedContext*, const RenderPassDesc&);
```
使用硬编码的 MSL 着色器创建 MSAA 加载管线。

## 内部实现细节

### 顶点描述创建

`create_vertex_descriptor` 为静态和追加属性分别配置:
- 属性格式通过 `attribute_type_to_mtlformat` 转换
- 静态数据固定使用 `PerVertex` 步进
- 追加数据根据渲染步骤使用 `PerVertex` 或 `PerInstance`

### 混合状态

`create_color_attachment` 配置 `MTLRenderPipelineColorAttachmentDescriptor`:
- 支持基本混合方程（Add/Subtract/ReverseSubtract）
- 双源混合系数需要 macOS 10.12+ / iOS 11+
- `BlendShouldDisable` 优化：当混合等效于直接写入时禁用混合

### MSL 着色器版本

MSAA 加载管线使用原始 MSL（非 SkSL），包含:
- 全屏三角形条带顶点着色器（通过 vertexID 生成坐标）
- 纹理读取片段着色器

### 管线状态组装

通过 `MTLRenderPipelineDescriptor` 配置:
- 顶点/片段函数
- 顶点描述符
- 颜色附件格式和混合
- 深度/模板附件格式
- 光栅化采样数

## 依赖关系

- `GraphicsPipeline` -- 基类
- `MtlGraphiteUtils` -- MSL 编译、格式转换
- `MtlSharedContext` -- 设备、深度模板状态缓存
- `ShaderInfo` -- SkSL 着色器生成
- `SkSLToMSL` -- SkSL 到 MSL 编译

## 设计模式与设计决策

1. **三合一管线对象**: 将 `MTLRenderPipelineState`、`MTLDepthStencilState` 和模板引用值打包在一起,简化命令缓冲区的管线绑定。
2. **MSLFunction 对**: 使用 `std::pair<id<MTLLibrary>, std::string>` 传递库和入口点名,支持同一库中的多个函数。
3. **内部 Make 重载**: 公共 `Make` 处理 SkSL 编译逻辑,内部 `Make` 处理纯 Metal 管线创建,实现关注点分离。

## 性能考量

- 管线创建涉及 MSL 编译,是耗时操作,通过 Graphite 的管线缓存避免重复。
- `MakeLoadMSAAPipeline` 使用预编译 MSL 字符串,编译开销较小。
- 标签同步仅在创建时执行一次。

## 相关文件

- `src/gpu/graphite/GraphicsPipeline.h` -- 管线基类
- `src/gpu/graphite/mtl/MtlSharedContext.h` -- Metal 共享上下文
- `src/gpu/graphite/mtl/MtlGraphiteUtils.h` -- MSL 编译
- `src/gpu/graphite/mtl/MtlCommandBuffer.h` -- 管线使用者
- `src/gpu/graphite/ShaderInfo.h` -- 着色器信息
