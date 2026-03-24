# CommonFlagsGraphite - Graphite GPU 测试选项标志

> 源文件:
> - [tools/flags/CommonFlagsGraphite.h](../../../tools/flags/CommonFlagsGraphite.h)
> - [tools/flags/CommonFlagsGraphite.cpp](../../../tools/flags/CommonFlagsGraphite.cpp)

## 概述

CommonFlagsGraphite 定义了 Graphite GPU 后端特有的命令行标志，并提供 `SetTestOptions()` 函数将这些标志转换为 `skiatest::graphite::TestOptions` 结构。包括 Dawn/WebGPU 特定选项、MSAA 配置、路径渲染阈值等。

## 架构位置

位于 `tools/flags/` 目录下，是 Graphite 测试配置层。桥接命令行参数与 Graphite 的 ContextOptions 和 TestOptions。

## 主要类与结构体

无独立类定义，使用 `CommonFlags` 命名空间包装函数。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `CommonFlags::SetTestOptions(TestOptions*)` | 将命令行标志应用到 Graphite 测试选项 |

### 定义的标志

| 标志 | 类型 | 说明 |
|------|------|------|
| `--disable_tint_symbol_renaming` | bool | 禁用 Dawn WGSL 符号重命名 |
| `--neverYieldToWebGPU` | bool | 使用永不让出的上下文选项 |
| `--useWGPUTextureView` | bool | 使用包装的 WGPU 纹理视图 |
| `--internalMSAATileSize` | int | 限制 MSAA 纹理尺寸 |
| `--minMSAAPathSize` | int | 小于此值的路径使用光栅图集 |
| `--useDrawListLayer` | bool | 启用实验性图层排序 |

## 内部实现细节

- 从 CommonFlagsConfig 中声明引用 `--gpuThreads` 和 `--internalSamples` 标志。
- GPU 线程池使用 `SkExecutor::MakeFIFOThreadPool`，通过静态变量确保全局唯一。
- Dawn 相关标志通过 `#if defined(SK_DAWN)` 条件编译。

## 依赖关系

- **工具**：CommandLineFlags、graphite::TestOptions
- **Skia**：SkExecutor、graphite::ContextOptions

## 设计模式与设计决策

- **集中配置**：将分散的标志定义和应用逻辑集中在一个文件中。
- **条件编译**：Dawn 特定标志仅在 SK_DAWN 编译时可用。
- **静态线程池**：全局唯一的执行器实例避免重复创建。

## 性能考量

- 配置仅在启动时应用一次。
- 线程池配置直接影响 Graphite 的并行性能。

## 相关文件

- `tools/flags/CommonFlagsGanesh.h` - Ganesh 对应标志
- `tools/graphite/TestOptions.h` - 测试选项结构
- `tools/flags/CommandLineFlags.h` - 基础框架
