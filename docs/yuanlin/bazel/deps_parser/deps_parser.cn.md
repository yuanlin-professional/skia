# Bazel 依赖解析器

> 源文件: `bazel/deps_parser/deps_parser.go`

## 概述

此程序解析 Skia 的 DEPS 文件（Chromium 风格的依赖管理文件），提取外部 C++ 和 Rust 依赖的 Git 仓库信息，并生成 JSON 配置文件供 Bazel 的 `git_repository` 规则使用。它是 Skia 从 GN/gclient 构建系统向 Bazel 迁移的依赖桥接工具。

## 架构位置

位于 Bazel 构建工具链 (`bazel/deps_parser/`)，在依赖同步流程中将 DEPS 文件转换为 Bazel 可消费的格式。

## 主要类与结构体

### `depConfig`
- `bazelNameOverride` - Bazel 风格名称覆盖（下划线替代连字符）
- `needsBazelFile` - 是否需要自定义 BUILD.bazel 文件
- `patches`, `patchCmds`, `patchCmdsWin` - 补丁配置
- `isIndirect` - 是否为间接依赖

### `repoConfig`
- JSON 可序列化结构，包含 `Name`, `Remote`, `Commit`, `BuildFile`, `Patches`, `PatchCmds`, `PatchCmdsWin`

### `deps`
- `Warning` - 提示不要手动修改
- `Direct` - 直接依赖列表
- `Indirect` - 间接依赖列表

## 公共 API 函数

- `main()` - 命令行入口，解析 DEPS 文件并写入 JSON
- `parseDEPSFile(contents)` - 解析 DEPS 文件内容，返回临时文件路径和依赖数量
- `moveWithCopyBackup(src, dst)` - 原子性文件移动，支持跨分区备份

## 内部实现细节

- `depsOverrides` 映射表定义了所有需要导入 Bazel 的依赖（约 30+ 个），包括 freetype、harfbuzz、icu、vulkan 等
- 使用正则表达式 `externals/(\S+)".+"(https.+)@([a-f0-9]+)"` 从 DEPS 文件中提取仓库 URL 和 commit hash
- 先写入临时文件再原子重命名，防止部分写入导致文件损坏
- 处理跨设备链接错误（`invalid cross-device link`），在无法重命名时回退到复制

## 依赖关系

- Go 标准库：`encoding/json`, `flag`, `fmt`, `os`, `regexp`, `strings`

## 设计模式与设计决策

- **白名单机制**：只有在 `depsOverrides` 中明确列出的依赖才会被导入 Bazel
- **区分直接/间接依赖**：`isIndirect` 标志区分 Skia 直接使用和被其他依赖间接使用的库
- **原子写入**：使用临时文件+重命名保证文件完整性
- **自定义 BUILD 文件**：大多数依赖需要 `needsBazelFile=true`，因为上游未提供 Bazel 构建规则

## 性能考量

一次性解析工具，性能不是关键指标。使用正则表达式逐行匹配，效率足够。

## 相关文件

- `DEPS` - Skia 依赖定义文件
- `bazel/deps.json` - 生成的输出 JSON 文件
- `bazel/external/*/BUILD.bazel` - 各依赖的自定义 Bazel 构建文件
