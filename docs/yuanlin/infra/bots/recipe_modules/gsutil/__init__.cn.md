# GSUtil Recipe Module 初始化

> 源文件: `infra/bots/recipe_modules/gsutil/__init__.py`

## 概述

`__init__.py` 是 GSUtil 配方模块的初始化文件，注册 `GSUtilApi` 类。该模块封装了 Google Cloud Storage 的上传下载操作。

## 架构位置

位于 `infra/bots/recipe_modules/gsutil/` 目录。

## 主要类与结构体

无。通过 `API = _api.GSUtilApi` 注册。

## 公共 API 函数

无直接 API。

## 内部实现细节

声明依赖: `recipe_engine/context`, `recipe_engine/step`, `run`, `vars`。

## 依赖关系

- `run`, `vars`: Skia 配方模块

## 设计模式与设计决策

LUCI 配方模块标准初始化。

## 性能考量

无。

## 相关文件

- `infra/bots/recipe_modules/gsutil/api.py`: API 实现
