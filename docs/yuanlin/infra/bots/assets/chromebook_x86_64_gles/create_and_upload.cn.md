# create_and_upload.py

> 源文件: infra/bots/assets/chromebook_x86_64_gles/create_and_upload.py

## 概述

`create_and_upload.py` 是用于创建和上传 Chromebook x86_64 GLES 资产的自动化脚本，负责协调资产创建并上传到 CIPD 系统。

## 架构位置

```
infra/bots/assets/chromebook_x86_64_gles/
├── create_and_upload.py          # 本文件：上传入口
├── create.py                     # 资产创建逻辑
└── __init__.py                   # 包标识
```

## 公共 API 函数

### main()
协调资产创建和上传流程，功能包括：
1. 验证运行平台为 Linux
2. 解析 `--lib_path` 参数（必需）
3. 通过环境变量 `CHROMEBOOK_X86_64_GLES_LIB_PATH` 传递路径给 `create.py`
4. 定位 `sk` 工具（位于 `<SKIA_ROOT>/bin/sk`）
5. 调用 `sk asset upload chromebook_x86_64_gles`

## 内部实现细节

### 环境变量传递机制
由于资产创建通过 `sk` 工具间接调用 `create.py`，无法直接传递参数，使用环境变量作为进程间通信：
```python
os.environ[create.ENV_VAR] = args.lib_path
```

### 工具路径导航
```python
sk = os.path.realpath(os.path.join(
    FILE_DIR, os.pardir, os.pardir, os.pardir, os.pardir, 'bin', 'sk'))
```
通过相对路径从当前资产目录导航到 Skia 根目录的 `bin/sk`，支持 Windows（添加 `.exe` 后缀）。

## 依赖关系

- **`sk` 工具**: Skia 资产管理 CLI（通过 `bin/fetch-sk` 获取）
- **`create.py`**: 同目录的资产创建实现
- **Linux 系统**: 必须在 Linux 上运行（包管理操作）

## 设计模式与设计决策

### 职责分离
- **create_and_upload.py**: 处理外部接口和工具调用
- **create.py**: 封装资产创建的具体逻辑
- **sk 工具**: 处理 CIPD 交互

### 平台限制
明确限制只在 Linux 运行，避免在不支持的平台出现难以诊断的错误。

## 性能考量

- **执行时间**: 2-5 分钟（取决于网络速度）
- **I/O 密集**: 包下载、文件复制、网络上传
- **磁盘空间**: ~100 MB 临时文件

## 相关文件

- **`create.py`**: 实际的资产创建实现
- **`chromebook_arm_gles/create_and_upload.py`**: ARM 版本
- **`chromebook_arm64_gles/create_and_upload.py`**: ARM64 版本
- **`infra/bots/gen_tasks_logic/gen_tasks_logic.go`**: 引用该资产的构建任务
