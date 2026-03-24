# push_to_android.py - Android 设备文件推送

> 源文件: `gn/push_to_android.py`

## 概述
将编译好的可执行文件推送到 Android 设备的 `/data/local/tmp/` 目录，设置执行权限，并创建时间戳文件通知 GN/Ninja 推送成功。

## 架构位置
Skia Android 构建部署工具。

## 内部实现细节
使用 `adb push` 传输文件，`adb shell chmod +x` 设置权限。支持通过序列号指定设备或自动选择。

## 相关文件
- GN Android 构建目标定义
