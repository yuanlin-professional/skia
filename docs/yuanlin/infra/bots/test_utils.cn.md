# Test Utils - 基础设施测试工具

> 源文件: `infra/bots/test_utils.py`

## 概述

`test_utils.py` 提供了用于 Skia 基础设施测试的文件操作工具和目录比较功能。主要包含 `FileWriter` 类（用于创建带权限控制的测试文件/目录）和 `compare_trees` 函数（递归比较两个目录树的内容和权限）。

## 架构位置

位于 `infra/bots/` 目录，属于 Skia CI/CD 基础设施的测试框架。被 `zip_utils_test.py` 等测试文件使用。

## 主要类与结构体

- **`FileWriter`**: 测试文件写入器
  - `__init__(cwd)`: 在指定工作目录初始化，自动创建目录
  - `mkdir(dname, mode=0o755)`: 创建目录并设置权限
  - `write(fname, mode=0o640)`: 创建文件（随机 UUID 内容）并设置权限
  - `remove(fname)`: 删除文件或目录

## 公共 API 函数

- **`compare_trees(test, a, b)`**: 递归比较两个目录树
  - 验证文件/目录名称一致
  - 验证文件内容完全相同
  - 验证文件权限模式一致
  - 递归处理子目录

## 内部实现细节

1. `FileWriter.write` 使用 `uuid.uuid4()` 生成随机文件内容，确保测试文件唯一
2. `FileWriter.remove` 智能判断目标是文件还是目录，分别调用 `os.remove` 或 `os.rmdir`
3. `compare_trees` 使用 `filecmp.dircmp` 构建目录比较对象
4. 内部 `_cmp` 函数递归遍历子目录，对每个级别进行完整验证
5. 同时检查 `filecmp.cmp`（内容比较）和 `os.stat().st_mode`（权限比较）

## 依赖关系

- Python 标准库: `filecmp`, `os`, `uuid`
- 无外部依赖

## 设计模式与设计决策

- 工具类模式：FileWriter 封装文件系统操作，简化测试代码
- 使用 UUID 确保测试文件内容的唯一性，避免缓存干扰
- 权限验证确保 zip/unzip 操作保持文件权限不变

## 性能考量

无特殊性能考量，面向测试场景设计。

## 相关文件

- `infra/bots/zip_utils_test.py`: 使用此工具的测试文件
- `infra/bots/zip_utils.py`: 被测试的 zip 工具
