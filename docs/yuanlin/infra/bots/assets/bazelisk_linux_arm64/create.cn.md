# Bazelisk Linux ARM64 资产创建脚本

> 源文件: infra/bots/assets/bazelisk_linux_arm64/create.py

## 概述

用于下载和验证 Bazelisk Linux ARM64 版本的资产创建脚本。Bazelisk 是 Bazel 的版本管理包装器，该脚本从 GitHub Releases 下载 v1.27.0 的 ARM64 二进制文件，通过 SHA256 校验确保完整性，并设置可执行权限。

## 架构位置

位于 `infra/bots/assets/bazelisk_linux_arm64/`，为 Skia 在 ARM64 架构 Linux 环境（如 Apple Silicon Mac、AWS Graviton 等）上的 Bazel 构建提供支持。

## 主要类与结构体

函数式风格脚本，使用标准库的 argparse、os 和 subprocess 模块。

### 模块级常量

```python
URL = 'https://github.com/bazelbuild/bazelisk/releases/download/v1.27.0/bazelisk-linux-arm64'
SHA256 = 'bb608519a440d45d10304eb684a73a2b6bb7699c5b0e5434361661b25f113a5d'
BINARY = URL.split('/')[-1]
```

## 公共 API 函数

### `create_asset(target_dir)`

下载、验证和准备 Bazelisk 二进制文件。执行流程：
1. 使用 wget 下载到 `target_dir/bazelisk`
2. 计算 SHA256 校验和并验证
3. 设置文件为可执行权限（ugo+x）

### `main()`

解析 `--target_dir` 参数并调用 `create_asset()`。

## 内部实现细节

### ARM64 特定考量

ARM64 架构的 Bazelisk 二进制文件适用于：
- **Apple Silicon**: M1/M2/M3 Mac（通过 Rosetta 2 或原生）
- **AWS Graviton**: ARM 服务器实例
- **树莓派 4**: 64 位 Raspberry Pi OS
- **其他 ARM64 Linux**: 如 Ampere、Rockchip 等

### 校验和安全

SHA256 验证防止：
- 下载损坏
- 中间人攻击
- 供应链投毒

### 权限设置

`chmod ugo+x` 确保所有用户可执行，适合 CI 环境中的多用户场景。

## 依赖关系

- **wget**: 下载工具
- **sha256sum**: 校验和计算
- **chmod**: 权限管理
- **Python 3**: shebang 指定 python3

## 设计模式与设计决策

### 版本固定

使用 Bazelisk v1.27.0 确保构建可重现性和稳定性。

### 简化命名

将 `bazelisk-linux-arm64` 重命名为 `bazelisk`，统一不同平台的可执行文件名。

## 性能考量

- 下载大小：~10-20 MB
- 典型下载时间：5-30 秒
- 校验时间：<0.5 秒

ARM64 处理器的能效比优势使其在 CI 环境中越来越受欢迎。

## 相关文件

- **`infra/bots/assets/bazelisk_linux_amd64/create.py`**: x86_64 版本
- **`infra/bots/assets/bazelisk_mac_arm64/create.py`**: macOS ARM64 版本
- **`infra/bots/assets/bazelisk_win_amd64/create.py`**: Windows 版本
- **`.bazelversion`**: 项目指定的 Bazel 版本
