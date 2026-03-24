# create.py

> 源文件: infra/bots/assets/gcloud_linux/create.py

## 概述

`create.py` 用于创建完整的 Google Cloud SDK（gcloud）资产，包括核心 SDK 和多个模拟器组件。该资产为 Skia 的云基础设施测试提供本地开发环境。

## 架构位置

该资产为 Skia CI 系统提供 Google Cloud 工具和模拟器，用于测试与 GCS、Datastore、Bigtable、Pub/Sub 和 Firestore 的集成。

## 公共 API 函数

### create_asset(target_dir)
执行以下操作：
1. 下载 Google Cloud SDK (v343.0.0) tar.gz 包
2. 解压到目标目录（使用 `--strip-components=1` 移除顶层目录）
3. 安装额外组件（使用临时 HOME 环境变量）：
   - beta cloud-datastore-emulator
   - beta bigtable
   - pubsub-emulator
   - beta cloud-firestore-emulator
4. 修复 Firestore 模拟器 JAR 的可执行权限
5. 更新所有组件
6. 清理下载的 tarball

**关键实现**：
```python
env = os.environ.copy()
env["HOME"] = target_dir
gcloud_exe = os.path.join(target_dir, 'bin', 'gcloud')
subprocess.check_call([gcloud_exe, 'components', 'install', 'beta',
                       'cloud-datastore-emulator', '--quiet'], env=env)
```

## 内部实现细节

### 版本固定
```python
GCLOUD_ARCHIVE = 'google-cloud-sdk-343.0.0-linux-x86_64.tar.gz'
GCLOUD_URL = BASE_URL % GCLOUD_ARCHIVE
```
使用固定版本（343.0.0）确保可重复性和稳定性。

### 临时 HOME 目录
```python
env["HOME"] = target_dir
```
将 HOME 环境变量设置为目标目录，避免覆盖用户的 `~/.config/gcloud` 配置。这是一个重要的隔离措施。

### 组件安装
安装以下模拟器组件（以 `--quiet` 模式静默安装）：

1. **cloud-datastore-emulator**: NoSQL 数据库模拟器
2. **bigtable**: 分布式列式存储模拟器
3. **pubsub-emulator**: 消息队列模拟器
4. **cloud-firestore-emulator**: 文档数据库模拟器

### Firestore 权限修复
```python
fs_jar = 'platform/cloud-firestore-emulator/cloud-firestore-emulator.jar'
subprocess.check_call(['chmod', '+x', os.path.join(target_dir, fs_jar)])
```
解决 gcloud v250.0.0 和 Cloud Firestore Emulator v1.4.6 的已知 bug：JAR 文件需要可执行权限但默认没有设置。

### 组件更新
```python
subprocess.check_call([gcloud_exe, 'components','update', '--quiet'], env=env)
```
确保所有已安装组件更新到与 SDK 版本兼容的最新版本。

## 依赖关系

### 系统依赖
- **curl**: HTTPS 下载工具
- **tar**: tar.gz 解压工具
- **Java**: Firestore 和 Datastore 模拟器需要 Java 运行时

### Python 依赖
- 标准库：`argparse`, `glob`, `os`, `shutil`, `subprocess`

### 网络资源
- Google Cloud SDK 下载（~100-150 MB）
- 组件下载（总计 ~300-500 MB）

## 设计模式与设计决策

### 环境隔离
使用临时 HOME 目录防止污染用户配置：
- 避免冲突：不覆盖现有 gcloud 配置
- 清洁构建：每次创建独立的配置
- 安全性：不泄露用户凭证

### 完整模拟器套件
包含多个 GCP 服务的本地模拟器，支持：
- 离线开发和测试
- CI 环境中的集成测试
- 无需实际 GCP 资源的成本节约

### 自动化权限修复
主动修复已知的 Firestore 模拟器权限 bug，避免运行时错误。

## 性能考量

### 安装时间
- **SDK 下载**: 30-60 秒（~100 MB）
- **SDK 解压**: 10-20 秒
- **组件安装**: 2-5 分钟（多个大型组件）
- **组件更新**: 30-60 秒
- **总时间**: 4-7 分钟

### 磁盘空间
- SDK 基础: ~500 MB
- 模拟器组件: ~1 GB
- 总计: ~1.5 GB

### 网络带宽
- 总下载量: ~500-800 MB
- 建议: 稳定的网络连接

## 相关文件

### Google Cloud 文档
- **安装指南**: `https://cloud.google.com/sdk/docs/install`
- **脚本安装**: `https://cloud.google.com/sdk/docs/scripting-gcloud`
- **模拟器文档**: `https://cloud.google.com/sdk/gcloud/reference/beta/emulators`

### Skia 集成
- **`gsutil/create.py`**: 轻量级 GCS 工具资产
- **构建脚本**: 使用 gcloud 上传构建产物
- **测试脚本**: 使用模拟器进行集成测试

### 相关资产
- **`cockroachdb/create.py`**: 另一个数据库工具资产
