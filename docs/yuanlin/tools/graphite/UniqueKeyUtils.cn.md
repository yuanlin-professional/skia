# UniqueKeyUtils

> 源文件
> - tools/graphite/UniqueKeyUtils.h
> - tools/graphite/UniqueKeyUtils.cpp

## 概述

UniqueKeyUtils 是 Skia Graphite 测试工具模块,提供管线唯一键(UniqueKey)的提取、解析和验证功能。该模块用于测试管线缓存的正确性,能够从 UniqueKey 中提取 GraphicsPipelineDesc 和 RenderPassDesc,并验证键的序列化和反序列化是否无损。

核心功能:
- 从 GlobalCache 提取所有管线的 UniqueKey
- 将 UniqueKey 解码为 GraphicsPipelineDesc 和 RenderPassDesc
- 验证键的往返(round-trip)转换
- 调试时输出详细的描述符信息
- 用于测试预编译和管线缓存机制

## 架构位置

```
skia/
├── include/gpu/graphite/
│   └── PrecompileContext.h         # 预编译上下文
├── src/gpu/
│   ├── ResourceKey.h                # UniqueKey 定义
│   └── graphite/
│       ├── Caps.h                   # GPU 能力接口
│       ├── ContextPriv.h            # Context 私有接口
│       ├── PrecompileContextPriv.h  # PrecompileContext 私有接口
│       ├── GraphicsPipelineDesc.h   # 图形管线描述符
│       ├── RenderPassDesc.h         # 渲染通道描述符
│       ├── RendererProvider.h       # 渲染器提供器
│       └── GlobalCache.h            # 全局缓存
└── tools/graphite/
    ├── UniqueKeyUtils.h             # 本模块头文件
    └── UniqueKeyUtils.cpp           # 本模块实现
```

在 Graphite 架构中:
- 访问 GlobalCache 的管线缓存
- 使用 Caps 的序列化/反序列化接口
- 配合 PrecompileContext 进行预编译测试
- 验证管线键的编码正确性

## 主要类与结构体

该模块不定义类,仅提供工具函数。涉及的主要类型:

### skgpu::UniqueKey
Skia GPU 资源的唯一标识符,由多个 32 位整数组成。

### skgpu::graphite::GraphicsPipelineDesc
图形管线描述符,包含:
- `renderStepID()`: 渲染步骤 ID
- `paintParamsID()`: 绘制参数 ID

### skgpu::graphite::RenderPassDesc
渲染通道描述符,包含:
- `fColorAttachment`: 颜色附件
- `fColorResolveAttachment`: 颜色解析附件
- `fDepthStencilAttachment`: 深度模板附件
- `fClearColor`: 清除颜色
- `fClearDepth`: 清除深度
- `fClearStencil`: 清除模板值
- `fWriteSwizzle`: 写入混合
- `fSampleCount`: 采样数

### skgpu::graphite::GlobalCache
全局资源缓存,存储管线对象。

## 公共 API 函数

### FetchUniqueKeys()
```cpp
void FetchUniqueKeys(PrecompileContext* precompileContext,
                     std::vector<UniqueKey>* keys)
```
**功能**: 从全局缓存中提取所有图形管线的 UniqueKey
**参数**:
- `precompileContext`: 预编译上下文
- `keys`: 输出参数,存储提取的键

**行为**:
1. 获取 GlobalCache 引用
2. 预留 vector 容量(优化性能)
3. 遍历所有图形管线,收集 UniqueKey

**用途**: 测试中获取已编译的管线列表

### DumpDescs() [仅 Debug]
```cpp
#ifdef SK_DEBUG
void DumpDescs(PrecompileContext* precompileContext,
               const GraphicsPipelineDesc& pipelineDesc,
               const RenderPassDesc& rpd)
#endif
```
**功能**: 输出管线描述符和渲染通道描述符的详细信息
**参数**:
- `precompileContext`: 预编译上下文
- `pipelineDesc`: 图形管线描述符
- `rpd`: 渲染通道描述符

**输出内容**:
- 管线的 paintParamsID 和 RenderStep 名称
- 着色器字典的详细信息
- 渲染通道的所有附件和参数

**用途**: 调试管线键不匹配问题

### ExtractKeyDescs()
```cpp
bool ExtractKeyDescs(PrecompileContext* precompileContext,
                     const UniqueKey& origKey,
                     GraphicsPipelineDesc* pipelineDesc,
                     RenderPassDesc* renderPassDesc)
```
**功能**: 从 UniqueKey 提取描述符,并验证往返转换
**参数**:
- `precompileContext`: 预编译上下文
- `origKey`: 原始 UniqueKey
- `pipelineDesc`: 输出参数,图形管线描述符
- `renderPassDesc`: 输出参数,渲染通道描述符

**返回值**:
- `true`: 提取成功
- `false`: 提取失败

**行为**:
1. 调用 `Caps::extractGraphicsDescs()` 解码键
2. Debug 模式下重新编码并验证一致性
3. 不匹配时输出详细调试信息

**用途**: 验证管线键的编码/解码正确性

## 内部实现细节

### 键提取实现
```cpp
void FetchUniqueKeys(PrecompileContext* precompileContext,
                     std::vector<UniqueKey>* keys) {
    GlobalCache* globalCache = precompileContext->priv().globalCache();

    // 预留空间,避免重分配
    keys->reserve(globalCache->numGraphicsPipelines());

    // 遍历所有管线
    globalCache->forEachGraphicsPipeline(
        [keys](const UniqueKey& key, const GraphicsPipeline* pipeline) {
            keys->push_back(key);
        });
}
```
**优化**: 预先 reserve 容量,避免 vector 多次重分配

### 往返验证逻辑
```cpp
bool ExtractKeyDescs(...) {
    const Caps* caps = precompileContext->priv().caps();
    const RendererProvider* rendererProvider = ...;

    // 1. 解码原始键
    bool extracted = caps->extractGraphicsDescs(
        origKey, pipelineDesc, renderPassDesc, rendererProvider);
    if (!extracted) {
        SkASSERT(0);
        return false;
    }

#ifdef SK_DEBUG
    // 2. 重新编码
    UniqueKey newKey = caps->makeGraphicsPipelineKey(
        *pipelineDesc, *renderPassDesc);

    // 3. 比较原始键和新键
    if (origKey != newKey) {
        SkDebugf("------- The UniqueKey didn't round trip!\n");
        origKey.dump("original key:");
        newKey.dump("reassembled key:");
        DumpDescs(precompileContext, *pipelineDesc, *renderPassDesc);
        SkDebugf("------------------------\n");
    }
    SkASSERT(origKey == newKey);
#endif

    return true;
}
```

**验证目标**: 确保 `makeKey() -> extractKey() -> makeKey()` 得到相同结果

**失败处理**:
- 输出原始键和重组键的十六进制转储
- 输出完整的描述符信息
- 断言失败,中止测试

### 调试信息输出
```cpp
void DumpDescs(...) {
    const RendererProvider* rendererProvider = ...;
    const ShaderCodeDictionary* dict = ...;

    // 输出管线信息
    const RenderStep* rs = rendererProvider->lookup(pipelineDesc.renderStepID());
    SkDebugf("GraphicsPipelineDesc: %u %s\n",
             pipelineDesc.paintParamsID().asUInt(), rs->name());

    // 输出着色器字典信息
    dict->dump(precompileContext->priv().caps(), pipelineDesc.paintParamsID());

    // 输出渲染通道详细信息
    SkDebugf("RenderPassDesc:\n");
    SkDebugf("   colorAttach: %s\n", rpd.fColorAttachment.toString().c_str());
    SkDebugf("   colorResolveAttach: %s\n", ...);
    SkDebugf("   depthStencilAttach: %s\n", ...);
    SkDebugf("   clearColor: %.2f %.2f %.2f %.2f\n", ...);
    SkDebugf("   clearDepth: %.2f\n", ...);
    SkDebugf("   stencilClear: %u\n", ...);
    SkDebugf("   writeSwizzle: %s\n", ...);
    SkDebugf("   sampleCount: %u\n", ...);
}
```

**信息丰富度**: 输出几乎所有描述符字段,便于分析问题

## 依赖关系

### Graphite 核心
- `skgpu::graphite::PrecompileContext`: 预编译上下文
- `skgpu::graphite::Caps`: GPU 能力接口,提供键编解码
- `skgpu::graphite::GlobalCache`: 全局缓存,存储管线
- `skgpu::graphite::GraphicsPipelineDesc`: 管线描述符
- `skgpu::graphite::RenderPassDesc`: 渲染通道描述符

### 资源管理
- `skgpu::UniqueKey`: GPU 资源唯一键
- `skgpu::graphite::GraphicsPipeline`: 图形管线对象

### 私有接口
- `PrecompileContextPriv`: 访问预编译上下文内部
- `ContextPriv`: 访问上下文内部

### 渲染系统
- `skgpu::graphite::RendererProvider`: 渲染器提供器
- `skgpu::graphite::RenderStep`: 渲染步骤
- `skgpu::graphite::ShaderCodeDictionary`: 着色器字典

## 设计模式与设计决策

### 工具函数模式
```cpp
namespace UniqueKeyUtils {
    void FetchUniqueKeys(...);
    bool ExtractKeyDescs(...);
    void DumpDescs(...);
}
```
**设计**: 使用命名空间而非类
**理由**:
- 无需状态管理
- 纯工具函数集合
- 避免不必要的类开销

### 回调遍历模式
```cpp
globalCache->forEachGraphicsPipeline(
    [keys](const UniqueKey& key, const GraphicsPipeline* pipeline) {
        keys->push_back(key);
    });
```
**优势**:
- 隐藏 GlobalCache 内部结构
- 灵活的遍历逻辑
- 类型安全的迭代

### 双向验证设计
```cpp
// 编码
UniqueKey key = caps->makeGraphicsPipelineKey(desc, rpd);
// 解码
caps->extractGraphicsDescs(key, &desc, &rpd);
// 再次编码验证
UniqueKey key2 = caps->makeGraphicsPipelineKey(desc, rpd);
SkASSERT(key == key2);
```
**目的**: 确保键编码的可逆性和一致性

### 条件编译调试
```cpp
#ifdef SK_DEBUG
    // 详细验证和输出
#endif
```
**权衡**:
- Debug 模式: 全面验证,输出详细信息
- Release 模式: 跳过验证,提高性能

### 输出参数模式
```cpp
bool ExtractKeyDescs(...,
                     GraphicsPipelineDesc* pipelineDesc,
                     RenderPassDesc* renderPassDesc)
```
**设计**: 使用输出指针参数
**替代方案**: 返回 `std::pair` 或结构体
**理由**: C++ 传统风格,清晰的输入输出分离

### 失败优先设计
```cpp
bool extracted = caps->extractGraphicsDescs(...);
if (!extracted) {
    SkASSERT(0);
    return false;  // 立即返回
}
// 继续正常逻辑
```
提前返回失败情况,减少嵌套。

## 性能考量

### 容量预留优化
```cpp
keys->reserve(globalCache->numGraphicsPipelines());
```
**收益**: 避免 `vector` 多次重分配
- 无预留: O(n log n) 次分配
- 预留: O(1) 次分配

### 迭代效率
```cpp
globalCache->forEachGraphicsPipeline([keys](...) {
    keys->push_back(key);
});
```
**时间复杂度**: O(n),n 为管线数量
**空间复杂度**: O(n),存储所有键

### 往返验证开销
```cpp
#ifdef SK_DEBUG
    UniqueKey newKey = caps->makeGraphicsPipelineKey(...);
    if (origKey != newKey) { ... }
#endif
```
**开销**: 仅在 Debug 模式
- 编码: O(k),k 为描述符大小
- 比较: O(k)
- 总计: 2 * O(k) + 常数开销

**可接受**: 测试代码,性能非关键。

### 调试输出开销
```cpp
SkDebugf(...);
dict->dump(...);
```
**开销**: 格式化和 I/O,较大
**频率**: 仅在验证失败时
**影响**: 可忽略(罕见情况)

## 相关文件

### Graphite 核心
- `include/gpu/graphite/PrecompileContext.h`: 预编译上下文接口
- `src/gpu/graphite/Caps.h`: GPU 能力和键编解码
- `src/gpu/graphite/GlobalCache.h`: 全局缓存
- `src/gpu/graphite/GraphicsPipeline.h`: 图形管线

### 描述符
- `src/gpu/graphite/GraphicsPipelineDesc.h`: 管线描述符
- `src/gpu/graphite/RenderPassDesc.h`: 渲染通道描述符
- `src/gpu/graphite/RenderStep.h`: 渲染步骤

### 资源键
- `src/gpu/ResourceKey.h`: UniqueKey 基础类型
- `src/gpu/graphite/ResourceTypes.h`: Graphite 资源类型

### 着色器系统
- `src/gpu/graphite/ShaderCodeDictionary.h`: 着色器字典
- `src/gpu/graphite/RendererProvider.h`: 渲染器提供器

### 测试用途
- `tests/GraphitePrecompileTest.cpp`: 使用本模块验证预编译
- `tests/GraphiteCacheTest.cpp`: 使用本模块测试缓存
- `tools/graphite/ContextFactory.h`: 测试上下文工厂
