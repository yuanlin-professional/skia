
---
title: "MSAN、ASAN 和 TSAN"
linkTitle: "MSAN、ASAN 和 TSAN"

---


*使用内存、地址和线程检测器 (sanitizers) 测试 Skia。*

使用最新版本的 Clang 可以使用 ASAN、UBSAN 或 TSAN 编译 Skia。

- UBSAN 可在 Linux、Mac、Android 和 Windows 上工作，但某些检查是特定于平台的。
- ASAN 可在 Linux、Mac、Android 和 Windows 上工作。
- TSAN 可在 Linux 和 Mac 上工作。
- MSAN 可在 Linux 上工作[1]。

我们发现使用 libc++ 测试检测器构建比使用系统提供的 C++ 标准库（通常是 libstdc++）能发现更多问题。libc++ 主动与检测器集成以辅助其分析。我们在 Linux 工具链的 /lib 中附带了一份 libc++ 的副本。

[1]要使用 MSAN 编译和运行，需要一个经 MSAN 检测的 libc++ 版本。最简单的方法是运行以下 2 个步骤之一来构建/下载最新版本的 Clang 和检测过的 libc++，位于 /msan。

下载 Clang 二进制文件（仅限 Google 员工）
------------------------------------------
这需要 gsutil，它是 [gcloud sdk](https://cloud.google.com/sdk/downloads) 的一部分。

<!--?prettify lang=sh?-->

    gcloud auth application-default login
    CLANGDIR="${HOME}/clang"
    ./bin/sk asset download clang_linux $CLANGDIR

从源代码构建 Clang 二进制文件（其他用户）
---------------------------

<!--?prettify lang=sh?-->

    CLANGDIR="${HOME}/clang"

    python3 tools/git-sync-deps
    CC= CXX= infra/bots/assets/clang_linux/create.py -t "$CLANGDIR"

配置和编译使用 MSAN 的 Skia
------------------------------------

<!--?prettify lang=sh?-->

    CLANGDIR="${HOME}/clang"
    mkdir -p out/msan
    cat > out/msan/args.gn <<- EOF
        cc = "${CLANGDIR}/bin/clang"
        cxx = "${CLANGDIR}/bin/clang++"
        extra_cflags = [ "-B${CLANGDIR}/bin" ]
        extra_ldflags = [
            "-B${CLANGDIR}/bin",
            "-fuse-ld=lld",
            "-L${CLANGDIR}/msan",
            "-Wl,-rpath,${CLANGDIR}/msan" ]
        sanitize = "MSAN"
        skia_use_fontconfig = false
    EOF
    python3 tools/git-sync-deps
    bin/gn gen out/msan
    ninja -C out/msan

配置和编译使用 ASAN 的 Skia
------------------------------------

<!--?prettify lang=sh?-->

    CLANGDIR="${HOME}/clang"
    mkdir -p out/asan
    cat > out/asan/args.gn <<- EOF
        cc = "${CLANGDIR}/bin/clang"
        cxx = "${CLANGDIR}/bin/clang++"
        sanitize = "ASAN"
        extra_ldflags = [ "-fuse-ld=lld", "-Wl,-rpath,${CLANGDIR}/lib/x86_64-unknown-linux-gnu" ]
    EOF
    python3 tools/git-sync-deps
    bin/gn gen out/asan
    ninja -C out/asan

配置和编译使用 TSAN 的 Skia
------------------------------------

<!--?prettify lang=sh?-->

    CLANGDIR="${HOME}/clang"
    mkdir -p out/tsan
    cat > out/tsan/args.gn <<- EOF
        cc = "${CLANGDIR}/bin/clang"
        cxx = "${CLANGDIR}/bin/clang++"
        sanitize = "TSAN"
        is_debug = false
        extra_ldflags = [ "-Wl,-rpath,${CLANGDIR}/lib" ]
    EOF
    python3 tools/git-sync-deps
    bin/gn gen out/tsan
    ninja -C out/tsan

