# CMake 构建模块

> 源文件: infra/bots/recipe_modules/build/cmake.py

## 概述

`cmake.py` 是 Skia 项目中使用 CMake 构建系统的 Recipe 模块。该模块通过 Docker 容器隔离编译环境,使用预构建的 CMake 工具链镜像来编译 Skia,主要用于验证 Skia 的 CMake 构建配置是否正常工作,而非作为主要的构建方式。

## 架构位置

该模块位于 Skia 构建系统的替代构建路径:

- **层级**: 基础设施 / 构建模块 / CMake 支持
- **功能域**: 跨平台构建验证
- **构建策略**: Docker 容器化构建
- **主要用途**: CI 测试和 CMake 用户支持验证

## 主要类与结构体

该模块不定义类,而是提供两个核心函数:

### 常量

- `DOCKER_IMAGE`: CMake Docker 镜像的完整标识符
- `INNER_BUILD_SCRIPT`: 容器内执行的构建脚本路径

## 公共 API 函数

### compile_fn

```python
def compile_fn(api, checkout_root, _ignore):
```

**功能**: 使用 CMake 和 Docker 编译 Skia。

**参数**:
- `api`: Recipe API 对象
- `checkout_root`: Skia 源码根目录
- `_ignore`: 忽略的输出目录参数 (使用自定义路径)

**执行流程**:
1. 配置输出目录为 `cache/docker/cmake`
2. 验证只支持 Release 模式
3. 创建输出目录并设置权限
4. 构建 Docker 运行命令
5. 在容器内执行 `build_skia.sh` 脚本

**特殊设计**:
- 使用独立的输出目录避免与其他构建冲突
- 设置目录权限 `0o777` 防止 Docker root 用户导致的权限问题
- 覆盖 Kitchen 设置的 `DOCKER_CONFIG` 环境变量

**Docker 绑定卷**:
- `/SRC`: 绑定到 Skia 源码目录
- `/OUT`: 绑定到输出目录

### copy_build_products

```python
def copy_build_products(api, src, dst):
```

**功能**: 复制 CMake 构建产物到目标目录。

**参数**:
- `api`: Recipe API 对象
- `src`: 源目录
- `dst`: 目标目录

**实现**: 委托给 `util.copy_listed_files`

## 内部实现细节

### Docker 镜像版本

```python
DOCKER_IMAGE = 'gcr.io/skia-public/cmake-release:git-376aa231c94dd9fabb170903dcfb8e95f2da502c'
```

- 使用特定的 Git 提交哈希确保构建可重现
- 镜像基于 `infra/cmake/Dockerfile` 构建
- 包含预配置的 CMake 工具链和依赖

### 构建脚本路径

```python
INNER_BUILD_SCRIPT = '/SRC/skia/infra/cmake/build_skia.sh'
```

- 脚本位于源码树中,在容器内可见
- 实际的编译逻辑封装在该脚本中
- 允许更新构建逻辑而无需重建 Docker 镜像

### 配置验证

```python
configuration = api.vars.builder_cfg.get('configuration', '')
if configuration != 'Release':  # pragma: nocover
    raise 'Only Release mode supported for CMake'
```

- CMake 构建当前只支持 Release 模式
- Debug 模式需要更新 `build_skia.sh` 脚本
- 提前失败避免无效的构建尝试

### 目录权限处理

```python
api.file.ensure_directory('mkdirs out_dir', out_dir, mode=0o777)
```

**问题**: Docker 以 root 用户运行,创建的文件属于 root

**解决方案**:
- 预先以 `chrome-bot` 用户创建目录
- 设置 777 权限允许 Docker 写入
- 避免后续清理时的权限错误

### Docker 命令构建

```python
cmd = ['docker', 'run', '--rm', '--volume', '%s:/SRC' % checkout_root,
       '--volume', '%s:/OUT' % out_dir,
       DOCKER_IMAGE, INNER_BUILD_SCRIPT]
```

**参数说明**:
- `--rm`: 容器退出后自动删除
- `--volume`: 绑定宿主机目录到容器
- 最后两个参数: 镜像名和要执行的命令

### 环境变量覆盖

```python
env = {'DOCKER_CONFIG': '/home/chrome-bot/.docker'}
with api.env(env):
    api.run(...)
```

Kitchen 默认设置的 `DOCKER_CONFIG` 可能不适用,使用标准路径确保 Docker 正常工作。

## 依赖关系

### 直接依赖
- Docker: 容器运行时
- `util.py`: 工具函数 (文件复制)
- `infra/cmake/build_skia.sh`: 实际构建脚本
- CMake Docker 镜像: 预配置的编译环境

### 被依赖者
- `api.py`: Build API 入口,根据构建器名称分派
- CI 任务: 包含 'CMake' 标记的构建器

### 外部依赖
- Docker daemon: 必须在执行机器上运行
- 网络访问: 拉取 Docker 镜像 (首次运行)
- GCR (Google Container Registry): 镜像存储

## 设计模式与设计决策

### 容器化构建

**优势**:
- **环境一致性**: 所有开发者和 CI 使用相同的工具链
- **隔离性**: 不污染宿主机环境
- **可重现性**: 镜像哈希保证构建环境一致

**权衡**:
- 增加复杂度和启动开销
- 需要 Docker 基础设施支持

### 分离构建脚本

构建逻辑在 `build_skia.sh` 而非 Recipe 中:

**优势**:
- 脚本可以独立测试和迭代
- 更新脚本无需重建镜像
- 降低 Recipe 复杂度

**一致性**: 镜像和脚本版本通过 Git 提交关联

### 缓存策略

使用 `cache/docker/cmake` 作为输出目录:
- 利用 Swarming 的命名缓存加速重复构建
- 与其他构建方式隔离,避免冲突
- 支持增量编译

### 限制配置

当前只支持 Release 模式:
- 简化实现和测试
- 满足当前用例 (验证构建可行性)
- 为未来扩展留下明确的扩展点

## 性能考量

### Docker 开销

- **镜像拉取**: 首次运行需要下载镜像 (~数百 MB)
- **容器启动**: 通常 <1 秒
- **卷挂载**: 基本无开销 (bind mount)

**优化**: 镜像在 CI 机器上预缓存

### 增量编译

- 输出目录通过 Swarming 缓存持久化
- CMake 和 Make 支持增量编译
- 重复构建只重新编译修改的文件

**注意**: Docker 容器重启不影响缓存 (通过卷挂载共享)

### 工具链固定

使用固定版本的编译器和工具:
- 避免工具链差异导致的性能波动
- 可预测的编译时间
- 便于性能回归分析

### 并行编译

`build_skia.sh` 内部通常使用 `make -j$(nproc)` 实现并行编译,充分利用多核 CPU。

## 相关文件

### 构建脚本
- `infra/cmake/build_skia.sh`: 容器内执行的实际构建脚本
- `infra/cmake/Dockerfile`: Docker 镜像定义

### Recipe 模块
- `infra/bots/recipe_modules/build/api.py`: Build API 入口
- `infra/bots/recipe_modules/build/util.py`: 工具函数
- `infra/bots/recipe_modules/build/default.py`: 默认 GN 构建

### Docker 基础设施
- `infra/bots/recipe_modules/docker/`: Docker 操作的 Recipe 模块
- `.dockerignore`: Docker 构建上下文排除规则

### CMake 配置
- `CMakeLists.txt`: Skia 的 CMake 配置文件
- `cmake/`: CMake 相关的辅助脚本和配置

### CI 配置
- `infra/bots/tasks.json`: 定义使用 CMake 的构建任务
- `infra/bots/jobs.json`: 任务调度配置

### 相关镜像
- `gcr.io/skia-public/cmake-release`: 发布版工具链镜像
- `gcr.io/skia-public/cmake-debug`: Debug 版工具链镜像 (如果存在)

该模块展示了 Skia 如何支持多种构建系统,通过容器化技术提供一致的 CMake 构建体验,同时保持与主要 GN 构建系统的分离。这种设计使得 Skia 能够更好地支持使用 CMake 的外部项目和贡献者。
