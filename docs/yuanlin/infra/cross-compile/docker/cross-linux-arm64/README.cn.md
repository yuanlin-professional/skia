# cross-linux-arm64 - Linux ARM64 交叉编译环境

## 概述

用于在 x86_64 Linux 主机上交叉编译 ARM64 目标 Skia 的 Docker 镜像配置。

## 目录结构

```
cross-linux-arm64/
└── Dockerfile   # Docker 镜像定义
```

## 依赖关系

- ARM64 系统根（sysroot）
- Clang 交叉编译器

## 相关文档与参考

- `infra/bots/assets/arm64_sysroot/` - ARM64 系统根资源
