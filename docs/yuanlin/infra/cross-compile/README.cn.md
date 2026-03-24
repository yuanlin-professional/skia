# cross-compile - 交叉编译配置

## 概述

`cross-compile/` 目录包含用于交叉编译 Skia 的 Docker 配置。主要用于在 x86_64 主机上为 ARM 架构目标编译 Skia。

## 目录结构

```
cross-compile/
└── docker/
    └── cross-linux-arm64/   # Linux ARM64 交叉编译
        └── Dockerfile       # Docker 镜像定义
```

## 依赖关系

- `infra/bots/assets/arm64_sysroot/` - ARM64 系统根
- `infra/bots/assets/armhf_sysroot/` - ARM Hard Float 系统根
- Clang 交叉编译器

## 相关文档与参考

- ARM 交叉编译工具链文档
