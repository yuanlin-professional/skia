# bloaty - 二进制体积分析工具

## 概述

Bloaty McBloatface 工具资源，用于分析二进制文件的体积分布。在 Skia 的构建统计流程中用于追踪代码体积变化。

## 目录结构

```
bloaty/
├── create.py   # 自动化创建脚本
└── VERSION     # 当前版本号
```

## 依赖关系

- 被构建统计（buildstats）任务使用
- 与 `infra/bots/buildstats/` 脚本配合

## 相关文档与参考

- [Bloaty GitHub](https://github.com/google/bloaty)
