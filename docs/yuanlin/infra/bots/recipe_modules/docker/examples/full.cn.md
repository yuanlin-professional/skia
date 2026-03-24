# Docker Module 测试示例

> 源文件: `infra/bots/recipe_modules/docker/examples/full.py`

## 概述

`full.py` 是 Docker 配方模块的测试示例，验证完整的 Docker 运行流程，包括目录挂载、脚本执行、参数传递、文件复制和环境变量设置。

## 架构位置

位于 `infra/bots/recipe_modules/docker/examples/` 目录。

## 主要类与结构体

无。

## 公共 API 函数

- `RunSteps(api)`: 调用 docker.run 执行容器化任务
- `GenTests(api)`: 生成 CanvasKit WASM 测试场景

## 内部实现细节

演示了完整的参数使用：docker_image、src_dir、out_dir、script、args、docker_args（CPU 限制）、copies（文件复制）、recursive_read、env（环境变量）。

## 依赖关系

- `docker`, `recipe_engine/context`, `recipe_engine/properties`, `recipe_engine/step`, `vars`

## 设计模式与设计决策

展示了 Docker 模块的完整用法模式。

## 性能考量

无。

## 相关文件

- `infra/bots/recipe_modules/docker/api.py`: 被测试的 API
