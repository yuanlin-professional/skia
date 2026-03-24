# ARM64 Sysroot 资产创建脚本

> 源文件: infra/bots/assets/arm64_sysroot/create.py

## 概述

使用 Docker 构建 ARM64 Linux sysroot 的资产创建脚本。Sysroot 包含交叉编译所需的头文件、库文件和系统文件，使得在 x86_64 主机上可以编译 ARM64 目标代码。该脚本构建 Docker 镜像生成 sysroot，然后从容器中提取资产。

## 架构位置

位于 `infra/bots/assets/arm64_sysroot/`，为 Skia 在 x86_64 Linux 主机上交叉编译 ARM64 目标提供编译环境，支持 ARM 服务器、树莓派等平台。

## 主要类与结构体

函数式风格，使用 Python 标准库和 Docker 命令。

## 公共 API 函数

### `create_asset(target_dir)`
执行流程：
1. 使用 Docker 构建包含 sysroot 的镜像
2. 运行容器并挂载目标目录
3. 从容器中复制 sysroot 文件
4. 修改文件权限为所有用户可写（避免 Docker root 权限问题）

**实现**:
```python
subprocess.run(['docker', 'build', '-t', 'arm64_sysroot',
                './infra/bots/assets/arm64_sysroot'], check=True)

subprocess.run(['docker', 'run', '--mount',
                f'type=bind,source={target_dir},target=/OUT',
                'arm64_sysroot', '/bin/sh', '-c',
                'cp -R /tmp/arm64_sysroot_output/* /OUT && chmod -R a+w /OUT'],
               check=True)
```

### `main()`
检查运行在 Linux 平台，解析参数并执行。

## 内部实现细节

### Docker 化构建

使用 Docker 构建 sysroot 的优势：
- **隔离性**: 不污染主机环境
- **可重现性**: Dockerfile 定义确定性构建
- **跨发行版**: 在任何 Linux 发行版上生成一致的 sysroot

### 权限处理

Docker 容器内以 root 运行，复制的文件默认 root 所有。`chmod -R a+w` 确保：
- CI 用户可以删除和修改文件
- 避免权限导致的构建失败

### 平台限制

脚本强制要求在 Linux 上运行：
```python
if 'linux' not in sys.platform:
    print('This script only runs on Linux.', file=sys.stderr)
    sys.exit(1)
```

这是因为 Docker sysroot 构建依赖 Linux 特定的工具。

## 依赖关系

- **Docker**: 构建和运行容器
- **Dockerfile**: `infra/bots/assets/arm64_sysroot/Dockerfile`
- **Linux 主机**: 必需

## 设计模式与设计决策

### Docker 作为构建环境

相比直接安装交叉编译工具链，使用 Docker：
- 更干净的环境
- 更容易维护和更新
- 更好的可移植性

### 文件复制策略

使用 Docker 卷挂载而非 `docker cp`：
- 更高效
- 支持大文件和目录
- 减少中间步骤

## 性能考量

- Docker 镜像构建: 5-15 分钟（首次，包含下载包）
- 文件复制: 10-30 秒
- 权限修改: 1-5 秒

后续构建可利用 Docker 缓存加速。

## 相关文件

- `infra/bots/assets/arm64_sysroot/Dockerfile`: sysroot 构建定义
- `infra/bots/assets/armhf_sysroot/create.py`: 32 位 ARM 版本
- GN 工具链配置使用该 sysroot
