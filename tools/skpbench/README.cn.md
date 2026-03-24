# skpbench

skpbench 是一个基准测试工具，用于在 Android 设备上回放 skp 或 mksp 文件。它通过控制时钟速度和停止所有其他可能造成干扰的进程来实现更低的帧率方差。

## 构建

skpbench 由 skpbench 二进制文件和 skpbench.py 组成，前者必须为你打算运行的手机构建，后者运行在通过 ADB 连接手机的主机上，是入口点。

Android 版 Skia 的构建说明位于 https://skia.org/user/build#android，此处转载。

下载 Android NDK

```
./bin/fetch-sk
./bin/sk asset download android_ndk_linux ~/ndk
```

完成一次性设置后，为你的目标 CPU 构建 skpbench（此处假设为 Pixel 3 的 arm64）

```
bin/gn gen out/arm64 --args='ndk="~/ndk" target_cpu="arm64" is_debug=false'
ninja -C out/arm64 skpbench
```

## 在已连接的设备上对 SKP 进行基准测试

首先，将构建好的 skpbench 二进制文件和示例 skp 文件复制到设备上。
（或使用下面章节中的说明拉取 skp 语料库）

```
adb push out/arm64/skpbench /data/local/tmp
adb push /home/nifong/Downloads/foo.skp /data/local/tmp/skps/
```

运行 skpbench.py

```
python tools/skpbench/skpbench.py \
  --adb \
  --config gles \
  /data/local/tmp/skpbench \
  /data/local/tmp/skps/foo.skp
```

`--adb` 指定应使用 adb 连接唯一已连接的设备并在其上运行 skpbench。
`--force` 是必要的，因为我们尚未针对 Pixel 3 配置生命体征监控。
`--config gles` 指定使用 Open GL ES 作为后端 GPU 配置。

通过 `python tools/skpbench/skpbench.py --help` 可以查看参数的更多文档

输出格式如下
```
   accum    median       max       min   stddev  samples  sample_ms  clock  metric  config    bench
  0.1834    0.1832    0.1897    0.1707    1.59%      101         50  cpu    ms      gles      foo.skp
```

`accum` 是绘制所有帧所用的时间除以帧数。
`metric` 指定单位为 ms（毫秒/帧）

## 生产环境

skpbench 作为 Gerrit 的 tryjob 运行，将结果上传到 perf.skia.org。
其中一个此类任务名称为 `Perf-Android-Clang-Pixel4XL-GPU-Adreno640-arm64-Release-All-Android_Skpbench`

可以通过以下或类似查询获取性能结果。
  extra_config = Android_Skpbench
  sub_result = accum_cpu_ms

性能查询示例
https://perf.skia.org/e/?queries=extra_config%3DAndroid_Skpbench%26sub_result%3Daccum_cpu_ms
