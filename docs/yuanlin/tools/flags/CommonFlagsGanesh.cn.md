# CommonFlagsGanesh - Ganesh GPU 上下文选项标志

> 源文件:
> - [tools/flags/CommonFlagsGanesh.h](../../../tools/flags/CommonFlagsGanesh.h)
> - [tools/flags/CommonFlagsGanesh.cpp](../../../tools/flags/CommonFlagsGanesh.cpp)

## 概述

CommonFlagsGanesh 定义了 Ganesh GPU 后端特有的命令行标志，并提供 `SetCtxOptions()` 函数将这些标志转换为 `GrContextOptions` 结构。包括路径渲染器选择、缓存控制、驱动 workaround、MSAA 和 OpsTask 分割等配置。

## 架构位置

位于 `tools/flags/` 目录下，是 Ganesh 测试配置层。连接命令行参数与 GrContextOptions，被 DM 和其他 GPU 测试工具使用。

## 主要类与结构体

无独立类定义，使用 `CommonFlags` 命名空间。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `CommonFlags::SetCtxOptions(GrContextOptions*)` | 将命令行标志应用到 Ganesh 上下文选项 |

### 定义的标志

| 标志 | 类型 | 说明 |
|------|------|------|
| `--cachePathMasks` | bool | 允许路径遮罩纹理缓存 |
| `--failFlushTimeCallbacks` | bool | 使所有 flush 回调失败 |
| `--allPathsVolatile` | bool | 所有路径标记为 volatile |
| `--pr` | string | 启用/禁用特定路径渲染器 |
| `--maxAtlasSize` | int | 纹理图集最大尺寸 |
| `--disableDriverCorrectnessWorkarounds` | bool | 禁用驱动兼容性修复 |
| `--dontReduceOpsTaskSplitting` | bool | 不重排任务减少渲染 pass |
| `--gpuResourceCacheLimit` | int | GPU 资源缓存字节限制 |
| `--allowMSAAOnNewIntel` | bool | 在新 Intel GPU 上启用 MSAA |

## 内部实现细节

- **路径渲染器解析**：`--pr` 接受空格分隔的渲染器名称列表，`~` 前缀表示排除。支持 none、dashline、aahairline、aaconvex、aalinearizing、small、tri、atlas、tess、default。
- **默认行为**：以 `~` 开头的列表从 default 开始排除；否则从 none 开始添加。
- **线程池**：与 CommonFlagsGraphite 类似，使用静态 `SkExecutor` 实例。

## 依赖关系

- **工具**：CommandLineFlags
- **Ganesh**：GrContextOptions、GpuPathRenderers
- **Skia**：SkExecutor

## 设计模式与设计决策

- **位掩码路径渲染器**：`GpuPathRenderers` 使用位运算组合多个渲染器。
- **集中映射**：字符串名称到枚举值的映射在单一函数中完成。
- **默认值策略**：大多数标志使用保守默认值，特殊测试需求通过命令行覆盖。

## 性能考量

- `--dontReduceOpsTaskSplitting` 影响渲染 pass 合并策略。
- `--gpuResourceCacheLimit` 直接影响 GPU 内存使用。
- `--maxAtlasSize` 影响字形和路径图集大小。
- 路径渲染器选择影响不同路径类型的渲染性能。

## 相关文件

- `tools/flags/CommonFlagsGraphite.h` - Graphite 对应标志
- `include/gpu/ganesh/GrContextOptions.h` - Ganesh 上下文选项
- `tools/flags/CommandLineFlags.h` - 基础框架
