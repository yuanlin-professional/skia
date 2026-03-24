# external_client - 外部客户端 Docker 构建任务驱动

> 源文件: `infra/bots/task_drivers/external_client/external_client.go`

## 概述

`external_client` 是一个任务驱动程序,用于在 Docker 容器内使用 Bazel 构建 Skia 的外部客户端示例。它将 Skia 代码库挂载到 GCC Debian11 Docker 容器中,然后在容器内执行 Bazel 构建脚本,验证外部客户端能否成功编译。

## 架构位置

属于 Skia CI 的外部兼容性验证子系统,确保 Skia 可以被外部项目作为依赖正确编译。

## 主要类与结构体

无自定义结构体。使用 `common.BazelFlags`。

## 公共 API 函数

- **`main()`**: 解析标志、设置 Docker 环境、运行构建
- **`runDocker()`**: 启动 Docker 容器执行构建

## 内部实现细节

- Docker 镜像: `gcr.io/skia-public/gcc-debian11` (固定 SHA256)
- 使用 `--shm-size=4gb` 增加共享内存供 Bazel 和编译/链接使用
- 通过 bind mount 将 Skia checkout 挂载到容器的 `/SRC`
- 执行容器内的 `bazel_build_with_docker.sh` 脚本

## 依赖关系

- Docker 运行时
- GCC Debian11 Docker 镜像
- `go.skia.org/skia/infra/bots/task_drivers/common` - Bazel 标志

## 设计模式与设计决策

- **容器隔离**: 使用 Docker 确保构建环境的一致性和可重复性
- **固定镜像版本**: 通过 SHA256 哈希锁定 Docker 镜像版本,避免意外更新

## 性能考量

Docker 容器启动和 Bazel 构建是主要耗时环节。4GB 共享内存避免大型链接操作的 OOM。

## 相关文件

- `infra/bots/task_drivers/external_client/bazel_build_with_docker.sh` - 容器内构建脚本
- `example/external_client/` - 默认的外部客户端示例代码
