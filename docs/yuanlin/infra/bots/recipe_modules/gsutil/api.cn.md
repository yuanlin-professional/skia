# GSUtil Recipe Module API

> 源文件: `infra/bots/recipe_modules/gsutil/api.py`

## 概述

`api.py` 实现了 `GSUtilApi` 配方模块，封装了 Google Cloud Storage (GCS) 的文件上传下载操作，内置重试机制以应对网络不稳定。

## 架构位置

位于 `infra/bots/recipe_modules/gsutil/` 目录，被 Gold 上传、性能结果上传等任务使用。

## 主要类与结构体

- **`GSUtilApi`** (recipe_api.RecipeApi): GCS 操作 API
- 常量: `UPLOAD_ATTEMPTS = 5`

## 公共 API 函数

- **`__call__(step_name, *args)`**: 直接调用 gsutil 命令
- **`cp(name, src, dst, extra_gsutil_args, extra_args, multithread)`**: 文件复制（上传/下载）

## 内部实现细节

1. `__call__` 直接执行 `gsutil` + 参数
2. `cp` 方法:
   - 支持 `extra_gsutil_args`（gsutil 全局参数，如 Mac 并行限制）
   - 支持 `-m` 多线程传输
   - 支持 `extra_args`（如 `-Z` gzip 压缩）
   - 最多重试 5 次，步骤名称包含 attempt 编号
   - 仅最后一次失败时抛出异常

## 依赖关系

- `recipe_engine/step`: 步骤执行
- 外部工具: `gsutil` (PATH 中)

## 设计模式与设计决策

- 重试模式: 5 次重试应对网络抖动
- 可调用对象: `__call__` 使 API 实例可像函数一样使用
- 假设 PATH 中有 gsutil，主要适用于 Linux/Mac

## 性能考量

- `-m` 多线程传输加速大量小文件上传
- `-Z` gzip 压缩减少传输数据量
- Mac 需要限制 `parallel_process_count=1` 避免问题

## 相关文件

- `infra/bots/recipe_modules/gsutil/__init__.py`: 模块初始化
- `infra/bots/recipe_modules/gold_upload/api.py`: 使用 gsutil 上传 Gold 结果
