# create.py - Linux AMD64 patch 工具资源创建脚本

> 源文件: [infra/bots/assets/patch_linux_amd64/create.py](https://github.com/aspect-build/aspect-cli/blob/main/infra/bots/assets/patch_linux_amd64/create.py)

## 概述

`create.py` 用于创建 Linux AMD64 平台上 `patch` 命令行工具的 CIPD 资源包。`patch` 是 Unix/Linux 系统上用于将差异文件（diff/patch）应用到源代码的标准工具。该脚本从 Debian 官方镜像下载 `patch` 的 `.deb` 包（v2.7.6-7），通过 SHA256 校验确保完整性，然后从 `.deb` 包中提取二进制文件。Skia CI 环境中某些任务需要此工具来应用补丁文件。

## 架构位置

该脚本位于 Skia 基础设施的系统工具管理子系统中。

```
infra/bots/assets/
├── patch_linux_amd64/
│   └── create.py              # 本文件 - 提取 patch 工具
└── ...

使用场景:
CI 任务 -> patch 工具 -> 应用源代码补丁
```

## 主要类与结构体

本脚本无类定义。关键常量：

| 常量 | 值 | 说明 |
|------|-----|------|
| `URL` | `https://ftp.debian.org/.../patch_2.7.6-7_amd64.deb` | Debian 包下载地址 |
| `SHA256` | `8c6d49b771530dbe...` | 预期的文件哈希值 |

## 公共 API 函数

### `create_asset(target_dir)`

从 Debian 包中提取 `patch` 二进制文件。

**参数**：
- `target_dir` (str): 资源输出目录路径

**行为**：
1. 创建临时目录
2. 使用 `wget` 下载 `.deb` 包
3. SHA256 校验
4. 使用 `dpkg-deb -x` 解压 `.deb` 包
5. 将 `usr/bin/patch` 复制到目标目录
6. 清理临时目录

### `main()`

命令行入口，解析 `--target_dir` / `-t` 参数并调用 `create_asset`。

## 内部实现细节

### Debian 包提取流程

```python
# 1. 创建临时目录
tmp = tempfile.mkdtemp()
target_file = os.path.join(tmp, 'patch.deb')

# 2. 下载 .deb 包
subprocess.call(['wget', '--quiet', '--output-document', target_file, URL])

# 3. SHA256 校验
output = subprocess.check_output(['sha256sum', target_file], encoding='utf-8')
actual_hash = output.split(' ')[0]
if actual_hash != SHA256:
    raise Exception(...)

# 4. 解压 .deb 包到临时目录
subprocess.check_call(['dpkg-deb', '-x', target_file, tmp])

# 5. 复制二进制文件
subprocess.check_call(['cp', tmp + '/usr/bin/patch', target_dir])

# 6. 清理
subprocess.check_call(['rm', '-rf', tmp])
```

### 为什么从 .deb 包提取

直接从 Debian 的 `.deb` 包中提取二进制文件而非从源码编译，原因可能是：
- `patch` 是一个成熟稳定的工具，不需要特殊编译选项
- Debian 的预编译二进制文件经过严格测试
- 避免了编译 GNU patch 所需的复杂依赖

### 临时目录管理

使用 `tempfile.mkdtemp()` 创建临时目录，在操作完成后通过 `rm -rf` 手动清理。如果脚本在清理前异常退出，临时目录将残留。使用 `try/finally` 或 `with` 语句可以改善这一点。

## 依赖关系

### 外部工具

- `wget`：下载 `.deb` 包
- `sha256sum`：文件完整性校验
- `dpkg-deb`：Debian 包解压工具
- `cp`：文件复制
- `rm`：临时文件清理

### 网络依赖

- Debian 官方 FTP 镜像：`https://ftp.debian.org/debian/`

### 标准库

- `argparse`：命令行参数解析
- `os`：路径操作
- `subprocess`：外部命令执行
- `tempfile`：临时目录创建

## 设计模式与设计决策

### 包提取模式

从操作系统发行版的预编译包中提取二进制文件是一种实用的策略，结合了预编译的便利性和 CIPD 分发的灵活性。

### 固定版本 + 哈希校验

URL 指向特定版本（2.7.6-7）且包含 SHA256 校验，确保可重复性和安全性。Debian 的包版本管理保证了 URL 内容的不变性。

### 手动临时目录管理

使用 `tempfile.mkdtemp()` + 手动 `rm -rf` 而非 `tempfile.TemporaryDirectory()` 上下文管理器。后者会在异常发生时自动清理。这是一个可改进的设计点。

### 工具隔离

将 `patch` 工具打包为 CIPD 资源而非依赖 CI 机器上的系统安装，确保了工具版本的一致性，避免了不同机器上工具版本差异导致的不可预测行为。

## 性能考量

- `.deb` 包体积小（几十 KB），下载和解压都极快
- SHA256 校验计算开销极低
- `dpkg-deb -x` 解压操作几乎瞬时完成
- 整个脚本执行时间通常在几秒以内

## 相关文件

- `infra/bots/assets/patch_linux_amd64/VERSION` - CIPD 资源版本号
- CI 配置中使用 `patch` 工具的任务定义
