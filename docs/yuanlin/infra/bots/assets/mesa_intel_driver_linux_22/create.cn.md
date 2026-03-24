# create.py - Mesa Intel GPU 驱动 (22.x) Linux 资源创建脚本

> 源文件: [infra/bots/assets/mesa_intel_driver_linux_22/create.py](https://github.com/aspect-build/aspect-cli/blob/main/infra/bots/assets/mesa_intel_driver_linux_22/create.py)

## 概述

`create.py` 用于创建 Mesa 22.1.3 版本 Intel GPU 驱动的 CIPD 资源包。Mesa 是开源的 OpenGL/Vulkan 图形驱动实现，其 Intel 驱动组件在 Skia 的 CI/CD 环境中用于在 Intel GPU 硬件上执行图形渲染测试。该脚本通过 Docker 容器来编译 Mesa 驱动，确保构建环境的一致性和可重复性。与旧版 `mesa_intel_driver_linux` 使用预构建 Docker 镜像不同，本脚本先在本地构建 Docker 镜像，再运行容器编译 Mesa。

## 架构位置

该脚本是 Skia GPU 测试基础设施的一部分，为 Intel GPU 测试提供驱动支持。

```
infra/bots/assets/
├── mesa_intel_driver_linux/
│   └── create.py              # 旧版 Mesa 18.3.3 驱动
├── mesa_intel_driver_linux_22/
│   ├── create.py              # 本文件 - Mesa 22.1.3 驱动
│   └── mesa-driver-builder/
│       └── Dockerfile         # Docker 构建定义
└── ...

GPU 测试流程:
Skia 测试 -> Mesa Intel 驱动 -> Intel GPU 硬件
```

## 主要类与结构体

本脚本无类定义。关键常量：

| 常量 | 值 | 说明 |
|------|-----|------|
| `MESA_VERSION` | `'22.1.3'` | 目标 Mesa 版本 |

## 公共 API 函数

### `create_asset(target_dir)`

通过 Docker 编译 Mesa 驱动。

**参数**：
- `target_dir` (str): 资源输出目录路径

**行为**：
1. 构建 Docker 镜像 `mesa-driver-builder:latest`
2. 运行容器，将 `target_dir` 挂载为 `/OUT` 卷
3. 通过环境变量 `MESA_VERSION` 传递版本号

### `main()`

命令行入口，解析 `--target_dir` / `-t` 参数并调用 `create_asset`。

## 内部实现细节

### Docker 构建流程

脚本分为两个 Docker 操作步骤：

```python
# 步骤 1: 构建 Docker 镜像
cmd = [
    'docker', 'build', '-t', 'mesa-driver-builder:latest',
    './mesa_intel_driver_linux_22/mesa-driver-builder',
]
subprocess.check_output(cmd)

# 步骤 2: 运行容器编译 Mesa
cmd = [
    'docker', 'run', '--volume', '%s:/OUT' % target_dir,
    '--env', 'MESA_VERSION=%s' % MESA_VERSION,
    'mesa-driver-builder'
]
subprocess.check_output(cmd)
```

### Docker 镜像本地构建

与旧版脚本使用远程 Docker 镜像 (`gcr.io/skia-public/mesa-driver-builder:v2`) 不同，本脚本从本地 Dockerfile 构建镜像。这提供了更好的可重复性和版本控制——Dockerfile 与脚本一起存储在代码仓库中。

### 卷挂载

通过 `--volume` 将目标目录挂载到容器内的 `/OUT`，容器内的构建脚本将编译产物写入该目录，从而将产出物传递到宿主机。

### 路径注意事项

Docker build 上下文路径为 `./mesa_intel_driver_linux_22/mesa-driver-builder`，这意味着脚本需要从特定的工作目录（通常是 `infra/bots/assets/`）运行。

## 依赖关系

### 外部工具

- `docker`：容器运行时，用于构建和运行编译环境

### 构建环境依赖（容器内）

- `mesa-driver-builder/Dockerfile`：定义编译环境的 Docker 配置文件
- 容器内的 Mesa 编译工具链（meson、ninja、LLVM 等）

### 标准库

- `argparse`：命令行参数解析
- `subprocess`：外部命令执行

## 设计模式与设计决策

### 容器化编译模式

使用 Docker 容器进行编译是大型 C/C++ 项目的常见做法，优势包括：
- **环境隔离**：编译环境与宿主机隔离，避免依赖冲突
- **可重复性**：Dockerfile 精确定义了所有编译依赖
- **跨机器一致性**：任何安装了 Docker 的机器都能生成相同的产物

### 本地镜像构建 vs 远程镜像拉取

对比旧版使用 `gcr.io` 远程镜像的方式，本脚本采用本地构建。这解决了旧版脚本注释中提到的问题："someone could accidentally change the Docker image that 'v2' points to"，即远程镜像可能被意外修改。

### 版本分离策略

Mesa 22.x 和 18.x 使用不同的资源目录（`mesa_intel_driver_linux_22` vs `mesa_intel_driver_linux`），而非在同一脚本中管理多版本。这使得不同测试任务可以选择不同版本的驱动。

## 性能考量

- **Docker 镜像构建**：首次构建可能需要较长时间（下载基础镜像和编译依赖），但 Docker 层缓存可以加速后续构建
- **Mesa 编译**：Mesa 是一个大型项目，完整编译可能需要几十分钟到数小时
- **`subprocess.check_output`**：捕获所有输出但不流式打印，在长时间编译过程中可能导致用户看不到进度。改用 `check_call` 可以实时显示输出
- **产物体积**：编译后的 Mesa 驱动库文件较大，CIPD 上传/下载时间可能较长
- 一旦 CIPD 包创建完成，CI 测试任务只需下载预编译驱动即可，避免了重复编译

## 相关文件

- `infra/bots/assets/mesa_intel_driver_linux_22/mesa-driver-builder/` - Docker 构建定义目录
- `infra/bots/assets/mesa_intel_driver_linux/create.py` - 旧版 Mesa 18.x 驱动创建脚本
- CI 配置中引用 Mesa 驱动的 GPU 测试任务定义
