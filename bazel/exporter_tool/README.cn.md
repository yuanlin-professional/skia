# Bazel 项目导出器 (Bazel Project Exporter)

Skia 的权威构建系统正在迁移到 Bazel。对于需要使用其他构建系统的用户，此工具可以将 Bazel 构建目标的一个子集导出到其他构建系统。

# Bazel 转 CMake

**注意：** 这不适用于开发以外的任何目的。

在 Skia 工作区的根目录下执行：

```sh
make -C bazel generate_cmake
```

这将生成一个 `CMakeLists.txt` 文件，其中包含一个有效的 CMake 项目，该项目具有构建 Bazel //:core 目标及其所有依赖目标所涵盖的产物的构建目标。

## 当前限制

* 不支持外部依赖。
* 仅支持 `//:core` 规则。其他规则*可能*有效。

# Bazel 转 *.gni

通过在 Skia 工作区的根目录下运行以下命令来生成预定义的 `*.gni` 文件：

```sh
make -C bazel generate_gni
```

这将更新位于 `//gn` 中的 `*.gni` 文件，这些文件包含 GN 构建所需的文件列表。导出器工具中硬编码了要导出的 Bazel 规则，以及它们应映射到哪个 GNI 文件和文件列表。随着 Bazel 项目规则的重构，可能需要更新导出器工具以反映这些变更。

## Bazel 规则到 GNI 文件列表的映射

GNI 导出过程与平台无关，在所有平台上生成相同文件列表的 GNI 文件。让我们用一个虚构的示例程序来描述映射过程：

在 `//include/example/BUILD.bazel` 中存在一个定义头文件的规则：

```bazel
filegroup(
    name = "public_hdrs",
    srcs = [ "example.h" ],
)
```

**注意：** Bazel 的**可见性规则会被忽略**。导出器工具可以导出私有文件。

在 `//src/example/BUILD.bazel` 中定义示例源文件的规则：

```bazel
filegroup(
    name = "example_srcs",
    srcs = [
        "main.cpp",
        "draw.cpp",
    ] + select({
        ":is_windows": [ "draw_win.cpp" ]
    })
)
```

导出器工具中的规则 → 文件列表映射如下所示：

```go
var gniExportDescs = []exporter.GNIExportDesc{
    // ... Other GNI definitions.
    {GNI: "gn/example.gni", Vars: []exporter.GNIFileListExportDesc{
		{Var: "example_headers",
			Rules: []string{"//include/example:public_hdrs"}},
		{Var: "example_sources",
			Rules: []string{"//src/example:example_srcs"}}},
	},
    // ... Other GNI definitions.
}
```

当导出器工具运行时，它将在 `//gn/example.gni` 中创建以下定义：

```gn
# DO NOT EDIT: This is a generated file.

_src = get_path_info("../src", "abspath")
_include = get_path_info("../include", "abspath")

example_headers = [ "$_include/example/example.h" ]

example_sources = [
    "$_src/example/main.cpp",
    "$_src/example/draw.cpp",
    "$_src/example/draw_win.cpp",
]
```

**注意：** 导出器始终包含所有 `select()` 调用的内容。这可能是期望的行为——如果不是，解决方案是将 select 中的文件提取到一个新的 Bazel filegroup 中。例如：

```bazel
filegroup(
    name = "win_example_srcs",
    srcs = [ "draw_win.cpp" ],
)

filegroup(
    name = "example_srcs",
    srcs = [
        "main.cpp",
        "draw.cpp",
        srcs = select({
            ":is_windows": [ ":win_example_srcs" ]
        }).
    ],
)
```

或者另一种方式：

```bazel
filegroup(
    name = "win_example_srcs",
    srcs = select({
        ":is_windows": [ "draw_win.cpp" ]
    }).
)

filegroup(
    name = "example_srcs",
    srcs = [
        "main.cpp",
        "draw.cpp",
        ":win_example_srcs", # Not recursively followed.
    ],
)
```

在每种情况下，被引用的规则（`win_example_srcs`）不会被递归跟踪，**只有直接列在规则中的文件才会被导出**到 GNI 文件中。
