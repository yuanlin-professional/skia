# create.py - macOS ARM64 平台 yq 工具资源创建脚本

> 源文件: [infra/bots/assets/yq_mac_arm64/create.py](https://github.com/aspect-build/aspect-cli/blob/main/infra/bots/assets/yq_mac_arm64/create.py)

## 概述

`create.py` 用于创建 macOS ARM64（Apple Silicon）平台上 `yq` 工具的 CIPD 资源包。`yq` 是一个功能强大的命令行 YAML/JSON/XML/CSV/TOML 处理工具，类似于 `jq` 但支持更多格式。该脚本从 GitHub 下载 v4.44.3 版本的 macOS ARM64 预编译二进制文件，通过 SHA256 校验确保完整性，并设置可执行权限。该资源供在 Apple Silicon Mac 上运行的 Skia CI 任务使用。

## 架构位置

该脚本是 Skia 多平台 yq 部署策略的组成部分。

```
infra/bots/assets/
├── yq/
│   └── create.py              # Linux AMD64 版本
├── yq_mac_arm64/
│   └── create.py              # 本文件 - macOS ARM64 版本
└── ...
```

随着 Skia CI 基础设施逐渐迁移到 Apple Silicon Mac，此脚本为 ARM64 Mac 提供了原生的 yq 工具。

## 主要类与结构体

本脚本无类定义。关键常量：

| 常量 | 值 | 说明 |
|------|-----|------|
| `URL` | `https://github.com/.../yq_darwin_arm64` | v4.44.3 macOS ARM64 下载地址 |
| `SHA256` | `559a594ef7a6ebc5...` | 预期的文件哈希值 |
| `BINARY` | `yq_darwin_arm64` | 从 URL 提取的原始文件名 |

## 公共 API 函数

### `create_asset(target_dir)`

下载并验证 yq 二进制文件。

**参数**：
- `target_dir` (str): 资源输出目录路径

**行为**：
1. 使用 `wget` 下载二进制文件到 `target_dir/yq`
2. 使用 `sha256sum` 计算并校验哈希值
3. 校验失败则抛出异常
4. 设置 `ugo+x` 可执行权限

### `main()`

命令行入口，解析 `--target_dir` / `-t` 参数并调用 `create_asset`。

## 内部实现细节

### 标准二进制资源创建模式

该脚本与 `yq/create.py`（Linux 版本）结构完全相同，仅 URL 和 SHA256 不同：

```python
target_file = os.path.join(target_dir, 'yq')
subprocess.call(['wget', '--quiet', '--output-document', target_file, URL])
# SHA256 校验...
subprocess.call(['chmod', 'ugo+x', target_file])
```

### 版本一致性

Linux 和 macOS ARM64 版本使用相同的 yq 版本号（v4.44.3），确保跨平台行为一致性。

### macOS 上的 sha256sum

值得注意的是 macOS 默认不提供 `sha256sum` 命令（macOS 使用 `shasum -a 256`）。在 Skia CI 环境中可能通过 Homebrew 或其他方式安装了 `sha256sum`，或者此脚本主要在 Linux 机器上运行来创建 CIPD 包。

## 依赖关系

### 外部工具

- `wget`：下载二进制文件
- `sha256sum`：文件完整性校验
- `chmod`：设置文件权限

### 网络依赖

- GitHub Releases：`https://github.com/mikefarah/yq/releases/`

### 标准库

- `argparse`：命令行参数解析
- `os`：文件路径操作
- `subprocess`：外部命令执行

## 设计模式与设计决策

### 平台分离部署

yq 工具按平台分为独立的 CIPD 包。当前存在两个平台版本：
- `yq`：Linux AMD64（Skia CI 的主要构建平台）
- `yq_mac_arm64`：macOS ARM64（Apple Silicon Mac）

### 代码复用 vs 平台分离

虽然多个平台的创建脚本几乎相同，但选择了独立文件而非共享函数的方式。这种做法的优势是每个脚本自包含、可独立维护，缺点是版本升级时需要修改多个文件。

### 通用输出名称

输出文件统一命名为 `yq`，隐藏了平台差异，使下游 CI 脚本无需进行平台判断。

## 性能考量

- yq 二进制文件约几 MB，下载极快
- SHA256 校验几乎无开销
- 脚本总执行时间在几秒以内
- CIPD 包创建后，CI 任务直接下载使用，无运行时性能影响

## 相关文件

- `infra/bots/assets/yq/create.py` - Linux AMD64 版本的 yq 创建脚本
- `infra/bots/assets/yq_mac_arm64/VERSION` - CIPD 资源版本号
- CI 配置中使用 yq 处理 YAML 的任务定义
