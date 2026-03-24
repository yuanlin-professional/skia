# calmbench.py

> 源文件: tools/calmbench/calmbench.py

## 概述

`calmbench.py` 是 Skia 性能基准测试系统的用户友好入口脚本。它封装了底层的 A/B 测试工具 `ab.py`，提供了简洁的命令行接口来比较不同 Git 分支的性能差异。该脚本自动化了编译、测试和结果分析的完整流程，让开发者能够轻松检测代码变更是否引入性能回归。

该工具特别适用于持续集成环境和本地开发测试，可以在提交代码前快速验证性能影响。

## 架构位置

该文件位于 Skia 性能测试工具集的顶层：

```
skia/
  tools/
    calmbench/
      calmbench.py    # 本文件（用户入口脚本）
      ab.py           # 底层 A/B 测试引擎
    nanobench/        # 底层性能测试工具
  out/
    Release/          # 编译输出目录
      nanobench       # nanobench 二进制
```

在 Skia 开发流程中的位置：
- **开发层**: 开发者的直接接口
- **编译层**: 自动编译不同分支的 nanobench
- **测试层**: 驱动 ab.py 执行性能测试
- **CI/CD 层**: 集成到持续集成流程

## 主要类与结构体

该脚本是过程式设计，不定义类，仅包含函数。

## 公共 API 函数

### parse_args()

```python
def parse_args():
    parser = ArgumentParser(
        description='Noiselessly (hence calm) becnhmark a git branch against ' +
                    'another baseline branch (e.g., main) using multiple ' +
                    ' nanobench runs.'
    )
    # 定义参数
    return args
```

**功能**: 解析命令行参数并返回配置对象。

**关键参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `branch` | str | 必填 | 要测试的分支名，或 'modified' 表示当前修改 |
| `--config` | str | '8888' | nanobench 配置（8888, gl, vulkan 等） |
| `--skiadir` | str | 自动检测 | Skia 源码目录 |
| `--ninjadir` | str | 'out/Release' | Ninja 编译输出目录 |
| `--writedir` | str | '/var/tmp' | 临时文件和输出目录 |
| `--extraarg` | str | '' | nanobench 额外参数 |
| `--baseline` | str | 'main' | 基线分支 |
| `--basearg` | str | '' | 基线分支的 nanobench 参数 |
| `--reps` | int | 2 | 初始重复次数 |
| `--threads` | int | CPU核心数/2 | 并发线程数 |
| `--no-compile` | flag | False | 跳过编译，复用已有二进制 |
| `--skip-base` | flag | False | 跳过基线分支测试，复用旧数据 |
| `--noinit` | flag | False | 跳过初始化运行 |
| `--concise` | flag | False | 简洁输出，不显示详细进度 |
| `--githash` | str | '' | Git 哈希值（机器人用） |
| `--keys` | list | [] | 额外的键值对（机器人用） |

**自动推导**:
```python
default_threads = max(1, multiprocessing.cpu_count() / 2)
default_skiadir = os.path.normpath(CURRENT_DIR + "/../../")
```

### nano_path(args, branch)

```python
def nano_path(args, branch):
    return args.writedir + '/nanobench_' + branch
```

**功能**: 生成指定分支的 nanobench 二进制路径。

**示例**:
- `nano_path(args, 'test_branch')` → `/var/tmp/nanobench_test_branch`

### compile_branch(args, branch)

```python
def compile_branch(args, branch):
    print("Compiling branch %s" % args.branch)
    commands = [
        ['git', 'checkout', branch],
        ['ninja', '-C', args.ninjadir, 'nanobench'],
        ['cp', args.ninjadir + '/nanobench', nano_path(args, branch)]
    ]
    for command in commands:
        subprocess.check_call(command, cwd=args.skiadir)
```

**功能**: 编译指定分支的 nanobench。

**流程**:
1. 切换到指定分支
2. 使用 Ninja 编译 nanobench
3. 复制二进制到临时目录（避免被后续切换覆盖）

### compile_modified(args)

```python
def compile_modified(args):
    print("Compiling modified code")
    # 编译当前修改
    subprocess.check_call(
        ['ninja', '-C', args.ninjadir, 'nanobench'], cwd=args.skiadir)
    subprocess.check_call(
        ['cp', args.ninjadir + '/nanobench', nano_path(args, args.branch)],
        cwd=args.skiadir)

    print("Compiling stashed code")
    stash_output = subprocess.check_output(['git', 'stash'], cwd=args.skiadir)
    if 'No local changes to save' in stash_output:
        subprocess.check_call(['git', 'reset', 'HEAD^', '--soft'])
        subprocess.check_call(['git', 'stash'])

    subprocess.check_call(['gclient', 'sync'], cwd=args.skiadir)
    # 编译 stash 前的代码
    subprocess.check_call(
        ['ninja', '-C', args.ninjadir, 'nanobench'], cwd=args.skiadir)
    subprocess.check_call(
        ['cp', args.ninjadir + '/nanobench', nano_path(args, args.baseline)],
        cwd=args.skiadir)
    subprocess.check_call(['git', 'stash', 'pop'], cwd=args.skiadir)
```

**功能**: 编译当前修改的代码和 stash 前的代码。

**特殊处理**:
- 如果没有本地修改，使用 `git reset HEAD^ --soft` 创建可 stash 的状态
- 使用 `gclient sync` 同步依赖
- 恢复 stash 保持工作目录不变

### compile_nanobench(args)

```python
def compile_nanobench(args):
    if args.branch == 'modified':
        compile_modified(args)
    else:
        compile_branch(args, args.branch)
        compile_branch(args, args.baseline)
```

**功能**: 根据分支类型选择编译策略。

**分支类型**:
- `modified`: 编译当前修改 vs stash 前代码
- 其他: 编译指定分支 vs 基线分支

### main()

```python
def main():
    args = parse_args()

    # 复制 ab.py 到临时目录（避免 git 切换时丢失）
    orig_ab_name = CURRENT_DIR + "/" + AB_SCRIPT
    temp_ab_name = args.writedir + "/" + AB_SCRIPT
    subprocess.check_call(['cp', orig_ab_name, temp_ab_name])

    if not args.no_compile:
        compile_nanobench(args)

    # 构造 ab.py 命令
    command = [
        'python',
        temp_ab_name,
        args.writedir,
        args.branch + ("_A" if args.branch == args.baseline else ""),
        args.baseline + ("_B" if args.branch == args.baseline else ""),
        nano_path(args, args.branch),
        nano_path(args, args.baseline),
        args.extraarg,
        args.basearg,
        str(args.reps),
        "true" if args.skipbase else "false",
        args.config,
        str(args.threads if args.config in ["8888", "565"] else 1),
        "true" if args.noinit else "false"
    ]

    if args.githash:
        command += ['--githash', args.githash]
    if args.keys:
        command += (['--keys'] + args.keys)
    if args.concise:
        command.append("--concise")

    # 执行 ab.py
    p = subprocess.Popen(command, cwd=args.skiadir)
    try:
        p.wait()
    except KeyboardInterrupt:
        try:
            p.terminate()
        except OSError as e:
            print(e)
```

**功能**: 主流程协调器。

**流程**:
1. 解析参数
2. 备份 ab.py 到临时目录
3. 编译 nanobench（可选）
4. 构造并执行 ab.py 命令
5. 处理键盘中断

## 内部实现细节

### 默认配置推导

```python
default_threads = max(1, multiprocessing.cpu_count() / 2)
default_skiadir = os.path.normpath(CURRENT_DIR + "/../../")
```

**逻辑**:
- 线程数默认为 CPU 核心数的一半（避免过载）
- Skia 目录通过相对路径推导（假设在 `tools/calmbench/` 下）

### Config 特定线程数

```python
str(args.threads if args.config in ["8888", "565"] else 1)
```

**原因**:
- CPU 渲染器（8888, 565）支持多线程
- GPU 渲染器（gl, vulkan）单线程避免资源竞争

### 分支名后缀处理

```python
args.branch + ("_A" if args.branch == args.baseline else "")
args.baseline + ("_B" if args.branch == args.baseline else "")
```

**目的**:
- 如果测试分支和基线相同，添加后缀区分
- 避免输出文件名冲突

### Git Stash 特殊处理

```python
stash_output = subprocess.check_output(['git', 'stash'], cwd=args.skiadir)
if 'No local changes to save' in stash_output:
    subprocess.check_call(['git', 'reset', 'HEAD^', '--soft'])
    subprocess.check_call(['git', 'stash'])
```

**场景**:
- 如果已经 commit 但未 push，需要先 soft reset 创建修改
- 确保总能创建可比较的基线版本

### 键盘中断处理

```python
except KeyboardInterrupt:
    try:
        p.terminate()
    except OSError as e:
        print(e)
```

**优雅退出**:
- 捕获 Ctrl+C
- 终止子进程
- 忽略已退出进程的异常

## 依赖关系

**标准库依赖**:
- `os`: 路径操作
- `sys`: 系统交互
- `subprocess`: 执行外部命令
- `multiprocessing`: CPU 核心数检测
- `argparse`: 命令行参数解析

**外部工具依赖**:
- `git`: Git 版本控制
- `ninja`: 构建系统
- `gclient`: Chromium 依赖管理工具
- `python`: Python 解释器（执行 ab.py）
- `nanobench`: Skia 性能测试工具

**内部依赖**:
- `ab.py`: A/B 测试引擎

**依赖图**:
```
用户命令行
    ↓
calmbench.py (本文件)
    ↓
git + ninja → 编译 nanobench
    ↓
ab.py → 执行性能测试
    ↓
性能回归报告
```

## 设计模式与设计决策

### 设计模式

1. **门面模式**: 封装复杂的 ab.py 接口
2. **模板方法**: `compile_nanobench` 根据分支类型选择策略
3. **命令模式**: 构造并执行 ab.py 命令

### 设计决策

**1. 备份 ab.py 到临时目录**:
```python
subprocess.check_call(['cp', orig_ab_name, temp_ab_name])
```
- 原因: Git 切换分支可能改变或删除 ab.py
- 确保测试过程中脚本不变

**2. 分离测试分支和基线分支**:
- 独立编译，避免相互覆盖
- 临时目录存储二进制

**3. 'modified' 特殊分支**:
- 支持测试未提交的代码
- 自动对比 stash 前状态
- 便于开发过程中的快速验证

**4. Config 特定线程策略**:
- CPU 渲染多线程提速
- GPU 渲染单线程避免竞争

**5. 默认参数优化用户体验**:
- 合理的默认值（2 次重复，8888 config）
- 自动检测 Skia 目录和线程数

**6. 机器人参数支持**:
- `--githash`, `--keys` 用于 CI 系统
- 可扩展的元数据支持

**7. 优雅的键盘中断处理**:
- 用户可随时终止长时间测试
- 子进程正确清理

### 用户友好设计

**简洁命令行**:
```bash
python calmbench.py test_branch
```
自动使用默认配置。

**完整命令行**:
```bash
python calmbench.py test_branch --config gl \
    --extraarg "--svgs ~/svgs --skps ~/skps" \
    --baseline main --threads 4
```

**README 提示**:
```python
README = """
Simply run
    python {0} TEST_GIT_BRANCH
to see if TEST_GIT_BRANCH has performance regressions against main in 8888.
"""
```

## 性能考量

### 时间开销

| 阶段 | 时间 | 说明 |
|------|------|------|
| 编译 nanobench | 1-3 分钟 | 取决于机器性能 |
| 初始测试 | 5-20 分钟 | 取决于基准测试数量和线程数 |
| 迭代测试 | 0-30 分钟 | 取决于可疑回归数量 |
| 总计 | 6-50 分钟 | 典型场景 10-30 分钟 |

### 优化策略

1. **复用编译结果**: `--no-compile`
2. **复用基线数据**: `--skip-base`
3. **跳过初始化**: `--noinit`（不推荐）
4. **多线程并行**: 自动检测 CPU 核心数

### 磁盘占用

- nanobench 二进制: ~50-100 MB
- 测试输出文件: ~1-10 MB
- 总计: ~100-200 MB（可接受）

## 相关文件

### 同目录文件
- `tools/calmbench/ab.py`: A/B 测试引擎
- `tools/calmbench/README.md`: 使用文档（如果存在）

### Skia 构建系统
- `out/Release/nanobench`: 编译输出
- `BUILD.gn`: Skia 构建配置
- `.gn`: GN 配置根

### 性能测试工具
- `tools/nanobench/`: nanobench 源代码
- `bench/`: 基准测试用例集

### CI/CD 配置
- `infra/bots/`: CI 机器人配置
- 性能监控仪表板

### 输出文件（推测）
- `/var/tmp/nanobench_{branch}`: nanobench 二进制
- `/var/tmp/{branch}.out{i}`: 测试输出文件
- `/var/tmp/report.json`: 回归报告

### 使用示例

**基本用法**:
```bash
# 测试当前分支对比 main
python tools/calmbench/calmbench.py my_feature_branch

# 测试未提交的修改
python tools/calmbench/calmbench.py modified

# 使用 GL 配置测试
python tools/calmbench/calmbench.py my_feature --config gl

# 包含 SVG 和 SKP 资源
python tools/calmbench/calmbench.py my_feature \
    --extraarg "--svgs ~/svgs --skps ~/skps"
```

**高级用法**:
```bash
# 快速迭代（复用编译和基线数据）
python tools/calmbench/calmbench.py my_feature \
    --no-compile --skip-base

# 指定自定义基线
python tools/calmbench/calmbench.py new_feature \
    --baseline stable_branch

# 机器人模式
python tools/calmbench/calmbench.py test_branch \
    --githash abc123 --keys arch arm64 os android
```
