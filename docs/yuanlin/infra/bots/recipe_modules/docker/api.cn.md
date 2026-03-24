# Docker Recipe Module API

> 源文件: `infra/bots/recipe_modules/docker/api.py`

## 概述

`api.py` 实现了 `DockerApi` 配方模块，提供在 Docker 容器中安全运行 Skia 构建和测试脚本的功能。它处理用户权限映射、目录挂载、文件权限设置和环境变量传递等容器化运行的复杂细节。

## 架构位置

位于 `infra/bots/recipe_modules/docker/` 目录，被需要容器化执行的任务（如 CanvasKit WASM 构建）使用。

## 主要类与结构体

- **`DockerApi`** (recipe_api.RecipeApi): Docker 运行 API
- 常量: `MOUNT_SRC = '/SRC'`, `MOUNT_OUT = '/OUT'`

## 公共 API 函数

- **`mount_src()`**: 返回容器内源码挂载路径 '/SRC'
- **`mount_out()`**: 返回容器内输出挂载路径 '/OUT'
- **`run(name, docker_image, src_dir, out_dir, script, ...)`**: 在 Docker 容器中运行脚本

## 内部实现细节

1. **Setup 阶段** ("Docker setup"):
   - 获取当前用户 uid:gid（通过 `get_uid_gid.py`）
   - 确保输出目录存在并设置 777 权限
   - 设置源目录 755 权限
   - 设置脚本 0755 可执行权限
   - 可选: 复制额外文件、递归设置读权限
2. **Run 阶段**: 构造 docker run 命令
   - `--shm-size=2gb`: 增加共享内存
   - `--rm`: 容器退出后自动清理
   - `--user uid:gid`: 映射主机用户
   - `--mount type=bind`: 绑定挂载源码和输出目录
   - 支持 `match_directory_structure` 保持容器内外路径一致
   - 支持自定义 docker_args 和环境变量
   - 通过 `with_retry` 支持重试
3. Docker 配置路径: `DOCKER_CONFIG=/home/chrome-bot/.docker`

## 依赖关系

- `recipe_engine/file`, `recipe_engine/path`, `recipe_engine/raw_io`, `recipe_engine/step`
- `run`: 重试执行模块

## 设计模式与设计决策

- 用户映射: 使用主机 uid:gid 运行容器内进程，避免文件权限问题
- 双模式挂载: 默认重映射为 /SRC 和 /OUT，可选保持原始路径
- 防御性权限设置: 确保 Docker 进程能读写所有必要的文件
- 重试支持: `attempts` 参数允许容器运行失败后重试

## 性能考量

- `--shm-size=2gb` 防止浏览器测试的共享内存不足
- bind mount 提供接近原生的文件系统性能

## 相关文件

- `infra/bots/recipe_modules/docker/__init__.py`: 模块初始化
- `infra/bots/recipe_modules/docker/examples/full.py`: 测试示例
