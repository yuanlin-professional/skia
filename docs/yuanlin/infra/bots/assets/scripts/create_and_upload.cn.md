# scripts 资产创建与上传脚本

> 源文件: infra/bots/assets/scripts/create_and_upload.py

## 概述

通用的资产创建和上传编排脚本，在临时目录中创建资产并上传。该脚本调用同目录的 create.py 和 upload.py，通过临时目录隔离构建过程，支持可选的 gsutil 工具路径配置。

## 架构位置

位于 `infra/bots/assets/scripts/`，这是一个通用脚本模板目录，其他资产包可以参考或继承这些脚本。

## 主要类与结构体

函数式风格，使用标准库和 Skia utils 模块。

## 公共 API 函数

### `main()`
执行流程：
1. 解析 `--gsutil` 可选参数
2. 创建临时目录
3. 在临时目录中调用 create.py
4. 调用 upload.py 上传资产
5. 捕获异常避免双重堆栈追踪

**实现**:
```python
with utils.tmp_dir():
    cwd = os.getcwd()
    subprocess.check_call(['python3', create_script, '-t', cwd])
    cmd = ['python3', upload_script, '-t', cwd]
    if args.gsutil:
        cmd.extend(['--gsutil', args.gsutil])
    subprocess.check_call(cmd)
```

## 内部实现细节

### 临时目录隔离

使用 `utils.tmp_dir()` 确保：
- 构建过程不污染源目录
- 异常时自动清理
- 并发安全

### 异常处理

捕获 CalledProcessError 并 exit(1)，避免打印两次堆栈追踪（子进程和父进程各一次）。

### Python 3 强制

使用 `python3` 而非 `python`，确保使用 Python 3 解释器。

## 设计模式与设计决策

这是一个标准的两阶段资产管理模式：创建 → 上传。临时目录模式确保构建产物不会意外提交到源代码仓库。

## 相关文件

- `create.py`: 资产创建逻辑
- `upload.py`: 资产上传逻辑
- `common.py`: 共享工具函数
