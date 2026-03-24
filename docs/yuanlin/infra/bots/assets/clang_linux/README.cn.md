# clang_linux - Linux Clang 编译器

## 概述

Linux 平台的 Clang/LLVM 编译器工具链资源。这是 Skia 在 Linux 上的主要编译器。

## 目录结构

```
clang_linux/
├── create.py    # 自动化创建脚本
├── Dockerfile   # 构建编译器的 Docker 配置
├── README.md    # 原始说明文档
└── VERSION      # 当前版本号
```

## 依赖关系

- 被大多数 Linux 编译和测试任务使用
- 可与 `binutils_linux_x64` 配合使用

## 相关文档与参考

- [LLVM/Clang 官方文档](https://clang.llvm.org/)
- `clang_mac_arm/`、`clang_mac_intel/`、`clang_win/` - 其他平台版本
