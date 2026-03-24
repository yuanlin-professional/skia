# cmake-release - CMake 构建镜像

## 概述

用于通过 CMake 构建 Skia 的 Docker 镜像。包含 Clang 编译器、CMake 和其他必要的构建工具。

## 目录结构

```
cmake-release/
└── Dockerfile   # Docker 镜像定义
```

## 使用方法

```bash
docker build -t cmake-release ./cmake-release/
docker run -v $SKIA_ROOT:/SRC -v /tmp/output:/OUT cmake-release /SRC/infra/cmake/build_skia.sh
```

## 依赖关系

- `infra/cmake/build_skia.sh` - CMake 构建脚本

## 相关文档与参考

- `infra/cmake/` - CMake 构建脚本
