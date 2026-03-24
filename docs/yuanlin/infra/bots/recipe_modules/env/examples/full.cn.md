# EnvApi 完整示例

> 源文件: infra/bots/recipe_modules/env/examples/full.py

## 概述

这是 `env` recipe 模块的完整功能测试示例,展示了如何在 recipe 中使用环境变量 API。该示例演示了基本的环境变量设置、PATH 变量的嵌套合并,以及与 `context` 模块的协同工作。通过这个示例可以理解 `env` 模块在实际 recipe 场景中的用法和行为。

## 架构位置

该示例文件位于 Skia 构建基础设施的测试框架中:
- 路径: `infra/bots/recipe_modules/env/examples/`
- 用途: 作为 recipe 模块的功能测试
- 在 recipe 测试系统中自动执行
- 验证 `env` 模块的正确性

## 主要类与结构体

### DEPS 配置

```python
DEPS = [
  'env',
  'recipe_engine/context',
  'recipe_engine/step',
]
```

**依赖说明:**
- `env`: 被测试的环境变量管理模块
- `recipe_engine/context`: 上下文管理器
- `recipe_engine/step`: 执行命令步骤

### RunSteps 函数

recipe 的主执行函数,包含三个测试场景:

**场景1: 无环境变量覆盖**
```python
api.step('1', cmd=['echo', 'hi'])
```
使用默认环境变量执行步骤

**场景2: 设置自定义环境变量**
```python
with api.env({'MYVAR': 'myval'}):
    api.step('2', cmd=['echo', 'hi'])
```
在作用域内添加 `MYVAR` 环境变量

**场景3: PATH 变量嵌套合并**
```python
path = 'mypath:%(PATH)s'
with api.context(env={'PATH': path}):
    api.step('3', cmd=['echo', 'hi'])
    with api.env({'PATH': '%(PATH)s:otherpath'}):
        api.step('4', cmd=['echo', 'hi'])
```
演示 PATH 变量的复杂嵌套和合并

## 公共 API 函数

### RunSteps(api)

**参数:**
- `api`: Recipe API 对象,提供访问各个模块的接口

**返回值:**
- 无返回值

**功能:**
执行一系列测试步骤,验证环境变量设置的正确性

**步骤说明:**

1. **步骤1 - 基准测试**: 不设置任何环境变量,使用系统默认环境
2. **步骤2 - 简单变量**: 设置单个自定义环境变量 `MYVAR=myval`
3. **步骤3 - PATH 前置**: 在 PATH 前添加 `mypath`
4. **步骤4 - PATH 追加**: 在 PATH 后追加 `otherpath`

### GenTests(api)

**参数:**
- `api`: Recipe 测试 API 对象

**返回值:**
- 生成器,产出测试用例

**功能:**
生成名为 'test' 的测试用例,验证示例的执行

## 内部实现细节

### PATH 变量合并逻辑

**第一层嵌套:**
```python
path = 'mypath:%(PATH)s'
with api.context(env={'PATH': path}):
```
将 `mypath` 添加到 PATH 前面

**第二层嵌套:**
```python
with api.env({'PATH': '%(PATH)s:otherpath'}):
```
在已经修改的 PATH 后追加 `otherpath`

**最终结果:**
假设原始 PATH 为 `/usr/bin:/bin`,最终 PATH 为:
```
mypath:/usr/bin:/bin:otherpath
```

### 占位符替换机制

`%(PATH)s` 占位符的工作原理:
- 在设置新 PATH 时保留原始值
- 使用 Python 字符串替换实现
- 支持任意位置插入新路径

### 作用域管理

使用 `with` 语句确保:
- 环境变量仅在代码块内有效
- 退出作用域后自动恢复
- 支持任意深度的嵌套

## 依赖关系

**模块依赖:**
```
env (被测试模块)
  ↓
context (上下文管理)
  ↓
step (命令执行)
```

**API 调用链:**
1. `api.env()` 创建环境上下文
2. `api.context()` 设置执行上下文
3. `api.step()` 在上下文中执行命令

## 设计模式与设计决策

### 测试用例设计

**渐进式复杂度:**
1. 最简单: 无环境变量
2. 简单: 单个变量
3. 中等: PATH 修改
4. 复杂: 嵌套 PATH 修改

**设计意图:**
- 从简单到复杂逐步验证功能
- 覆盖常见使用场景
- 验证嵌套行为的正确性

### 上下文管理器使用

**api.env vs api.context:**
- `api.env`: 专门用于环境变量
- `api.context`: 更通用的上下文设置

**嵌套策略:**
```python
with api.context(...):  # 外层
    with api.env(...):   # 内层
```
演示两种方式的兼容性

### 显式 vs 隐式

使用显式的占位符 `%(PATH)s` 而非自动追加:
- **优点:** 行为可预测
- **优点:** 用户控制插入位置
- **缺点:** 需要理解占位符语法

## 性能考量

### 测试效率

**执行开销:**
- 4 个简单的 echo 命令
- 环境变量设置: O(1) 操作
- 总执行时间: 毫秒级

**资源使用:**
- 内存占用极小
- 无 I/O 密集操作
- 适合频繁执行

### 实际应用建议

1. **避免过度嵌套:** 超过 3 层嵌套降低可读性
2. **清晰的变量命名:** 使用描述性变量名
3. **文档化 PATH 修改:** 注释说明路径添加原因

## 相关文件

**核心实现:**
- `infra/bots/recipe_modules/env/api.py`: EnvApi 实现
- `infra/bots/recipe_modules/env/__init__.py`: 模块定义

**其他示例:**
- `flavor/examples/full.py`: 使用 env 模块的更复杂示例
- 其他 recipe 模块的示例文件

**文档:**
- Recipe Engine 官方文档
- Skia 构建系统文档

**测试框架:**
- Recipe 测试系统自动运行此示例
- 验证环境变量行为的正确性
