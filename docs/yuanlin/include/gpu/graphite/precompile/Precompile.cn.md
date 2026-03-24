# Precompile

> 源文件: `include/gpu/graphite/precompile/Precompile.h`

## 概述
Precompile 模块提供了 Skia Graphite 渲染管线预编译功能,允许客户端在实际绘制前提前编译着色器和创建管线对象,从而减少运行时的编译卡顿,提升渲染性能和用户体验。该模块是 Graphite 高性能渲染架构的关键组成部分。

## 架构位置
该文件位于 Skia Graphite GPU 后端的公共接口层,属于 `skgpu::graphite` 命名空间。它是 Graphite 预编译系统的顶层 API,配合 `PaintOptions`、`DrawTypeFlags` 等组件工作,位于应用层和渲染管线创建层之间。

## 主要类与结构体

### RenderPassProperties
描述渲染通道属性的结构体,用于指定管线创建时的渲染目标配置。

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fDSFlags | DepthStencilFlags | 深度模板标志 (是否使用深度、模板测试) |
| fDstCT | SkColorType | 目标颜色类型 (如 RGBA_8888) |
| fDstCS | sk_sp<SkColorSpace> | 目标颜色空间 (如 sRGB) |
| fRequiresMSAA | bool | 是否需要多重采样抗锯齿 |

**操作符重载**:
- `operator==`: 完整比较所有成员,包括颜色空间的等价性检查
- `operator!=`: 非等价判断

**用途**:
- 定义预编译的渲染目标配置
- 支持不同颜色格式和抗锯齿模式的管线变体
- 与 `SkCanvas` 的渲染目标属性对应

## 公共 API 函数

### `Precompile`
```cpp
void SK_API Precompile(
    PrecompileContext* precompileContext,
    const PaintOptions& paintOptions,
    DrawTypeFlags drawTypes,
    SkSpan<const RenderPassProperties> renderPassProperties);
```

**功能**: 预编译指定配置的渲染管线

**参数**:
- `precompileContext`: 线程安全的预编译上下文,持有必需的 GPU 上下文资源
- `paintOptions`: 捕获一组 `SkPaint` 配置的集合 (颜色、着色器、混合模式等)
- `drawTypes`: 绘制类型标志位掩码 (如 kRect、kPath、kText)
- `renderPassProperties`: 渲染通道属性的数组,支持多种目标配置

**行为**:
1. 遍历所有 `paintOptions` × `drawTypes` × `renderPassProperties` 的组合
2. 为每个组合生成对应的管线键 (Pipeline Key)
3. 检查管线缓存,编译缺失的着色器和管线对象
4. 异步编译,不阻塞调用线程 (具体行为依赖后端实现)

**返回值**: 无 (编译在后台进行)

**使用场景**:
- **启动时预加载**: 在应用启动或关卡加载时编译常用管线
- **分帧预编译**: 在空闲帧逐步编译,避免卡顿
- **场景切换**: 在场景转换前预编译下个场景的管线

## 内部实现细节

### 组合爆炸处理
预编译需要遍历大量组合:
```
总组合数 = paintOptions.numCombinations()
          × popcount(drawTypes)
          × renderPassProperties.size()
```

**优化策略**:
- `PaintOptions` 内部使用选项集合避免枚举所有可能
- 管线缓存去重,相同配置只编译一次
- 支持部分预编译,客户端控制粒度

### 线程安全设计
`PrecompileContext` 设计为线程安全:
- 可从后台线程调用 `Precompile`
- 内部使用锁保护管线缓存
- 编译任务可能提交到 GPU 专用线程

### 颜色空间等价性检查
`RenderPassProperties::operator==` 使用 `SkColorSpace::Equals`:
- 比较颜色空间的实际转换矩阵,而非指针相等
- 支持不同对象但等价的颜色空间匹配缓存

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/core/SkColorSpace.h | 颜色空间表示 |
| include/core/SkColorType.h | 颜色类型枚举 |
| include/core/SkSpan.h | 轻量级数组视图 |
| include/gpu/graphite/GraphiteTypes.h | DepthStencilFlags、DrawTypeFlags 等类型 |
| PaintOptions (前向声明) | 绘制配置的封装 |
| PrecompileContext (前向声明) | 预编译执行上下文 |

### 被依赖的模块
- 应用层代码: 在初始化阶段调用预编译
- Graphite Context: 提供 `PrecompileContext` 实例
- 管线缓存系统: 接收预编译结果

## 设计模式与设计决策

### 命令模式 (Command Pattern)
`Precompile` 函数封装了管线编译请求:
- **命令**: 预编译指定配置的管线
- **接收者**: GPU 后端的编译器和缓存
- **参数化**: 通过 `PaintOptions`、`DrawTypeFlags`、`RenderPassProperties` 配置

### 策略模式 (Strategy Pattern)
`RenderPassProperties` 定义渲染策略的变体:
- 不同的颜色格式策略
- 不同的抗锯齿策略
- 不同的深度模板策略

### 享元模式 (Flyweight Pattern)
管线对象共享:
- 相同配置的管线只存储一份
- `RenderPassProperties::operator==` 用于查找现有对象
- 减少内存占用和编译时间

## 性能考量

### 预编译时机权衡
- **启动时全量预编译**: 延长启动时间,但运行时无卡顿
- **延迟预编译**: 快速启动,但首次绘制可能卡顿
- **增量预编译**: 分帧编译,平衡启动和运行性能

### 组合数优化
建议策略:
- 只预编译实际会使用的配置 (如游戏中的 UI 和角色)
- 使用统计数据驱动,预编译热门管线
- 分级预编译,高优先级先处理

### 内存开销
每个管线对象占用内存:
- 着色器代码 (编译后的二进制)
- 管线状态对象 (PSO)
- 元数据 (键、引用计数)

建议使用缓存淘汰策略,限制最大缓存大小。

### 异步编译优化
现代 GPU API 支持异步编译:
- **Vulkan**: 使用 `VkPipelineCache` 和多线程编译
- **Metal**: 后台编译管线状态对象
- **D3D12**: 异步 PSO 创建

`Precompile` 应利用这些特性避免阻塞主线程。

## 使用示例

### 基础预编译
```cpp
// 1. 创建预编译上下文
sk_sp<skgpu::graphite::Context> context = createGraphiteContext();
std::unique_ptr<PrecompileContext> precompileCtx =
    context->makePrecompileContext();

// 2. 定义绘制配置
PaintOptions paintOptions;
paintOptions.setShaders({
    PrecompileShaders::Color(),
    PrecompileShaders::Image(),
    PrecompileShaders::LinearGradient()
});
paintOptions.setBlendModes({SkBlendMode::kSrcOver, SkBlendMode::kScreen});

// 3. 指定绘制类型
DrawTypeFlags drawTypes = DrawTypeFlags::kRect | DrawTypeFlags::kRRect;

// 4. 定义渲染目标
RenderPassProperties props;
props.fDstCT = kRGBA_8888_SkColorType;
props.fDstCS = SkColorSpace::MakeSRGB();
props.fRequiresMSAA = true;

// 5. 执行预编译
Precompile(precompileCtx.get(), paintOptions, drawTypes, {&props, 1});
```

### 多目标预编译
```cpp
std::vector<RenderPassProperties> targets;

// HDR 渲染目标
targets.push_back({
    .fDstCT = kRGBA_F16_SkColorType,
    .fDstCS = SkColorSpace::MakeRec2020(),
    .fRequiresMSAA = false
});

// SDR 渲染目标
targets.push_back({
    .fDstCT = kRGBA_8888_SkColorType,
    .fDstCS = SkColorSpace::MakeSRGB(),
    .fRequiresMSAA = true
});

Precompile(precompileCtx.get(), paintOptions, drawTypes, targets);
```

### 分帧预编译
```cpp
void precompileIncrementally(PrecompileContext* ctx,
                             const std::vector<PaintOptions>& allOptions) {
    static size_t index = 0;
    const size_t batchSize = 10;  // 每帧编译 10 个配置

    for (size_t i = 0; i < batchSize && index < allOptions.size(); ++i, ++index) {
        Precompile(ctx, allOptions[index], DrawTypeFlags::kAll, renderProps);
    }
}

// 在渲染循环中调用
void onIdle() {
    if (!precompileComplete) {
        precompileIncrementally(precompileCtx.get(), paintConfigs);
    }
}
```

## 平台相关说明

### Vulkan 后端
- 使用 `VkPipelineCache` 跨会话持久化
- 支持多线程并行编译
- 验证层开销较大,发布版本建议关闭

### Metal 后端
- 利用 `MTLBinaryArchive` 持久化编译结果
- 异步编译通过 `newRenderPipelineStateWithDescriptor:completionHandler:`
- Apple Silicon 上编译速度更快

### D3D12 后端
- 使用 PSO 库管理管线对象
- 支持异步编译
- 着色器缓存依赖 DXC 编译器

## 相关文件
| 文件 | 关系 |
|------|------|
| include/gpu/graphite/precompile/PaintOptions.h | 定义绘制配置集合 |
| include/gpu/graphite/precompile/PrecompileBase.h | 预编译对象的基类 |
| include/gpu/graphite/GraphiteTypes.h | 定义 DrawTypeFlags、DepthStencilFlags |
| include/gpu/graphite/Context.h | 提供创建 PrecompileContext 的方法 |
| src/gpu/graphite/PipelineCache.h | 内部管线缓存实现 |

## 常见问题与解决方案

### 问题 1: 预编译时间过长
**原因**: 组合数过多或硬件编译速度慢
**解决**:
- 减少 `PaintOptions` 的选项数量
- 使用更精确的 `DrawTypeFlags`
- 分批预编译,显示进度条

### 问题 2: 运行时仍然卡顿
**原因**: 实际绘制使用了未预编译的配置
**解决**:
- 启用调试日志,找出缺失的组合
- 扩大预编译覆盖范围
- 使用运行时统计指导预编译策略

### 问题 3: 内存占用过高
**原因**: 预编译了过多不常用的管线
**解决**:
- 实现基于 LRU 的缓存淘汰
- 限制缓存大小上限
- 只预编译热门配置

### 问题 4: 跨平台行为不一致
**原因**: 不同 GPU API 的编译器特性差异
**解决**:
- 测试所有目标平台
- 使用持久化缓存减少编译需求
- 关注平台特定的编译器警告

## 最佳实践

1. **使用持久化缓存**: 将编译结果保存到磁盘,下次启动直接加载
2. **监控预编译效果**: 统计缓存命中率和编译时间
3. **按需预编译**: 根据用户行为预测下一步需要的管线
4. **测试覆盖率**: 确保预编译覆盖实际绘制的所有路径
5. **渐进式加载**: UI 相关管线优先,装饰性效果延后
6. **版本管理**: 缓存与 GPU 驱动版本关联,更新后重新编译

## 扩展阅读

### DepthStencilFlags 常用值
- `kNone`: 不使用深度模板
- `kDepth`: 仅使用深度测试
- `kStencil`: 仅使用模板测试
- `kDepthStencil`: 同时使用深度和模板

### DrawTypeFlags 常用值
- `kRect`: 矩形绘制
- `kRRect`: 圆角矩形
- `kPath`: 通用路径
- `kText`: 文本渲染
- `kImage`: 图像绘制
- `kAll`: 所有类型

### 颜色空间选择建议
- **UI 渲染**: sRGB (最广泛支持)
- **HDR 内容**: Display P3 或 Rec2020
- **线性混合**: 使用线性 sRGB (避免 gamma 校正)
