# scripts - 资源管理通用脚本

## 概述

包含资源管理操作的通用 Python 脚本，供各资源目录中的 `create.py` 和 `create_and_upload.py` 调用。

## 目录结构

```
scripts/
├── common.py                # 通用工具函数
├── create.py                # 通用创建逻辑
├── create_and_upload.py     # 通用创建并上传逻辑
├── download.py              # 通用下载逻辑
└── upload.py                # 通用上传逻辑
```

## 关键文件

- `common.py` - 定义资源管理的通用常量和工具函数
- `create.py` / `upload.py` / `download.py` - 资源生命周期管理的核心脚本

## 依赖关系

- 被各资源子目录中的脚本引用
- 依赖 Google Cloud Storage 和 `sk` CLI 工具

## 相关文档与参考

- 父目录 `assets/README.md` 中关于资源管理的说明
