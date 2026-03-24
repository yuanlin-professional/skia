此文件夹用于存放外部（例如第三方）依赖的 `BUILD.bazel` 文件。

如果某个依赖支持 Bazel，我们应该使用其提供的规则；但如果该依赖不支持 Bazel，我们需要在子目录中创建自己的规则。

我们通常从源代码编译第三方依赖。如果是这样，我们会克隆仓库并使用给定的 BUILD.bazel 文件来构建它。这在 `WORKSPACE.bazel` 中指定（例如 `new_local_repository` 或 `new_git_repository`），我们使用类似 `@freetype` 或 `@libpng` 的标签来引用这些目标。

有些第三方依赖我们只链接其预构建版本。对于这些，我们不涉及 WORKSPACE.bazel，而是直接链接它们，例如 `//bazel/external/fontconfig`。

注意事项
-----

避免使用 strip_include_prefix
==========================
[strip_include_prefix](https://docs.bazel.build/versions/main/be/c-cpp.html#cc_library.strip_include_prefix) 会导致库的头文件路径通过 `-I` 添加到编译器的包含搜索路径中，这意味着 Clang 会将其视为 Skia 自身的文件。这意味着如果这些头文件存在 Clang 诊断警告能捕获的问题（例如缺少 `override`），我们将看到这些警告并且构建将失败。

通常，我们不希望修复第三方代码的警告，因此请使用 `includes` 代替 `strip_include_prefix`。这更加便捷，因为它可以让我们从多个位置公开头文件（例如 `freetype` 的 API 在 `includes` 中，自定义头文件在 `builds` 中），并且通过 `-isystem` 将这些路径添加到搜索路径中。Clang 会忽略这些"系统"头文件中的警告，这意味着我们的警告将集中在 Skia 代码库本身。
