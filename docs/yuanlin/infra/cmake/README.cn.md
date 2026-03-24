# cmake - CMake 构建脚本

## 概述

`cmake/` 目录包含使用 CMake 构建 Skia 的脚本。该脚本设计为在 `cmake-release` Docker 容器中运行，先使用 GN 生成 CMake 项目文件，再使用 CMake 进行编译。

## 目录结构

```
cmake/
└── build_skia.sh   # CMake 构建脚本
```

## 关键文件

### build_skia.sh

CMake 构建流程：
1. 运行 `bin/fetch-gn` 和 `bin/fetch-ninja` 获取构建工具
2. 使用 GN 生成 CMake 项目（`--ide=json --json-ide-script=gn_to_cmake.py`）
3. 设置 Clang 编译器环境变量
4. 使用 CMake 生成 Unix Makefiles
5. 并行编译（8 线程）
6. 将产物复制到输出目录

## 使用方法

```bash
# 在 Docker 容器中运行
docker run --volume $SKIA_ROOT:/SRC --volume /tmp/cmake_out:/OUT \
  gcr.io/skia-public/cmake-release:latest /SRC/infra/cmake/build_skia.sh
```

## 依赖关系

- `infra/docker/cmake-release/` - CMake 构建 Docker 镜像
- GN 构建系统（用于生成 CMake 项目）
- Clang 编译器

## 相关文档与参考

- [CMake 官方文档](https://cmake.org/)
- `infra/docker/cmake-release/` - Docker 镜像配置
