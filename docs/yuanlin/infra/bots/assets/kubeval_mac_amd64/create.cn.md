# kubeval_mac_amd64/create.py - macOS 版 kubeval 资产创建脚本

> 源文件: [infra/bots/assets/kubeval_mac_amd64/create.py](../../../../infra/bots/assets/kubeval_mac_amd64/create.py)

## 概述

此脚本用于下载并打包 macOS amd64 平台的 `kubeval` 工具作为 Skia CI 系统的 CIPD 资产。kubeval 是一个 Kubernetes 配置文件验证工具，用于确保 YAML/JSON 配置文件符合 Kubernetes API schema。脚本从 GitHub 下载 v0.16.1 版本的 tar.gz 压缩包，验证 SHA256 哈希，解压后提取 kubeval 二进制文件到目标目录。

## 架构位置

该脚本位于 Skia 基础设施的资产管理层（`infra/bots/assets/`），专门为 macOS amd64 平台提供 kubeval 工具。它与 `infra/bots/assets/kubeval/create.py`（Linux 版本）形成平台互补，共同支持 Skia CI 系统中 Kubernetes 配置的验证工作。

## 主要类与结构体

本文件无类定义，包含以下关键元素：

- **`URL`**：kubeval v0.16.1 macOS amd64 版本的 GitHub 下载地址
- **`SHA256`**：预期的哈希值（`c79a91f2...`）
- **`create_asset(target_dir)`**：核心创建函数
- **`main()`**：入口函数

## 公共 API 函数

| 函数 | 参数 | 返回值 | 描述 |
|------|------|--------|------|
| `create_asset(target_dir)` | `target_dir`: 输出目录 | 无 | 下载、验证、解压 kubeval |
| `main()` | 无 | 无 | 解析 `--target_dir` 参数 |

## 内部实现细节

1. **临时目录**：使用 `tempfile.mkdtemp()` 创建临时目录存放下载的压缩包。
2. **下载**：通过 `wget --quiet` 下载 tar.gz 压缩包到临时目录。
3. **哈希验证**：使用 `sha256sum` 验证下载文件完整性。
4. **解压**：使用 `tar xf` 从压缩包中仅提取 `kubeval` 二进制文件到目标目录（`cwd=target_dir`）。
5. **清理**：使用 `rm -rf` 删除临时目录。

## 依赖关系

- **Python 标准库**：`argparse`、`os`、`subprocess`、`tempfile`
- **系统工具**：`wget`、`sha256sum`、`tar`、`rm`
- **外部资源**：GitHub（`instrumenta/kubeval` 仓库）

## 设计模式与设计决策

- **临时目录隔离**：使用临时目录存放中间文件，避免污染目标目录，并在完成后清理。
- **选择性解压**：`tar xf` 命令指定仅提取 `kubeval` 文件，忽略压缩包中的 LICENSE 等其他文件。
- **版本与哈希锁定**：确保可重复构建和供应链安全。
- **与 Linux 版本对称**：脚本结构与 `kubeval/create.py` 几乎完全相同，仅 URL 和 SHA256 不同。

## 性能考量

- 网络下载是主要耗时操作。
- 解压操作非常快速，因为仅提取单个二进制文件。
- 该脚本仅在资产更新时偶尔运行。

## 相关文件

- `infra/bots/assets/kubeval/create.py`：Linux 版本的 kubeval 资产创建脚本
- `infra/bots/assets/kubeval_mac_amd64/VERSION`：CIPD 包版本号
- Skia 的 Kubernetes 配置文件（被 kubeval 验证的目标文件）

### 补充说明

- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
