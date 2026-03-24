# CommonFlagsConfig - 渲染配置命令行解析

> 源文件:
> - [tools/flags/CommonFlagsConfig.h](../../../tools/flags/CommonFlagsConfig.h)
> - [tools/flags/CommonFlagsConfig.cpp](../../../tools/flags/CommonFlagsConfig.cpp)

## 概述

CommonFlagsConfig 定义了 Skia 的渲染配置字符串解析系统。它将命令行 `--config` 参数（如 `"gl"`, `"vk"`, `"gpu(api=gl,samples=4)"`, `"graphite-metal"`）解析为结构化的配置对象，包含后端类型、颜色类型、采样数、via 处理管线等信息。这是 DM 测试运行器配置系统的核心。

## 架构位置

位于 `tools/flags/` 目录下，是 DM 和其他工具程序的配置基础设施。它连接命令行参数解析（CommandLineFlags）与具体的渲染后端配置（Ganesh/Graphite/SVG）。

## 主要类与结构体

### `SkCommandLineConfig`（基类）
表示一个渲染配置字符串，包含 tag（完整标签）、backend（后端名）和 viaParts（via 处理步骤）。

### `SkCommandLineConfigGpu`（Ganesh GPU 配置）
从配置字符串中提取 GPU 相关参数：
- `ContextType` - GL/Vulkan/Metal/Dawn 等上下文类型
- `SurfType` - 默认/后端纹理/后端渲染目标
- `samples`、`colorType`、`alphaType`、`surfaceFlags`
- 布尔选项：DDL、Slug、reduced shaders、persistent cache 等

### `SkCommandLineConfigGraphite`（Graphite 配置）
Graphite 后端专用配置：
- `ContextType`、`colorType`、`alphaType`
- `testPersistentStorage`、`testPrecompileGraphite`、`testPipelineTracking`

### `SkCommandLineConfigSvg`
SVG 后端配置，包含 `pageIndex`。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `ParseConfigs(configList, outResult)` | 将配置字符串列表解析为配置对象数组 |
| `asConfigGpu()` / `asConfigGraphite()` / `asConfigSvg()` | 类型安全的向下转型 |
| 各种 getter | 获取上下文类型、颜色类型、采样数等配置参数 |

## 内部实现细节

- **配置字符串格式**：`[via-]*backend`，其中 backend 可以是简写（如 `"gl"`）或完整形式（如 `"gpu(api=gl,samples=16)"`）。
- **简写展开**：`"glmsaa16"` 展开为 `"gpu(api=gl,samples=16)"`。
- **Via 管线**：配置字符串中 `-` 分隔的前缀表示 via 处理步骤（如 `"serialize-"` 表示序列化/反序列化往返）。
- **GPU 后端检测**：支持 GL、GLES、Vulkan、Metal、Dawn、Direct3D 等多种 API。

## 依赖关系

- **工具**：CommandLineFlags、GrContextFactory、ContextType
- **Skia 核心**：SkColorType、SkAlphaType、SkColorSpace、SkString

## 设计模式与设计决策

- **多态配置层次**：基类 + 多个子类，通过虚函数 `asConfig*()` 实现类型安全的向下转型。
- **字符串解析**：支持简写和完整参数化两种配置语法。
- **灵活的 via 管线**：via 机制允许在渲染管线中插入序列化/反序列化等处理步骤。

## 性能考量

- 配置解析仅在启动时执行一次，不影响测试运行性能。
- 使用 `TArray` 存储配置对象的 `unique_ptr`，避免拷贝。

## 相关文件

- `tools/flags/CommandLineFlags.h` - 基础命令行参数框架
- `dm/DM.cpp` - 使用 ParseConfigs 解析 --config
- `tools/ganesh/GrContextFactory.h` - GPU 上下文工厂
