# gsutil - Google Cloud Storage 操作模块

## 概述

`gsutil` 模块封装了 Google Cloud Storage（GCS）的操作，提供文件上传、下载和管理功能。Skia CI 大量使用 GCS 来存储构建产物、测试结果和性能数据。

## 目录结构

```
gsutil/
├── __init__.py    # DEPS 依赖声明
├── api.py         # GsutilApi 核心类
└── examples/      # 使用示例和测试
```

## 关键文件

### api.py
提供 GCS 操作的高级接口，包括：
- 文件上传到 GCS bucket
- 从 GCS bucket 下载文件
- 列出和管理 GCS 对象

## 依赖关系

DEPS: 依赖 `recipe_engine` 中的相关模块。

## 相关文档与参考

- `infra/bots/README.recipes.md` 中 `gsutil` 模块的 API 文档
