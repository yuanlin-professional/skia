# Zip Utils 测试

> 源文件: `infra/bots/zip_utils_test.py`

## 概述

`zip_utils_test.py` 是 `zip_utils` 模块的单元测试文件，验证 zip/unzip 操作的正确性，包括基本的压缩解压、文件过滤（跳过指定模式的文件），以及对不存在目录的错误处理。

## 架构位置

位于 `infra/bots/` 目录，属于 Skia CI/CD 基础设施的测试套件。使用 Python `unittest` 框架。

## 主要类与结构体

- **`ZipUtilsTest`** (unittest.TestCase): 测试用例类
  - `test_zip_unzip()`: 基本 zip/unzip 流程测试
  - `test_to_skip()`: 文件跳过模式测试
  - `test_nonexistent_dir()`: 不存在目录的错误处理测试

## 公共 API 函数

三个测试方法通过 `unittest.main()` 自动发现和执行。

## 内部实现细节

1. **`test_zip_unzip`**: 创建含目录和文件（不同权限）的测试结构，zip 后 unzip，使用 `compare_trees` 验证一致性
2. **`test_to_skip`**: 创建包含 `.git/`、`.DS_STORE`、`*.pyc` 的文件，使用 `to_skip` 参数排除后验证
3. **`test_nonexistent_dir`**: 验证对不存在的目录调用 zip 时抛出 `IOError`
4. 所有测试在 `utils.tmp_dir()` 临时目录中运行，确保隔离

## 依赖关系

- `test_utils`: FileWriter 和 compare_trees
- `utils`: tmp_dir 上下文管理器
- `zip_utils`: 被测试的模块
- Python 标准库: `filecmp`, `os`, `unittest`, `uuid`

## 设计模式与设计决策

- 每个测试在独立的临时目录中运行，保证测试隔离
- 测试不同权限模式（0o777, 0o751, 0o640 等）确保权限保持功能
- 使用 glob 模式（`.git`, `.DS*`, `*.pyc`）测试灵活的文件跳过功能

## 性能考量

无特殊性能考量。

## 相关文件

- `infra/bots/zip_utils.py`: 被测试的 zip 工具
- `infra/bots/test_utils.py`: 测试辅助工具
- `infra/bots/utils.py`: 通用工具（tmp_dir）
