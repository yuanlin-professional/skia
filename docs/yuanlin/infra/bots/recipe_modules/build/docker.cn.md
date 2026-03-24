# Docker 构建模块

> 源文件: infra/bots/recipe_modules/build/docker.py

## 概述

`docker.py` 是 Skia 项目中通过 Docker 容器进行编译的 Recipe 模块。该模块使用预配置的 Docker 镜像来提供一致的编译环境,特别是针对使用 GCC 编译器的 Debian 和 Ubuntu 系统。通过容器化构建,确保编译环境的可重现性,并支持增量编译以提高构建效率。

## 架构位置

该模块位于 Skia 构建系统的容器化构建路径:

- **层级**: 基础设施 / 构建模块 / Docker 支持
- **功能域**: Linux 平台 GCC 编译
- **构建策略**: 容器化隔离编译
- **支持平台**: Debian 11, Ubuntu 18

## 主要类与结构体

该模块不定义类,而是提供常量和函数。

### 常量

#### IMAGES

```python
IMAGES = {
    'gcc-debian11': 'gcr.io/skia-public/gcc-debian11@sha256:...',
    'gcc-debian11-x86': 'gcr.io/skia-public/gcc-debian11-x86@sha256:...',
    'gcc-ubuntu18': 'gcr.io/skia-public/clang-ubuntu18@sha256:...',
}
```

定义支持的 Docker 镜像及其 SHA256 哈希值,确保镜像不可变性。

## 公共 API 函数

### compile_fn

```python
def compile_fn(api, checkout_root, out_dir):
```

**功能**: 使用 Docker 容器和 GCC 编译 Skia。

**参数**:
- `api`: Recipe API 对象
- `checkout_root`: 源码检出根目录
- `out_dir`: 构建输出目录

**执行流程**:
1. 从构建器配置提取编译器、操作系统、目标架构等信息
2. 移除 `extra_tokens` 中的 'Docker' 标记
3. 生成 GN 编译参数 (使用 `default.get_compile_flags`)
4. 根据操作系统和架构选择合适的 Docker 镜像
5. 注入镜像哈希到编译标志,触发工具链变更时的重新编译
6. 在 Docker 容器中执行编译脚本

**支持配置**:
- **Debian 11 + GCC + x86_64**: `gcc-debian11`
- **Debian 11 + GCC + x86**: `gcc-debian11-x86`
- 其他配置会抛出 "Not implemented" 异常

### copy_build_products

```python
def copy_build_products(api, src, dst):
```

**功能**: 复制 Docker 构建产物。

**实现**: 委托给 `util.copy_listed_files` 使用默认产物列表。

## 内部实现细节

### 镜像选择逻辑

```python
image_name = None
if os == 'Debian11' and compiler == 'GCC':
    if target_arch == 'x86_64':
        image_name = 'gcc-debian11'
    elif target_arch == 'x86':
        image_name = 'gcc-debian11-x86'

if not image_name:
    raise Exception('Not implemented: ' + api.vars.builder_name)
```

**策略**: 根据操作系统、编译器和目标架构组合选择镜像

**扩展性**: 新平台通过添加镜像和条件分支支持

### 工作目录映射

```python
workdir = api.path.cast_to_path('/SRC')
```

- 容器内的固定路径 `/SRC`
- 实际映射到宿主机的 `checkout_root`
- 简化容器内脚本的路径处理

### 重新编译触发机制

```python
args['extra_cflags'].append('-DREBUILD_IF_CHANGED_docker_image=%s' % image_hash)
```

**设计意图**:
- 当 Docker 镜像更新时,触发完全重新编译
- 通过 C 预处理器定义实现
- 任何源文件的预处理结果都会改变,导致重新编译

**工作原理**:
- 镜像哈希改变 → 宏定义值改变 → 编译器检测到变化 → 重新编译

### 增量编译支持

```python
# We always perform an incremental compile, since out dir is cached across
# compile tasks.
```

- 输出目录通过 Swarming 缓存持久化
- Docker 容器每次启动时挂载同一缓存目录
- GN/Ninja 自动检测文件变化,只重新编译必要的部分

### Docker 执行脚本

```python
script = api.build.resource('docker-compile.sh')
api.docker.run('Run build script in Docker', image_hash,
               api.vars.workdir, out_dir, script, args=[gn_flags], env=env)
```

**参数说明**:
- `image_hash`: Docker 镜像完整标识符
- `api.vars.workdir`: 宿主机工作目录
- `out_dir`: 输出目录
- `script`: 容器内执行的 shell 脚本
- `args`: 传递给脚本的参数 (GN 标志字符串)
- `env`: 环境变量

## 依赖关系

### 直接依赖
- `default.py`: 提供 `get_compile_flags` 和 `finalize_gn_flags` 函数
- `util.py`: 提供 `copy_listed_files` 和 `DEFAULT_BUILD_PRODUCTS`
- `docker` Recipe 模块: 提供 `api.docker.run` 方法
- `docker-compile.sh`: 容器内执行的构建脚本

### 被依赖者
- `api.py`: BuildApi 根据构建器名称中的 'Docker' 标记选择此模块
- CI 任务: 名称包含 'Docker' 的构建器

### 外部依赖
- Docker daemon: 必须在宿主机上运行
- Docker 镜像: 托管在 Google Container Registry (GCR)
- GCC 工具链: 打包在 Docker 镜像中

## 设计模式与设计决策

### 不可变镜像

使用 SHA256 哈希而非标签:
```python
'gcc-debian11@sha256:1117ea368f43e45e0f543f74c8e3bf7ff6932df54ddaa4ba1fe6131209110d3d'
```

**优势**:
- 完全可重现的构建
- 防止镜像被恶意替换
- 明确的版本控制

**权衡**: 更新镜像需要修改代码

### 代理模式

该模块是 `default.py` 的代理:
- 复用 `get_compile_flags` 生成编译参数
- 只改变执行环境 (Docker 容器)
- 保持编译逻辑一致

### 策略模式

通过条件分支选择镜像:
- 不同配置使用不同镜像
- 集中管理镜像映射
- 易于添加新配置

### 显式失败

```python
if not image_name:
    raise Exception('Not implemented: ' + api.vars.builder_name)
```

未支持的配置立即失败,而非静默使用错误的镜像。

## 性能考量

### 增量编译优化

- **缓存目录**: 输出目录通过 Swarming 持久化
- **变更检测**: Ninja 只编译修改的文件
- **典型场景**: 增量编译比完全编译快 5-10 倍

### 镜像缓存

- **本地缓存**: CI 机器预先拉取镜像
- **拉取时间**: 首次 ~1-2 分钟,后续几乎为零
- **磁盘占用**: 每个镜像 ~500MB-1GB

### 容器启动开销

- **启动时间**: <1 秒
- **卷挂载**: 零拷贝 bind mount
- **网络**: 不使用网络命名空间,开销极小

### 编译并行度

Docker 容器继承宿主机 CPU 配置:
- `docker-compile.sh` 通常使用 `ninja -j$(nproc)`
- 充分利用多核 CPU
- 与非容器化构建性能相当

### 工具链固定

使用固定版本的 GCC:
- 避免编译器升级导致的不兼容
- 可预测的编译时间和行为
- 便于性能基准测试

## 相关文件

### 构建脚本
- `infra/bots/recipe_modules/build/resources/docker-compile.sh`: 容器内执行的构建脚本
- `infra/bots/recipe_modules/build/default.py`: 编译标志生成逻辑

### Docker 镜像定义
- `infra/bots/docker/gcc-debian11/Dockerfile`: Debian 11 镜像定义
- `infra/bots/docker/gcc-debian11-x86/Dockerfile`: 32 位镜像定义
- `infra/bots/docker/clang-ubuntu18/Dockerfile`: Ubuntu 镜像定义

### Recipe 模块
- `infra/bots/recipe_modules/build/api.py`: Build API 入口
- `infra/bots/recipe_modules/build/util.py`: 工具函数
- `infra/bots/recipe_modules/docker/`: Docker 操作封装

### 镜像构建
- 镜像构建脚本和 CI 流程
- GCR 推送和管理工具

### CI 配置
- `infra/bots/tasks.json`: 定义 Docker 构建任务
- `infra/bots/jobs.json`: 任务调度配置

### 相关 Recipe
- `infra/bots/recipes/compile.py`: 调用 build 模块的主 Recipe
- `infra/bots/recipes/sync_and_compile.py`: 带源码同步的编译

### 缓存配置
- Swarming 命名缓存配置
- 缓存清理策略

该模块展示了 Skia 如何通过 Docker 实现跨平台的一致构建体验,特别是对于 GCC 工具链的支持。容器化策略在提供环境一致性的同时,通过增量编译和缓存机制保持了良好的构建性能。
