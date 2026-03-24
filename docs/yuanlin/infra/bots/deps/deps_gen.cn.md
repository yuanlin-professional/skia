# deps_gen.go - Skia 依赖项声明数据文件

> 源文件: [infra/bots/deps/deps_gen.go](https://github.com/aspect-build/aspect-cli/blob/main/infra/bots/deps/deps_gen.go)

## 概述

`deps_gen.go` 是一个由代码生成工具 `generate.go` 自动生成的 Go 源文件，用于以结构化数据的形式声明 Skia 项目的所有第三方依赖项。该文件定义了一个 `deps` 变量，类型为 `deps_parser.DepsEntries`，其中包含了所有外部依赖的标识符（ID）、版本号（commit hash 或语义版本）以及在本地文件系统中的存放路径。此文件不应手动编辑，而应通过 `generate.go` 重新生成。

## 架构位置

该文件位于 Skia 基础设施机器人（infra/bots）的依赖管理子系统中。在 Skia 的整体架构中，它属于构建基础设施层，负责：

- 为 CI/CD 系统提供精确的依赖版本信息
- 作为依赖解析器（deps_parser）的数据源
- 与 DEPS 文件（Chromium 风格的依赖声明）保持同步

```
Skia 项目结构
├── src/              # 核心源代码
├── include/          # 公共头文件
├── third_party/      # 第三方依赖存放目录
│   └── externals/    # 由 deps_gen.go 管理的外部依赖
├── infra/
│   └── bots/
│       └── deps/
│           ├── deps_gen.go    # 本文件 (自动生成)
│           └── generate.go    # 生成器脚本
└── DEPS              # 上游依赖声明文件
```

## 主要类与结构体

### `deps_parser.DepsEntries`

这是一个 map 类型，键为依赖项的字符串标识符，值为包含依赖详细信息的结构体。

### 依赖条目结构

每个依赖条目包含三个字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `Id` | `string` | 依赖的唯一标识符，通常为 Git 仓库 URL |
| `Version` | `string` | 依赖的特定版本，通常为 Git commit hash 或 CIPD 版本号 |
| `Path` | `string` | 依赖在本地文件系统中的相对路径 |

## 公共 API 函数

本文件不包含函数定义，仅导出一个包级别的变量：

```go
var deps = deps_parser.DepsEntries{...}
```

该变量供 `deps` 包内其他文件使用，用于查询和解析依赖信息。

## 内部实现细节

### 依赖来源分类

文件中声明的依赖可以按来源分为以下几类：

1. **Android 相关**：来自 `android.googlesource.com`，如 `dng_sdk`、`perfetto`、`piex`
2. **Chromium 相关**：来自 `chromium.googlesource.com`，包括：
   - 图形库：ANGLE、Vulkan Headers/Tools/Utility Libraries、SPIRV-Cross、glslang
   - 编解码器：libjpeg-turbo、libgav1、libwebp、libyuv、libjxl
   - 通用库：abseil-cpp、zlib、ICU、freetype、harfbuzz、highway、expat、icu4x
   - 模板引擎：jinja2、markupsafe
3. **Skia 自有镜像**：来自 `skia.googlesource.com`，如 libpng、brotli、wuffs、imgui、SPIRV-Tools/Headers
4. **其他**：Dawn (WebGPU)、SwiftShader (软件渲染)、CIPD 工具包（ninja、sk、bazel_build）

### 版本控制策略

- 大部分依赖使用 40 字符的 Git commit SHA-1 hash 作为版本标识，确保构建的可重复性
- 少数 CIPD 包使用语义版本号（如 `version:2@1.12.1.chromium.4`）或 `git_revision:` 前缀

### 路径映射规则

- 绝大多数第三方依赖映射到 `third_party/externals/` 目录下
- 构建工具映射到 `bin/` 目录
- 任务驱动器映射到 `task_drivers/` 目录
- Skia 基础设施映射到 `infra/skia-infra/`
- 构建工具元数据映射到 `buildtools/`

## 依赖关系

### 直接依赖

- `go.skia.org/infra/go/depot_tools/deps_parser`：提供 `DepsEntries` 类型定义

### 生成依赖

- `generate.go`：生成本文件的工具，运行命令为 `go run generate.go`
- `DEPS`（项目根目录）：上游依赖声明文件，作为生成器的输入源

### 被依赖

- Skia 基础设施中的自动化工具和 CI 系统通过导入 `deps` 包来获取依赖版本信息

## 设计模式与设计决策

### 代码生成模式

采用代码生成而非运行时解析 DEPS 文件，有以下优势：
- **编译时类型检查**：Go 编译器可以验证数据结构的正确性
- **无运行时开销**：不需要在运行时解析文本文件
- **版本控制友好**：生成的文件可以提交到版本控制中，便于追踪变化

### 单一数据源模式

所有依赖信息集中在一个文件中声明，避免了依赖信息分散在多处导致的不一致性问题。

### 不可变版本锁定

每个依赖使用精确的 commit hash，而非分支名或标签，确保了构建的确定性和可重复性。这是 Chromium 生态系统中常见的做法（类似于 `npm lock` 或 `go.sum`）。

## 性能考量

- 该文件在编译时被静态嵌入二进制文件，不产生运行时文件 I/O 开销
- 使用 map 数据结构，依赖查找的时间复杂度为 O(1)
- 文件约 265 行，包含约 50 个依赖条目，生成和编译速度极快
- 由于是自动生成的，更新依赖版本时只需重新运行生成器，无需手动编辑

## 相关文件

- `infra/bots/deps/generate.go` - 生成本文件的工具脚本
- `DEPS` - 项目根目录的上游依赖声明文件
- `third_party/externals/` - 第三方依赖的实际存放目录
- `infra/bots/` - CI/CD 机器人基础设施目录
- `.gitmodules` 或其他子模块配置（如果存在）
