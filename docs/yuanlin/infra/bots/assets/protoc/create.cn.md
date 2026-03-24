# protoc 资产创建脚本

> 源文件: infra/bots/assets/protoc/create.py

## 概述

用于下载和准备 protoc（Protocol Buffers 编译器）Linux x86_64 版本的资产创建脚本。protoc 用于将 .proto 文件编译成各种语言的代码，Skia 的某些组件使用 Protocol Buffers 进行数据序列化。该脚本从 GitHub Releases 下载预编译的 protoc 3.3.0 zip 包并解压。

## 架构位置

位于 `infra/bots/assets/protoc/`，为 Skia 构建流程提供 Protocol Buffers 编译器，用于生成序列化和反序列化代码，主要用于性能数据收集和远程通信。

## 主要类与结构体

函数式风格脚本，使用 argparse 和 subprocess 模块。

### 模块级常量

```python
ZIP_URL = ('https://github.com/google/protobuf/releases/download/v3.3.0/'
           'protoc-3.3.0-linux-x86_64.zip')
```

固定使用 protoc 3.3.0 版本，这是一个稳定的早期版本，满足 Skia 的需求。

## 公共 API 函数

### `create_asset(target_dir)`

下载并解压 protoc 工具。

**执行流程**:
1. 使用 curl 下载 zip 包到 `/tmp/protoc.zip`
2. 使用 unzip 解压到目标目录

**实现**:
```python
def create_asset(target_dir):
    local_zip = '/tmp/protoc.zip'
    subprocess.check_call(['curl', '-L', ZIP_URL, '-o', local_zip])
    subprocess.check_call(['unzip', local_zip, '-d', target_dir])
```

### `main()`

解析 `--target_dir` 参数并调用 `create_asset()`。

## 内部实现细节

### protoc 包结构

解压后的目录结构：
```
target_dir/
├── bin/
│   └── protoc          # 主可执行文件
├── include/
│   └── google/
│       └── protobuf/   # .proto 头文件
└── readme.txt          # 说明文档
```

### 固定临时路径

使用 `/tmp/protoc.zip` 作为固定的临时文件路径。这种做法：
- **简单**: 无需临时文件管理
- **风险**: 并发执行可能冲突
- **清理**: 需要手动清理或依赖系统重启

更好的做法是使用 `tempfile.mktemp()` 或在完成后删除文件。

### 版本选择

使用 protoc 3.3.0（2017年发布）而非最新版本的原因：
- **稳定性**: 成熟的稳定版本
- **兼容性**: 与 Skia 使用的 proto 语法兼容
- **体积小**: 早期版本更轻量
- **足够**: 满足 Skia 的所有需求

Protocol Buffers 向后兼容性很好，3.x 版本可以读取新版本生成的消息。

### curl -L 参数

`-L` 参数让 curl 跟随 HTTP 重定向，这对 GitHub Releases 很重要，因为：
- GitHub 可能将下载重定向到 CDN
- 确保能够成功下载文件

## 依赖关系

### 外部工具

- **curl**: 文件下载，支持 HTTPS
- **unzip**: zip 文件解压

### 运行时依赖

protoc 二进制文件在 Linux x86_64 上运行需要：
- **glibc**: C 标准库
- **libstdc++**: C++ 标准库
- **libm**: 数学库

### Protocol Buffers 使用

Skia 可能在以下场景使用 protobuf：
- **性能指标**: 序列化性能数据
- **配置文件**: 结构化配置
- **远程通信**: 与其他服务通信

## 设计模式与设计决策

### 预编译二进制

下载预编译二进制而非从源码构建：
- **速度快**: 下载和解压只需几秒
- **简单**: 无需配置构建环境
- **一致**: 官方构建确保质量

从源码编译 protobuf 需要：
- autotools 工具链
- 10-30 分钟编译时间
- 更多依赖

### 无校验和验证

脚本不验证下载文件的校验和，依赖：
- HTTPS 传输层安全
- GitHub 的基础设施安全
- curl 的传输错误检测

**改进建议**: 添加 SHA256 校验以提升安全性。

### 固定路径临时文件

使用 `/tmp/protoc.zip` 而非随机临时文件：
- **简单**: 无需生成随机文件名
- **风险**: 并发冲突、安全问题
- **改进**: 使用 `tempfile` 模块

## 性能考量

### 下载和解压时间

- **文件大小**: protoc 3.3.0 zip 约 1-2 MB
- **下载时间**: 1-5 秒（取决于网络）
- **解压时间**: <1 秒
- **总时间**: 2-10 秒

非常快速，是获取 protoc 的高效方式。

### 资产体积

- **压缩**: ~1.5 MB
- **解压后**: ~3-4 MB

相比从源码构建（需要 ~100 MB 的构建工具），这是非常轻量的方案。

## 相关文件

### Protocol Buffers

- **`.proto 文件`**: Skia 中定义消息格式的文件（如果存在）
- **生成的代码**: protoc 生成的 .pb.h 和 .pb.cc 文件

### 构建集成

- **BUILD.gn**: 可能包含 proto 编译规则
- **gn/proto.gni**: Protocol Buffers 构建配置（如果存在）

### protobuf 库

Skia 可能还需要 protobuf 运行时库：
- **libprotobuf.so**: Protocol Buffers 运行时
- **protobuf-lite**: 轻量级版本

### 上游项目

- GitHub: https://github.com/protocolbuffers/protobuf
- 文档: https://developers.google.com/protocol-buffers
- v3.3.0 Release: https://github.com/protocolbuffers/protobuf/releases/tag/v3.3.0

### 使用示例

编译 proto 文件：
```bash
protoc --cpp_out=. message.proto
```

生成 Python 代码：
```bash
protoc --python_out=. message.proto
```

### 其他平台

如果需要其他平台的 protoc：
- **Windows**: `protoc-3.3.0-win32.zip`
- **macOS**: `protoc-3.3.0-osx-x86_64.zip`
- **Linux ARM**: 需要从源码构建

该脚本为 Skia 的数据序列化需求提供了快速轻量的 protoc 工具。
