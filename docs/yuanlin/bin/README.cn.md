# bin/ - 构建辅助脚本

## 概述

`bin/` 目录包含 Skia 项目的各种构建辅助脚本和开发者工具。这些脚本主要用于自动化构建环境的配置（如下载 GN、Ninja 等工具）、管理依赖同步、运行 Android 设备测试、执行性能对比分析和生成代码覆盖率报告等。

这些脚本大多数是 Python 或 Shell 脚本，设计为从 Skia 项目根目录运行。它们是 Skia 开发工作流程中的重要组成部分，特别是 `fetch-gn`、`fetch-ninja` 和 `sync` 三个脚本构成了 Skia 构建环境初始化的核心流程。开发者在首次检出 Skia 代码后，通常需要运行这些脚本来准备构建环境。

`bin/` 目录中的脚本按功能可分为三类：构建工具获取脚本（`fetch-*` 系列）、开发辅助脚本（`sync`、`droid`、`coverage`、`compare`）和 Skia 基础设施工具（`gerrit-number`、`list-skia-bots`、`try-clients`）。部分工具在构建过程中会被 GN 或 Ninja 调用（如 `activate-emsdk`），其余则由开发者手动使用。

## 目录结构

```
bin/
├── activate-emsdk         # Emscripten SDK 安装和激活
├── compare                # nanobench 性能对比分析
├── coverage               # 代码覆盖率报告生成
├── droid                  # Android 设备运行辅助脚本
├── fetch-clang-format     # 下载 clang-format 代码格式化工具
├── fetch-fonts-testdata   # 下载字体测试数据
├── fetch-gn               # 下载 GN 构建工具
├── fetch-ninja            # 下载 Ninja 构建工具
├── fetch-sk               # 下载 sk 基础设施工具
├── fetch-skps             # 下载 SKP 测试资源
├── fetch-svgs             # 下载 SVG 测试资源
├── gerrit-number          # Gerrit 代码评审编号查询
├── list-skia-bots         # 列出 Skia CI 机器人
├── sync                   # 同步第三方依赖
├── sysopen                # 跨平台打开文件/URL
└── try-clients            # 触发 CI 试验构建
```

## 关键文件

### fetch-gn - 下载 GN 构建工具

```python
#!/usr/bin/env python3
# 自动下载平台匹配的 GN 二进制文件
```

从 Chrome 基础设施包（CIPD）下载指定版本的 GN 二进制文件。脚本会：
1. 检测当前操作系统（darwin/linux/win32）和 CPU 架构（amd64/arm64）
2. 使用硬编码的 Git revision（`b2afae122eeb6ce09c52d63f67dc53fc517dbdc8`）确定版本
3. 从 `chrome-infra-packages.appspot.com` 下载 zip 压缩包
4. 解压 `gn` 二进制文件到 `bin/` 目录
5. 同时复制到 `third_party/gn/` 以兼容 depot_tools

### fetch-ninja - 下载 Ninja 构建工具

从 CIPD 下载指定版本的 Ninja 构建工具：
1. 从 `DEPS` 文件中读取 `ninja_version` 确定所需版本
2. 检查本地是否已有正确版本（通过 SHA256 校验）
3. 如需更新，从 CIPD 下载并安装到 `third_party/ninja/` 目录
4. 记录版本信息到 `bin/ninja.version` 文件

### sync - 同步第三方依赖

```python
#!/usr/bin/env python3
# 静默调用 tools/git-sync-deps 同步所有第三方依赖
```

这是一个薄包装器，设置 `GIT_SYNC_DEPS_QUIET=T` 环境变量后调用 `tools/git-sync-deps` 脚本。该脚本读取 `DEPS` 文件，使用 Git 将所有第三方依赖同步到指定的提交版本。

### activate-emsdk - Emscripten SDK 激活

```python
EMSDK_VERSION = '4.0.7'
```

安装并激活指定版本的 Emscripten SDK（当前为 4.0.7）：
1. 定位 `third_party/externals/emsdk/` 中的 EMSDK
2. 执行 `emsdk install --permanent <version>`
3. 执行 `emsdk activate --permanent <version>`
4. 在 `linux-aarch64`/`linux-arm64` 平台上跳过（不支持）

### droid - Android 设备运行脚本

```bash
#!/bin/bash
# 将编译产物推送到 Android 设备并执行
# 用法：droid out/dm --src gm --config gpu
```

将 GN 构建的可执行文件推送到连接的 Android 设备上运行：
1. 通过 `adb push` 将 `resources/` 目录同步到设备的 `/data/local/tmp/`
2. 推送可执行文件到设备
3. 在设备上设置执行权限并运行，传递命令行参数

### compare - 性能对比工具

使用 Mann-Whitney U 统计检验比较两次 nanobench 运行的性能差异：
- 读取两个基准测试结果文件
- 使用 Bonferroni 校正处理多重比较
- 仅报告具有统计显著性（p < 0.0001 调整后）的性能变化
- 需要 `scipy` 库支持完整的统计分析

### coverage - 代码覆盖率报告

```bash
#!/bin/sh
# 用法：coverage SKIA_EXECUTABLE [ARGUMENTS...]
# 示例：coverage dm --src tests
```

生成代码覆盖率报告的完整流程：
1. 使用 GCC 的 `--coverage` 标志编译指定的可执行文件
2. 使用 `lcov` 生成零基线（覆盖所有编译文件）
3. 运行可执行文件生成实际覆盖数据
4. 合并基线和实际数据
5. 使用 `genhtml` 生成 HTML 报告并在浏览器中打开

### fetch-sk - 下载 sk 基础设施工具

从 CIPD 下载 Skia 的 `sk` 命令行工具：
- 从 `DEPS` 文件读取 `infra_revision` 确定版本
- 支持增量更新（SHA256 校验避免重复下载）
- 安装到 `bin/sk` 路径

### 其他工具

| 脚本 | 功能 |
|------|------|
| `fetch-clang-format` | 下载 clang-format 代码格式化工具 |
| `fetch-fonts-testdata` | 下载字体模块测试所需的字体文件 |
| `fetch-skps` | 下载 SKP（Skia Picture）测试资源 |
| `fetch-svgs` | 下载 SVG 测试资源 |
| `gerrit-number` | 从 Gerrit 代码评审 URL 提取变更编号 |
| `list-skia-bots` | 列出 Skia Swarming CI 机器人 |
| `sysopen` | 跨平台打开文件或 URL（macOS: open, Linux: xdg-open） |
| `try-clients` | 触发 Skia CI 试验构建 |

## 构建配置说明

### 初次构建环境配置

```bash
# 1. 同步第三方依赖
python3 bin/sync

# 2. 下载 GN 构建工具
python3 bin/fetch-gn

# 3. 下载 Ninja 构建工具
python3 bin/fetch-ninja

# 4. 生成构建文件并编译
bin/gn gen out/Debug
third_party/ninja/ninja -C out/Debug
```

### WebAssembly 构建准备

```bash
# 安装并激活 Emscripten SDK
python3 bin/activate-emsdk

# 配置 WASM 构建
bin/gn gen out/wasm --args='target_cpu="wasm" is_official_build=true'
```

### Android 设备测试

```bash
# 编译 Android 目标
ninja -C out/android dm

# 推送并在设备上运行
bin/droid out/android/dm --src gm --config gpu
```

## 依赖关系

- `DEPS` 文件 - `fetch-ninja` 和 `fetch-sk` 从中读取工具版本
- `tools/git-sync-deps` - `sync` 脚本的实际执行者
- `third_party/externals/emsdk/` - `activate-emsdk` 的操作目标
- `gn/toolchain/emsdk/BUILD.gn` - 引用 `activate-emsdk` 作为构建 action
- CIPD (`chrome-infra-packages.appspot.com`) - 工具二进制文件的下载源

## 相关文档与参考

- [Skia 构建入门指南](https://skia.org/docs/user/build/)
- [GN 快速入门](https://gn.googlesource.com/gn/+/main/docs/quick_start.md)
- [Ninja 手册](https://ninja-build.org/manual.html)
- [Emscripten 文档](https://emscripten.org/docs/)
- `gn/BUILDCONFIG.gn` - GN 全局构建配置
- `DEPS` - 第三方依赖版本清单
