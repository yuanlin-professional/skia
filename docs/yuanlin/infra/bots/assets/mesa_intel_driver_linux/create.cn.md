# create.py - Mesa Intel GPU 驱动 (18.x) Linux 资源创建脚本

> 源文件: [infra/bots/assets/mesa_intel_driver_linux/create.py](https://github.com/aspect-build/aspect-cli/blob/main/infra/bots/assets/mesa_intel_driver_linux/create.py)

## 概述

`create.py` 用于创建旧版 Mesa 18.3.3 Intel GPU 驱动的 CIPD 资源包。Mesa 是 Linux 上主要的开源 GPU 驱动实现，为 OpenGL 和 Vulkan 提供硬件加速支持。该脚本使用预构建的 Docker 镜像（`gcr.io/skia-public/mesa-driver-builder:v2`）来编译 Mesa 驱动，通过在容器内运行 `build_mesa.sh` 脚本完成编译。相较于新版 `mesa_intel_driver_linux_22`，本脚本使用远程 Docker 镜像而非本地构建。

## 架构位置

该脚本是 Skia GPU 测试基础设施的一部分，为需要旧版 Mesa 驱动的测试提供支持。

```
infra/bots/assets/
├── mesa_intel_driver_linux/
│   └── create.py              # 本文件 - 旧版 Mesa 18.3.3
├── mesa_intel_driver_linux_22/
│   └── create.py              # 新版 Mesa 22.1.3
└── ...

版本关系:
Mesa 18.3.3 (本文件) <- 旧版测试兼容性
Mesa 22.1.3 (v22)    <- 新版测试环境
```

## 主要类与结构体

本脚本无类定义。关键常量：

| 常量 | 值 | 说明 |
|------|-----|------|
| `DOCKER_IMAGE` | `gcr.io/skia-public/mesa-driver-builder:v2` | 预构建的 Docker 镜像 |
| `BUILD_SCRIPT` | `/opt/build_mesa.sh` | 容器内的 Mesa 编译脚本路径 |
| `MESA_VERSION` | `'18.3.3'` | 目标 Mesa 版本 |

## 公共 API 函数

### `create_asset(target_dir)`

通过 Docker 容器编译 Mesa 驱动。

**参数**：
- `target_dir` (str): 资源输出目录路径

**行为**：
1. 构建 Docker 运行命令，挂载目标目录为 `/OUT`
2. 通过环境变量 `MESA_VERSION` 传递版本号
3. 在容器中执行 `build_mesa.sh` 脚本

### `main()`

命令行入口，解析 `--target_dir` / `-t` 参数并调用 `create_asset`。

## 内部实现细节

### Docker 运行命令

```python
cmd = [
    'docker', 'run',
    '--volume', '%s:/OUT' % target_dir,   # 挂载输出目录
    '--env', 'MESA_VERSION=%s' % MESA_VERSION,  # 传递版本号
    DOCKER_IMAGE,                          # 使用预构建镜像
    BUILD_SCRIPT                           # 运行编译脚本
]
subprocess.check_output(cmd)
```

容器内的 `/opt/build_mesa.sh` 脚本负责：
- 下载 Mesa 源代码
- 配置编译选项（针对 Intel GPU）
- 编译并安装到 `/OUT` 目录（即宿主机的 `target_dir`）

### 与新版脚本的对比

| 特性 | mesa_intel_driver_linux (本文件) | mesa_intel_driver_linux_22 |
|------|----------------------------------|---------------------------|
| Mesa 版本 | 18.3.3 | 22.1.3 |
| Docker 镜像来源 | 远程 `gcr.io` | 本地 Dockerfile 构建 |
| 构建脚本 | 容器内预置 | 本地 Dockerfile 定义 |
| 可重复性 | 较低（镜像可能被修改） | 较高（Dockerfile 受版本控制） |

### 源代码注释中的警告

脚本包含一段重要的 TODO 注释：

> In the future, it might be simpler to build the docker image as part of this script so that we don't need to push it to the container repo. Doing so would make this script more repeatable, since someone could accidentally change the Docker image that "v2" points to.

这说明开发者已经意识到远程镜像方式的可重复性问题，而新版脚本（`mesa_intel_driver_linux_22`）正是采纳了这个建议。

## 依赖关系

### 外部工具

- `docker`：容器运行时

### Docker 镜像依赖

- `gcr.io/skia-public/mesa-driver-builder:v2`：预构建的 Mesa 编译环境
  - 包含 Mesa 编译所需的全部依赖（meson/autotools、LLVM、libdrm 等）
  - 包含 `/opt/build_mesa.sh` 编译脚本

### 标准库

- `argparse`：命令行参数解析
- `subprocess`：外部命令执行

## 设计模式与设计决策

### 远程镜像模式

使用预构建的远程 Docker 镜像简化了本地脚本的复杂度，但引入了外部依赖的可变性风险。任何对 `gcr.io` 上 `v2` 标签的修改都可能影响构建结果的一致性。

### 版本通过环境变量传递

Mesa 版本通过 Docker 环境变量传递给容器内脚本，使得同一个 Docker 镜像可以编译不同版本的 Mesa（只要编译脚本支持）。

### 遗留兼容设计

保留旧版 Mesa 18.3.3 驱动可能是为了：
- 测试 Skia 在旧版驱动上的兼容性
- 某些 CI 机器的硬件可能需要旧版驱动
- 历史测试结果的对比基准

## 性能考量

- **Docker 镜像拉取**：首次运行需要从 `gcr.io` 拉取镜像，可能需要较长时间
- **Mesa 编译**：Mesa 是大型项目，编译时间取决于容器内的 CPU 资源
- **`subprocess.check_output`**：捕获全部输出，长时间编译过程中用户看不到进度
- 编译完成后产物通过卷挂载直接写入宿主机，无需额外复制
- CIPD 包创建后，CI 任务直接下载预编译驱动，无需重复编译

## 相关文件

- `infra/bots/assets/mesa_intel_driver_linux_22/create.py` - 新版 Mesa 22.x 驱动创建脚本
- `infra/bots/assets/mesa_intel_driver_linux/VERSION` - CIPD 资源版本号
- CI 配置中引用 Mesa 驱动的 GPU 测试任务定义
