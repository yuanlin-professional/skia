# FileSystem Mock

> 源文件: bazel/exporter/interfaces/mocks/FileSystem.go

## 概述

`FileSystem.go` 是由 mockery 自动生成的 `FileSystem` 接口的 mock 实现,用于在单元测试中模拟文件系统操作。该 mock 允许测试代码在内存中模拟文件读写,无需实际访问磁盘,提高测试速度和可靠性。

## 架构位置

```
测试代码 → FileSystem (mock) → 内存中的文件数据
         ↓
      (无需真实文件系统)
```

## 主要类与结构体

### FileSystem Mock 结构体

```go
type FileSystem struct {
    mock.Mock
}
```

## 公共 API 函数

### OpenFile 方法

```go
func (_m *FileSystem) OpenFile(path string) (interfaces.Writer, error)
```

mock 实现的 `OpenFile()` 方法:
- 记录 `path` 参数
- 返回预设的 `Writer` 和 `error`
- 支持函数返回和直接值返回

### ReadFile 方法

```go
func (_m *FileSystem) ReadFile(filename string) ([]byte, error)
```

mock 实现的 `ReadFile()` 方法:
- 记录 `filename` 参数
- 返回预设的文件内容和错误
- 验证方法调用

### NewFileSystem 构造函数

```go
func NewFileSystem(t interface {
    mock.TestingT
    Cleanup(func())
}) *FileSystem
```

创建配置好的 mock 实例,自动设置断言验证。

## 内部实现细节

### 参数记录

```go
ret := _m.Called(path)  // OpenFile
ret := _m.Called(filename)  // ReadFile
```

记录所有方法调用及其参数,用于后续验证。

### 灵活的返回值

支持多种返回值设置方式:
```go
// 直接返回值
mockFS.On("ReadFile", "/path").Return([]byte("content"), nil)

// 动态计算
mockFS.On("ReadFile", mock.Anything).Return(func(path string) ([]byte, error) {
    return computeContent(path), nil
})
```

### 自动清理

测试结束时自动验证所有预期是否满足。

## 依赖关系

- `github.com/stretchr/testify/mock`: Mock 框架
- `go.skia.org/skia/bazel/exporter/interfaces`: 原始接口
- `go.skia.org/skia/bazel/exporter/interfaces.Writer`: Writer 接口

## 设计模式与设计决策

### 测试替身模式

提供文件系统的测试替身,优势:
- **隔离性**: 测试不影响真实文件系统
- **速度**: 内存操作远快于磁盘 I/O
- **可控性**: 精确控制文件内容和错误

### 行为验证

除了返回值,还可验证:
- 方法是否被调用
- 调用次数
- 参数匹配

## 性能考量

Mock 文件系统性能:
- **读取**: 纳秒级(内存访问)
- **写入**: 无实际 I/O,瞬间完成
- **测试速度**: 比真实文件系统快 100-1000 倍

## 相关文件

- `bazel/exporter/interfaces/file_system.go`: 原始接口
- `bazel/exporter/interfaces/mocks/generate.go`: 生成配置
- `bazel/exporter/interfaces/mocks/QueryCommand.go`: QueryCommand mock

**使用示例**:
```go
func TestExporter(t *testing.T) {
    mockFS := mocks.NewFileSystem(t)

    // 模拟文件读取
    mockFS.On("ReadFile", "/template.txt").
        Return([]byte("template content"), nil)

    // 模拟文件写入
    mockWriter := &MockWriter{}
    mockFS.On("OpenFile", "/output.txt").
        Return(mockWriter, nil)

    // 使用 mock 进行测试
    exporter := NewExporter(mockFS)
    err := exporter.Export(...)
    assert.NoError(t, err)

    // 验证文件操作
    mockFS.AssertCalled(t, "OpenFile", "/output.txt")
}
```

该 mock 实现使得文件 I/O 相关的代码可以快速、可靠地进行单元测试,无需创建临时文件或清理文件系统。
