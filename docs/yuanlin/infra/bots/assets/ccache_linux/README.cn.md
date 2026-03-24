# ccache_linux - Linux 编译缓存工具

## 概述

Linux 版 ccache 编译缓存工具资源。ccache 可缓存编译结果以加速重复构建。

## 目录结构

```
ccache_linux/
├── create.py   # 自动化创建脚本
└── VERSION     # 当前版本号
```

## 依赖关系

- 被 Linux 编译任务用于加速构建

## 相关文档与参考

- [ccache 官方文档](https://ccache.dev/)
- `infra/bots/assets/ccache_mac/` - macOS 版本
