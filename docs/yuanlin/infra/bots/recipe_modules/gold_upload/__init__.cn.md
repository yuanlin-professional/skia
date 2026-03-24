# Gold Upload Recipe Module 初始化

> 源文件: `infra/bots/recipe_modules/gold_upload/__init__.py`

## 概述

`__init__.py` 是 Gold Upload 配方模块的初始化文件，注册 `GoldUploadApi` 类。该模块负责将 DM 测试生成的图像和 JSON 结果上传到 Skia Gold 图像比对系统。

## 架构位置

位于 `infra/bots/recipe_modules/gold_upload/` 目录，是测试结果上传管线的核心模块。

## 主要类与结构体

无。通过 `API = _api.GoldUploadApi` 注册。

## 公共 API 函数

无直接 API。

## 内部实现细节

声明依赖: `recipe_engine/json`, `recipe_engine/context`, `recipe_engine/file`, `recipe_engine/platform`, `recipe_engine/properties`, `recipe_engine/step`, `recipe_engine/time`, `flavor`, `gsutil`, `run`, `vars`。

## 依赖关系

- `flavor`: 设备 flavor（处理不同设备的文件路径差异）
- `gsutil`: GCS 上传
- `run`, `vars`: 基础设施模块

## 设计模式与设计决策

LUCI 配方模块标准初始化。

## 性能考量

无。

## 相关文件

- `infra/bots/recipe_modules/gold_upload/api.py`: API 实现
