Docker
======

用于简化 CanvasKit 和其他 WASM 工件 (Artifact) 开发的 Docker 文件。

emsdk-base
----------

此镜像包含一个 Emscripten SDK 环境，可用于将项目（例如 Skia 的 CanvasKit）编译为 WASM。

此镜像跟踪官方 emscripten Docker 镜像并安装 Python 2（我们的某些脚本仍在使用）。

    make publish_emsdk_base

在本地测试镜像时，以下流程可能有所帮助：

    docker build -t emsdk-base ./emsdk-base/
    # 在其中运行 bash 以查看并确保各项已正确安装
    docker run -it emsdk-base /bin/bash
    # 使用本地镜像编译 CanvasKit
    docker run -v $SKIA_ROOT:/SRC -v $SKIA_ROOT/out/dockerpathkit:/OUT emsdk-base /SRC/infra/canvaskit/build_canvaskit.sh

karma-chrome-tests
------------------

此镜像安装了 Google Chrome 和 karma/jasmine，可用于运行 JS 测试。

此镜像是独立的，没有使其成为 Skia 专属的额外依赖。

每当 Dockerfile 或相关安装的库有更新时，需要手动推送。

    make publish_karma_chrome_tests

需要注意的是，某些版本（通常是 Chrome 60 之前）在使用默认 Docker 设置时会在 /dev/shm 上耗尽空间。为安全起见，建议使用 --shm-size=2gb 标志运行容器。

在本地测试镜像时，以下内容可能有所帮助：

    docker build -t karma-chrome-tests ./karma-chrome-tests/
    # 在其中运行 bash 以查看并确保各项已正确安装
    docker run -it --shm-size=2gb karma-chrome-tests /bin/bash
    # 使用本地源代码仓库运行测试（但不捕获 Gold 输出）
    docker run --shm-size=2gb -v $SKIA_ROOT:/SRC karma-chrome-tests karma start /SRC/infra/pathkit/karma-docker.conf.js --single-run

gold-karma-chrome-tests
------------------

此镜像安装了 Google Chrome 和 karma/jasmine，可用于运行 JS 测试。

此镜像假设运行者希望收集特定于 Skia Infra 的 Gold 工具（图像正确性）的输出图像和 JSON 数据。

每当 Dockerfile 或父镜像（karma-chrome-tests）有更新时，需要手动推送。

    # Run the following from $SKIA_ROOT/infra/pathkit
    make publish_gold_karma_chrome_tests

需要注意的是，某些版本（通常是 Chrome 60 之前）在使用默认 Docker 设置时会在 /dev/shm 上耗尽空间。为安全起见，建议使用 --shm-size=2gb 标志运行容器。

在本地测试镜像时，以下内容可能有所帮助：

    # Run the following from $SKIA_ROOT/infra/pathkit
    make gold-docker-image
    # 在其中运行 bash 以查看并确保各项已正确安装
    docker run -it --shm-size=2gb gold-karma-chrome-tests /bin/bash
    # 使用本地源代码仓库运行测试并收集 Gold 输出
    mkdir -p -m 0777 /tmp/dockergold
    docker run --shm-size=2gb -v $SKIA_ROOT:/SRC -v /tmp/dockergold:/OUT gold-karma-chrome-tests /SRC/infra/pathkit/test_pathkit.sh

perf-karma-chrome-tests
------------------

此镜像安装了 Google Chrome 和 karma/jasmine，可用于运行 JS 测试。

此镜像假设运行者希望收集特定于 Skia Infra 的 Perf 工具的输出图像和 JSON 数据。

每当 Dockerfile 或父镜像（karma-chrome-tests）有更新时，需要手动推送。

    # Run the following from $SKIA_ROOT/infra/pathkit
    make publish_perf_karma_chrome_tests

需要注意的是，某些版本（通常是 Chrome 60 之前）在使用默认 Docker 设置时会在 /dev/shm 上耗尽空间。为安全起见，建议使用 --shm-size=2gb 标志运行容器。

在本地测试镜像时，以下内容可能有所帮助：

    # Run the following from $SKIA_ROOT/infra/pathkit
    make perf-docker-image
    # 在其中运行 bash 以查看并确保各项已正确安装
    docker run -it --shm-size=2gb perf-karma-chrome-tests /bin/bash
    # 使用本地源代码仓库运行测试并收集 Perf 输出
    mkdir -p -m 0777 /tmp/dockerperf
    docker run --shm-size=2gb -v $SKIA_ROOT:/SRC -v /tmp/dockerperf:/OUT perf-karma-chrome-tests /SRC/infra/pathkit/perf_pathkit.sh
