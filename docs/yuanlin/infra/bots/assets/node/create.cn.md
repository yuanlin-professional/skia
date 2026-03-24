# create.py - Node.js 运行时资源创建脚本

> 源文件: [infra/bots/assets/node/create.py](https://github.com/aspect-build/aspect-cli/blob/main/infra/bots/assets/node/create.py)

## 概述

`create.py` 用于创建 Linux x86_64 平台上 Node.js 运行时的 CIPD 资源包。Node.js 是一个基于 Chrome V8 引擎的 JavaScript 运行时，在 Skia 的 CI/CD 基础设施中用于运行 JavaScript 相关的测试和工具脚本（如 CanvasKit 的 WebAssembly 测试）。该脚本从 Node.js 官方网站下载 v12.16.3 的预编译 Linux 发行版，通过管道解压并重命名为标准目录结构。

## 架构位置

该脚本属于 Skia 基础设施中的 JavaScript/WebAssembly 测试工具链。

```
infra/bots/assets/
├── node/
│   └── create.py              # 本文件 - Node.js 运行时
└── ...

使用场景:
CanvasKit (WebAssembly) 测试 -> Node.js -> JavaScript 测试脚本
PathKit 测试 -> Node.js -> 单元测试
```

## 主要类与结构体

本脚本无类定义。关键常量：

| 常量 | 值 | 说明 |
|------|-----|------|
| `NODE_URL` | `https://nodejs.org/.../node-v12.16.3-linux-x64.tar.xz` | Node.js 下载地址 |
| `NODE_EXTRACT_NAME` | `"node-v12.16.3-linux-x64"` | 解压后的目录名 |

## 公共 API 函数

### `create_asset(target_dir)`

下载并安装 Node.js 到目标目录。

**参数**：
- `target_dir` (str): 资源输出目录路径

**行为**：
1. 使用 `curl | tar` 管道下载并解压 Node.js 到目标目录
2. 将解压后的目录从版本化名称重命名为 `node`

### `main()`

命令行入口，解析 `--target_dir` / `-t` 参数并调用 `create_asset`。

## 内部实现细节

### 管道下载-解压模式

```python
p1 = subprocess.Popen(["curl", NODE_URL], stdout=subprocess.PIPE)
p2 = subprocess.Popen(["tar", "-C", target_dir, "-xJf" "-"], stdin=p1.stdout)
p1.stdout.close()  # 允许 p1 在 p2 退出时收到 SIGPIPE
_,_ = p2.communicate()
```

使用 `curl | tar` 管道进行流式下载和解压。`tar` 的 `-C` 选项指定解压目录，`-J` 选项处理 `.xz` 压缩格式。

### 与 cockroachdb/create.py 相同的潜在问题

代码中 `"-xJf" "-"` 存在与 `cockroachdb/create.py` 相同的隐式字符串拼接问题。Python 的隐式字符串拼接会将 `"-xJf" "-"` 变为 `"-xJf-"`，这可能导致 `tar` 命令行为异常。正确写法应为 `"-xJf", "-"`。

### 目录重命名

解压后的目录名包含版本号（`node-v12.16.3-linux-x64`），脚本将其重命名为通用的 `node`：

```python
os.rename(
    os.path.join(target_dir, NODE_EXTRACT_NAME),
    os.path.join(target_dir, "node")
)
```

这使得 CI 脚本可以通过固定路径 `node/bin/node` 和 `node/bin/npm` 引用 Node.js 工具。

### Node.js 版本

使用的是 Node.js v12.16.3，这是 Node.js 12.x LTS（Erbium）系列的一个版本。Node.js 12.x 已于 2022 年 4 月停止维护（EOL）。使用旧版本可能是出于兼容性考虑或尚未更新。

### 发行版内容

Node.js 的 Linux 发行版包含：
- `bin/node` - Node.js 运行时
- `bin/npm` - Node.js 包管理器
- `bin/npx` - 包执行器
- `lib/node_modules/` - 内置模块
- `include/` - C++ 头文件（用于原生插件开发）

## 依赖关系

### 外部工具

- `curl`：下载压缩包
- `tar`：解压 `.tar.xz` 文件（需要 xz 支持）

### 网络依赖

- Node.js 官方发行版：`https://nodejs.org/dist/`

### 标准库

- `argparse`：命令行参数解析
- `os`：文件路径操作和重命名
- `subprocess`：进程管理

## 设计模式与设计决策

### 流式下载-解压

与 `cockroachdb/create.py` 采用相同的 `curl | tar` 管道模式，避免中间文件的磁盘占用。

### 无 SHA256 校验

该脚本未实施哈希校验。Node.js 官方提供了 SHASUMS256.txt 文件用于验证下载完整性，建议在后续更新中添加校验。

### 通用目录命名

将带版本号的目录重命名为 `node`，使下游脚本无需硬编码版本号即可引用 Node.js。版本升级时只需更新本脚本，CI 脚本无需修改。

### 版本固定

Node.js 版本硬编码为 v12.16.3。虽然版本较旧，但对于 Skia CI 中的 JavaScript 测试任务来说，可能不需要最新的 Node.js 特性。

## 性能考量

- **下载大小**：Node.js Linux x64 发行版约 15-20 MB（xz 压缩），下载速度较快
- **xz 解压**：xz 格式比 gzip 压缩率更高，但解压速度稍慢
- **管道模式**：避免了中间文件的磁盘写入
- **`os.rename`**：目录重命名是原子操作（同文件系统），几乎瞬时完成
- Node.js 运行时本身约 70-100 MB（解压后），CIPD 包下载和缓存机制使得 CI 任务通常能快速获取

## 相关文件

- `infra/bots/assets/node/VERSION` - CIPD 资源版本号
- `modules/canvaskit/` - CanvasKit 模块（使用 Node.js 运行测试）
- `modules/pathkit/` - PathKit 模块（使用 Node.js 运行测试）
- CI 配置中使用 Node.js 的测试任务定义
