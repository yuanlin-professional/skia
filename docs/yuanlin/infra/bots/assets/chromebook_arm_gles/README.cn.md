# chromebook_arm_gles - Chromebook ARM GLES 支持

## 概述

Chromebook ARM 平台的 OpenGL ES 支持库资源，用于在 Chromebook ARM 设备上运行 Skia 的 GPU 测试。

## 目录结构

```
chromebook_arm_gles/
├── __init__.py              # Python 包标识
├── create.py                # 自动化创建脚本
├── create_and_upload.py     # 创建并上传便捷脚本
├── README.md                # 原始说明文档
└── VERSION                  # 当前版本号
```

## 依赖关系

- 被 Chromebook ARM GPU 测试任务使用

## 相关文档与参考

- `infra/bots/assets/chromebook_arm64_gles/` - ARM64 版本
- `infra/bots/assets/chromebook_x86_64_gles/` - x86_64 版本
