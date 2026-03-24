# GCS 镜像工具

> 源文件: `bazel/gcs_mirror/gcs_mirror.go`

## 概述

此工具将外部依赖文件下载、SHA256 校验后上传到 Skia 的 Google Cloud Storage (GCS) 镜像。它支持单文件模式和批量 JSON 模式，用于维护 Bazel 构建的依赖镜像，确保构建的可重现性和可靠性。

## 架构位置

位于 Bazel 基础设施工具 (`bazel/gcs_mirror/`) 中，是依赖管理流程的一部分。上传到 `gs://skia-cdn/bazel/` 存储桶。

## 主要类与结构体

### `urlEntry`
- `SHA256 string` - 文件的 SHA256 哈希
- `URL string` - 原始下载 URL

## 公共 API 函数

- `main()` - 命令行入口，支持 `--url`/`--sha256`、`--file`/`--sha256` 和 `--json` 三种模式
- `processJSON(workDir, b)` - 批量处理 JSON/Starlark 格式的依赖列表
- `processOneDownload(workDir, url, hash, addSuffix, noSuffix)` - 下载并上传单个文件
- `processOneLocalFile(file, hash)` - 上传本地文件
- `upload(ctx, contents, hash, suffix, metadataKey, metadataValue)` - 上传到 GCS

## 内部实现细节

- 使用内容寻址存储 (CAS)：文件以 SHA256 哈希命名，重复上传是幂等的
- `fixStarlarkComments` 将 Starlark 注释 (`#`) 转为 JSON 注释 (`//`)，支持从 Bazel 文件直接复制
- 支持的文件类型后缀：`.tar.gz`, `.tgz`, `.tar.xz`, `.deb`, `.zip`
- GCS 对象附加元数据记录原始来源 URL 或文件路径
- 使用 `json5` 解析器支持尾部逗号等宽松 JSON 语法

## 依赖关系

- `cloud.google.com/go/storage` - GCS 客户端
- `github.com/flynn/json5` - JSON5 解析器
- `go.skia.org/infra/go/skerr` - 错误处理

## 设计模式与设计决策

- **CAS 存储**：以内容哈希为文件名，确保相同内容只存储一份
- **先校验后上传**：下载后立即进行 SHA256 校验，防止供应链攻击
- **Starlark 兼容**：支持直接粘贴 Bazel 文件中的依赖列表

## 性能考量

下载和上传操作的性能取决于网络带宽，工具本身无特殊优化需求。

## 相关文件

- `WORKSPACE.bazel` - 引用镜像 URL 的 Bazel 工作区文件
