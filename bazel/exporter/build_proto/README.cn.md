此目录包含为 Bazel cquery 结果协议缓冲区 (Protocol Buffers) 生成的 Go 包装器，这些协议缓冲区定义在 https://github.com/bazelbuild/bazel/tree/master/src/main/protobuf 中。

曾尝试使用 [go_proto_library](https://github.com/bazelbuild/rules_go/blob/master/proto/core.rst#go-proto-library) 在构建时生成此代码，使用 embedded_tools 依赖作为源，但始终未能成功。原因似乎是 Bazel 源代码中的 protobuf 定义了同名的消息（具体来说是 "Target"），这导致了构建冲突。下面的命令使用不同的包名生成两个 Go 类以避免此冲突——这与 Bazel 生成的 Java 包装器的做法相同。

它们是这样生成的：

```bash
BAZEL_DIR=/path/to/bazel/source
DST_DIR=${PWD}/bazel/exporter/build_proto
GO_PACKAGE=go.skia.org/skia/bazel/exporter/build_proto
GO_GEN_CODE_ROOT=${DST_DIR}/go.skia.org/skia/bazel/exporter/build_proto

protoc \
  --proto_path=${BAZEL_DIR} \
  --go_out=${DST_DIR} \
  --go_opt=Msrc/main/protobuf/build.proto=${GO_PACKAGE}/build \
  --go_opt=Msrc/main/protobuf/analysis_v2.proto=${GO_PACKAGE}/analysis_v2 \
  ${SRC_DIR}/analysis_v2.proto ${SRC_DIR}/build.proto
```

上述调用将生成的代码写入 `${DST_DIR}/go.skia.org/skia/bazel/exporter/build_proto`，然后将其移动到 `${DST_DIR}/build` 和 `${DST_DIR}/build` 中。
