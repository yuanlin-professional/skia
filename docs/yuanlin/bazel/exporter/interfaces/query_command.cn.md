# QueryCommand

> 源文件: bazel/exporter/interfaces/query_command.go

## 概述

`query_command.go` 文件定义了用于执行和获取 Bazel 查询命令响应数据的接口。`QueryCommand` 接口抽象了 Bazel 的 `query` 和 `cquery` 命令的执行过程,使得导出器可以从不同的数据源(实际命令执行、缓存文件、测试数据等)获取构建信息,而无需关心数据获取的具体实现细节。

## 架构位置

该文件位于 `bazel/exporter/interfaces` 包中,在 Bazel 导出系统的架构中扮演数据源抽象层的角色:

- **上层调用者**: `Exporter` 接口的实现类,需要查询数据来完成导出操作
- **实现层**: 具体的查询命令执行器(如执行真实的 `bazel cquery` 命令,或从文件读取缓存的查询结果)
- **数据流**: Bazel 构建系统 → QueryCommand 实现 → 导出器 → 目标项目格式

该接口通过依赖倒置原则,使得高层的导出逻辑不依赖于底层的数据获取方式,提高了系统的灵活性和可测试性。

## 主要类与结构体

### QueryCommand 接口

```go
type QueryCommand interface {
    Read() ([]byte, error)
}
```

**功能**: 定义了获取 Bazel 查询或配置查询(cquery)响应数据的统一接口。

**职责**:
- 封装 Bazel 查询命令的执行和数据读取逻辑
- 返回查询结果的原始字节数据(通常是 Protocol Buffer 格式)
- 处理查询过程中可能出现的错误

**典型使用场景**:
- 获取 Bazel 构建图(build graph)信息
- 查询目标依赖关系
- 获取构建规则的配置信息
- 在测试中提供模拟的查询数据

## 公共 API 函数

### Read 方法

```go
Read() ([]byte, error)
```

**功能**: 执行 Bazel 查询命令并返回响应数据。

**返回值**:
- `[]byte`: 查询结果的原始字节数据,通常是序列化的 Protocol Buffer 格式
- `error`: 查询执行失败时的错误信息,成功则返回 `nil`

**可能的错误类型**:
- 命令执行错误(Bazel 未安装、命令语法错误)
- I/O 错误(文件读取失败、网络超时)
- 数据格式错误(Protocol Buffer 解析失败)
- 权限错误(无法访问 Bazel 工作空间)

**数据格式**:
返回的字节数据通常对应 Bazel 的 `build.proto` 定义的消息格式,包含目标(target)、规则(rule)、属性(attribute)等构建元数据。

## 内部实现细节

该文件只包含接口定义,具体实现由实现类提供。典型的实现方式包括:

### 1. 命令执行实现

```go
type BazelQueryCommand struct {
    workspace string
    query     string
}

func (b *BazelQueryCommand) Read() ([]byte, error) {
    cmd := exec.Command("bazel", "cquery", b.query, "--output=proto")
    cmd.Dir = b.workspace
    return cmd.Output()
}
```

### 2. 文件缓存实现

```go
type CachedQueryCommand struct {
    cachePath string
}

func (c *CachedQueryCommand) Read() ([]byte, error) {
    return os.ReadFile(c.cachePath)
}
```

### 3. 测试 Mock 实现

```go
type MockQueryCommand struct {
    data []byte
    err  error
}

func (m *MockQueryCommand) Read() ([]byte, error) {
    return m.data, m.err
}
```

## 依赖关系

**直接依赖**:
- 无直接依赖(纯接口定义)

**被依赖关系**:
- `Exporter` 接口将 `QueryCommand` 作为参数,依赖此接口获取数据
- `bazel/exporter/interfaces/mocks/QueryCommand.go` 提供 mock 实现用于测试

**数据流依赖**:
```
Bazel 构建系统
    ↓
QueryCommand 实现
    ↓
Exporter 实现
    ↓
目标项目格式文件
```

## 设计模式与设计决策

### 1. 命令模式 (Command Pattern)

`QueryCommand` 接口封装了查询请求,将请求的发起者(导出器)与请求的执行者(Bazel 命令)解耦。

**优势**:
- 调用者无需知道命令如何执行
- 支持命令的延迟执行
- 便于实现命令队列和缓存

### 2. 策略模式 (Strategy Pattern)

不同的 `QueryCommand` 实现代表不同的查询策略(实时查询、缓存查询、测试数据等)。

**优势**:
- 运行时可切换查询策略
- 易于添加新的查询数据源
- 测试时可替换为 mock 实现

### 3. 单一职责原则 (SRP)

接口只包含一个方法 `Read()`,职责明确:获取查询数据。

**优势**:
- 接口简单易实现
- 易于理解和维护
- 减少接口变更的影响范围

### 4. 依赖倒置原则 (DIP)

高层模块(导出器)依赖于抽象接口而非具体实现。

**优势**:
- 提高代码的可测试性
- 降低模块间的耦合度
- 支持多种数据源实现

## 性能考量

### 1. 数据获取开销

- **实时查询**: 每次调用 `Read()` 都会执行 Bazel 命令,耗时较长(秒级)
- **缓存查询**: 从文件读取,耗时较短(毫秒级)
- **内存缓存**: 最快,但需要额外的内存开销

### 2. 数据大小

Bazel 查询结果可能非常大(数 MB 到数百 MB),尤其是大型项目:
- 需要考虑内存占用
- 可能需要流式处理而非一次性加载
- Protocol Buffer 格式的解析也有性能开销

### 3. 优化建议

**实现层优化**:
- 使用缓存机制,避免重复查询
- 对于大型项目,考虑增量查询
- 使用 `--output=proto` 而非 `--output=xml`,Protocol Buffer 更高效

**接口扩展建议**:
```go
// 可扩展的接口设计
type StreamingQueryCommand interface {
    ReadStream() (io.Reader, error)  // 流式读取
}

type CachedQueryCommand interface {
    QueryCommand
    IsCached() bool  // 查询是否已缓存
    Invalidate()     // 使缓存失效
}
```

## 相关文件

**同包接口文件**:
- `bazel/exporter/interfaces/exporter.go` - 定义 `Exporter` 接口,使用本接口
- `bazel/exporter/interfaces/file_system.go` - 文件系统操作接口

**Mock 实现**:
- `bazel/exporter/interfaces/mocks/QueryCommand.go` - 由 mockery 生成的 mock 实现
- `bazel/exporter/interfaces/mocks/generate.go` - mock 生成配置

**Protocol Buffer 定义**:
- `bazel/exporter/build_proto/build/build.pb.go` - Bazel 查询结果的数据结构定义

**典型使用示例**:
```go
// 使用 QueryCommand 接口
func ProcessBazelQuery(qcmd QueryCommand) error {
    data, err := qcmd.Read()
    if err != nil {
        return fmt.Errorf("failed to read query: %w", err)
    }

    // 解析 Protocol Buffer 数据
    var result build.QueryResult
    if err := proto.Unmarshal(data, &result); err != nil {
        return fmt.Errorf("failed to parse query result: %w", err)
    }

    // 处理查询结果
    for _, target := range result.Target {
        // 处理每个构建目标...
    }

    return nil
}
```

该接口设计简洁而强大,为 Bazel 导出系统提供了灵活的数据获取抽象,是整个导出器架构的关键组成部分。
