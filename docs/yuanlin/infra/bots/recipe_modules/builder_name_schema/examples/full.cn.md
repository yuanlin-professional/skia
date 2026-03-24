# full.py - Builder Name Schema 模块测试用例

> 源文件:
> - `infra/bots/recipe_modules/builder_name_schema/examples/full.py`

## 概述

full.py 是 `builder_name_schema` Recipe 模块的完整测试脚本，验证构建器名称的序列化/反序列化双向一致性以及各种错误输入的异常处理。该脚本通过正向测试（有效名称的往返转换）和反向测试（无效输入的异常捕获）确保命名 schema 引擎的正确性和健壮性。

## 架构位置

```
infra/bots/recipe_modules/builder_name_schema/
├── builder_name_schema.py (核心逻辑)
├── api.py (API 层)
└── examples/
    └── full.py (测试用例)  <── 本文件
```

## 主要类与结构体

无类定义。

## 公共 API 函数

| 函数 | 描述 |
|------|------|
| `RunSteps(api)` | 测试执行入口 |
| `GenTests(api)` | 生成测试用例 |

## 内部实现细节

### 正向测试（往返一致性）

测试两个标准构建器名称的解析-重建往返：

```python
names = [
    'Build-Debian10-Clang-x64-Release-Android',
    'Upload-Test-Debian10-Clang-GCE-CPU-AVX2-x86_64-Debug-Shard_12-Coverage',
]
for name in names:
    d = api.builder_name_schema.DictForBuilderName(name)
    got = api.builder_name_schema.MakeBuilderName(**d)
    assert got == name
```

第二个名称包含递归角色（Upload -> Test）和可选键（test_filter、extra_config），覆盖了更复杂的场景。

### 反向测试（错误处理）

测试 9 种错误场景，每种都预期抛出 `ValueError`：

| 场景 | 测试的错误类型 |
|------|--------------|
| `MakeBuilderName(role='nope')` | 未知角色 |
| `MakeBuilderName(compiler='Build', os='ab')` | 缺少 role 键 |
| `MakeBuilderName(role='Build', bogus='BOGUS')` | 多余的键 |
| `MakeBuilderName(..., extra_config='A-B')` | 值包含分隔符 |
| `DictForBuilderName('Build-')` | 名称部分不足 |
| `DictForBuilderName('Build-...-Bogus')` | 名称部分过多 |
| `DictForBuilderName('Bogus-...')` | 未知角色 |
| `MakeBuilderName(role='Upload')` | 缺少递归子角色 |
| `MakeBuilderName(role='Upload', sub-role-1='fake')` | 未知子角色 |
| `MakeBuilderName(..., extra_extra_config='Bogus')` | 多余的未定义键 |

### 测试生成

```python
def GenTests(api):
    yield api.test('test')
```

只需一个测试用例即可覆盖所有路径，因为 `RunSteps` 中的测试逻辑是确定性的。

## 依赖关系

- **Recipe 模块**: `builder_name_schema`（被测模块）
- **DEPS**: 仅依赖 `builder_name_schema` 一个模块

## 设计模式与设计决策

- **往返测试**: `DictForBuilderName` + `MakeBuilderName` 的双向测试确保了编解码的一致性
- **异常边界测试**: 覆盖了所有可能的错误输入类别
- **try/except/pass**: 使用 Python 惯用的异常测试模式，捕获预期的 `ValueError` 后继续执行
- **最小测试集**: 只需一个 `GenTests` 用例就能覆盖所有代码路径

## 性能考量

测试执行在 Recipe 模拟环境中，无实际设备或网络操作，执行速度极快。

## 相关文件

- `infra/bots/recipe_modules/builder_name_schema/builder_name_schema.py` - 被测试的核心模块
- `infra/bots/recipe_modules/builder_name_schema/api.py` - 被测试的 API 层
- `infra/bots/recipe_modules/builder_name_schema/builder_name_schema.json` - 命名规则 JSON
