# create.py - Linux AMD64 平台 Bazelisk 资源创建脚本

> 源文件: [infra/bots/assets/bazelisk_linux_amd64/create.py](https://github.com/aspect-build/aspect-cli/blob/main/infra/bots/assets/bazelisk_linux_amd64/create.py)

## 概述

`create.py` 用于创建 Linux AMD64 平台上 Bazelisk 工具的 CIPD 资源包。Bazelisk 是 Bazel 构建系统的版本管理器和启动包装器，能够根据项目中的 `.bazelversion` 文件自动下载并运行对应版本的 Bazel。该脚本从 GitHub 下载 v1.27.0 版本的预编译二进制文件，通过 SHA256 哈希校验确保完整性，并设置可执行权限。这是 Skia CI 中 Linux 构建任务所使用的 Bazelisk 版本。

## 架构位置

该脚本是 Skia 多平台 Bazelisk 部署策略的组成部分，专门负责 Linux x86_64 平台。

```
infra/bots/assets/
├── bazelisk_linux_amd64/
│   └── create.py              # 本文件 - Linux x86_64
├── bazelisk_mac_amd64/
│   └── create.py              # macOS x86_64
├── bazelisk_mac_arm64/
│   └── create.py              # macOS Apple Silicon
└── bazel_build_task_driver/
    └── create.py              # Bazel 构建任务驱动器
```

Linux AMD64 是 Skia CI 最主要的构建平台，大部分编译和测试任务都在该平台上运行。

## 主要类与结构体

本脚本无类定义。关键常量：

| 常量 | 值 | 说明 |
|------|-----|------|
| `URL` | `https://github.com/.../bazelisk-linux-amd64` | v1.27.0 Linux 版本下载地址 |
| `SHA256` | `e1508323f347ad14...` | 预期的文件哈希值 |
| `BINARY` | `bazelisk-linux-amd64` | 从 URL 提取的原始文件名 |

## 公共 API 函数

### `create_asset(target_dir)`

下载并验证 Bazelisk 二进制文件。

**参数**：
- `target_dir` (str): 资源输出目录路径

**行为**：
1. 使用 `wget` 静默下载二进制文件到 `target_dir/bazelisk`
2. 使用 `sha256sum` 计算哈希值并与预期值比较
3. 哈希不匹配则抛出 `Exception`
4. 使用 `chmod ugo+x` 设置可执行权限

### `main()`

命令行入口，解析 `--target_dir` / `-t` 参数并调用 `create_asset`。

## 内部实现细节

### 下载-校验-授权标准流程

该脚本遵循 Skia 基础设施中的标准二进制资源创建模式：

```python
# 步骤 1: 下载并重命名
target_file = os.path.join(target_dir, 'bazelisk')
subprocess.call(['wget', '--quiet', '--output-document', target_file, URL])

# 步骤 2: SHA256 校验
output = subprocess.check_output(['sha256sum', target_file], encoding='utf-8')
actual_hash = output.split(' ')[0]
if actual_hash != SHA256:
    raise Exception(...)

# 步骤 3: 设置可执行权限
subprocess.call(['chmod', 'ugo+x', target_file])
```

### 与其他平台版本的差异

该脚本与 `bazelisk_mac_amd64` 和 `bazelisk_mac_arm64` 版本结构完全相同，仅 `URL` 和 `SHA256` 常量不同。三个脚本下载同一版本（v1.27.0）的不同平台构建。

### subprocess.call vs check_call

`wget` 和 `chmod` 使用 `subprocess.call`（不检查返回码），而非 `subprocess.check_call`。这意味着如果 `wget` 下载失败（如网络错误），脚本不会在下载步骤报错，但后续的 SHA256 校验将捕获问题（空文件或不完整文件的哈希值不会匹配）。

## 依赖关系

### 外部工具

- `wget`：下载二进制文件
- `sha256sum`：计算文件哈希值（Linux 标准工具）
- `chmod`：设置文件权限

### 网络依赖

- GitHub Releases：`https://github.com/bazelbuild/bazelisk/releases/`

### 标准库

- `argparse`：命令行参数解析
- `os`：文件路径操作
- `subprocess`：外部命令执行

## 设计模式与设计决策

### 平台分离部署

每个目标平台维护独立的创建脚本和 CIPD 包。虽然会导致代码重复，但具有以下优势：
- 每个平台可以独立更新版本
- CI 配置中可以精确指定平台对应的包
- 消除了运行时平台检测的复杂性

### 供应链安全

SHA256 校验是防止供应链攻击的关键措施。即使 GitHub 被入侵或中间人攻击修改了二进制文件，校验也会检测到篡改。

### 通用命名

输出文件命名为 `bazelisk`（不带平台后缀），使得 CI 脚本可以统一引用 `bazelisk` 命令而无需关心底层平台。

## 性能考量

- Bazelisk 二进制文件约几 MB，下载速度快
- SHA256 校验计算的 CPU 开销可忽略
- 脚本总执行时间通常在几秒以内，主要受网络延迟影响
- 相比从源码编译 Bazel（可能需要几十分钟），使用预编译的 Bazelisk 极大地节省了时间

## 相关文件

- `infra/bots/assets/bazelisk_mac_amd64/create.py` - macOS AMD64 版本
- `infra/bots/assets/bazelisk_mac_arm64/create.py` - macOS ARM64 版本
- `infra/bots/assets/bazel_build_task_driver/create.py` - Bazel 构建任务驱动器
- `.bazelversion` - 项目根目录的 Bazel 版本配置文件
