创建 Mesa Intel Linux 驱动资产（支持 Vulkan）
============================================================

使用自动化资产 Python 脚本需要安装 Docker。

    mesa_intel_driver_linux$ python create_and_upload.py

构建驱动的步骤见下文。

使用 Docker
------------
最简单的方式是使用预构建的 Docker 镜像。

    docker run -v /tmp/out:/OUT -e MESA_VERSION=18.1.7 gcr.io/skia-public/mesa-driver-builder:latest /opt/build_mesa.sh

您可以将 `/tmp/out` 更改为所需的输出目录，将 `18.1.7` 更改为所需的 Mesa 驱动版本。

最后，将 `/tmp/out` 作为上传脚本的输入目录。

手动构建
--------------------
如果未安装 Docker，可以使用以下步骤构建驱动。
这些步骤已知在 Ubuntu 18.04 上可以正常工作，但由于我们日常构建使用 Docker 容器，这些步骤可能已过时。

安装所有依赖项

    sudo apt-get install autoconf libtool scons flex bison llvm-dev libpthread-stubs0-dev x11proto-gl-dev libdrm-dev libdrm2 x11proto-dri2-dev x11proto-dri3-dev x11proto-present-dev libxcb1-dev libxcb-dri3-dev libxcb-present-dev libxshmfence-dev xserver-xorg-core xserver-xorg-dev x11proto-xext-dev libxext-dev libxdamage-dev libx11-xcb-dev libxcb-glx0-dev libxcb-dri2-0-dev libva-dev libomxil-bellagio-dev

    sudo pip install mako

以下步骤也体现在 `mesa-driver-builder/build_mesa.sh` 中

从 ftp.freedesktop.org/pub/mesa/ 获取源代码

    MESA_VERSION=18.1.7
    wget ftp://ftp.freedesktop.org/pub/mesa/mesa-$MESA_VERSION.tar.gz
    gunzip mesa-$MESA_VERSION.tar.gz
    tar --extract -f mesa-$MESA_VERSION.tar
    mv mesa-$MESA_VERSION/ mesa
    cd mesa


构建驱动

    # 对于调试资源，使用 --enable-debug
    mesa$ ./autogen.sh --disable-radeon --with-gallium-drivers=i915 --with-vulkan-drivers=intel
    mesa$ make -j 50


调整 icd.json 文件和输出目录（mesa/lib）

    mesa$ cp src/intel/vulkan/intel_icd.x86_64.json lib/
    # 将 intel_icd.x86_64.json 文件中的路径名修改为 ./libvulkan_intel.so
    mesa$ rm -rf lib/gallium  # 我们不需要这个
    mesa$ rm lib/nouveau_vieux_dri.so lib/r200_dri.so lib/radeon_dri.so # 我们不需要这些

最后，将 mesa/lib 作为上传脚本的输入目录。


Docker 镜像维护
------------------------
Docker 镜像 `mesa-driver-builder` 是一个安装了许多构建工具（包括 Clang 6）的 Ubuntu 容器。它专门用于构建 Mesa 驱动。

只有在依赖项发生变化或 build_mesa.sh 更新时才需要重新构建该镜像。

    docker build -t mesa-driver-builder ./mesa-driver-builder/
    # 使用 v1、v2、v3 等来处理镜像的变更/更新。
    docker tag mesa-driver-builder gcr.io/skia-public/mesa-driver-builder:v1
    docker push gcr.io/skia-public/mesa-driver-builder:v1
