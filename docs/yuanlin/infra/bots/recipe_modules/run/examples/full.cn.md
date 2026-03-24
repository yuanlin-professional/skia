# Run Recipe 完整示例

> 源文件: infra/bots/recipe_modules/run/examples/full.py

## 概述

`full.py` 是 Run Recipe 模块的完整使用示例和测试文件,展示了 SkiaStepApi 的所有核心功能,包括失败处理、run_once 缓存、文件操作、资产版本读取、环境变量管理和重试机制。该文件既是文档也是测试,确保 Run API 的所有功能正常工作。

## 架构位置

该文件位于 Recipe 模块的示例和测试层:

- **层级**: 基础设施 / Recipe 示例和测试
- **功能域**: Run API 功能验证
- **覆盖范围**: 所有主要 API 方法
- **作用**: 使用文档和回归测试

## 主要类与结构体

### myfunc

辅助函数,用于演示 `run_once` 功能。

### RunSteps

主要执行函数,演示所有 Run API 特性。

### GenTests

测试用例生成器。

## 公共 API 函数

### myfunc

```python
def myfunc(api, i):
    api.run(api.step, 'run %d' % i, cmd=['echo', str(i)])
```

**功能**: 简单的辅助函数,执行 echo 命令。

**用途**: 演示 `run_once` 缓存机制

### RunSteps

```python
def RunSteps(api):
```

**功能**: 演示 Run API 的所有主要功能。

**执行流程**:

1. **失败处理测试**:
   ```python
   try:
       api.run(api.step, 'fail', cmd=['false'])
   except api.step.StepFailure:
       pass
   api.run(api.step, 'fail again', cmd=['false'], abort_on_failure=False)
   api.run(api.step, 'do a thing', cmd=['echo', 'do the thing'])
   assert len(api.run.failed_steps) == 2
   ```
   - 捕获第一个失败(abort_on_failure=True)
   - 第二个失败不中止(abort_on_failure=False)
   - 验证记录了 2 个失败步骤

2. **run_once 测试**:
   ```python
   for i in range(10):
       api.run.run_once(myfunc, api, i)
   ```
   - 循环调用 10 次
   - 只执行一次(返回缓存结果)
   - 验证缓存机制

3. **文件操作测试**:
   ```python
   api.run.readfile('myfile.txt')
   api.run.writefile('myfile.txt', 'contents')
   api.run.rmtree('mydir')
   api.run.asset_version('my_asset', api.vars.cache_dir.joinpath('work', 'skia'))
   ```
   - 读取文件
   - 写入文件
   - 删除目录
   - 获取资产版本

4. **环境变量测试**:
   ```python
   with api.context(env={'PATH': 'mydir:%(PATH)s'}):
       api.run(api.step, 'env', cmd=['env'])
   ```
   - 修改 PATH 环境变量
   - 验证环境变量合并

5. **重试机制测试**:
   ```python
   def between_attempts_fn(attempt):
       api.run(api.step, 'between_attempts #%d' % attempt,
               cmd=['echo', 'between_attempt'])

   try:
       api.run.with_retry(api.step, 'retry fail', 5, cmd=['false'],
                          between_attempts_fn=between_attempts_fn)
   except api.step.StepFailure:
       pass
   assert len(api.run.failed_steps) == 7  # 2 + 5

   api.run.with_retry(api.step, 'retry success', 3, cmd=['false'],
                      between_attempts_fn=between_attempts_fn)
   assert len(api.run.failed_steps) == 7  # 清理了重试的失败
   ```
   - 测试重试失败场景(5 次全失败)
   - 测试重试成功场景(第3次成功)
   - 验证失败记录清理逻辑
   - 测试 between_attempts_fn 回调

6. **最终检查**:
   ```python
   api.run.check_failure()
   ```
   - 抛出异常,因为有失败步骤

### GenTests

```python
def GenTests(api):
    buildername = 'Build-Win-Clang-x86_64-Release-Vulkan'
    yield (
        api.test('test') +
        api.properties(...) +
        api.platform('win', 64) +
        api.step_data('fail', retcode=1) +
        api.step_data('fail again', retcode=1) +
        api.step_data('retry fail', retcode=1) +
        # ... 重试步骤
        api.step_data('retry success', retcode=1) +
        api.step_data('retry success (attempt 2)', retcode=1)
    )
```

**功能**: 生成测试用例,模拟步骤失败。

**配置**:
- Windows 平台
- 多个步骤返回非零退出码
- 模拟重试场景

## 内部实现细节

### 依赖声明

```python
DEPS = [
    'recipe_engine/context',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/step',
    'run',
    'vars',
]
```

依赖 Recipe Engine 核心模块和 Skia 自定义模块。

### 失败场景测试

**第一个失败** (中止):
```python
try:
    api.run(api.step, 'fail', cmd=['false'])
except api.step.StepFailure:
    pass
```
- `abort_on_failure=True` (默认)
- 抛出异常,需要捕获

**第二个失败** (不中止):
```python
api.run(api.step, 'fail again', cmd=['false'], abort_on_failure=False)
```
- 记录失败但继续执行
- 不抛出异常

### run_once 验证

```python
for i in range(10):
    api.run.run_once(myfunc, api, i)
```

**预期行为**:
- 只有第一次调用实际执行 `myfunc`
- 后续 9 次返回缓存结果
- 测试期望输出只显示一个 'run 0' 步骤

**注意**: `run_once` 只基于函数名缓存,忽略参数 `i`

### 重试测试覆盖

**完全失败场景**:
- 尝试 5 次,全部失败
- 每次尝试间调用 `between_attempts_fn`
- 总共 5 个失败 + 之前的 2 个 = 7 个失败步骤

**部分成功场景**:
- 尝试 3 次,前 2 次失败,第 3 次成功
- 成功后清理前 2 次的失败记录
- 失败步骤数保持 7(未增加)

### 测试数据配置

```python
api.step_data('retry fail', retcode=1)
api.step_data('retry fail (attempt 2)', retcode=1)
api.step_data('retry fail (attempt 3)', retcode=1)
# ...
```

为每次重试尝试配置失败:
- 模拟真实的重试行为
- 验证重试次数和命名

## 依赖关系

### 模块依赖
- `run`: Run API 模块(被测试)
- `vars`: 变量管理
- `recipe_engine/*`: Recipe Engine 核心

### 数据流
1. 初始化变量
2. 执行各种 Run API 调用
3. 验证内部状态(失败计数)
4. 调用 `check_failure()` 触发异常

## 设计模式与设计决策

### 渐进式测试

按功能组织测试:
- 失败处理 → 缓存 → 文件操作 → 环境变量 → 重试
- 每个部分独立演示一个特性
- 便于理解和维护

### 断言验证

使用 `assert` 验证状态:
```python
assert len(api.run.failed_steps) == 2
assert len(api.run.failed_steps) == 7
```
- 明确的期望值
- 立即失败如果不符合

### 异常测试

显式测试异常场景:
- 捕获预期异常
- 验证异常抛出时机
- 确保错误处理正确

### 回调机制

演示 `between_attempts_fn`:
- 展示灵活性
- 常用于添加延迟或日志
- 提供扩展点

### 真实命令

使用真实的 shell 命令:
- `false`: 返回非零退出码
- `echo`: 输出文本
- `env`: 显示环境变量

提高测试真实性。

## 性能考量

### 测试执行

- **模拟模式**: 不实际执行命令
- **快速反馈**: 测试运行 <1 秒
- **无副作用**: 不创建文件或修改状态

### run_once 效率

演示缓存带来的性能提升:
- 10 次调用只执行 1 次
- 避免重复的昂贵操作

### 重试策略

展示重试对时间的影响:
- 5 次重试可能显著增加执行时间
- `between_attempts_fn` 可添加延迟
- 权衡可靠性与速度

## 相关文件

### 被测试模块
- `infra/bots/recipe_modules/run/api.py`: SkiaStepApi 实现
- `infra/bots/recipe_modules/run/__init__.py`: 模块入口

### Recipe Engine
- `recipe_engine/step.py`: 步骤执行
- `recipe_engine/file.py`: 文件操作
- `recipe_engine/context.py`: 上下文管理

### 测试基础设施
- `.recipes/*.expected/`: 测试期望输出
- Recipe Engine 测试框架

### 实际使用
- 几乎所有 Skia Recipe 文件
- 所有构建和测试模块

该文件是理解 Run API 的最佳资源,通过实际可执行的示例展示每个功能的正确使用方式,同时作为回归测试保护 API 稳定性。
