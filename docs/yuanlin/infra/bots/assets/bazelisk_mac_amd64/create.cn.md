# create.py - macOS AMD64 平台 Bazelisk 资源创建脚本

> 源文件: [infra/bots/assets/bazelisk_mac_amd64/create.py](https://github.com/aspect-build/aspect-cli/blob/main/infra/bots/assets/bazelisk_mac_amd64/create.py)

## 概述

`create.py` 是用于创建 macOS AMD64 平台上 Bazelisk 工具 CIPD 资源包的 Python 脚本。Bazelisk 是 Bazel 构建系统的版本管理包装器，能自动下载和管理正确版本的 Bazel。该脚本从 GitHub 下载特定版本的 Bazelisk 二进制文件，验证其 SHA256 哈希值以确保完整性，然后设置可执行权限。

## 架构位置

该脚本位于 Skia 基础设施资源管理体系中，是多平台 Bazelisk 部署策略的一部分。

```
infra/bots/assets/
├── bazelisk_mac_amd64/
│   └── create.py              # 本文件 - macOS x86_64
├── bazelisk_mac_arm64/
│   └── create.py              # macOS Apple Silicon
├── bazelisk_linux_amd64/
│   └── create.py              # Linux x86_64
└── bazel_build_task_driver/
    └── create.py              # Bazel 构建任务驱动器
```

Bazelisk 被 Skia 用于在 CI/CD 环境中执行 Bazel 构建，确保跨平台使用一致的 Bazel 版本。

## 主要类与结构体

本脚本无类定义。关键常量：

| 常量 | 值 | 说明 |
|------|-----|------|
| `URL` | `https://github.com/.../bazelisk-darwin-amd64` | v1.27.0 版本的下载地址 |
| `SHA256` | `8fcd7ba828f673ba4...` | 预期的文件哈希值 |
| `BINARY` | `bazelisk-darwin-amd64` | 从 URL 提取的文件名 |

## 公共 API 函数

### `create_asset(target_dir)`

下载并验证 Bazelisk 二进制文件。

**参数**：
- `target_dir` (str): 资源输出目录路径

**行为**：
1. 使用 `wget` 下载二进制文件并重命名为 `bazelisk`
2. 使用 `sha256sum` 计算下载文件的哈希值
3. 对比预期哈希值，不匹配则抛出异常
4. 设置 `ugo+x` 可执行权限

### `main()`

命令行入口，解析 `--target_dir` / `-t` 参数并调用 `create_asset`。

## 内部实现细节

### SHA256 校验流程

```python
output = subprocess.check_output(['sha256sum', target_file], encoding='utf-8')
actual_hash = output.split(' ')[0]
if actual_hash != SHA256:
    raise Exception('SHA256 does not match (%s != %s)' % (actual_hash, SHA256))
```

通过调用系统工具 `sha256sum` 进行校验，解析其输出（格式为 `hash  filename`）提取哈希值进行比较。如果不匹配，脚本抛出异常中止执行。

### 权限设置

使用 `chmod ugo+x` 为所有用户（user、group、others）添加可执行权限，确保在 CI 环境中任何用户身份都可以执行该二进制文件。

### 注意事项

`subprocess.call` 用于 `wget` 和 `chmod` 命令，不会在失败时抛出异常（与 `check_call` 不同）。这意味着下载失败时不会立即中断，但后续的 SHA256 校验会捕获此问题。

## 依赖关系

### 外部工具

- `wget`：用于下载二进制文件
- `sha256sum`：用于计算 SHA256 哈希值
- `chmod`：用于设置文件权限

### 网络依赖

- GitHub Releases：`https://github.com/bazelbuild/bazelisk/releases/`

### 标准库

- `argparse`：命令行参数解析
- `os`：文件路径操作
- `subprocess`：外部命令执行

## 设计模式与设计决策

### 哈希校验安全模式

与旧版脚本（如 `win_ninja/create.py`）不同，本脚本实施了 SHA256 完整性校验，这是一种供应链安全最佳实践，可以防止：
- 下载过程中的数据损坏
- 中间人攻击篡改二进制文件
- 上游意外替换文件内容

### 平台特定分离

每个平台（mac_amd64、mac_arm64、linux_amd64）有独立的创建脚本和 CIPD 包，避免在运行时进行平台检测，简化了 CI 配置。

### 固定版本策略

URL 和 SHA256 均硬编码，版本升级需要同时更新两个值，确保了版本和完整性的双重确定性。

## 性能考量

- Bazelisk 二进制文件体积较小（约几 MB），下载速度快
- SHA256 校验计算开销可忽略不计
- 脚本执行时间主要取决于网络延迟

## 相关文件

- `infra/bots/assets/bazelisk_mac_arm64/create.py` - macOS ARM64 版本
- `infra/bots/assets/bazelisk_linux_amd64/create.py` - Linux AMD64 版本
- `infra/bots/assets/bazel_build_task_driver/create.py` - Bazel 构建任务驱动器
- `.bazelversion` - Bazel 版本配置文件（Bazelisk 使用）
