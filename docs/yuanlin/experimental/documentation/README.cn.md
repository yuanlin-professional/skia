# documentation - Skia 开发文档

## 概述

`experimental/documentation/` 包含 Skia 开发相关的补充文档，主要是关于开发
工作流和工具使用的指南。

## 目录结构

```
documentation/
└── gerrit.md              # Gerrit 代码审查工具使用指南
```

## 关键文件

### gerrit.md
详细介绍了不使用 `git-cl` 直接通过 Git 命令与 Gerrit 代码审查系统交互的方法，包括：
- 初始设置（Change-Id 钩子配置）
- 认证方式
- 创建变更（Change）的完整流程
- 更新已有变更的操作
- 触发 Commit-Queue 干运行
- 常用 Git 别名脚本

## 相关文档与参考

- Gerrit 官方文档: https://gerrit-review.googlesource.com/Documentation/
- Skia Gerrit 实例: https://skia-review.googlesource.com/
- `experimental/tools/` 中的辅助脚本
