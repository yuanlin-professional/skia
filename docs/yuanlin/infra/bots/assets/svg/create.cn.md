# create.py - SVG 测试资源创建脚本

> 源文件: [infra/bots/assets/svg/create.py](https://github.com/aspect-build/aspect-cli/blob/main/infra/bots/assets/svg/create.py)

## 概述

`create.py` 是 Skia 基础设施中用于创建 SVG 测试资源包的 Python 脚本。它从多个来源下载 SVG 文件和相关图像资源，包括通过 `svg_downloader.py` 从网络下载公开的 SVG 文件，以及从 Google Cloud Storage 下载私有 SVG 文件。这些资源被打包上传到 CIPD（Chrome Infrastructure Package Deployment）系统，供 Skia 的 CI/CD 测试管道使用。

## 架构位置

该脚本属于 Skia 基础设施中的资源管理子系统，专门负责 SVG 测试数据的创建和管理。

```
infra/bots/assets/
├── svg/
│   └── create.py          # 本文件 - SVG 资源创建
├── skp/
│   └── create.py          # SKP 资源创建
└── ...                    # 其他资源类型

tools/svg/
├── svg_downloader.py      # SVG 下载工具
├── svgs.txt               # SVG 文件列表
├── svgs_parse_only.txt    # 仅解析测试的 SVG 列表
└── svg_images.txt         # SVG 引用的图像列表
```

## 主要类与结构体

本脚本为过程式脚本，不定义类。主要使用以下全局变量：

| 变量 | 值 | 说明 |
|------|-----|------|
| `FILE_DIR` | 脚本所在目录的绝对路径 | 用于计算相对路径 |
| `INFRA_BOTS_DIR` | `infra/bots/` 的绝对路径 | 基础设施根目录 |
| `SVG_TOOLS` | `tools/svg/` 的路径 | SVG 工具目录 |
| `SVG_GS_BUCKET` | `gs://skia-svgs` | Google Cloud Storage 桶地址 |

## 公共 API 函数

### `create_asset(target_dir)`

创建 SVG 资源包的主要函数。

**参数**：
- `target_dir` (str): 资源输出目录路径

**行为**：
1. 在 `target_dir` 下创建 `svg/` 和 `images/` 子目录
2. 下载 `svgs.txt` 中列出的 SVG 文件到 `svg/` 目录
3. 下载 `svgs_parse_only.txt` 中列出的 SVG 文件（添加 `svgparse_` 前缀）
4. 下载 `svg_images.txt` 中列出的图像文件到 `images/` 目录
5. 从 GCS 下载私有 SVG（skbug4713、skbug6918、skbug11244）

### `main()`

命令行入口，解析 `--target_dir` / `-t` 参数并调用 `create_asset`。

## 内部实现细节

### 三阶段下载流程

脚本通过三次调用 `svg_downloader.py` 和一次 GCS 下载来收集所有资源：

1. **常规 SVG 下载**：从 `svgs.txt` 指定的 URL 下载 SVG 文件，用于渲染测试
2. **仅解析 SVG 下载**：从 `svgs_parse_only.txt` 下载 SVG，添加 `svgparse_` 前缀以区分。这些 SVG 仅用于测试解析器的健壮性，不参与渲染对比
3. **图像资源下载**：下载 SVG 中引用的外部图像（如 `<image>` 元素引用的位图），使用 `--keep_common_prefix` 保留目录结构
4. **私有 SVG 下载**：从 `gs://skia-svgs` 下载与特定 bug 相关的私有 SVG 文件

### GCS 私有 SVG

通过 `gcloud storage cp` 命令从 Google Cloud Storage 下载特定 bug 相关的 SVG 文件。这些文件要么包含敏感内容（私有 SVG），要么无法通过公共互联网下载：

- `skbug4713`：对应 Skia bug 4713 的测试用例
- `skbug6918`：对应 Skia bug 6918 的测试用例
- `skbug11244`：对应 Skia bug 11244 的测试用例

## 依赖关系

### 外部工具依赖

- `python3`：脚本运行环境
- `gcloud`：Google Cloud SDK 命令行工具，用于从 GCS 下载文件

### 内部脚本依赖

- `tools/svg/svg_downloader.py`：SVG 文件下载工具
- `tools/svg/svgs.txt`：标准 SVG 文件 URL 列表
- `tools/svg/svgs_parse_only.txt`：仅解析测试 SVG URL 列表
- `tools/svg/svg_images.txt`：SVG 关联图像 URL 列表

### 基础设施依赖

- Google Cloud Storage bucket `gs://skia-svgs`：存储私有 SVG 文件
- CIPD 系统：资源包的最终上传目标

## 设计模式与设计决策

### 多源聚合模式

脚本从多个不同来源（公开 URL、GCS 私有存储）收集资源到统一的目标目录，实现了资源的集中管理。

### 前缀区分策略

使用 `svgparse_` 前缀来区分仅用于解析测试的 SVG 文件和用于渲染测试的 SVG 文件，避免在测试流程中混淆不同用途的测试数据。

### 目录结构分离

将 SVG 文件和图像文件分别存储在 `svg/` 和 `images/` 子目录中，保持资源包内部结构的清晰性。

### 错误处理

使用 `subprocess.check_call` 确保每个下载步骤成功执行，任何失败会立即中止脚本并抛出异常。

## 性能考量

- 所有下载操作是顺序执行的，在大量 SVG 文件场景下可能较慢
- GCS 下载使用通配符模式 (`*`)，可减少单文件请求次数
- `os.path.realpath` 用于规范化路径，避免符号链接导致的路径问题
- 目录存在性检查 (`os.path.exists`) 避免了重复创建目录的错误

## 相关文件

- `tools/svg/svg_downloader.py` - SVG 文件下载工具
- `tools/svg/svgs.txt` - 标准 SVG 文件 URL 列表
- `tools/svg/svgs_parse_only.txt` - 仅解析测试 SVG URL 列表
- `tools/svg/svg_images.txt` - SVG 关联图像 URL 列表
- `infra/bots/assets/svg/VERSION` - 当前 SVG 资源包版本号
