# docker - Docker 构建配置

## 概述

`docker/` 目录包含用于构建不同 Skia 目标的 Docker 配置文件。这些 Docker 镜像提供标准化的构建环境，确保 CI 构建的可重复性。镜像通过 Louhi 系统手动触发重建。

## 目录结构

```
docker/
├── debian9/          # Debian 9 基础镜像
│   └── Dockerfile    # Debian 9 Docker 配置
├── binary-size/      # 二进制体积分析镜像
│   └── Dockerfile    # 体积分析工具 Docker 配置
├── cmake-release/    # CMake 构建镜像
│   └── Dockerfile    # CMake 构建环境 Docker 配置
├── docker_build.sh   # Docker 构建辅助脚本（供 Louhi 使用）
├── make_image_tag.sh # 生成镜像标签脚本
├── Makefile          # 便捷 make 命令
└── README.md         # 原始说明文档
```

## 关键文件

### docker_build.sh
Louhi 系统使用的 Docker 构建脚本。需要在调用前定义 `copy_release_files` 函数和 `IMAGE_NAME` 变量。

### cmake-release/
用于使用 CMake 构建 Skia 的镜像。本地测试流程：
```bash
docker build -t cmake-release ./cmake-release/
docker run -v $SKIA_ROOT:/SRC -v /tmp/output:/OUT cmake-release /SRC/infra/cmake/build_skia.sh
```

### binary-size/
用于构建代码体积树状图的镜像。本地测试：
```bash
docker build -t binary-size ./binary-size/
docker run -v $SKIA_ROOT/out/Release:/IN -v /tmp/output:/OUT binary-size \
  /opt/binary_size/src/run_binary_size_analysis.py --library /IN/skottie_tool --destdir /OUT
```

## 依赖关系

- Louhi 部署系统
- `infra/cmake/build_skia.sh` - CMake 构建脚本

## 相关文档与参考

- 原始 `README.md` 中的详细使用说明
