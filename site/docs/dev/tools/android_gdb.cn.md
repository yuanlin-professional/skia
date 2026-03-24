
---
title: "在 Android 上调试 DM"
linkTitle: "在 Android 上调试 DM"

---

默认情况下，我们不会使用完整符号进行 Android 构建。假设你需要的不仅仅是调用栈，请在你的 GN 参数中添加以下内容：

~~~
extra_cflags = [ "-g" ]
~~~

构建时，你需要已经构建了 `gdbserver` 目标。可以构建所有内容，或者至少同时构建 `dm` 和 `gdbserver`：

<!--?prettify lang=sh?-->

    ninja -C out/android dm gdbserver

此时，Android gdb 脚本应该可以工作了。尝试运行：

<!--?prettify lang=sh?-->

    platform_tools/android/bin/android_gdb_native -C out/android dm -i /data/local/tmp/resources <args>

你将进入一个连接到设备上 dm 的命令行 gdb 会话。这就完成了，但你可以做得更好。从这里开始，我假设你使用 VS Code。我强烈怀疑这可以适配到其他 IDE 的 GDB 集成中。

VS Code 自带 lldb 支持，但此工作流程需要一个 GDB 扩展。在扩展浏览器中搜索 'Native Debug' 并安装它，如果你不确定的话，你需要的来自 https://github.com/WebFreak001/code-debug。

在你的 VS Code 项目的 `launch.json` 中，添加一个类似以下的条目。你需要将 <NDK_BUNDLE> 替换为你的 NDK bundle 路径（即 $ANDROID_NDK_HOME）：

~~~
{
    "name": "Android GDB",
    "type": "gdb",
    "request": "attach",
    "target": ":5039",
    "remote": true,
    "gdbpath": "<NDK bundle>/prebuilt/linux-x86_64/bin/gdb",
    "executable": "out/android/android_gdb_tmp/dm",
    "cwd": "${workspaceRoot}",
    "autorun": [ "break main" ]
}
~~~

与其运行 `android_gdb_native`，不如在同一目录中（使用相同的参数）运行 `android_gdbserver`。这将执行所有相同的部署，并在设备上运行 `gdbserver`，但不会在你的主机上启动命令行 gdb。

现在，只需在 VS Code 中"开始调试"（如果你有多个配置，选择新的配置）。VSC 托管的 gdb 将连接到 gdbserver，你将获得一个交互式调试器，可以在源代码窗口中设置断点，有监视、局部变量和调用栈的面板等。享受吧：

![VS Code Debugger Screenshot](../android_gdb.png)
