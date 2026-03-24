# create.py - yq (Linux AMD64) YAML 处理工具资源创建脚本

> 源文件: [infra/bots/assets/yq/create.py](https://github.com/aspect-build/aspect-cli/blob/main/infra/bots/assets/yq/create.py)

## 概述

`create.py` 用于创建 Linux AMD64 平台上 `yq` 工具的 CIPD 资源包。`yq` 是一个轻量级的命令行 YAML/JSON/XML 处理工具（类似于 `jq` 之于 JSON），由 Mike Farah 开发。该脚本从 GitHub 下载指定版本（v4.44.3）的预编译二进制文件，通过 SHA256 校验确保文件完整性，并设置可执行权限。Skia 的 CI/CD 基础设施使用 `yq` 来处理配置文件中的 YAML 数据。

## 架构位置

该脚本是 Skia 多平台 yq 部署策略的一部分：

```
infra/bots/assets/
├── yq/
│   └── create.py              # 本文件 - Linux AMD64 版本
├── yq_mac_arm64/
│   └── create.py              # macOS ARM64 版本
└── ...
```

## 主要类与结构体

本脚本无类定义。关键常量：

| 常量 | 值 | 说明 |
|------|-----|------|
| `URL` | `https://github.com/.../yq_linux_amd64` | v4.44.3 版本下载地址 |
| `SHA256` | `a2c097180dd884a8...` | 预期的文件哈希值 |
| `BINARY` | `yq_linux_amd64` | 从 URL 提取的原始文件名 |

## 公共 API 函数

### `create_asset(target_dir)`

下载并验证 yq 二进制文件。

**参数**：
- `target_dir` (str): 资源输出目录路径

**行为**：
1. 使用 `wget` 静默下载二进制文件，重命名为 `yq`
2. 计算下载文件的 SHA256 哈希值并校验
3. 校验失败则抛出异常
4. 设置 `ugo+x` 可执行权限

### `main()`

命令行入口，解析 `--target_dir` / `-t` 参数并调用 `create_asset`。

## 内部实现细节

### 标准化下载-校验-授权流程

本脚本遵循 Skia 基础设施中通用的二进制资源创建模式：

```python
# 1. 下载：wget 静默模式，重命名输出文件
subprocess.call(['wget', '--quiet', '--output-document', target_file, URL])

# 2. 校验：sha256sum 计算哈希
output = subprocess.check_output(['sha256sum', target_file], encoding='utf-8')
actual_hash = output.split(' ')[0]

# 3. 授权：设置可执行权限
subprocess.call(['chmod', 'ugo+x', target_file])
```

### 文件重命名

下载时将原始文件名 `yq_linux_amd64` 重命名为通用名 `yq`，使得在 CI 脚本中可以统一使用 `yq` 命令而无需关心平台后缀。

## 依赖关系

### 外部工具

- `wget`：用于下载二进制文件
- `sha256sum`：用于计算 SHA256 哈希值
- `chmod`：用于设置文件权限

### 网络依赖

- GitHub Releases：`https://github.com/mikefarah/yq/releases/`

### 标准库

- `argparse`：命令行参数解析
- `os`：文件路径操作
- `subprocess`：外部命令执行

## 设计模式与设计决策

### 固定版本 + 哈希校验模式

URL 和 SHA256 均硬编码，这是一种供应链安全最佳实践：
- 版本号固定确保可重复性
- SHA256 校验防止文件篡改或损坏

### 平台分离部署

每个目标平台有独立的创建脚本和 CIPD 包，相比运行时平台检测，这种方式更简单、更可靠。

### 通用命名策略

输出文件命名为 `yq` 而非带平台后缀的名称，简化了下游脚本中对该工具的引用。

## 性能考量

- yq 二进制文件体积小（约几 MB），下载速度快
- SHA256 校验计算开销极低
- 脚本总执行时间主要取决于网络延迟
- `subprocess.call`（而非 `check_call`）用于 wget 和 chmod，下载失败不会直接报错，但 SHA256 校验会间接捕获问题

## 相关文件

- `infra/bots/assets/yq_mac_arm64/create.py` - macOS ARM64 版本的 yq 创建脚本
- `infra/bots/assets/yq/VERSION` - 当前 CIPD 资源版本号
- CI 配置文件中引用 yq 的作业定义
