# gcc - GCC 编译 Docker 配置

## 概述

`gcc/` 目录包含使用 GCC 编译器构建 Skia 的 Docker 配置。这些 Docker 镜像用于测试 Skia 在默认 Bazel 工具链（GCC）下的编译兼容性。

镜像重建后，应使用最终镜像的 sha256 哈希值来引用它。

## 目录结构

```
gcc/
├── Debian11/       # Debian 11 GCC 环境
│   └── Dockerfile  # Docker 配置
├── Debian11-x86/   # Debian 11 x86 GCC 环境
│   └── Dockerfile  # Docker 配置
├── Ubuntu18/       # Ubuntu 18 GCC 环境
│   └── Dockerfile  # Docker 配置
├── Makefile        # 构建命令
└── README.md       # 原始说明文档
```

## 关键文件

### Makefile
提供便捷的 Docker 镜像构建命令。

### 各子目录 Dockerfile
定义不同 Linux 发行版和架构下的 GCC 编译环境。

## 依赖关系

- Docker 运行环境
- 被 Bazel 默认工具链测试任务引用

## 相关文档与参考

- 原始 `README.md` 中的说明
