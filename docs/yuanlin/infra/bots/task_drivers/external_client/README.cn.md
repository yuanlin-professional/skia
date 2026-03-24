# external_client - 外部客户端构建测试驱动

## 概述

测试外部客户端（如 Chromium、Android 等）能否成功集成和使用 Skia。模拟外部项目依赖 Skia 的构建场景。

## 目录结构

```
external_client/
├── external_client.go               # 主程序
├── bazel_build_with_docker.sh       # Docker 内 Bazel 构建脚本
└── BUILD.bazel                      # Bazel 构建文件
```

## 依赖关系

- Docker 环境
- Bazel 构建系统

## 相关文档与参考

- 父目录 `task_drivers/` 说明
