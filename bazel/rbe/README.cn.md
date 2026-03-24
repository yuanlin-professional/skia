RBE 配置
==================

此文件夹的某些子目录是自动生成的。例如，`gce_linux` 是通过运行 `make generate_linux_config` 生成的。这些生成的文件描述了 RBE Docker 镜像中的 C++ 和 Java 工具链 (Toolchain)；这些工具链是运行 Bazel 所必需的，但**不是**我们用来编译代码的工具链。

我们构建自己的精简 Docker 镜像用于 RBE。我们打算使用密封工具链 (Hermetic Toolchain)（参见 //toolchain），该工具链指定了编译和链接 Skia 所需的一切。在 RBE 内外使用密封工具链使得构建可重复且在不同机器间保持一致，并且不需要互联网访问（假设工具链已至少缓存过一次）。这种设置的理想特性在于，如果我们需要更改工具链的一个小细节，不需要更改和上传 RBE Docker 镜像。

我们对 Docker 镜像的唯一要求（除了运行 Bazel 的最低要求之外）是它具有足够的运行时库来运行我们的工具链。例如，这意味着 Linux RBE 镜像至少需要 glibc 2.32，这是我们工具链中 Linux 二进制文件的当前最低要求。这与任何尝试在本地使用 Bazel 构建 Skia 的开发者的要求相同。

获取 rbe_configs_gen
-----------------------
建议从 [GitHub](https://github.com/bazelbuild/bazel-toolchains/releases/tag/v5.1.1) 下载预构建的二进制文件并将其放入你的 PATH 中。

创建/更新 RBE 镜像
-------------------------------
根据 SLSA 级别 1 的要求，我们希望有一种脚本化的方式来构建镜像，并精确指定其中包含的产物。为此，我们指定了所使用的基础 Docker 镜像的确切 sha256 哈希值，以及我们在其上安装的软件包的确切版本。如果我们需要添加软件包或进行更新，最好先在不使用这些限定符的情况下构建镜像，看看实际使用了什么，然后重新指定它们，以便其他人再次构建 Docker 镜像时可能得到相同的镜像。

此流程为：
 1) 修改相应的 Dockerfile（例如 gce_linux_container/Dockerfile）以移除版本或哈希限定符。同时在 `Makefile` 中递增相应的 VERSION 变量。
 2) 添加任何新软件包或进行任何更改。
 3) 运行 `make build_linux_container` 在本地构建镜像。可以通过运行类似 `docker run -it gcr.io/skia-public/rbe_linux:v3 /bin/bash` 的命令来验证其是否正常工作。
 4) 记录所使用的版本和基础镜像哈希值。修改 Dockerfile 以使用这些值。
    1) `docker pull debian:bookworm-slim` 是查看 sha256 并获取最新版本的最简单方法。
    2) 可以通过查找如下日志来找到版本信息：
       `Get:89 http://deb.debian.org/debian bookworm/main amd64 clang amd64 1:14.0-55.2+b1 [9976 B]`
 5) 运行 `make push_linux_container` 重新构建容器并将其推送到 GCS，以供我们的 RBE 工作节点使用。记录此创建容器的 sha256 哈希值。
 6) 修改 `Makefile` 中相应的生成步骤（例如 `generate_linux_config`）以引用正确的 toolchain_container。然后运行该步骤。
 7) 修改 `//platform/BUILD.bazel` 中的 RBE 平台以引用新的 `container_image`。

我们选择不对此容器步骤使用 Bazel 规则，因为在 Bazel 尚未设置的情况下引导可能会很困难。此外，Make 是一种简单且足够的方式来为 SLSA 目的编写脚本步骤。

定义我们自己的 Bazel RBE 平台
------------------------------------
虽然生成的文件*确实*有一个我们可以使用的平台（例如 `//bazel/rbe/gce_linux/config:platform`），但我们不使用它，因为我们无法轻松地对其进行自定义，且更新镜像时有丢失更改的风险。幸运的是，我们可以指定自己的平台，我们在 `//bazel/platform` 中这样做，这里是我们放置使用 RBE 实例所需的 exec_properties 的地方。

更多详情
------------
https://docs.google.com/document/d/14xMZCKews69SSTfULhE8HDUzT5XvPwZ4CvRufEvcZ74/edit

RBE 指标
-----------
http://go/skia-rbe-metrics
