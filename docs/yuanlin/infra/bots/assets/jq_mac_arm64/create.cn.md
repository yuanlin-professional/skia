# jq macOS ARM64 资产创建脚本

> 源文件: infra/bots/assets/jq_mac_arm64/create.py

## 概述

用于下载和验证 jq（JSON 处理工具）macOS ARM64 版本的资产创建脚本。jq 是强大的命令行 JSON 处理器，广泛用于解析和转换 JSON 数据。该脚本从 GitHub Releases 下载 jq 1.7.1 的 macOS ARM64 二进制文件，通过 SHA256 校验确保完整性。

## 架构位置

位于 `infra/bots/assets/jq_mac_arm64/`，为 Skia 在 Apple Silicon Mac 上的 CI/CD 流程提供 JSON 处理能力，用于解析构建配置、测试结果和 API 响应等。

## 主要类与结构体

函数式风格脚本，使用标准库的 argparse、os 和 subprocess。

### 模块级常量

```python
URL = 'https://github.com/jqlang/jq/releases/download/jq-1.7.1/jq-macos-arm64'
SHA256 = '0bbe619e663e0de2c550be2fe0d240d076799d6f8a652b70fa04aea8a8362e8a'
```

## 公共 API 函数

### `create_asset(target_dir)`
下载、验证 jq 二进制文件并设置可执行权限。

### `main()`
解析命令行参数并执行资产创建。

## 内部实现细节

使用 wget 下载，sha256sum 验证，chmod 设置权限。jq 1.7.1 是 2023 年发布的稳定版本，支持更多 JSON 操作和性能优化。

## 依赖关系

- wget, sha256sum, chmod
- Python 3

## 性能考量

jq 二进制文件约 1-2 MB，下载和验证时间小于 5 秒。

## 相关文件

- `infra/bots/assets/jq/create.py`: Linux 版本
- CI 脚本中使用 jq 解析 JSON 输出
