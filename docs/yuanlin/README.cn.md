# Skia 项目中文文档索引

## 概述

Skia 是由 Google 开发和维护的开源 2D 图形库，提供跨平台的高性能渲染能力。它是 Google Chrome、Android、Flutter、Chrome OS 等众多产品的底层图形引擎。Skia 支持多种后端渲染器，包括 CPU 软件渲染、OpenGL、Vulkan、Metal 和 Direct3D，能够在几乎所有主流平台上运行。

本文档是 Skia 项目的中文技术文档索引，旨在为中文开发者提供全面的代码架构解析和模块功能说明。文档结构与 Skia 源码目录一一对应，方便开发者在阅读源码时查阅参考。

## 项目架构总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Skia 2D 图形库                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  include/     │  │  modules/    │  │  tools/      │              │
│  │  公共 API     │  │  扩展模块    │  │  开发工具    │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                 │                 │                       │
│  ┌──────▼─────────────────▼─────────────────▼───────┐              │
│  │                    src/ 核心实现                    │              │
│  ├──────────────────────────────────────────────────┤              │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐    │              │
│  │  │ core/  │ │ gpu/   │ │ sksl/  │ │ codec/ │    │              │
│  │  │ 核心   │ │ GPU    │ │ 着色器 │ │ 编解码 │    │              │
│  │  └────────┘ └────────┘ └────────┘ └────────┘    │              │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐    │              │
│  │  │effects/│ │shaders/│ │ image/ │ │ pdf/   │    │              │
│  │  │ 特效   │ │ 着色器 │ │ 图像   │ │ PDF    │    │              │
│  │  └────────┘ └────────┘ └────────┘ └────────┘    │              │
│  └──────────────────────────────────────────────────┘              │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  tests/      │  │  bench/      │  │  gm/         │              │
│  │  单元测试    │  │  性能基准    │  │  黄金测试    │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  infra/      │  │  gn/bazel/   │  │ third_party/ │              │
│  │  基础设施    │  │  构建系统    │  │  第三方依赖  │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
```

## 目录索引

### 核心源码

| 目录 | 说明 | 文档链接 |
|------|------|----------|
| [src/](src/) | 核心源码实现 | [README](src/README.md) |
| [include/](include/) | 公共头文件和 API 定义 | [README](include/README.md) |

### 扩展模块

| 目录 | 说明 | 文档链接 |
|------|------|----------|
| [modules/](modules/) | 扩展模块（CanvasKit、Skottie 等） | [README](modules/README.md) |

### 测试与基准

| 目录 | 说明 | 文档链接 |
|------|------|----------|
| [tests/](tests/) | 单元测试 | [README](tests/README.md) |
| [bench/](bench/) | 性能基准测试 | [README](bench/README.md) |
| [gm/](gm/) | Golden Master 图形测试 | [README](gm/README.md) |
| [fuzz/](fuzz/) | 模糊测试 | [README](fuzz/README.md) |
| [dm/](dm/) | 测试运行器（Dungeon Master） | [README](dm/README.md) |

### 开发工具

| 目录 | 说明 | 文档链接 |
|------|------|----------|
| [tools/](tools/) | 开发和调试工具 | [README](tools/README.md) |
| [bin/](bin/) | 构建和辅助脚本 | [README](bin/README.md) |

### 构建系统

| 目录 | 说明 | 文档链接 |
|------|------|----------|
| [gn/](gn/) | GN 构建配置 | [README](gn/README.md) |
| [bazel/](bazel/) | Bazel 构建配置 | [README](bazel/README.md) |
| [build_overrides/](build_overrides/) | 构建参数覆盖 | [README](build_overrides/README.md) |
| [toolchain/](toolchain/) | 工具链配置 | [README](toolchain/README.md) |

### 基础设施

| 目录 | 说明 | 文档链接 |
|------|------|----------|
| [infra/](infra/) | CI/CD 基础设施 | [README](infra/README.md) |

### 平台与客户端

| 目录 | 说明 | 文档链接 |
|------|------|----------|
| [platform_tools/](platform_tools/) | 平台特定构建工具 | [README](platform_tools/README.md) |
| [client_utils/](client_utils/) | 客户端工具库 | [README](client_utils/README.md) |
| [example/](example/) | 示例代码 | [README](example/README.md) |

### 实验性功能

| 目录 | 说明 | 文档链接 |
|------|------|----------|
| [experimental/](experimental/) | 实验性功能和原型 | [README](experimental/README.md) |

### 其他

| 目录 | 说明 | 文档链接 |
|------|------|----------|
| [third_party/](third_party/) | 第三方依赖库配置 | [README](third_party/README.md) |
| [rust/](rust/) | Rust 语言集成 | [README](rust/README.md) |
| [resources/](resources/) | 测试资源文件 | [README](resources/README.md) |
| [docs/](docs/) | 项目文档 | [README](docs/README.md) |
| [demos.skia.org/](demos.skia.org/) | Web 演示 | [README](demos.skia.org/README.md) |
| [specs/](specs/) | 规范文档 | [README](specs/README.md) |
| [relnotes/](relnotes/) | 发布说明 | [README](relnotes/README.md) |
| [site/](site/) | 网站源码 | [README](site/README.md) |

## 文档约定

- 所有文档使用中文撰写
- 每个目录对应一个 README.md 文件
- 文档包含：概述、架构图、关键类/函数、依赖关系、设计模式分析
- 代码引用格式：`文件名:行号`
- 架构图使用 ASCII 字符绘制

## 如何使用本文档

1. **按模块浏览**：从上方索引表选择感兴趣的模块
2. **按功能查找**：参考架构图了解功能对应的模块位置
3. **深入源码**：每个 README 中的"关键类与函数"章节提供了源码入口点

## Skia 版本信息

本文档基于 Skia 主分支（main branch）生成，反映最新的代码结构和架构。
