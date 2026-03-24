# run_gn_to_bp - GN 到 Blueprint 转换驱动

## 概述

运行 GN 到 Android Blueprint 的转换工具，为 Android 构建系统（Soong/Blueprint）生成 Skia 的构建文件。

## 目录结构

```
run_gn_to_bp/
├── run_gn_to_bp.go   # 主程序
└── BUILD.bazel       # Bazel 构建文件
```

## 依赖关系

- GN 构建系统
- Android 构建系统知识

## 相关文档与参考

- [Android Soong 构建系统](https://source.android.com/docs/setup/build)
