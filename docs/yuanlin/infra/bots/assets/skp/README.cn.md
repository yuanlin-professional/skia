# skp - SKP 测试文件

## 概述

SKP（Skia Picture）测试文件资源。SKP 是 Skia 的序列化绘图记录格式，包含一系列绘图命令。用于渲染回放测试和性能评测。

## 目录结构

```
skp/
├── __init__.py              # Python 包标识
├── create.py                # 自动化创建脚本
├── create_and_upload.py     # 创建并上传便捷脚本
├── README.md                # 原始说明文档
└── VERSION                  # 当前版本号
```

## 依赖关系

- 被 DM 渲染测试和 Nanobench 性能评测任务使用
- 通过 `recreate_skps` 任务驱动重新生成

## 相关文档与参考

- `infra/bots/task_drivers/recreate_skps/` - SKP 重新生成任务
- `mskp/` - 多页 SKP 文件
