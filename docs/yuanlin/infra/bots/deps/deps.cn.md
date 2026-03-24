# DEPS 依赖查询包 (deps.go)

> 源文件: `infra/bots/deps/deps.go`

## 概述

此文件定义了 `deps` Go 包，提供了查询 Skia DEPS 文件中声明的外部依赖的功能。它将 Chromium 风格的 `DEPS` 文件中的依赖信息转化为可在 Go 代码中类型安全访问的 API。核心函数 `Get` 接受一个依赖名称，返回该依赖的版本、路径等信息。该包的底层数据由 `generate.go` 代码生成器自动生成。

## 架构位置

此文件位于 Skia 基础设施的依赖管理层：

- **层级**: 依赖查询 API 层
- **消费者**: 需要在 Go 代码中查询 Skia 外部依赖版本的基础设施工具
- **数据来源**: 由 `generate.go` 从 `DEPS` 文件自动生成（通过 `go generate`）
- **生成指令**: `//go:generate bazelisk run //:go -- run ./generate.go`

## 主要类与结构体

| 名称 | 类型 | 说明 |
|------|------|------|
| `deps` | 包级变量 | 自动生成的依赖数据（类型未在此文件中显式定义，由生成代码提供） |

## 公共 API 函数

### `Get(dep string) (*deps_parser.DepsEntry, error)`

查询指定名称的依赖项信息。

- **参数**: `dep` -- 依赖名称（如仓库 URL 或路径）
- **返回值**:
  - `*deps_parser.DepsEntry` -- 包含 `Id`（标识符）、`Version`（版本/commit hash）、`Path`（本地路径）的结构体指针
  - `error` -- 依赖不存在时返回错误
- **特性**: 返回的是数据副本，防止调用者修改包内部状态
- **依赖名称规范化**: 内部使用 `deps_parser.NormalizeDep` 对名称进行标准化

## 内部实现细节

- **go:generate 指令**: `//go:generate bazelisk run //:go -- run ./generate.go` 使用 Bazel 管理的 Go 工具链运行代码生成器
- **防御性复制**: `Get` 函数返回 `DepsEntry` 的副本（`&deps_parser.DepsEntry{...}`），而非直接返回包内部数据的指针，这是一种常见的不可变性保护模式
- **依赖名称规范化**: `deps_parser.NormalizeDep` 将依赖名称统一为标准格式（可能包括去除 `.git` 后缀、统一 URL scheme 等），错误消息中同时显示原始名称和规范化后的名称
- **nil 检查**: 当 `deps.Get(dep)` 返回 nil 时，表示依赖不存在，返回描述性错误

## 依赖关系

- **go.skia.org/infra/go/depot_tools/deps_parser** -- DEPS 文件解析库，提供 `DepsEntry` 类型和 `NormalizeDep` 函数
- **go.skia.org/infra/go/skerr** -- Skia 错误格式化库
- **generate.go** -- 代码生成器（同目录下，通过 `go generate` 触发）
- **自动生成代码** -- 包含实际的 `deps` 变量定义（由 generator 生成）

## 设计模式与设计决策

- **代码生成 + 类型安全**: 通过代码生成将文本格式的 DEPS 文件转为 Go 代码，获得编译时类型检查
- **防御性复制**: 返回副本而非引用，防止调用者意外修改共享数据
- **Bazel + Go Generate**: 使用 Bazel 管理的 Go 工具链执行代码生成，确保工具链版本一致
- **错误信息丰富性**: 错误消息同时包含原始输入和规范化结果，便于调试依赖名称不匹配的问题

## 性能考量

- 依赖数据在包初始化时加载到内存中，`Get` 查询是 O(1) 或 O(n) 的内存操作
- 返回副本有微小的内存分配开销，但保证了数据安全性
- 代码生成发生在构建前而非运行时，不影响运行时性能

## 相关文件

- `infra/bots/deps/generate.go` -- 代码生成器程序
- `DEPS` -- Skia 根目录的依赖声明文件
- `go.skia.org/infra/go/depot_tools/deps_parser` -- DEPS 解析库
- `go.skia.org/infra/go/skerr` -- 错误处理库
