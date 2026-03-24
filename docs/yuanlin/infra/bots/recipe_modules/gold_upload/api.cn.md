# Gold Upload Recipe Module API

> 源文件: `infra/bots/recipe_modules/gold_upload/api.py`

## 概述

`api.py` 实现了 `GoldUploadApi` 配方模块，负责将 DM 测试生成的图像（PNG）和元数据（dm.json）上传到 Google Cloud Storage，供 Skia Gold 图像比对系统使用。

## 架构位置

位于 `infra/bots/recipe_modules/gold_upload/` 目录，是测试后处理管线的关键组件。

## 主要类与结构体

- **`GoldUploadApi`** (recipe_api.RecipeApi): Gold 上传 API
- 常量: `DM_JSON = 'dm.json'`

## 公共 API 函数

- **`upload()`**: 执行完整的 Gold 结果上传流程

## 内部实现细节

1. **图像上传** (优先):
   - 目标: `gs://<gs_bucket>/dm-images-v1`
   - 使用 glob 搜索 `.png` 文件
   - Mac 上限制 `parallel_process_count=1` 避免问题
   - 使用 gsutil 多线程上传
2. **JSON 上传**:
   - 目标路径格式: `gs://<bucket>/[trybot/]dm-json-v1/<YYYY>/<MM>/<DD>/<HH>/<ref>/<builder>/<timestamp>/dm.json`
   - Trybot: 路径包含 `trybot/` 前缀，ref 为 `issue_patchset`
   - 非 trybot: ref 为 git revision
   - 使用 `-Z` 参数启用 gzip 压缩
3. **时间戳**: 使用 UTC 时间和 Unix 时间戳组织上传路径

## 依赖关系

- `recipe_engine/file`, `recipe_engine/platform`, `recipe_engine/properties`, `recipe_engine/time`
- `flavor`: 获取 DM 输出目录
- `gsutil`: GCS 上传操作
- `vars`: 构建变量

## 设计模式与设计决策

- 图像优先上传: 确保 JSON 被处理时图像已经存在
- 按时间分片存储: 使用 YYYY/MM/DD/HH 路径结构便于管理和清理
- trybot 隔离: trybot 结果存储在独立路径，不干扰主线结果
- gzip 压缩: JSON 文件使用 `-Z` 在存储端压缩

## 性能考量

- 多线程上传图像文件
- Mac 串行限制避免系统资源竞争
- gzip 压缩减少 JSON 存储和传输成本

## 相关文件

- `infra/bots/recipe_modules/gold_upload/__init__.py`: 模块初始化
- `infra/bots/recipe_modules/gold_upload/examples/full.py`: 测试示例
- `infra/bots/recipe_modules/gsutil/api.py`: GCS 上传工具
