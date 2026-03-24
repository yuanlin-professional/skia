# arm64_sysroot - ARM64 系统根

## 概述

ARM64（AArch64）架构的系统根目录资源，用于在 x86_64 机器上交叉编译 ARM64 目标的 Skia。包含必要的头文件和库文件。

## 目录结构

```
arm64_sysroot/
├── create.py    # 自动化创建脚本
├── Dockerfile   # 构建 sysroot 的 Docker 配置
├── README.md    # 原始说明文档
└── VERSION      # 当前版本号
```

## 依赖关系

- 被 ARM64 交叉编译任务使用
- 与 `clang_linux` 编译器配合使用

## 相关文档与参考

- `infra/bots/assets/armhf_sysroot/` - ARM Hard Float 版本
- `infra/cross-compile/` - 交叉编译配置
