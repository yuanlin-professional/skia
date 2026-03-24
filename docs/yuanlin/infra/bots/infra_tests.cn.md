# Infra Tests - 基础设施测试运行器

> 源文件: `infra/bots/infra_tests.py`

## 概述

`infra_tests.py` 是 Skia 基础设施测试的统一运行器，负责执行三类测试：Python 单元测试、配方（recipe）测试和任务生成（gen_tasks）测试。支持 `--train` 模式用于更新测试期望值。

## 架构位置

位于 `infra/bots/` 目录，是 CI 系统中 `Housekeeper-PerCommit-InfraTests` 任务的核心脚本。

## 主要类与结构体

无类定义。

## 公共 API 函数

- `main()`: 运行所有测试并报告结果
- `test(cmd, cwd)`: 执行命令并捕获输出
- `python_unit_tests(train)`: 发现并运行 Python 单元测试
- `recipe_test(train)`: 运行配方测试
- `gen_tasks_test(train)`: 运行任务生成测试

## 内部实现细节

1. **`python_unit_tests`**: 使用 `unittest discover` 发现 `*_test.py` 文件并执行
2. **`recipe_test`**: 调用 `recipes.py test run` 或 `recipes.py test train`
3. **`gen_tasks_test`**: 运行 `go run gen_tasks.go --test`（需要 Go 环境）
4. **`test` 辅助函数**: 使用 `subprocess.check_output` 执行命令，捕获 `CalledProcessError` 返回输出
5. **`--train` 模式**: 更新测试期望值而非验证
6. 所有测试错误收集后统一输出，带分隔线格式

## 依赖关系

- `infra/bots/recipes.py`: 配方引擎
- `infra/bots/gen_tasks.go`: 任务生成器
- Python 标准库: `os`, `subprocess`, `sys`
- 运行时: Go 语言环境（用于 gen_tasks_test）

## 设计模式与设计决策

- 聚合测试模式: 运行所有测试并收集结果，即使某个测试失败也继续执行其他测试
- Train/Run 双模式: `--train` 更新期望值，默认模式验证结果
- gen_tasks_test 优雅降级: 当 Go 不可用时返回友好错误信息

## 性能考量

- 测试串行执行，确保互不干扰
- `subprocess.check_output` 合并 stderr 到 stdout 便于错误诊断

## 相关文件

- `infra/bots/recipes.py`: 配方引擎脚本
- `infra/bots/gen_tasks.go`: 任务生成入口
- `infra/bots/zip_utils_test.py`: Python 单元测试示例
