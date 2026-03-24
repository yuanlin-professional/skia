# Env Recipe Module 初始化

> 源文件: `infra/bots/recipe_modules/env/__init__.py`

## 概述

`__init__.py` 是 Env 配方模块的初始化文件，注册 `EnvApi` 类。该模块提供环境变量管理功能。

## 架构位置

位于 `infra/bots/recipe_modules/env/` 目录，是一个轻量级的环境变量管理模块。

## 主要类与结构体

无。通过 `API = _api.EnvApi` 注册。

## 公共 API 函数

无直接 API。

## 内部实现细节

声明依赖: 仅 `recipe_engine/context`。这是依赖最少的配方模块之一。

## 依赖关系

- `recipe_engine/context`

## 设计模式与设计决策

最小化模块设计，仅依赖 context 进行环境变量管理。

## 性能考量

无。

## 相关文件

- `infra/bots/recipe_modules/docker/__init__.py`: 依赖此模块
