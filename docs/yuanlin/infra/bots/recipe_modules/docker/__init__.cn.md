# Docker Recipe Module 初始化

> 源文件: `infra/bots/recipe_modules/docker/__init__.py`

## 概述

`__init__.py` 是 Docker 配方模块的初始化文件，注册 `DockerApi` 类。该模块提供在 Docker 容器中运行 Skia 任务的能力。

## 架构位置

位于 `infra/bots/recipe_modules/docker/` 目录。

## 主要类与结构体

无。通过 `API = _api.DockerApi` 注册。

## 公共 API 函数

无直接 API。

## 内部实现细节

声明依赖: `env`, `recipe_engine/file`, `recipe_engine/path`, `recipe_engine/raw_io`, `recipe_engine/step`, `run`。

## 依赖关系

- `env`, `run`: Skia 配方模块
- 多个 `recipe_engine` 标准模块

## 设计模式与设计决策

LUCI 配方模块标准初始化。

## 性能考量

无。

## 相关文件

- `infra/bots/recipe_modules/docker/api.py`: API 实现
