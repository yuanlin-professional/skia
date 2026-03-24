# SkiaStepApi 执行接口

> 源文件: infra/bots/recipe_modules/run/api.py

## 概述

`api.py` 定义了 `SkiaStepApi` 类,这是 Skia Recipe 系统中的核心执行接口,提供命令执行、失败处理、文件操作、重试逻辑和资产版本管理等功能。该 API 通过统一的接口包装 Recipe Engine 的底层功能,添加 Skia 特定的错误处理和便利方法,使 Recipe 编写更加简洁和可靠。

## 架构位置

该模块位于 Recipe 系统的工具层:

- **层级**: 基础设施 / 执行工具 / 通用 API
- **功能域**: 命令执行、文件操作、失败管理
- **使用频率**: 极高(几乎所有步骤)
- **设计模式**: 包装器模式 + 策略模式

## 主要类与结构体

### SkiaStepApi

继承自 `recipe_api.RecipeApi` 的核心 API 类。

**实例变量**:
- `_already_ran`: 缓存已执行的函数结果
- `_ccache`: ccache 路径缓存
- `_checked_for_ccache`: ccache 检查标志
- `_failed`: 失败步骤列表

## 公共 API 函数

### __init__

```python
def __init__(self, *args, **kwargs):
```

**功能**: 初始化 API 实例,设置内部状态。

**初始化状态**:
- `_already_ran`: 空字典
- `_ccache`: None
- `_checked_for_ccache`: False
- `_failed`: 空列表

### check_failure

```python
def check_failure(self):
    """Raise an exception if any step failed."""
```

**功能**: 检查是否有失败的步骤,如果有则抛出异常。

**异常**: `self.m.step.StepFailure`,包含所有失败步骤的名称

**使用场景**: Recipe 结束时验证所有步骤是否成功

### failed_steps (属性)

```python
@property
def failed_steps(self):
    return self._failed[:]
```

**功能**: 返回失败步骤列表的副本。

**返回值**: 失败步骤对象列表(副本,防止外部修改)

### run_once

```python
def run_once(self, fn, *args, **kwargs):
```

**功能**: 确保函数只执行一次,后续调用返回缓存结果。

**参数**:
- `fn`: 要执行的函数
- `*args`, `**kwargs`: 传递给函数的参数

**返回值**: 函数的返回值(首次执行或缓存)

**实现**: 使用函数名作为键存储结果

**用例**: 避免重复执行昂贵的初始化操作

### readfile

```python
def readfile(self, filename, *args, **kwargs):
    """Convenience function for reading files."""
```

**功能**: 读取文件内容的便利函数。

**参数**:
- `filename`: 文件路径
- `name`: 步骤名称(可选,默认 "read {basename}")

**返回值**: 文件内容字符串

**实现**: 包装 `self.m.file.read_text`

### writefile

```python
def writefile(self, filename, contents):
    """Convenience function for writing files."""
```

**功能**: 写入文件内容的便利函数。

**参数**:
- `filename`: 文件路径
- `contents`: 要写入的内容

**返回值**: Recipe 步骤结果

**实现**: 包装 `self.m.file.write_text`

### rmtree

```python
def rmtree(self, path):
    """Wrapper around api.file.rmtree."""
```

**功能**: 递归删除目录。

**参数**:
- `path`: 目录路径

**实现**: 包装 `self.m.file.rmtree`

### asset_version

```python
def asset_version(self, asset_name, skia_dir, test_data=None):
    """Return the contents of VERSION for the given asset as a string."""
```

**功能**: 获取 CIPD 资产的版本字符串。

**参数**:
- `asset_name`: 资产名称(如 'clang_linux')
- `skia_dir`: Skia 源码目录
- `test_data`: 测试数据(可选)

**返回值**: 版本字符串(去除尾部空白)

**路径**: `infra/bots/assets/{asset_name}/VERSION`

**测试数据**: 使用属性 `test_{asset_name}_version` 或默认值 '42'

### __call__

```python
def __call__(self, steptype, name, abort_on_failure=True,
             fail_build_on_failure=True, **kwargs):
```

**功能**: 执行步骤,捕获失败但可选择继续执行。

**参数**:
- `steptype`: 步骤类型(通常是 `api.step`)
- `name`: 步骤名称
- `abort_on_failure`: 失败时是否中止(默认 True)
- `fail_build_on_failure`: 失败时是否标记构建失败(默认 True)
- `**kwargs`: 传递给 steptype 的参数

**返回值**: 步骤执行结果

**行为**:
1. 在 `vars.default_env` 环境中执行步骤
2. 捕获 `StepFailure` 异常
3. 如果 `fail_build_on_failure`,记录失败
4. 如果 `abort_on_failure`,重新抛出异常
5. 否则继续执行(非致命失败)

**用例**: 允许某些步骤失败但继续构建

### with_retry

```python
def with_retry(self, steptype, name, attempts, between_attempts_fn=None,
               abort_on_failure=True, fail_build_on_failure=True, **kwargs):
```

**功能**: 执行步骤,失败时自动重试。

**参数**:
- `steptype`: 步骤类型
- `name`: 步骤名称
- `attempts`: 最大尝试次数
- `between_attempts_fn`: 两次尝试之间执行的函数(可选)
- `abort_on_failure`: 所有尝试失败后是否中止
- `fail_build_on_failure`: 失败时是否标记构建失败
- `**kwargs`: 传递给 steptype 的参数

**返回值**: 成功执行的步骤结果

**行为**:
1. 循环尝试执行步骤
2. 重试时步骤名称添加 " (attempt N)"
3. 成功后清理之前的失败记录
4. 失败时调用 `between_attempts_fn`(如提供)
5. 最后一次尝试失败且 `abort_on_failure` 时抛出异常

**用例**: 处理网络请求、CIPD 下载等不稳定操作

## 内部实现细节

### 失败管理

**失败记录**:
```python
except self.m.step.StepFailure as e:
    if fail_build_on_failure:
        self._failed.append(e)
```

记录失败但不立即中止,允许后续步骤执行。

**清理重试失败**:
```python
if attempt > 0 and fail_build_on_failure:
    del self._failed[-attempt:]
```

重试成功后删除之前的失败记录,避免误报。

### run_once 缓存

```python
if not fn.__name__ in self._already_ran:
    self._already_ran[fn.__name__] = fn(*args, **kwargs)
return self._already_ran[fn.__name__]
```

**特点**:
- 使用函数名作为键(不考虑参数)
- 简单但有效
- 假设同名函数不会用不同参数调用

**限制**: 不支持参数化缓存

### 环境上下文

```python
with self.m.env(self.m.vars.default_env):
    return steptype(name=name, **kwargs)
```

所有步骤在 `vars.default_env` 环境中执行,确保一致的环境变量。

### 测试支持

```python
TEST_DEFAULT_ASSET_VERSION = '42'
```

测试时使用固定版本号,避免依赖实际文件。

## 依赖关系

### 直接依赖
- `recipe_engine`: Recipe Engine 框架
- `vars`: Skia 变量模块
- `file`: 文件操作
- `step`: 步骤执行
- `path`: 路径处理

### 被依赖者
- 所有 Skia Recipe 模块
- 所有 Recipe 文件
- 几乎每个构建步骤

## 设计模式与设计决策

### 包装器模式

包装 Recipe Engine API 添加 Skia 特定功能:
- 统一的失败处理
- 默认环境注入
- 便利方法

### 策略模式

通过参数控制失败行为:
- `abort_on_failure`: 中止策略
- `fail_build_on_failure`: 标记策略

### 容错设计

允许步骤失败但继续执行:
- 收集所有错误
- 最后统一报告
- 最大化信息收集

### 重试机制

自动重试不稳定操作:
- 提高构建可靠性
- 支持自定义重试间隔操作
- 清晰的重试标记

### 便利方法

提供简化的文件操作:
- 减少样板代码
- 统一命名规范
- 自动生成步骤名称

## 性能考量

### 缓存优化

`run_once` 避免重复执行:
- 函数级缓存
- O(1) 查找
- 内存开销极小

### 失败列表

使用列表存储失败步骤:
- 添加操作 O(1)
- 内存占用与失败数成正比
- 典型场景 <10 个失败

### 重试开销

重试增加执行时间:
- 每次重试完整执行步骤
- `between_attempts_fn` 可添加延迟
- 权衡可靠性与速度

### 环境上下文

每次调用创建环境上下文:
- 开销极小(dict 复制)
- 确保环境一致性

## 相关文件

### 同模块文件
- `infra/bots/recipe_modules/run/__init__.py`: 模块入口
- `infra/bots/recipe_modules/run/examples/full.py`: 完整示例

### 依赖模块
- `infra/bots/recipe_modules/vars/`: vars 模块
- `infra/bots/recipe_modules/env/`: env 模块
- `recipe_engine/`: Recipe Engine 核心

### 使用者
- 所有 Recipe 模块和文件
- 构建、测试、基础设施任务

### 资产文件
- `infra/bots/assets/*/VERSION`: 资产版本文件

### 测试
- `.recipes/*.expected/`: 测试期望输出

该 API 是 Skia Recipe 系统的基石,通过提供强大而灵活的执行接口,使 Recipe 能够可靠地处理各种构建和测试场景,同时保持代码简洁和可维护。
