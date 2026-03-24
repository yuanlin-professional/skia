# create_and_upload.py - SKP 资源创建与上传脚本

> 源文件: [infra/bots/assets/skp/create_and_upload.py](https://github.com/aspect-build/aspect-cli/blob/main/infra/bots/assets/skp/create_and_upload.py)

## 概述

`create_and_upload.py` 是 SKP 资源管理的上层入口脚本，负责协调 SKP 测试资源的创建和上传流程。SKP 是 Skia 的序列化绘图格式（Skia Picture），记录了一系列绘图命令，用于渲染性能测试和回归检测。该脚本接收 Chrome 浏览器路径、源码路径和 DM 工具路径等参数，通过环境变量传递给底层的 `create.py` 脚本，然后使用 `sk` 工具将生成的 SKP 资源上传到 CIPD。

## 架构位置

该脚本是 SKP 资源管理的顶层协调器，位于 `create.py`（资源创建）和 `sk` 工具（CIPD 上传）之间。

```
SKP 资源创建流程:
create_and_upload.py (入口 + 上传)
    ├── 设置环境变量
    ├── 调用 sk asset upload
    │   └── sk 内部调用 create.py (资源创建)
    │       ├── Flutter SKP 生成
    │       ├── Chrome 网页录制
    │       └── GCS 私有 SKP 下载
    └── 附加 Chromium revision 标签
```

## 主要类与结构体

本脚本为过程式脚本，无类定义。关键变量：

| 变量 | 来源 | 说明 |
|------|------|------|
| `FILE_DIR` | 脚本目录路径 | 锚点路径 |
| `ASSET` | 目录名 `skp` | CIPD 资源名称 |

## 公共 API 函数

### `main()`

脚本主入口，处理以下命令行参数：

| 参数 | 必需 | 说明 |
|------|------|------|
| `--chrome_src_path` / `-c` | 是 | Chromium 源代码路径 |
| `--browser_executable` / `-e` | 是 | 浏览器可执行文件路径 |
| `--dm_path` / `-d` | 是 | Skia DM 工具路径 |
| `--upload_to_partner_bucket` | 否 | 是否上传到合作伙伴 GCS 桶 |
| `--dry_run` | 否 | 模拟运行，不实际上传 |
| `--local` | 否 | 本地模式运行 |

## 内部实现细节

### 环境变量传递机制

由于 `create.py` 是通过 `sk` 工具间接调用的，无法直接传递命令行参数。因此使用环境变量作为参数传递机制：

```python
os.environ[create.BROWSER_EXECUTABLE_ENV_VAR] = args.browser_executable
os.environ[create.CHROME_SRC_PATH_ENV_VAR] = args.chrome_src_path
os.environ[create.UPLOAD_TO_PARTNER_BUCKET_ENV_VAR] = '1' if args.upload_to_partner_bucket else '0'
os.environ[create.DM_PATH_ENV_VAR] = args.dm_path
```

### sk 工具定位

脚本通过相对路径定位 `sk` 工具：

```python
sk = os.path.realpath(os.path.join(
    FILE_DIR, os.pardir, os.pardir, os.pardir, os.pardir, 'bin', 'sk'))
```

对应路径为项目根目录下的 `bin/sk`。在 Windows 上自动添加 `.exe` 后缀。

### Chromium 版本标签

脚本从 Chrome 源码目录获取当前 Git HEAD 的 commit hash，作为 CIPD 包的标签：

```python
chromium_revision = subprocess.check_output(
    ['git', 'rev-parse', 'HEAD'], cwd=args.chrome_src_path).decode().rstrip()
```

这使得 SKP 资源可以追溯到生成它的 Chromium 版本。

### 上传命令构建

根据参数动态构建 `sk asset upload` 命令：
- `--tags chromium_revision:<hash>`：附加 Chromium 版本标签
- `--dry-run`：模拟运行模式
- `--ci`：CI 模式（非 `--local` 时启用）

## 依赖关系

### 内部模块

- `create`：导入 `create.py` 模块以获取环境变量常量定义

### 外部工具

- `sk`：Skia 基础设施命令行工具，用于 CIPD 资源上传
- `git`：用于获取 Chromium 版本号

### 标准库

- `argparse`：命令行参数解析
- `os`：环境变量和路径操作
- `subprocess`：外部命令执行
- `sys`、`tempfile`：辅助工具（已导入但未直接使用）

## 设计模式与设计决策

### 间接调用模式

`create.py` 通过 `sk` 工具间接调用，而非直接导入执行。这是因为 `sk asset upload` 需要控制整个创建-上传流程（包括临时目录管理、CIPD 包装等），`create.py` 作为回调被 `sk` 在适当时机调用。

### 环境变量通信

使用环境变量在父脚本和子脚本之间传递参数，这是一种在工具链层次较深时常用的参数传递方式。缺点是类型信息丢失（所有值为字符串），优点是不受中间工具（`sk`）的参数解析限制。

### 版本追溯标签

通过将 Chromium revision 作为 CIPD 标签，实现了 SKP 资源到浏览器版本的完整追溯链，有助于调试渲染差异和性能回归。

## 性能考量

- 脚本本身的执行开销很小，主要时间消耗在 `sk asset upload` 调用（包括 `create.py` 的 SKP 生成过程）
- SKP 生成过程涉及浏览器启动和网页渲染，是整个流程中最耗时的部分
- `git rev-parse HEAD` 执行极快
- `--dry-run` 模式可用于快速测试脚本逻辑而不执行实际上传

## 相关文件

- `infra/bots/assets/skp/create.py` - SKP 资源创建的核心逻辑
- `infra/bots/assets/skp/__init__.py` - Python 包初始化文件
- `bin/sk` - Skia 基础设施命令行工具
- `tools/skp/webpages_playback.py` - 网页录制工具
- `tools/skp/page_sets/` - 网页集合定义目录
