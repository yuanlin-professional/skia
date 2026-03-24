# create.py - CockroachDB 数据库资源创建脚本

> 源文件: [infra/bots/assets/cockroachdb/create.py](https://github.com/aspect-build/aspect-cli/blob/main/infra/bots/assets/cockroachdb/create.py)

## 概述

`create.py` 用于创建 CockroachDB 数据库的 CIPD 资源包。CockroachDB 是一个分布式 SQL 数据库，在 Skia 的基础设施中用于数据存储和管理。该脚本从 CockroachDB 官方网站下载 v20.2.8 的 Linux AMD64 预编译发行版，通过管道下载并解压，然后提取 `cockroach` 可执行文件到目标目录。该脚本使用了 `infra/bots/utils.py` 提供的临时目录工具。

## 架构位置

该脚本属于 Skia 基础设施的数据存储工具管理部分。

```
infra/bots/assets/
├── cockroachdb/
│   └── create.py              # 本文件 - CockroachDB 资源创建
└── ...

Skia 基础设施数据栈:
CockroachDB (数据库) -> Skia 基础设施服务 (数据存储)
```

CockroachDB 被 Skia 的部分基础设施服务用作持久化存储后端。

## 主要类与结构体

本脚本无类定义。关键常量和变量：

| 变量 | 值 | 说明 |
|------|-----|------|
| `FILE_DIR` | 脚本所在目录路径 | 用于计算路径 |
| `INFRA_BOTS_DIR` | `infra/bots/` 路径 | 导入 utils 模块 |
| `URL` | `https://binaries.cockroachdb.com/...` | v20.2.8 Linux AMD64 下载地址 |

## 公共 API 函数

### `create_asset(target_dir)`

下载并提取 CockroachDB 二进制文件。

**参数**：
- `target_dir` (str): 资源输出目录路径

**行为**：
1. 在临时目录中使用 `curl` 下载压缩包
2. 通过管道将下载内容传递给 `tar` 解压
3. 将 `cockroach` 可执行文件移动到目标目录

### `main()`

命令行入口，解析 `--target_dir` / `-t` 参数并调用 `create_asset`。

## 内部实现细节

### 管道下载-解压模式

脚本使用进程管道将下载和解压合并为一步操作：

```python
p1 = subprocess.Popen(["curl", URL], stdout=subprocess.PIPE)
p2 = subprocess.Popen(["tar", "-xzf" "-"], stdin=p1.stdout)
p1.stdout.close()  # 允许 p1 在 p2 退出时收到 SIGPIPE
_,_ = p2.communicate()
```

这种模式避免了先将完整压缩包写入磁盘再解压的两步操作，节省了磁盘空间和 I/O 时间。

### SIGPIPE 处理

`p1.stdout.close()` 的关键作用：当 `tar`（p2）提前退出时（如错误或中断），`curl`（p1）向已关闭的管道写入会收到 SIGPIPE 信号，从而正确终止。如果不关闭 p1 的 stdout，p1 可能会一直等待（因为 Python 进程仍持有管道引用）。

### 代码中的潜在问题

`tar` 命令中存在一个参数拼写问题：`"-xzf" "-"` 实际上是两个独立的参数 `"-xzf"` 和 `"-"` 的列表元素，但在代码中写成了 `"-xzf" "-"` 之间缺少逗号（`"-xzf""-"` 会被 Python 拼接为 `"-xzf-"`）。不过实际查看代码，确实是 `[..."tar", "-xzf" "-"]`，这在 Python 中会被隐式字符串拼接为 `"-xzf-"`，这可能是一个 bug，正确写法应为 `"-xzf", "-"`。

### 文件提取

解压后的目录结构为 `cockroach-v20.2.8.linux-amd64/cockroach`，脚本使用 `shutil.move` 将 `cockroach` 可执行文件移动到目标目录。

## 依赖关系

### 内部模块

- `infra/bots/utils.py`：提供 `tmp_dir()` 上下文管理器

### 外部工具

- `curl`：下载压缩包（通过管道）
- `tar`：解压 `.tgz` 压缩包

### 网络依赖

- CockroachDB 官方发行版：`https://binaries.cockroachdb.com/`

### 标准库

- `argparse`：命令行参数解析
- `os`：路径操作
- `shutil`：文件移动
- `subprocess`：进程管理
- `sys`：模块路径操作

## 设计模式与设计决策

### 流式下载-解压模式

使用进程管道（`curl | tar`）是一种经典的 Unix 模式，优点是：
- 无需为中间文件分配磁盘空间
- 下载和解压并行执行，节省总时间
- 内存使用量小（流式处理）

### 无 SHA256 校验

该脚本未实施 SHA256 校验，这与较新的脚本设计不一致。考虑到 CockroachDB 发行版来自可信源，且版本号精确固定，风险相对较低，但建议在后续更新中添加校验。

### 临时目录隔离

使用 `utils.tmp_dir()` 确保解压操作在临时目录中进行，不污染工作目录。

### 固定版本

CockroachDB 版本锁定为 v20.2.8，这是一个 2021 年发布的版本。版本固定确保了基础设施服务的稳定性。

## 性能考量

- **流式处理**：管道模式避免了中间文件的磁盘 I/O，比两步操作更高效
- **下载大小**：CockroachDB 发行版约几百 MB，下载时间取决于网络带宽
- **解压速度**：tar + gzip 解压是 CPU 密集操作，但现代硬件上通常较快
- **仅提取必要文件**：虽然解压了整个发行版，但只将 `cockroach` 可执行文件移动到目标目录。更高效的做法是使用 `tar` 的文件过滤功能只解压所需文件

## 相关文件

- `infra/bots/utils.py` - 基础设施工具函数
- `infra/bots/assets/cockroachdb/VERSION` - CIPD 资源版本号
- Skia 基础设施中使用 CockroachDB 的服务配置
