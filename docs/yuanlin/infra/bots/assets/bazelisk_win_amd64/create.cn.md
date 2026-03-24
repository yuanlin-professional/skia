# Bazelisk Windows AMD64 资产创建脚本

> 源文件: infra/bots/assets/bazelisk_win_amd64/create.py

## 概述

这是一个用于下载和验证 Bazelisk Windows AMD64 版本的资产创建脚本。Bazelisk 是 Bazel 构建系统的包装工具，能够自动下载和使用项目所需的 Bazel 版本。该脚本从 GitHub Releases 下载特定版本的预编译二进制文件，验证其 SHA256 校验和以确保完整性和安全性，并设置适当的可执行权限。

## 架构位置

该脚本位于 Skia 基础设施资产管理系统的 `infra/bots/assets/bazelisk_win_amd64/` 目录。Bazelisk 资产用于 Skia 的 Bazel 构建流程，特别是在 Windows AMD64 平台上。它解决了不同项目可能需要不同 Bazel 版本的问题，通过读取 `.bazelversion` 文件自动选择正确的 Bazel 版本。该资产被 CI/CD 系统用于在 Windows 环境中执行 Bazel 构建任务。

## 主要类与结构体

脚本采用简洁的函数式编程风格，不包含自定义类。主要依赖 Python 标准库：

- **argparse**: 命令行参数解析
- **os**: 文件路径操作
- **subprocess**: 外部命令执行

### 模块级常量

```python
URL = 'https://github.com/bazelbuild/bazelisk/releases/download/v1.27.0/bazelisk-windows-amd64.exe'
SHA256 = 'd4b5e1cea61fcdb0bed60f8868c2e37684221b65feae898d1124482cd39ec89e'
BINARY = URL.split('/')[-1]  # 'bazelisk-windows-amd64.exe'
```

这些常量固定了要下载的 Bazelisk 版本和期望的文件完整性校验值。

## 公共 API 函数

### `create_asset(target_dir)`

核心资产创建函数，执行下载、验证和权限设置流程。

**参数**:
- `target_dir` (str): 存放下载文件的目标目录

**执行流程**:
1. 构建目标文件路径为 `target_dir/bazelisk.exe`
2. 使用 wget 下载二进制文件
3. 计算下载文件的 SHA256 校验和
4. 与预期的 SHA256 值比对，不匹配则抛出异常
5. 设置文件为可执行（所有用户可读、可执行）

**实现细节**:
```python
target_file = os.path.join(target_dir, 'bazelisk.exe')
subprocess.call(['wget', '--quiet', '--output-document', target_file, URL])
output = subprocess.check_output(['sha256sum', target_file], encoding='utf-8')
actual_hash = output.split(' ')[0]
if actual_hash != SHA256:
    raise Exception('SHA256 does not match (%s != %s)' % (actual_hash, SHA256))
subprocess.call(['chmod', 'ugo+x', target_file])
```

**安全机制**: SHA256 校验确保下载文件未被篡改，防止供应链攻击。

### `main()`

脚本入口函数，负责参数解析和函数调用。

**命令行参数**:
- `--target_dir, -t`: 必需参数，指定资产输出目录

## 内部实现细节

### 下载机制

使用 `wget` 而非 Python 库（如 `urllib` 或 `requests`）的原因：
- **简单性**: 无需处理 HTTP 细节
- **可靠性**: wget 久经考验，支持断点续传
- **一致性**: Skia 基础设施脚本统一使用 wget
- **静默模式**: `--quiet` 减少输出噪音

### 校验和验证

使用 SHA256 作为校验算法的优势：
- **安全性**: SHA256 是密码学安全的哈希算法
- **标准化**: GitHub Releases 提供 SHA256 校验和
- **碰撞抵抗**: 几乎不可能找到两个不同文件具有相同 SHA256 值

校验过程：
```python
output = subprocess.check_output(['sha256sum', target_file], encoding='utf-8')
# 输出格式: "hash_value  filename\n"
actual_hash = output.split(' ')[0]  # 提取哈希值
```

### 跨平台权限设置

虽然这是 Windows 二进制文件，但脚本在 Linux 环境中运行（Skia CI 主要使用 Linux）。`chmod ugo+x` 设置 Unix 风格的可执行权限，这在以下场景有用：
- CI 脚本在 Linux 容器中准备资产
- 资产包被复制到 Windows 环境时保留元数据
- 跨平台构建流程的一致性

### 文件重命名策略

下载的文件名为 `bazelisk-windows-amd64.exe`，但重命名为 `bazelisk.exe`。这种简化：
- 统一不同平台的可执行文件名
- 简化脚本和配置
- 提升用户体验

## 依赖关系

### 外部工具依赖

- **wget**: 文件下载工具，需在系统 PATH 中
- **sha256sum**: 校验和计算工具，GNU coreutils 的一部分

### 运行时依赖

- **Python 3**: shebang 指定 `python3`
- **网络连接**: 访问 GitHub Releases

### 资产依赖

下载的 Bazelisk 二进制文件在 Windows 上运行时需要：
- Windows 7 或更高版本
- Visual C++ 运行时库（通常已预装）

## 设计模式与设计决策

### 版本固定策略

脚本固定使用 Bazelisk v1.27.0，而非动态获取最新版本。这种选择的权衡：

**优点**:
- **可重现性**: 确保构建结果一致
- **稳定性**: 避免新版本引入的破坏性变更
- **测试可控**: 版本升级需要显式测试

**缺点**:
- **维护负担**: 需要手动更新版本
- **安全风险**: 旧版本可能存在已知漏洞

### 校验和硬编码

SHA256 值直接硬编码在脚本中，而非从外部文件读取。这种设计：
- **简单性**: 无需额外的配置文件
- **安全性**: 防止配置文件被篡改
- **原子性**: 版本和校验和作为整体更新

### 错误处理策略

脚本使用简单的异常抛出处理校验失败：
```python
if actual_hash != SHA256:
    raise Exception('SHA256 does not match (%s != %s)' % (actual_hash, SHA256))
```

这种处理方式：
- 立即失败，不继续执行
- 提供清晰的错误消息
- 显示期望值和实际值便于调试

### subprocess 调用方式

混合使用 `call` 和 `check_output`：
- `subprocess.call()`: 用于 wget 和 chmod，不需要捕获输出
- `subprocess.check_output()`: 用于 sha256sum，需要解析输出

这种区分提升了代码的清晰度和性能。

## 性能考量

### 下载速度

性能瓶颈主要是网络下载：
- **文件大小**: Bazelisk 约 10-20 MB
- **下载时间**: 取决于网络带宽，通常 5-30 秒
- **优化**: wget 支持并行下载和断点续传（未启用）

### 校验开销

SHA256 计算性能：
- **算法复杂度**: O(n)，n 为文件大小
- **实际时间**: 10-20 MB 文件约 100-200ms
- **影响**: 可忽略，相比下载时间

### 整体执行时间

典型执行时间分解：
- 下载: 5-30 秒（主要瓶颈）
- 校验: <0.5 秒
- 权限设置: <0.1 秒
- 总计: 5-30 秒

### 优化建议

潜在优化方向：
1. **本地缓存**: 缓存已验证的文件，避免重复下载
2. **并行下载**: wget 支持 `-N` 参数，仅在文件更新时下载
3. **镜像源**: 使用地理位置更近的镜像加速下载
4. **压缩传输**: 使用 gzip 压缩传输（需服务端支持）

## 相关文件

### 同系列资产脚本

- **`infra/bots/assets/bazelisk_linux_arm64/create.py`**: Linux ARM64 版本
- **`infra/bots/assets/bazelisk_mac_arm64/create.py`**: macOS ARM64 版本
- **`infra/bots/assets/bazelisk_linux_amd64/create.py`**: Linux AMD64 版本

这些脚本结构几乎相同，只是 URL 和 SHA256 不同。

### 资产管理文件

- **`infra/bots/assets/bazelisk_win_amd64/VERSION`**: 资产版本标识
- **`infra/bots/assets/bazelisk_win_amd64/download.py`**: 下载脚本
- **`infra/bots/assets/bazelisk_win_amd64/upload.py`**: 上传脚本

### Bazel 构建配置

- **`.bazelversion`**: 项目根目录的 Bazel 版本指定文件
- **`WORKSPACE`**: Bazel 工作空间定义
- **`BUILD.bazel`**: Bazel 构建规则

### 使用该资产的任务

- **`infra/bots/tasks.json`**: CI 任务定义，指定使用 Bazelisk 的任务
- **`infra/bots/recipes/`**: 构建配方，调用 Bazelisk 执行构建

### Bazelisk 上游项目

- GitHub: https://github.com/bazelbuild/bazelisk
- 文档: https://github.com/bazelbuild/bazelisk/blob/master/README.md

该脚本是 Skia 使用 Bazel 构建系统的关键基础设施组件，确保所有开发者和 CI 环境使用一致的 Bazel 版本。
