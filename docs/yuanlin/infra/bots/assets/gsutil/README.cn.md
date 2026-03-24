# gsutil - Google Cloud Storage 工具

## 概述

gsutil 命令行工具资源，用于与 Google Cloud Storage 交互。在 CI 中用于上传和下载构建产物、测试结果等。

## 目录结构

```
gsutil/
├── create.py   # 自动化创建脚本
└── VERSION     # 当前版本号
```

## 依赖关系

- 被需要 GCS 操作的各类任务使用

## 相关文档与参考

- [gsutil 文档](https://cloud.google.com/storage/docs/gsutil)
