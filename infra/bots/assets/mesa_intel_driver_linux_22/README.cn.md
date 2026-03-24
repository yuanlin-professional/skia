# 创建 Mesa Intel Linux 驱动资产（支持 Vulkan）

使用自动化资产 Python 脚本需要安装 Docker。

    $ sk asset upload mesa_intel_driver_linux_22

构建驱动的步骤见下文。

## 警告

此资产是 `mesa_intel_driver_linux_22`。

还有一个 `mesa_intel_driver_linux`，其中包含 22 版本之前的 Mesa 驱动副本，因为在 v22 版本中 Mesa 放弃了对"旧版"驱动的支持，而这些驱动涵盖了我们许多现有的 Intel 任务。

## 使用 Docker

最简单的方式是使用提供的 Dockerfile：

    docker build -t mesa-driver-builder:latest ./mesa-driver-builder/
    docker run --volume /tmp/out:/OUT --env MESA_VERSION=22.1.3 mesa-driver-builder:latest

您可以将 `/tmp/out` 更改为所需的输出目录，将 `22.1.3` 更改为所需的 Mesa 驱动版本。

最后，将 `/tmp/out` 作为上传脚本的输入目录。

## 测试

Vulkan 和 GLX 驱动的测试都通过设置环境变量来完成。

例如，如果按上述步骤运行且构建的驱动位于 `/tmp/out/`，则可以通过以下方式测试：

    cd /tmp/out
    LIBGL_DRIVERS_PATH=`pwd` glxinfo | grep -i Mesa
    VK_ICD_FILENAMES="./intel_icd.x86_64.json" vulkaninfo | grep Mesa

注意：请确保选择一个您桌面当前未使用的 Mesa 版本，然后分别在设置和未设置环境变量的情况下运行上述两个命令，以确认驱动确实被正确加载。例如：

使用 22.1.3 驱动：

~~~console
chrome-bot@skia-e-linux-600:~/mesa/foo$ VK_ICD_FILENAMES="./intel_icd.x86_64.json" vulkaninfo | grep Mesa
VK_LAYER_MESA_overlay (Mesa Overlay layer) Vulkan version 1.3.211, layer version 1:
        driverName      = Intel open-source Mesa driver
        driverInfo      = Mesa 22.1.3
        driverName                                           = Intel open-source Mesa driver
        driverInfo                                           = Mesa 22.1.3
~~~

与已安装的 22.0.5 驱动对比：

~~~console
chrome-bot@skia-e-linux-600:~/mesa/foo$  vulkaninfo | grep Mesa
WARNING: lavapipe is not a conformant vulkan implementation, testing use only.
VK_LAYER_MESA_overlay (Mesa Overlay layer) Vulkan version 1.3.211, layer version 1:
WARNING: lavapipe is not a conformant vulkan implementation, testing use only.
        driverName      = Intel open-source Mesa driver
        driverInfo      = Mesa 22.0.5
        driverName                                           = Intel open-source Mesa driver
        driverInfo                                           = Mesa 22.0.5
        driverInfo      = Mesa 22.0.5 (LLVM 14.0.4)
        driverInfo                                           = Mesa 22.0.5 (LLVM 14.0.4)
~~~
