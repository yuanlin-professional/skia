# create.py

> 源文件: infra/bots/assets/go/create.py

## 概述

`create.py` 用于创建 Go 编程语言工具链资产（Linux AMD64 版本）。Skia 的基础设施代码（任务生成器、工具脚本等）大量使用 Go 语言编写，需要 Go 编译器和标准库。

## 架构位置

该资产为 Skia CI 系统提供 Go 工具链，用于编译和运行基础设施代码。

## 公共 API 函数

### create_asset(target_dir)
从 Go 官网下载 Linux AMD64 版本的 Go 工具链并解压到目标目录。

**实现**：
```python
GO_URL = "https://go.dev/dl/go1.24.0.linux-amd64.tar.gz"

def create_asset(target_dir):
    with utils.tmp_dir():
        cwd = os.getcwd()
        zipfile = os.path.join(cwd, 'go.tar.gz')
        subprocess.check_call(["wget", '-O', zipfile, GO_URL])
        subprocess.check_call(["tar", "-xzf", zipfile, "-C", target_dir])
```

## 内部实现细节

### Go 版本
```python
GO_URL = "https://go.dev/dl/go1.24.0.linux-amd64.tar.gz"
```
- **版本**: Go 1.24.0
- **平台**: linux-amd64
- **格式**: tar.gz 压缩归档

### 版本同步
脚本中的注释提醒：
```python
# Remember to also update the go_win asset when this is updated.
```
更新时需要同步更新 Windows 版本（`go_win/create.py`），确保跨平台一致性。

### 解压行为
使用 `tar -xzf` 解压到目标目录，创建 `go/` 子目录：
```
<target_dir>/
└── go/
    ├── bin/
    │   ├── go
    │   ├── gofmt
    │   └── ...
    ├── src/
    ├── pkg/
    └── ...
```

## 依赖关系

- **wget**: 下载工具
- **tar**: 解压工具（支持 gzip）
- **`utils`**: Skia 工具模块

## 设计模式与设计决策

### 官方二进制策略
下载 Go 官方预编译包而非从源代码编译：
- **简化**: 不需要 bootstrap Go 编译器
- **速度**: 下载和解压远快于编译（~5 分钟 vs. ~20 分钟）
- **可靠**: 官方构建经过充分测试

### 版本固定
硬编码 Go 版本确保：
- CI 环境一致性
- 避免语言特性变更导致的构建问题
- 手动控制升级时机

## 性能考量

- **下载时间**: 30-60 秒（~140 MB）
- **解压时间**: 10-20 秒
- **总时间**: 1-2 分钟
- **磁盘空间**: ~500 MB（解压后）

## 相关文件

- **`go_win/create.py`**: Windows 版本（需要同步更新）
- **`infra/bots/gen_tasks.go`**: 使用 Go 编译的任务生成器
- **`infra/bots/gen_tasks_logic/`**: Go 源代码目录
- **Go 官网**: `https://go.dev/dl/`
