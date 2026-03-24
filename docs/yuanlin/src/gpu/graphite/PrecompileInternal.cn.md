# PrecompileInternal

> 源文件: src/gpu/graphite/PrecompileInternal.h

## 概述

`PrecompileInternal.h` 是 Skia Graphite GPU 后端预编译系统的内部实现头文件。该文件定义了 `PrecompileCombinations` 函数，用于将绘制选项与渲染器组合，生成所有可能的图形管线变体并提交到 GPU 进行预编译。这是 Graphite 预编译系统的核心算法实现，负责穷举所有渲染状态组合。

该文件属于内部实现，不应被外部代码直接使用。它为公共 API `Precompile()` 提供底层支持。

## 架构位置

在 Skia Graphite 预编译系统中的位置：

```
skia/
├── include/
│   └── gpu/graphite/
│       ├── PrecompileContext.h           # 公共预编译上下文
│       └── precompile/
│           └── Precompile.h              # 公共预编译 API
├── src/
    └── gpu/
        └── graphite/
            ├── PrecompileInternal.h      # 本文件（内部实现）
            ├── PublicPrecompile.cpp      # 公共 API 实现
            └── GraphicsPipeline.h        # 图形管线
```

该文件在预编译流程中的角色：
- **输入**: 接收绘制选项和渲染通道描述
- **处理**: 穷举所有渲染器和绘制类型组合
- **输出**: 触发图形管线创建任务

## 主要函数

### PrecompileCombinations

```cpp
void PrecompileCombinations(const RendererProvider*,
                            ResourceProvider*,
                            const PaintOptions&,
                            const KeyContext&,
                            DrawTypeFlags,
                            bool withPrimitiveBlender,
                            Coverage,
                            const RenderPassDesc&);
```

**功能：** 生成并预编译所有指定条件下的图形管线组合

**参数说明：**

1. **RendererProvider***
   - 提供所有可用的渲染器（`Renderer`）
   - 每个渲染器支持特定的绘制类型

2. **ResourceProvider***
   - 资源提供者，用于创建管线对象
   - 管理 GPU 资源和缓存

3. **PaintOptions&**
   - 绘制选项，包含着色器、混合模式等
   - 定义了着色部分的变体

4. **KeyContext&**
   - 键上下文，提供管线键生成所需的信息
   - 包含能力信息、字典等

5. **DrawTypeFlags**
   - 绘制类型标志（位掩码）
   - 如：矩形、路径、文本等

6. **withPrimitiveBlender**
   - 是否使用原始混合器
   - 影响管线颜色处理方式

7. **Coverage**
   - 覆盖率类型（无、单通道）
   - 决定抗锯齿方式

8. **RenderPassDesc&**
   - 渲染通道描述符
   - 包含目标格式、MSAA 等信息

**工作流程：**

1. **遍历渲染器**
```cpp
for (const Renderer* r : rendererProvider->renderers()) {
    // 检查渲染器是否支持指定的绘制类型
    if (!(r->drawTypes() & drawTypes)) {
        continue;
    }
    // 处理该渲染器...
}
```

2. **匹配原始混合器**
```cpp
if (r->emitsPrimitiveColor() != withPrimitiveBlender) {
    continue;  // 跳过不匹配的渲染器
}
```

3. **匹配覆盖率类型**
```cpp
if (r->coverage() != coverage) {
    continue;  // 跳过不匹配的渲染器
}
```

4. **遍历渲染步骤**
```cpp
for (auto&& s : r->steps()) {
    // 为每个步骤创建管线
}
```

5. **创建图形管线**
```cpp
GraphicsPipelineHandle handle = resourceProvider->createGraphicsPipelineHandle(
    { s->renderStepID(), paintID },
    renderPassDesc,
    PipelineCreationFlags::kForPrecompilation);
resourceProvider->startPipelineCreationTask(keyContext.rtEffectDict(), handle);
```

**组合数量计算：**
```
总管线数 = Σ (匹配的渲染器数量 × 每个渲染器的步骤数 × 绘制选项变体数)
```

典型场景可能生成数百到数千个管线变体。

## 内部实现细节

### 渲染器筛选条件

**条件 1: 绘制类型匹配**
```cpp
if (!(r->drawTypes() & drawTypes)) {
    continue;
}
```

**条件 2: 原始混合器匹配**
```cpp
if (r->emitsPrimitiveColor() != withPrimitiveBlender) {
    continue;
}
```

**条件 3: 覆盖率类型匹配**
```cpp
if (r->coverage() != coverage) {
    continue;
}
```

### 着色步骤处理

```cpp
for (auto&& s : r->steps()) {
    SkASSERT(!s->performsShading() || s->emitsPrimitiveColor() == withPrimitiveBlender);

    UniquePaintParamsID paintID = s->performsShading() ? uniqueID
                                                       : UniquePaintParamsID::Invalid();
    // 创建管线...
}
```

**逻辑：**
- 执行着色的步骤使用实际的 `uniqueID`
- 不执行着色的步骤使用无效 ID

### 管线创建标志

```cpp
PipelineCreationFlags::kForPrecompilation
```

**含义：**
- 标记为预编译管线
- 可能影响编译优化策略
- 允许异步后台编译

### 前向声明

```cpp
enum class Coverage;
class Context;
class KeyContext;
class PaintOptions;
struct RenderPassDesc;
```

**优势：**
- 减少编译依赖
- 加快编译速度
- 避免头文件包含循环

## 依赖关系

### 直接依赖

1. **GraphiteTypes.h** (include/gpu/graphite/GraphiteTypes.h)
   - 提供 `DrawTypeFlags` 等类型定义

2. **RendererProvider** (前向声明)
   - 提供所有可用的渲染器

3. **ResourceProvider** (前向声明)
   - 管理 GPU 资源和管线缓存

4. **PaintOptions** (前向声明)
   - 绘制选项和着色器变体

5. **KeyContext** (前向声明)
   - 管线键生成上下文

6. **RenderPassDesc** (前向声明)
   - 渲染通道描述符

7. **Coverage** (前向声明)
   - 覆盖率类型枚举

### 被依赖模块

1. **PublicPrecompile.cpp**
   - 实现公共 `Precompile()` API
   - 调用 `PrecompileCombinations` 进行实际编译

2. **PrecompileContext**
   - 预编译上下文管理
   - 协调预编译流程

## 设计模式与设计决策

### 1. 内部实现分离

**设计选择：**
- 公共 API 在 `Precompile.h`
- 内部实现在 `PrecompileInternal.h`

**优势：**
- 清晰的 API 边界
- 实现细节隐藏
- 便于维护和测试

### 2. 穷举组合算法

使用嵌套循环穷举所有组合：

**优势：**
- 确保完整覆盖
- 逻辑简单直观
- 易于调试

**劣势：**
- 可能生成大量管线
- 编译时间较长

### 3. 渐进式筛选

按顺序应用多个筛选条件：

```cpp
if (条件1) continue;
if (条件2) continue;
if (条件3) continue;
```

**优势：**
- 早期退出减少计算
- 清晰的条件判断
- 易于添加新条件

### 4. 异步管线创建

```cpp
startPipelineCreationTask(...)
```

**优势：**
- 不阻塞主线程
- 充分利用多核 CPU
- 提升应用响应性

### 5. 断言验证

```cpp
SkASSERT(!s->performsShading() || s->emitsPrimitiveColor() == withPrimitiveBlender);
```

**目的：**
- 验证内部一致性
- 捕获逻辑错误
- 文档化假设

## 性能考量

### 1. 组合爆炸问题

**示例计算：**
```
渲染器: 20 个
每个渲染器步骤: 2-5 个
绘制选项变体: 50 个
覆盖率类型: 2 个

最坏情况: 20 × 5 × 50 × 2 = 10,000 个管线
```

**缓解策略：**
- 智能筛选减少组合数
- 异步编译避免阻塞
- 增量预编译

### 2. 筛选效率

**早期退出优化：**
```cpp
// 快速路径：不匹配直接跳过
if (!(r->drawTypes() & drawTypes)) {
    continue;  // ~5 ns
}
// 较慢路径：需要进一步检查
```

**优化：**
- 将最常失败的条件放在前面
- 使用位运算加速类型检查

### 3. 管线创建开销

**单个管线创建时间：**
- 简单管线：1-5 ms
- 复杂管线：10-50 ms

**优化策略：**
- 后台线程创建
- 优先编译常用管线
- 缓存已编译管线

### 4. 内存使用

**管线对象大小：**
- 管线句柄：~64 bytes
- 编译后着色器：10-100 KB
- 元数据：~1 KB

**总内存：** 数千管线 × 100 KB = 数百 MB

**管理策略：**
- LRU 缓存淘汰
- 按需加载
- 压缩不活跃管线

### 5. 编译时间

**预编译总时间：**
```
10,000 管线 × 5 ms = 50 秒（单线程）
10,000 管线 × 5 ms / 8 核 ≈ 6 秒（多线程）
```

**用户体验影响：**
- 应用启动时间增加
- 可在后台进行
- 显示进度提示

## 相关文件

### 核心依赖
- `include/gpu/graphite/GraphiteTypes.h` - 类型定义
- `src/gpu/graphite/Renderer.h` - 渲染器定义
- `src/gpu/graphite/GraphicsPipeline.h` - 图形管线

### 预编译系统
- `include/gpu/graphite/precompile/Precompile.h` - 公共 API
- `src/gpu/graphite/PublicPrecompile.cpp` - API 实现
- `include/gpu/graphite/PrecompileContext.h` - 预编译上下文
- `src/gpu/graphite/PrecompileContextPriv.h` - 上下文私有接口

### 管线系统
- `src/gpu/graphite/GraphicsPipelineDesc.h` - 管线描述符
- `src/gpu/graphite/PipelineCreationTask.h` - 管线创建任务
- `src/gpu/graphite/ResourceProvider.h` - 资源提供者

### 渲染系统
- `src/gpu/graphite/RendererProvider.h` - 渲染器提供者
- `src/gpu/graphite/RenderPassDesc.h` - 渲染通道描述
- `src/gpu/graphite/KeyContext.h` - 键上下文

### 测试文件
- `tests/graphite/PrecompileTest.cpp` - 预编译测试
