这里包含从源代码构建的、用于 Linux 主机的 Clang 编译器及其他工具（例如 clang-tidy 和 IWYU）。

此资产同时用于我们的 GN 构建和 Bazel 构建。使用 `sk` 工具更新此资产后，GN 构建将自动更新。

手动更新 Bazel 构建的步骤：
  1) 从 CIPD 下载最新版本的 .zip 文件。
     <https://chrome-infra-packages.appspot.com/p/skia/bots/clang_linux>
  2) 将文件名更改为 clang_linux_amd64_vNN.zip，其中 NN 是 `VERSION` 文件中的新版本号。
  3) 上传到 GCS 镜像存储桶
     `go run ./bazel/gcs_mirror/gcs_mirror.go --sha256 <hash> --file /path/to/clang_linux_amd64_vNN.zip`
  4) 更新 `//toolchain/download_linux_amd64_toolchain.bzl` 中的 sha256。
  5) 在本地使用 `make -C bazel known_good_builds` 进行测试。
     您可能需要更新生成的 BUILD.bazel 文件以适应重新定位/新增的文件，
     以及更新 `//toolchain/linux_amd64_toolchain_config.bzl` 以正确使用它们。
