# Mock 生成配置

> 源文件: bazel/exporter/interfaces/mocks/generate.go

## 概述

`generate.go` 文件是一个 Go 代码生成配置文件,使用 `go:generate` 指令自动生成接口的 mock 实现。该文件本身不包含可执行代码,而是通过 Go 工具链的代码生成机制,调用 mockery 工具为 `QueryCommand` 和 `FileSystem` 接口生成测试用的 mock 类。这些 mock 类用于单元测试中模拟接口行为,无需依赖真实的 Bazel 命令执行或文件系统操作。

## 架构位置

该文件位于 `bazel/exporter/interfaces/mocks` 包中,在测试基础设施层:

- **目标接口**: `QueryCommand` 和 `FileSystem`(定义在父包 `interfaces` 中)
- **生成工具**: mockery(通过 Bazel 运行)
- **生成产物**: `QueryCommand.go` 和 `FileSystem.go`(同目录下的 mock 实现)
- **使用场景**: 单元测试中替代真实实现

**代码生成流程**:
```
go generate → Bazel 运行 mockery → 读取接口定义 → 生成 mock 代码
```

## 主要类与结构体

该文件不包含类或结构体定义,只包含 `go:generate` 指令。

### go:generate 指令

```go
//go:generate bazelisk run //infra:mockery "--run_under=cd $PWD && " -- --name QueryCommand --srcpkg=go.skia.org/skia/bazel/exporter/interfaces --output ${PWD}
//go:generate bazelisk run //infra:mockery "--run_under=cd $PWD && " -- --name FileSystem --srcpkg=go.skia.org/skia/bazel/exporter/interfaces --output ${PWD}
```

**指令解析**:

**第一条指令**(生成 QueryCommand mock):
- `bazelisk run //infra:mockery`: 通过 Bazel 执行 mockery 工具
- `--run_under=cd $PWD &&`: 在当前目录下执行
- `--name QueryCommand`: 指定要 mock 的接口名称
- `--srcpkg=go.skia.org/skia/bazel/exporter/interfaces`: 接口所在的包路径
- `--output ${PWD}`: 输出到当前目录

**第二条指令**(生成 FileSystem mock):
- 参数同上,但 `--name FileSystem` 指定生成 FileSystem 接口的 mock

## 公共 API 函数

该文件不提供任何公共 API 函数,其作用是配置代码生成。

## 内部实现细节

### 代码生成触发

执行以下命令会触发 mock 代码生成:
```bash
cd bazel/exporter/interfaces/mocks
go generate
```

### mockery 工具

mockery 是一个流行的 Go mock 生成工具,能够:
- 解析 Go 接口定义
- 生成符合接口签名的 mock 结构体
- 提供方法调用记录和验证功能
- 支持返回值设置和参数匹配

### 生成的 mock 特性

生成的 mock 类(如 `QueryCommand.go` 和 `FileSystem.go`)包含:
- `mock.Mock` 嵌入,提供核心 mock 功能
- 接口的所有方法实现
- 每个方法调用 `_m.Called()` 记录调用信息
- 类型安全的返回值处理
- `New*()` 构造函数,自动注册清理函数

### Bazel 集成

使用 `bazelisk run //infra:mockery` 而非直接调用 `mockery`,确保:
- 版本一致性(由 Bazel 管理)
- 构建可重现性
- 依赖隔离

## 依赖关系

**工具依赖**:
- `go generate`: Go 标准工具链的代码生成命令
- `bazelisk`: Bazel 包装器,确保使用正确的 Bazel 版本
- `mockery`: Mock 生成工具(由 Bazel 目标 `//infra:mockery` 提供)

**接口依赖**:
- `go.skia.org/skia/bazel/exporter/interfaces.QueryCommand`
- `go.skia.org/skia/bazel/exporter/interfaces.FileSystem`

**生成产物**:
- `QueryCommand.go`: QueryCommand 接口的 mock 实现
- `FileSystem.go`: FileSystem 接口的 mock 实现

## 设计模式与设计决策

### 1. 代码生成模式 (Code Generation Pattern)

通过自动生成 mock 代码,避免手动编写和维护繁琐的 mock 实现。

**优势**:
- 减少样板代码
- 接口变更时自动更新 mock
- 降低维护成本
- 提高代码一致性

### 2. 构建时生成 vs 提交生成代码

Skia 项目选择将生成的 mock 代码提交到版本控制系统:

**优势**:
- 构建过程更快(无需每次生成)
- 代码审查时可以查看 mock 变更
- 不依赖外部工具进行构建

**权衡**:
- 需要记得在接口变更后重新生成
- 增加仓库大小

### 3. 依赖注入与可测试性

Mock 生成是依赖注入模式的配套基础设施:
- 接口定义抽象
- Mock 实现用于测试
- 真实实现用于生产

### 4. 约定优于配置

使用标准的 `go:generate` 指令和目录结构,遵循 Go 社区惯例。

## 性能考量

### 代码生成性能

- **生成时间**: 对于简单接口,生成时间在秒级
- **构建影响**: 生成的代码会增加编译时间,但影响很小
- **仓库大小**: 每个 mock 文件约 50-100 行,影响可忽略

### Mock 运行时性能

Mock 实现使用反射和接口,有轻微性能开销:
- 接口方法调用:动态分派
- 参数记录:内存分配
- 返回值处理:类型断言

**测试中的影响**:
- 单元测试通常不关注性能
- Mock 的灵活性远大于性能开销
- 如需性能测试,应使用真实实现或轻量级 fake

## 相关文件

**接口定义文件**:
- `bazel/exporter/interfaces/query_command.go` - QueryCommand 接口定义
- `bazel/exporter/interfaces/file_system.go` - FileSystem 接口定义

**生成的 Mock 文件**:
- `bazel/exporter/interfaces/mocks/QueryCommand.go` - QueryCommand mock 实现
- `bazel/exporter/interfaces/mocks/FileSystem.go` - FileSystem mock 实现

**Bazel 构建文件**:
- `//infra:mockery` - mockery 工具的 Bazel 目标定义

**使用示例**:

**重新生成 mock**:
```bash
cd bazel/exporter/interfaces/mocks
go generate
```

**在测试中使用 mock**:
```go
import (
    "testing"
    "github.com/stretchr/testify/mock"
    "go.skia.org/skia/bazel/exporter/interfaces/mocks"
)

func TestExporter(t *testing.T) {
    // 创建 mock
    mockFS := mocks.NewFileSystem(t)
    mockQry := mocks.NewQueryCommand(t)

    // 设置期望行为
    mockQry.On("Read").Return([]byte("query result"), nil)
    mockFS.On("OpenFile", "/path/to/file").Return(mockWriter, nil)

    // 执行测试代码
    exporter := NewExporter(mockFS)
    err := exporter.Export(mockQry)

    // 断言
    assert.NoError(t, err)
    mockQry.AssertExpectations(t)
    mockFS.AssertExpectations(t)
}
```

该文件虽然简短,但在测试基础设施中起着关键作用,通过自动化 mock 生成显著提升了测试代码的质量和开发效率。
