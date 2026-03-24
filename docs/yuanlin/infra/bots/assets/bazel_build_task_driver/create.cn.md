# create.py - Bazel 构建任务驱动器资源创建脚本

> 源文件: [infra/bots/assets/bazel_build_task_driver/create.py](https://github.com/aspect-build/aspect-cli/blob/main/infra/bots/assets/bazel_build_task_driver/create.py)

## 概述

`create.py` 用于编译并打包 Skia 的 Bazel 构建任务驱动器（task driver）为 CIPD 资源。任务驱动器是一个 Go 程序，在 Swarming 任务中运行以执行 Bazel 构建操作。通过将编译好的二进制文件预打包到 CIPD 中，可以避免在每次 CI 运行时重新编译，从而显著减少构建延迟。该脚本使用 Bazel 进行交叉编译，目标平台为 Linux AMD64。

## 架构位置

该脚本是 Skia CI/CD 流水线优化的关键组件，衔接了 Bazel 构建系统和 Swarming 任务执行系统。

```
infra/bots/
├── assets/
│   └── bazel_build_task_driver/
│       └── create.py              # 本文件
├── task_drivers/
│   └── bazel_build/
│       └── bazel_build.go         # 任务驱动器源代码
└── ...

构建产物路径:
bazel-bin/infra/bots/task_drivers/bazel_build/bazel_build_/bazel_build
```

## 主要类与结构体

本脚本无类定义。关键变量：

| 变量 | 值 | 说明 |
|------|-----|------|
| `FILE_DIR` | 脚本所在目录的绝对路径 | 锚点路径 |
| `SKIA_ROOT_DIR` | Skia 项目根目录路径 | 通过相对路径推算（四层父目录） |

## 公共 API 函数

### `create_asset(target_dir)`

编译并复制 Bazel 构建任务驱动器二进制文件。

**参数**：
- `target_dir` (str): 资源输出目录路径

**行为**：
1. 调用 `bazel build //infra/bots/task_drivers/bazel_build` 编译目标
2. 使用 `--platforms=@rules_go//go/toolchain:linux_amd64` 指定交叉编译平台
3. 从 Bazel 输出目录复制编译好的二进制文件到目标目录

### `main()`

命令行入口，解析 `--target_dir` / `-t` 参数并调用 `create_asset`。

## 内部实现细节

### Bazel 交叉编译

脚本使用 `rules_go` 的平台定义进行交叉编译：

```python
subprocess.check_output([
    "bazel", "build", "//infra/bots/task_drivers/bazel_build",
    "--platforms=@rules_go//go/toolchain:linux_amd64",
], encoding='utf-8')
```

这意味着即使在 macOS 开发机上运行此脚本，生成的二进制文件也是 Linux AMD64 格式的，因为 CI 的 Swarming 任务运行在 Linux 机器上。

### 二进制文件路径

Bazel 输出的 Go 二进制文件路径遵循 `rules_go` 的约定：
```
bazel-bin/infra/bots/task_drivers/bazel_build/bazel_build_/bazel_build
```

其中 `bazel_build_` 是 `rules_go` 为 Go 二进制目标创建的中间目录。

### CIPD 缓存优化

如文档注释所述，将任务驱动器预编译到 CIPD 中的主要目的是避免 `BuildTaskDrivers` 作业的重复编译。虽然 Swarming 的去重机制有时会缓存幂等任务，但在 `//bazel` 目录下发生不相关变更时，缓存可能失效，导致不必要的重新编译。

## 依赖关系

### 构建工具

- `bazel`：必须在 PATH 中可用，用于编译 Go 源代码
- `rules_go`：Bazel 的 Go 语言构建规则

### 源代码依赖

- `infra/bots/task_drivers/bazel_build/`：任务驱动器的 Go 源代码

### 标准库

- `argparse`：命令行参数解析
- `os`：文件路径操作
- `shutil`：文件复制
- `subprocess`：外部命令执行

## 设计模式与设计决策

### 预编译缓存模式

这是一种典型的构建加速策略：将不经常变化的构建产物预编译并缓存到 CIPD 中，避免在每次 CI 运行中重复编译。任务驱动器源代码很少变化，因此这种策略非常有效。

### 交叉编译策略

使用 Bazel 和 `rules_go` 的交叉编译能力，允许在任何平台上生成目标平台（Linux AMD64）的二进制文件，简化了资源创建流程。

### 显式路径计算

通过 `os.path.realpath` 和多层 `os.pardir` 计算 Skia 根目录路径，避免依赖环境变量或工作目录假设。

## 性能考量

- Bazel 构建本身利用了增量编译和远程缓存，首次编译可能较慢，但后续编译通常很快
- 生成的二进制文件为静态链接的 Go 程序，无运行时依赖，部署简单
- 通过 CIPD 缓存避免了重复编译，显著减少了 CI 流水线的整体耗时
- `subprocess.check_output` 捕获输出但不流式打印，对于长时间编译可能导致用户无法看到进度

## 相关文件

- `infra/bots/task_drivers/bazel_build/bazel_build.go` - 任务驱动器源代码
- `infra/bots/assets/bazelisk_mac_amd64/create.py` - Bazelisk 资源创建脚本
- `infra/bots/assets/bazelisk_linux_amd64/create.py` - Linux Bazelisk 资源创建脚本
- `BUILD.bazel` 或 `BUILD` - Bazel 构建定义文件
- `.bazelversion` - Bazel 版本配置
