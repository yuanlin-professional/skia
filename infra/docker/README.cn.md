# Docker

用于构建不同 Skia 目标的 Docker 文件。

## cmake-release

此镜像用于使用 CMake 构建 Skia。

每当 Dockerfile 或相关安装的库有更新时，应通过 Louhi（手动调用）重新构建该镜像。

在本地测试镜像时，以下流程可能有所帮助：

    docker build -t cmake-release ./cmake-release/
    # 在其中运行 bash 以查看并确保各项已正确安装和配置。
    # 也可用于获取 CMake 的版本。
    docker run -it cmake-release /bin/bash
    # 使用本地镜像在本地检出中编译 Skia
    docker run -v $SKIA_ROOT:/SRC -v /tmp/output:/OUT cmake-release /SRC/infra/cmake/build_skia.sh

## binary-size

此镜像用于构建 Skia 的代码体积树状图 (Tree Map)。

每当 Dockerfile 或相关安装的库有更新时，应通过 Louhi（手动调用）重新构建该镜像。

在本地测试镜像时，以下流程可能有所帮助：

    docker build -t binary-size ./binary-size/
    # 在其中运行 bash 以查看并确保各项已正确安装和配置。
    docker run -it binary-size /bin/sh
    # 分析构建目录 out/Release 中的可执行文件 "skottie_tool"
    docker run -v $SKIA_ROOT/out/Release:/IN -v /tmp/output:/OUT binary-size /opt/binary_size/src/run_binary_size_analysis.py --library /IN/skottie_tool --destdir /OUT
