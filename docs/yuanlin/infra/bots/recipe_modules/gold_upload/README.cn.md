# gold_upload - Gold 结果上传模块

## 概述

`gold_upload` 模块负责将 Skia 的图像测试结果（DM 输出）上传到 Skia Gold 服务。Gold 是 Skia 的视觉回归测试平台，用于检测图像渲染结果的变化。

## 目录结构

```
gold_upload/
├── __init__.py    # DEPS 依赖声明
├── api.py         # GoldUploadApi 核心类
├── examples/      # 使用示例和测试
└── resources/     # 辅助资源脚本
```

## 关键文件

### api.py
实现上传逻辑，包括：
- 格式化测试结果数据
- 使用 goldctl 工具上传图像和元数据
- 处理上传认证和错误重试

## 依赖关系

DEPS: 依赖 `recipe_engine` 和 `gsutil` 等模块。

## 相关文档与参考

- [Skia Gold](https://gold.skia.org/) - 视觉回归测试平台
- `infra/bots/README.recipes.md` 中 `gold_upload` 模块的 API 文档
