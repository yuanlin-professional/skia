# create.py

> 源文件: infra/bots/assets/go_win/create.py

## 概述

`create.py` 用于创建 Windows 平台的 Go 编程语言工具链资产。与 Linux 版本对应，为 Windows CI 机器提供 Go 编译器和工具。

## 架构位置

该资产为 Windows 构建机器提供 Go 工具链，用于编译基础设施代码和运行构建脚本。

## 公共 API 函数

### create_asset(target_dir)
从 Go 官网下载 Windows AMD64 版本的 Go 工具链（ZIP 格式）并解压。

**实现**：
```python
GO_URL = "https://go.dev/dl/go1.24.0.windows-amd64.zip"

def create_asset(target_dir):
    with utils.tmp_dir():
        cwd = os.getcwd()
        zipfile = os.path.join(cwd, 'go.zip')
        subprocess.check_call(["wget", '-O', zipfile, GO_URL])
        subprocess.check_call(["unzip", zipfile, "-d", target_dir])
```

## 内部实现细节

### 与 Linux 版本的差异

| 特性 | Linux | Windows |
|------|-------|---------|
| URL | `go1.24.0.linux-amd64.tar.gz` | `go1.24.0.windows-amd64.zip` |
| 格式 | tar.gz | zip |
| 解压工具 | tar | unzip |
| 可执行文件 | `go`, `gofmt` | `go.exe`, `gofmt.exe` |

### 版本同步
注释提醒需要与 Linux 版本保持同步：
```python
# Remember to also update the go asset when this is updated.
```

### 目录结构
解压后创建 `go/` 目录，包含：
```
<target_dir>/
└── go/
    ├── bin/
    │   ├── go.exe
    │   ├── gofmt.exe
    │   └── ...
    ├── src/
    ├── pkg/
    └── ...
```

## 依赖关系

- **wget**: 下载工具（Git for Windows 自带）
- **unzip**: ZIP 解压工具（Windows 10+ 内置）
- **`utils`**: Skia 工具模块

## 设计模式与设计决策

### ZIP 格式选择
Windows 使用 ZIP 而非 tar.gz：
- **原生支持**: Windows 原生支持 ZIP
- **工具可用性**: `unzip` 在 Git Bash 中可用
- **官方格式**: Go 官方为 Windows 提供 ZIP 包

### 版本一致性
与 Linux 版本使用相同的 Go 版本号（1.24.0），确保跨平台构建一致性。

## 性能考量

- **下载时间**: 30-60 秒（~140 MB）
- **解压时间**: 10-20 秒
- **总时间**: 1-2 分钟
- **磁盘空间**: ~500 MB

## 相关文件

- **`go/create.py`**: Linux 版本（需要同步更新）
- **`infra/bots/gen_tasks.go`**: 使用 Go 编译的任务生成器
- **Go 官网**: `https://go.dev/dl/`
