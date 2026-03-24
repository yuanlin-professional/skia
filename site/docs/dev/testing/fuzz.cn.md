---
title: '模糊测试 (Fuzzing)'
linkTitle: '模糊测试 (Fuzzing)'
---

## 使用 `fuzz` 复现

我们假设你可以[构建 Skia](/docs/user/build)。许多模糊测试用例只有在使用 ASAN 或 MSAN 构建时才能复现；有关更多详细信息，请参阅[相关说明](../xsan)。

构建时，你应该在 BUILD.gn 中添加以下参数，以减少对特定机器和平台的依赖：

    skia_use_fontconfig=false
    skia_use_freetype=true
    skia_use_system_freetype2=false
    skia_use_wuffs=true
    skia_enable_skottie=true
    skia_enable_fontmgr_custom_directory=false
    skia_enable_fontmgr_custom_embedded=false
    skia_enable_fontmgr_custom_empty=true

从 ClusterFuzz 或 oss-fuzz 下载的模糊测试用例，只需运行类似以下命令即可复现：

    out/ASAN/fuzz -b /path/to/downloaded/testcase

fuzz 二进制文件会尽力根据测试用例的名称猜测类型/名称。也支持手动提供类型和名称，例如：

    out/ASAN/fuzz -t filter_fuzz -b /path/to/downloaded/testcase
    out/ASAN/fuzz -t api -n RasterN32Canvas -b /path/to/downloaded/testcase

要列出所有支持的类型和名称，运行以下命令：

    out/ASAN/fuzz --help  # 将列出所有类型
    out/ASAN/fuzz -t api  # 将列出所有名称

如果崩溃没有出现，尝试添加 --loops 标志：

    out/ASAN/fuzz -b /path/to/downloaded/testcase --loops <times-to-run>

## 使用 libfuzzer 编写模糊测试器

libfuzzer 是编写新模糊测试器的简便方法，也是我们在 oss-fuzz 上运行它们的方式。你的模糊测试器入口点应实现以下 API：

    extern "C" int LLVMFuzzerTestOneInput(const uint8_t*, size_t);

首先安装 Clang 和 libfuzzer，例如：

    sudo apt install clang-10 libc++-10-dev libfuzzer-10-dev

现在你应该可以使用 Clang 的 `-fsanitize=fuzzer` 了。

设置 GN 参数以使用 libfuzzer：

    cc = "clang-10"
    cxx = "clang++-10"
    sanitize = "fuzzer"
    extra_cflags = [ "-DSK_BUILD_FOR_LIBFUZZER", # 启用模糊测试器约束（见下文）
                     "-O1"  # 或你想要的任何优化级别。
                   ]
    ...

构建 Skia 和你的模糊测试器入口点：

    ninja -C out/libfuzzer skia
    clang++-10 -I. -O1 -fsanitize=fuzzer fuzz/oss_fuzz/whatever.cpp out/libfuzzer/libskia.a

运行你的新模糊测试器二进制文件：

    ./a.out

## 模糊测试定义

有一些定义可以帮助引导模糊测试器更高效（例如避免 OOM、避免不必要的慢速代码）。

    // 使用 afl-fuzz 进行模糊测试时必需，以防止 OOM 产生噪声。
    SK_BUILD_FOR_AFL_FUZZ

    // 使用 libfuzzer 进行模糊测试时必需
    SK_BUILD_FOR_LIBFUZZER

    // 此定义添加了保护措施，当我们认为某些代码路径会花费很长时间或
    // 使用大量内存时会中止。当设置了上述任一定义时，此定义默认生效。
    SK_BUILD_FOR_FUZZER

## OSS-Fuzz
我们的模糊测试器运行的基础设施称为 [OSS-Fuzz](https://google.github.io/oss-fuzz/)（[GitHub](https://github.com/google/oss-fuzz/tree/master)）。有一个自动化系统会重新构建 Skia 和某些模糊测试器，然后运行这些模糊测试器，[提交错误报告](https://issues.oss-fuzz.com/issues?q=status:open%20componentid:1638179%20project:skia)。

Skia 特定的模糊测试器构建代码位于 [oss-fuzz/projects/skia](https://github.com/google/oss-fuzz/tree/master/projects/skia)，构建状态可在[此处](https://oss-fuzz-build-logs.storage.googleapis.com/index.html#skia)查看。当一切运行正常时，被模糊测试的 Skia 版本应该每天更新约 2 次。

更多详细信息请参阅 <https://skia.googlesource.com/skia/+/refs/heads/main/fuzz/README.md>。
