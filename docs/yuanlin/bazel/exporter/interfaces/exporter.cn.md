# Exporter

> 源文件: bazel/exporter/interfaces/exporter.go

## 概述

`exporter.go` 文件定义了 Bazel 导出器的核心接口,用于将 Bazel 工作空间的构建规则转换并导出到不同的项目格式。该文件提供了两个关键接口:`Writer` 和 `Exporter`,分别用于处理输出写入操作和整体导出逻辑。这是 Skia 项目中用于构建系统集成和互操作性的重要抽象层。

## 架构位置

该文件位于 `bazel/exporter/interfaces` 包中,作为 Bazel 导出器模块的接口定义层。它在 Skia 的构建系统架构中处于以下位置:

- **上层**: 具体的导出器实现(如 CMake 导出器、GN 导出器等)
- **同层**: 其他接口定义(`QueryCommand`、`FileSystem`)
- **下层**: Go 标准库的 I/O 接口(`io.StringWriter`、`io.Writer`)

该接口层通过依赖注入模式,使得导出器的实现与具体的查询命令和文件系统操作解耦,提高了代码的可测试性和可维护性。

## 主要类与结构体

### Writer 接口

```go
type Writer interface {
    io.StringWriter
    io.Writer
}
```

**功能**: `Writer` 是一个组合接口,集成了 Go 标准库的 `io.StringWriter` 和 `io.Writer` 接口。

**设计目的**:
- 提供统一的写入抽象,支持字符串和字节数组两种写入方式
- 简化导出文本的写入操作,使调用代码更加灵活
- 便于 mock 测试和不同输出目标的切换(文件、内存缓冲区等)

### Exporter 接口

```go
type Exporter interface {
    Export(qcmd QueryCommand) error
}
```

**功能**: `Exporter` 定义了导出器的核心行为接口。

**职责**:
- 接收 `QueryCommand` 参数,该参数提供 Bazel cquery 的响应数据
- 将 Bazel 构建规则转换为目标项目格式
- 返回错误信息以指示导出过程中的问题

## 公共 API 函数

### Writer 接口方法

**继承自 io.Writer**:
```go
Write(p []byte) (n int, err error)
```
- 写入字节切片数据
- 返回写入的字节数和可能的错误

**继承自 io.StringWriter**:
```go
WriteString(s string) (n int, err error)
```
- 直接写入字符串数据,避免字符串到字节切片的转换开销
- 返回写入的字节数和可能的错误

### Exporter 接口方法

**Export**:
```go
Export(qcmd QueryCommand) error
```
- **参数**: `qcmd QueryCommand` - 提供 Bazel 查询结果的命令对象
- **返回值**: `error` - 导出过程中的错误,成功则返回 `nil`
- **功能**: 执行完整的导出流程,包括读取查询数据、解析、转换和写入目标格式

## 内部实现细节

该文件只包含接口定义,没有具体实现。接口的实现细节取决于具体的导出器类型:

**典型实现流程**:
1. 通过 `QueryCommand.Read()` 获取 Bazel cquery 的响应数据
2. 解析响应数据(通常是 Protocol Buffer 格式)
3. 遍历构建目标和依赖关系
4. 转换为目标格式的语法结构
5. 通过 `Writer` 接口写入输出文件

**接口解耦优势**:
- `QueryCommand` 接口使得查询数据源可以是实际的 Bazel 命令执行结果,也可以是缓存数据或测试数据
- `Writer` 接口使得输出可以重定向到不同的目标(文件、网络、内存等)

## 依赖关系

**直接依赖**:
- `io` 包: 使用 Go 标准库的 I/O 接口

**被依赖关系**:
- 具体的导出器实现必须实现 `Exporter` 接口
- 查询命令实现必须实现 `QueryCommand` 接口(定义在同一包中)
- 文件系统操作需要返回 `Writer` 接口的实现

**包内依赖**:
```
exporter.go (本文件)
    └── 依赖 QueryCommand 接口 (query_command.go)
```

## 设计模式与设计决策

### 1. 接口隔离原则 (ISP)

文件定义了最小化的接口,每个接口只包含必要的方法:
- `Writer` 只关注写入操作
- `Exporter` 只包含单一的 `Export` 方法

### 2. 依赖倒置原则 (DIP)

通过接口定义,使得高层模块(导出器)不依赖于低层模块(文件系统、命令执行)的具体实现,而是依赖于抽象接口。

### 3. 组合模式

`Writer` 接口通过嵌入多个标准库接口,实现接口组合,提供更丰富的功能而无需重新定义方法。

### 4. 策略模式

`Exporter` 接口允许不同的导出策略(CMake、GN、Ninja 等),通过统一接口进行调用,支持运行时的策略选择。

### 5. 命令模式

`QueryCommand` 作为参数传入,封装了查询操作的执行细节,使得导出器无需关心数据获取的具体方式。

## 性能考量

**接口调用开销**:
- Go 的接口调用涉及动态分派,有轻微的性能开销
- 对于 I/O 密集型的导出操作,这种开销可以忽略不计

**内存效率**:
- `Writer` 接口允许流式写入,避免在内存中构建完整的输出字符串
- 支持增量写入,降低内存峰值

**优化建议**:
- 实现 `Writer` 时应使用带缓冲的写入器(`bufio.Writer`)以减少系统调用
- 对于大型项目,建议分块处理依赖关系,避免一次性加载所有数据

## 相关文件

**同包文件**:
- `bazel/exporter/interfaces/query_command.go` - 定义 `QueryCommand` 接口
- `bazel/exporter/interfaces/file_system.go` - 定义文件系统操作接口
- `bazel/exporter/interfaces/mocks/` - 包含接口的 mock 实现,用于测试

**实现文件**:
- `bazel/exporter/build_proto/` - Protocol Buffer 定义和生成代码
- `bazel/exporter/` - 具体的导出器实现(需要实现 `Exporter` 接口)

**使用示例**:
```go
// 典型使用方式
func ExportProject(exporter Exporter, queryCmd QueryCommand) error {
    return exporter.Export(queryCmd)
}
```

该接口设计为 Bazel 导出器系统提供了清晰的抽象边界,使得系统具有良好的扩展性和可测试性。
