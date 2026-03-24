---
title: '如何构建 Skia'
linkTitle: '如何构建 Skia'

weight: 20
---

请确保你已先按照
[下载 Skia 的说明](../download)完成操作。

Skia 使用 [GN](https://chromium.googlesource.com/chromium/src/tools/gn/) 来
配置其构建。

## `is_official_build` 与第三方依赖

大多数 Skia 用户应将 `is_official_build=true` 设置为启用，而大多数开发者
应保留其默认值 `false`。

此模式将 Skia 配置为适合发布的方式：优化构建，
无调试符号，使用常规库搜索路径动态链接第三方依赖。

相比之下，面向开发者的默认设置是未优化构建，包含完整的
调试符号，所有第三方依赖从源代码构建并嵌入
到 libskia 中。这是我们进行所有手动和自动测试的方式。

Skia 提供了多项利用第三方库的功能，例如
libpng、libwebp 或 libjpeg-turbo 用于解码图像，ICU 和 sftnly 用于子集化
字体。所有这些第三方依赖都是可选的，可以通过
类似 `skia_use_foo` 的 GN 参数来控制（其中 `foo` 为对应的库名）。

如果启用了 `skia_use_foo`，那么启用 `skia_use_system_foo` 将使用系统路径中
找到的头文件和库来构建和链接 Skia。
`is_official_build=true` 默认启用所有 `skia_use_system_foo`。如果需要，你可以
使用 `extra_cflags` 和 `extra_ldflags` 添加包含路径或库路径。

### third_party 中的 Rust 代码

Skia 有一些用 Rust 编写的第三方依赖。为了
从 Skia 的 GN 构建中编译这些依赖，你需要安装
[Bazel](https://bazel.build/)（或使用 `bazelisk`），它将
下载 Rust 工具链并构建这些依赖。

### Dawn

Skia 使用 [Dawn](https://dawn.googlesource.com/dawn) 作为部分 GPU
后端，并使用 CMake 构建它。要从 GN 构建 Dawn，你
必须安装 `cmake` 3.30 或更高版本。

## 支持和推荐的编译器

虽然 Skia 应该可以用 GCC、MSVC 和其他编译器编译，但 Skia
软件后端中的许多例程被编写为在使用 Clang 编译时运行最快。
如果你依赖软件光栅化 (software rasterization)、图像解码或
色彩空间转换，并且使用 Clang 以外的编译器编译 Skia，你将看到
明显更差的性能。这个选择仅仅是优先级问题；
非 Clang 编译器本身没有根本性的问题。
因此，如果这对你来说是一个严重的问题，请在邮件列表上告诉我们。

Skia 使用 C++20 语言特性（使用 `-std=c++20` 标志编译），
因此需要兼容 C++20 的编译器。Clang 21 实现了大部分
C++20 标准的特性。缺少 C++20 支持的旧编译器可能会
产生不明显的编译错误。你可以配置构建以使用
特定的可执行文件进行 `cc` 和 `cxx` 调用，例如
`--args='cc="clang" cxx="clang++"'` GN 构建参数，如
[快速开始](#quickstart)所示。这在不需要修改
机器默认编译器工具链的情况下构建 Skia 时很有用。

如果你没有在 gn 参数中指定 `cc` 和 `cxx`，Skia 将默认使用
`cc` 和 `c++`。在许多平台上这通常默认是 GCC，而非 Clang。

## 快速开始

运行 `gn gen` 来生成构建文件。作为 `gn gen` 的参数，传入一个
构建目录名称，以及可选的 `--args=` 来配置构建类型。

要在名为 `out/Static` 的构建目录中将 Skia 构建为静态库：

```
bin/gn gen out/Static --args='is_official_build=true'
```

要在名为 `out/Shared` 的构建目录中将 Skia 构建为共享库（DLL）：

```
bin/gn gen out/Shared --args='is_official_build=true is_component_build=true'
```

如果你发现没有 `bin/gn`，请确保你已运行：

```
python3 tools/git-sync-deps
```

要查看可用的构建参数列表，请查看 `gn/skia.gni`，或运行：

```
bin/gn args out/Debug --list
```

GN 允许多个构建文件夹共存；每个构建可以根据需要单独配置。例如：

```
bin/gn gen out/Debug
bin/gn gen out/Release  --args='is_debug=false'
bin/gn gen out/Clang    --args='cc="clang" cxx="clang++"'
bin/gn gen out/Cached   --args='cc_wrapper="ccache"'
bin/gn gen out/RTTI     --args='extra_cflags_cc=["-frtti"]'
```

生成构建文件后，运行 Ninja 编译和链接所有 Skia：

```
ninja -C out/Static
```

要避免构建所有内容，请在 ninja 命令后包含目标。例如：

```
ninja -C out/Debug skia
ninja -C out/Debug viewer dm
```

并非所有目标都适用于所有的构建参数集。要查看给定构建目录的所有可用目标列表，请运行：

```
gn ls out/Debug
```

如果缺少某些头文件，请安装相应的依赖：

```
tools/install_dependencies.sh
```

要拉取新更改并重新构建：

```
git pull
python3 tools/git-sync-deps
ninja -C out/Static
```

## Android

要为 Android 构建 Skia，你需要最新版本的
[Java](https://www.oracle.com/java/technologies/downloads/) 和最新的
[Android NDK](https://developer.android.com/ndk/index.html)。

如果你没有 NDK 并且可以访问 CIPD，你可以使用以下
命令获取我们的构建机器人使用的 NDK：

```
./bin/fetch-sk
./bin/sk asset download android_ndk_linux ~/ndk        # on Linux
./bin/sk asset download android_ndk_darwin ~/ndk       # on Mac
./bin/sk.exe asset download android_ndk_windows C:/ndk # on Windows
```

生成 GN 构建文件时，传入你的 `ndk` 路径和
所需的 `target_cpu`：

```
bin/gn gen out/arm   --args='ndk="~/ndk" target_cpu="arm"'
bin/gn gen out/arm64 --args='ndk="~/ndk" target_cpu="arm64"'
bin/gn gen out/x64   --args='ndk="~/ndk" target_cpu="x64"'
bin/gn gen out/x86   --args='ndk="~/ndk" target_cpu="x86"'
```

其他参数如 `is_debug` 和 `is_component_build` 继续有效。
调整 `ndk_api` 可以让你访问更新的 Android 功能，如 Vulkan。

要在 Android 设备上测试，将二进制文件和 `resources` 推送过去，然后正常运行。你可能会发现 `bin/droid` 很方便。

```
ninja -C out/arm64
adb push out/arm64/dm /data/local/tmp
adb push resources /data/local/tmp
adb shell "cd /data/local/tmp; ./dm --src gm --config gl"
```

## ChromeOS

要为 ARM ChromeOS 设备交叉编译 Skia，需要以下条件：

- Clang 4 或更新版本
- armhf sysroot
- ARM chromebook 上的 (E)GL 库文件用于链接。

要为 x86 ChromeOS 设备编译 Skia，只需要 Clang 和库
文件。

如果你可以访问 CIPD，你可以按如下方式获取所有这些：

```
./bin/sk asset download clang_linux /opt/clang
./bin/sk asset download armhf_sysroot /opt/armhf_sysroot
./bin/sk asset download chromebook_arm_gles /opt/chromebook_arm_gles
./bin/sk asset download chromebook_x86_64_gles /opt/chromebook_x86_64_gles
```

如果你没有使用这些资源的授权，请参阅以下 README.md 文件：
[armhf_sysroot](https://skia.googlesource.com/skia/+/main/infra/bots/assets/armhf_sysroot/README.md)、
[chromebook_arm_gles](https://skia.googlesource.com/skia/+/main/infra/bots/assets/chromebook_arm_gles/README.md)
和
[chromebook_x86_64_gles](https://skia.googlesource.com/skia/+/main/infra/bots/assets/chromebook_x86_64_gles/README.md)
以获取创建这些资源的说明。

一旦这些文件就位，生成类似以下的 GN 参数：

```
#ARM
cc= "/opt/clang/bin/clang"
cxx = "/opt/clang/bin/clang++"

extra_asmflags = [
    "--target=armv7a-linux-gnueabihf",
    "--sysroot=/opt/armhf_sysroot/",
    "-march=armv7-a",
    "-mfpu=neon",
    "-mthumb",
]
extra_cflags=[
    "--target=armv7a-linux-gnueabihf",
    "--sysroot=/opt/armhf_sysroot",
    "-I/opt/chromebook_arm_gles/include",
    "-I/opt/armhf_sysroot/include/",
    "-I/opt/armhf_sysroot/include/c++/4.8.4/",
    "-I/opt/armhf_sysroot/include/c++/4.8.4/arm-linux-gnueabihf/",
    "-DMESA_EGL_NO_X11_HEADERS",
    "-funwind-tables",
]
extra_ldflags=[
    "--sysroot=/opt/armhf_sysroot",
    "-B/opt/armhf_sysroot/bin",
    "-B/opt/armhf_sysroot/gcc-cross",
    "-L/opt/armhf_sysroot/gcc-cross",
    "-L/opt/armhf_sysroot/lib",
    "-L/opt/chromebook_arm_gles/lib",
    "--target=armv7a-linux-gnueabihf",
]
target_cpu="arm"
skia_use_fontconfig = false
skia_use_system_freetype2 = false
skia_use_egl = true


# x86_64
cc= "/opt/clang/bin/clang"
cxx = "/opt/clang/bin/clang++"
extra_cflags=[
    "-I/opt/clang/include/c++/v1/",
    "-I/opt/chromebook_x86_64_gles/include",
    "-DMESA_EGL_NO_X11_HEADERS",
    "-DEGL_NO_IMAGE_EXTERNAL",
]
extra_ldflags=[
    "-stdlib=libc++",
    "-fuse-ld=lld",
    "-L/opt/chromebook_x86_64_gles/lib",
]
target_cpu="x64"
skia_use_fontconfig = false
skia_use_system_freetype2 = false
skia_use_egl = true
```

像往常一样使用 ninja 编译 dm（或你选择的其他可执行文件）。

通过 ssh 将二进制文件推送到 chromebook 上，并使用 gles GPU 配置
[正常运行 dm](/docs/dev/testing/tests)。

大多数 chromebook 默认将其主目录分区标记为
noexec。为避免"权限被拒绝"错误，记得运行类似以下的命令：

```
sudo mount -i -o remount,exec /home/chronos
```

## Mac

Mac 用户可能想要将 `--ide=xcode` 传递给 `bin/gn gen` 来生成 Xcode
项目。

Mac GN 构建默认假定使用 Intel CPU。如果你要为 Apple
Silicon（M1 及更新版本）构建，请添加 gn 参数设置 `target_cpu="arm64"`：

```
bin/gn gen out/AppleSilicon --args='target_cpu="arm64"'
```

Google 员工应参阅 [go/skia-corp-xcode](http://go/skia-corp-xcode) 了解
在公司机器上设置 Xcode 的说明。

### Python

Apple 提供的 Python 版本落后了几个版本，
且已知与我们的构建系统交互不佳。我们建议
从 https://www.python.org/downloads/ 安装最新的 Python 官方版本。然后运行
"Applications/Python 3.11/Install Certificates.command"。

## iOS

运行 GN 来生成构建文件。设置 `target_os="ios"` 以构建 iOS 版本。
默认为 `target_cpu="arm64"`。要使用 iOS 模拟器，设置
`ios_use_simulator=true` 并将 `target_cpu` 设置为你 Mac 的架构。
在 Intel Mac 上，单独设置 `target_cpu="x64"` 也将面向 iOS
模拟器。

```
bin/gn gen out/ios64  --args='target_os="ios"'
bin/gn gen out/ios32  --args='target_os="ios" target_cpu="arm"'
bin/gn gen out/iossim-apple --args='target_os="ios" target_cpu="arm64" ios_use_simulator=true'
bin/gn gen out/iossim-intel --args='target_os="ios" target_cpu="x64"'
```

默认情况下，这也会打包（对于非模拟器设备还会签名）iOS 测试二进制文件。
如果你希望跳过签名（例如仅测试编译），可以通过
将 `skia_ios_use_signing` 设置为 `false` 来禁用它。

签名时，构建默认使用 Google 签名身份和配置文件。
要使用不同的身份和配置文件，
将 GN 参数 `skia_ios_identity` 设置为匹配你的代码签名身份，
`skia_ios_profile` 设置为你的配置文件名称，例如

```
skia_ios_identity=".*Jane Doe.*"
skia_ios_profile="iPad Profile"`
```

可以通过在命令行输入 `security find-identity` 找到身份列表。
配置文件的名称应该可以在 Apple 开发者网站上找到。或者，你可以在 Finder 中
检查已安装的配置文件，
路径为 `~/Library/MobileDevice/Provisioning Profiles`，选择 `.mobileprovision` 文件
并按空格键。`skia_ios_profile` 的值可以是
该文件顶部或开发者网站上给出的字符串，也可以是
该文件的绝对路径。

如果你发现自己缺少 Google 签名身份或配置文件，
你需要阅读 go/appledev 和 go/ios-signing。

对于已签名的包，`ios-deploy` 使安装和在设备上运行它们
变得简单：

```
ios-deploy -b out/Debug/dm.app -d --args "--match foo"
```

如果你希望通过 Xcode 部署，可以通过将 `--ide=xcode` 传递给
`bin/gn gen` 来生成项目。如果你使用的是 Xcode 10 或更高版本，你可能需要进入
`Project Settings...` 并验证 `Build System:` 设置为
`Legacy Build System`。

部署到操作系统版本低于当前 SDK 的设备可以通过
设置 `ios_min_target` 参数来完成：

```
ios_min_target = "<major>.<minor>"
```

其中 `<major>.<minor>` 是设备上的 iOS 版本，例如 12.0 或 11.4。

## Windows

Skia 可以在 Windows 上使用 Visual Studio 2017 或 2019 构建。如果 GN 无法
找到这两者之一，它将打印错误消息。在这种情况下，你可以
通过 `win_vc` 将 `VC` 路径传递给 GN。

Skia 可以使用免费的
[Build Tools for Visual Studio 2017 或 2019](https://www.visualstudio.com/downloads/#build-tools-for-visual-studio-2019) 编译。

构建机器人使用打包的 2019 工具链，Google 员工可以这样下载：

```
./bin/sk.exe asset download win_toolchain C:/toolchain
```

然后你可以通过设置 GN 参数将 VC 和 SDK 路径传递给 GN：

```
win_vc = "C:\toolchain\VC"
win_sdk = "C:\toolchain\win_sdk"
```

此工具链是我们支持 32 位构建的唯一方式，同时需要设置
`target_cpu="x86"`。

Skia 构建假设 PATHEXT 环境变量包含 ".EXE"。

### **强烈推荐**：使用 clang-cl 构建

Skia 使用的生成代码只在使用 clang 构建 Skia 时才会被优化。
其他编译器会使用通用的未优化代码。

设置 `cc` 和 `cxx` gn 参数 _不足以_ 使用 clang-cl 构建。
这些变量在 Windows 上会被忽略。相反，将变量 `clang_win` 设置为
你的 LLVM 安装目录。如果你在默认位置安装了从
[这里](https://releases.llvm.org/download.html 'LLVM Download')下载的预构建 LLVM，
那就是：

```
clang_win = "C:\Program Files\LLVM"
```

请遵循标准 Windows 路径规范，而非 MinGW 约定（例如
`C:\Program Files\LLVM` 而不是 ~~`/c/Program Files/LLVM`~~）。

如果你将使用 Clang 以外的编译器编译程序的其余部分，
还需要添加此 GN 参数：

```
is_trivial_abi = false
```

### Visual Studio 解决方案

如果你使用 Visual Studio，你可能想将 `--ide=vs` 传递给 `bin/gn gen` 来
生成 `all.sln`。该解决方案将存在于特定配置的 GN 目录中，
并且只会构建/运行该配置。

如果你想要一个支持多个 GN 配置的 Visual Studio 解决方案，
有一个辅助脚本。它要求你所有的 GN 目录都在
`out` 目录内。首先，像往常一样创建所有 GN 配置。在
为每个配置运行 `bin/gn gen` 时传递 `--ide=vs`。然后：

```
python3 gn/gn_meta_sln.py
```

这将创建一个新的专用输出目录和解决方案文件
`out/sln/skia.sln`。它为每个 GN 配置有一个解决方案配置，
并支持构建和运行其中任何一个。它还根据
所选解决方案配置的预处理器定义调整非活动代码块的语法高亮。

## Windows ARM64

[Windows 10 on ARM](https://docs.microsoft.com/en-us/windows/arm/) 有早期的实验性支持。这
目前需要（较新版本的）MSVC，以及 Visual Studio Installer 中的
`Visual C++ compilers and libraries for ARM64` 独立组件。
对于 Google 员工，win_toolchain 资源包含 ARM64 编译器。

要使用该工具链，将 `target_cpu` GN 参数设置为 `"arm64"`。注意
Windows 10 on ARM 不支持 OpenGL，因此 Skia 的 GL 后端是桩实现，
不会工作。ANGLE 是受支持的：

```
bin/gn gen out/win-arm64 --args='target_cpu="arm64" skia_use_angle=true'
```

这将生成一个可以在 DM 中使用软件或 ANGLE 后端的 Skia 构建。
Viewer 只能在使用 `--backend angle` 启动时工作，因为
软件后端尝试使用 OpenGL 来显示窗口内容。

## CMake

我们添加了一个 GN 到 CMake 的转换器，主要用于喜欢 CMake
项目描述的 IDE。这不适用于开发以外的任何目的。

```
bin/gn gen out/config --ide=json --json-ide-script=../../gn/gn_to_cmake.py
```
