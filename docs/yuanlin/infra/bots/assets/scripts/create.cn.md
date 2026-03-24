# scripts 资产创建模板脚本

> 源文件: infra/bots/assets/scripts/create.py

## 概述

资产创建脚本的模板文件，提供标准的接口定义但未实现具体逻辑。该脚本导入 common 模块修复 Python 导入路径，定义 `create_asset()` 函数接口，具体实现需要在各资产包中覆盖。

## 架构位置

位于 `infra/bots/assets/scripts/`，作为新资产包的起始模板。开发者复制该目录创建新资产时，需要实现 `create_asset()` 函数。

## 主要类与结构体

极简函数式风格。

## 公共 API 函数

### `create_asset(target_dir)`
接口函数，抛出 NotImplementedError。

**参数**:
- `target_dir` (str): 资产输出目录

**实现**:
```python
def create_asset(target_dir):
    raise NotImplementedError('Implement me!')
```

### `main()`
解析 `--target_dir` 参数并调用 `create_asset()`。

## 内部实现细节

### 导入路径修复

```python
import common  # fixes python import path
```

common 模块设置 sys.path，使得可以导入 `infra/bots/` 下的模块。

### 模板模式

这是典型的模板方法模式：
- 主流程定义在基类/模板中
- 具体实现由子类/具体文件提供

## 设计模式与设计决策

采用 NotImplementedError 强制子类实现，这是 Python 中实现抽象方法的常见模式。

## 相关文件

实际的资产创建脚本如：
- `infra/bots/assets/mockery/create.py`
- `infra/bots/assets/bloaty/create.py`

都遵循相同的接口签名。
