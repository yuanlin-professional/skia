# docker - Docker 操作模块

## 概述

`docker` 模块封装了 Docker 容器操作，使 Recipe 能够在 Docker 容器内执行构建和测试任务。它处理镜像拉取、容器启动、卷挂载和执行环境配置等细节。

## 目录结构

```
docker/
├── __init__.py    # DEPS 依赖声明
├── api.py         # DockerApi 核心类
├── examples/      # 使用示例和测试
└── resources/     # 辅助资源脚本
```

## 关键文件

### api.py
提供 Docker 容器操作的高级接口，包括：
- 拉取 Docker 镜像
- 在容器中运行命令
- 管理卷挂载和环境变量
- 容器生命周期管理

## 依赖关系

DEPS: 依赖 `recipe_engine` 中的相关模块。

## 相关文档与参考

- `infra/bots/README.recipes.md` 中 `docker` 模块的 API 文档
