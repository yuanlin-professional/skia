Docker
======

用于处理 Gold + lottie-web 集成的 Docker 文件。


lottie-web-puppeteer
--------------------

此镜像包含 Google Chrome、[puppeteer](https://github.com/GoogleChrome/puppeteer) 以及一些用于自动化网页浏览器测试的其他工具。

此镜像是独立的，没有使其成为 Skia 专属的额外依赖。

每当 Dockerfile 或相关安装的库有更新时，需要手动推送。

    docker build -t lottie-web-puppeteer ./lottie-web-puppeteer/
    LOTTIE_VERSION="v2"  # use v1, v2, etc for any re-spins of the container.
    docker tag lottie-web-puppeteer gcr.io/skia-public/lottie-web-puppeteer:$LOTTIE_VERSION
    docker push gcr.io/skia-public/lottie-web-puppeteer:$LOTTIE_VERSION

需要注意的是，某些版本（通常是 Chrome 60 之前）在使用默认 Docker 设置时会在 /dev/shm 上耗尽空间。为安全起见，建议使用 --shm-size=2gb 标志运行容器。

在本地测试镜像时，以下内容可能有所帮助：

    docker build -t lottie-web-puppeteer ./lottie-web-puppeteer/
    # 在其中运行 bash 以查看并确保各项已正确安装
    docker run -it --shm-size=2gb lottie-web-puppeteer /bin/bash
    # 创建单个 .json 文件的截图，该截图将放在
    # $SKIA_ROOT/tools/lottiecap/docker_strip.png
    docker run -it -v $SKIA_ROOT:/SRC -v ~/lottie-samples:/LOTTIE_FILES -v $LOTTIE_ROOT/build/player:/LOTTIE_BUILD -w /SRC/tools/lottiecap lottie-web-puppeteer node /SRC/tools/lottiecap/lottiecap.js --input /LOTTIE_FILES/body_movin.json --lottie_player /LOTTIE_BUILD/lottie.min.js --in_docker --output docker_strip.png

gold-lottie-web-puppeteer
-------------------------

此镜像包含 Google Chrome、[puppeteer](https://github.com/GoogleChrome/puppeteer) 以及一些用于自动化网页浏览器测试的其他工具。

此镜像假设运行者希望收集特定于 Skia Infra 的 Gold 工具（图像正确性）的输出图像和 JSON 数据。

每当 Dockerfile 或相关安装的库有更新时，需要手动推送。

    # Run the following from $SKIA_ROOT/infra/pathkit
    make gold-docker-image
    LOTTIE_VERSION="v2"  # use v1, v2, etc for any re-spins of the container.
    docker tag gold-lottie-web-puppeteer gcr.io/skia-public/gold-lottie-web-puppeteer:$LOTTIE_VERSION
    docker push gcr.io/skia-public/gold-lottie-web-puppeteer:$LOTTIE_VERSION


需要注意的是，某些版本（通常是 Chrome 60 之前）在使用默认 Docker 设置时会在 /dev/shm 上耗尽空间。为安全起见，建议使用 --shm-size=2gb 标志运行容器。

在本地测试镜像时，以下内容可能有所帮助：

    # Run the following from $SKIA_ROOT/infra/pathkit
    make gold-docker-image
    docker run -it --shm-size=2gb gold-lottie-web-puppeteer /bin/bash
    # 使用本地源代码仓库和 lottie-samples 中的 *所有* 文件收集 gold 输出
    mkdir -p -m 0777 /tmp/dockerout
    docker run -v ~/lottie-samples:/LOTTIE_FILES -v $SKIA_ROOT:/SRC -v $LOTTIE_ROOT/build/player:/LOTTIE_BUILD -v /tmp/dockerout:/OUT gold-lottie-web-puppeteer /SRC/infra/lottiecap/docker/lottiecap_gold.sh