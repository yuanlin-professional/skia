# armhf_sysroot - ARM Hard Float 系统根

## 概述

ARM Hard Float（armhf）架构的系统根目录资源，用于在 x86_64 机器上交叉编译 32 位 ARM 目标的 Skia。

## 目录结构

```
armhf_sysroot/
├── create.py   # 自动化创建脚本
├── README.md   # 原始说明文档
└── VERSION     # 当前版本号
```

## 依赖关系

- 被 ARM 32 位交叉编译任务使用

## 相关文档与参考

- `infra/bots/assets/arm64_sysroot/` - ARM64 版本
