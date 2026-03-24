# Doxygen Recipe Module 初始化

> 源文件: `infra/bots/recipe_modules/doxygen/__init__.py`

## 概述

`__init__.py` 是 Doxygen 配方模块的初始化文件，注册 `DoxygenApi` 类。该模块提供运行 Doxygen 文档生成工具的配方支持。

## 架构位置

位于 `infra/bots/recipe_modules/doxygen/` 目录，用于 CI 系统中的 API 文档自动生成任务。

## 主要类与结构体

无。通过 `API = _api.DoxygenApi` 注册。

## 公共 API 函数

无直接 API。

## 内部实现细节

声明依赖: `recipe_engine/context`, `recipe_engine/step`, `run`。依赖非常精简，仅需要步骤执行和运行支持。

## 依赖关系

- `run`: 执行辅助模块
- `recipe_engine/context`, `recipe_engine/step`

## 设计模式与设计决策

LUCI 配方模块标准初始化，依赖最小化。

## 性能考量

无。

## 相关文件

- Doxygen 配置文件（位于仓库根目录）
- `infra/bots/recipe_modules/doxygen/api.py`: API 实现
