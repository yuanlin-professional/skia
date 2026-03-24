# create.py - macOS ARM64 平台 Bazelisk 资源创建脚本

> 源文件: [infra/bots/assets/bazelisk_mac_arm64/create.py](https://github.com/aspect-build/aspect-cli/blob/main/infra/bots/assets/bazelisk_mac_arm64/create.py)

## 概述

`create.py` 用于创建 macOS ARM64（Apple Silicon）平台上 Bazelisk 工具的 CIPD 资源包。Bazelisk 是 Bazel 构建系统的版本管理包装器，自动根据项目配置下载并使用正确版本的 Bazel。该脚本从 GitHub 下载 v1.27.0 版本的 macOS ARM64 预编译二进制文件，通过 SHA256 哈希校验确保完整性，并设置可执行权限。该资源供 Apple Silicon Mac 上的 Skia CI 构建任务使用。

## 架构位置

该脚本是 Skia 三平台 Bazelisk 部署策略的一部分。

```
infra/bots/assets/
├── bazelisk_linux_amd64/
│   └── create.py              # Linux x86_64
├── bazelisk_mac_amd64/
│   └── create.py              # macOS x86_64
├── bazelisk_mac_arm64/
│   └── create.py              # 本文件 - macOS Apple Silicon
└── bazel_build_task_driver/
    └── create.py              # Bazel 构建任务驱动器
```

三个 Bazelisk 脚本使用相同的版本号（v1.27.0），确保所有平台使用一致的 Bazelisk 版本。

## 主要类与结构体

本脚本无类定义。关键常量：

| 常量 | 值 | 说明 |
|------|-----|------|
| `URL` | `https://github.com/.../bazelisk-darwin-arm64` | v1.27.0 ARM64 下载地址 |
| `SHA256` | `8bf08c894ccc19ef...` | 预期的文件哈希值 |
| `BINARY` | `bazelisk-darwin-arm64` | 从 URL 提取的原始文件名 |

## 公共 API 函数

### `create_asset(target_dir)`

下载并验证 Bazelisk 二进制文件。

**参数**：
- `target_dir` (str): 资源输出目录路径

**行为**：
1. 使用 `wget` 下载二进制文件到 `target_dir/bazelisk`
2. 使用 `sha256sum` 校验文件哈希值
3. 哈希不匹配则抛出异常
4. 设置 `ugo+x` 可执行权限

### `main()`

命令行入口，解析 `--target_dir` / `-t` 参数并调用 `create_asset`。

## 内部实现细节

### 与其他平台版本的一致性

该脚本与 `bazelisk_mac_amd64/create.py` 和 `bazelisk_linux_amd64/create.py` 的代码结构完全相同，仅 `URL` 和 `SHA256` 常量不同。

三个平台的版本对照：

| 平台 | URL 后缀 | SHA256 (前16位) |
|------|----------|-----------------|
| Linux AMD64 | `bazelisk-linux-amd64` | `e1508323f347ad14` |
| macOS AMD64 | `bazelisk-darwin-amd64` | `8fcd7ba828f673ba` |
| macOS ARM64 | `bazelisk-darwin-arm64` | `8bf08c894ccc19ef` |

### Apple Silicon 支持

Apple Silicon Mac 使用 ARM64 架构，需要专门的二进制文件。从 Bazelisk v1.11.0 开始提供 macOS ARM64 原生构建。使用原生 ARM64 二进制可避免 Rosetta 2 翻译的性能开销。

### subprocess.call 注意事项

`wget` 和 `chmod` 使用 `subprocess.call` 而非 `subprocess.check_call`，这意味着这两个命令的失败不会直接引发异常。但 SHA256 校验会间接捕获下载失败的情况。

## 依赖关系

### 外部工具

- `wget`：下载二进制文件
- `sha256sum`：文件完整性校验
- `chmod`：设置文件权限

### 网络依赖

- GitHub Releases：`https://github.com/bazelbuild/bazelisk/releases/`

### 标准库

- `argparse`：命令行参数解析
- `os`：文件路径操作
- `subprocess`：外部命令执行

## 设计模式与设计决策

### 三平台一致版本

所有三个平台使用相同的 Bazelisk 版本（v1.27.0），确保无论在哪个平台上运行 Bazelisk，都会表现出相同的版本管理行为。

### 二进制资源标准模式

该脚本严格遵循 Skia 基础设施的标准模式：下载 -> SHA256 校验 -> 设置权限。这种一致性使得维护者可以快速理解和更新任何平台的脚本。

### 独立 CIPD 包

每个平台作为独立的 CIPD 包管理，CI 任务根据运行平台选择对应的包。这避免了在运行时下载不需要的平台二进制文件。

## 性能考量

- Bazelisk 二进制文件约几 MB，下载速度快
- ARM64 原生二进制在 Apple Silicon 上比 x86_64 二进制（需要 Rosetta 2 翻译）运行更快
- SHA256 校验和权限设置的开销可忽略不计
- 脚本总执行时间通常在几秒以内

## 相关文件

- `infra/bots/assets/bazelisk_linux_amd64/create.py` - Linux AMD64 版本
- `infra/bots/assets/bazelisk_mac_amd64/create.py` - macOS AMD64 版本
- `infra/bots/assets/bazel_build_task_driver/create.py` - Bazel 构建任务驱动器
- `.bazelversion` - 项目根目录的 Bazel 版本配置文件
