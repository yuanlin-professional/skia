# QueryCommand Mock

> 源文件: bazel/exporter/interfaces/mocks/QueryCommand.go

## 概述

`QueryCommand.go` 是由 mockery 自动生成的 `QueryCommand` 接口的 mock 实现。该 mock 类用于单元测试中模拟 Bazel 查询命令的行为,无需执行真实的 Bazel 命令,从而提高测试速度和可控性。

## 架构位置

```
测试代码 → QueryCommand (mock) → 预设的返回值
         ↓
      (无需真实 Bazel 命令)
```

**在测试中的作用**: 替代真实的 `QueryCommand` 实现,提供可预测的测试数据。

## 主要类与结构体

### QueryCommand Mock 结构体

```go
type QueryCommand struct {
    mock.Mock
}
```

继承自 `testify/mock.Mock`,提供 mock 功能支持。

## 公共 API 函数

### Read 方法

```go
func (_m *QueryCommand) Read() ([]byte, error)
```

mock 实现的 `QueryCommand.Read()` 方法:
1. 调用 `_m.Called()` 记录方法调用
2. 检查返回值是否已设置
3. 根据类型断言返回适当的值
4. 支持函数返回和直接值返回两种模式

### NewQueryCommand 构造函数

```go
func NewQueryCommand(t interface {
    mock.TestingT
    Cleanup(func())
}) *QueryCommand
```

创建新的 mock 实例:
- 注册测试接口
- 设置自动断言清理
- 返回配置好的 mock 对象

## 内部实现细节

### 返回值处理

```go
if rf, ok := ret.Get(0).(func() ([]byte, error)); ok {
    return rf()
}
```

支持两种返回值模式:
1. **函数返回**: 允许动态计算返回值
2. **直接值返回**: 返回预设的固定值

### 类型安全

通过类型断言确保返回值类型正确:
```go
if ret.Get(0) != nil {
    r0 = ret.Get(0).([]byte)
}
```

### 自动验证

```go
t.Cleanup(func() { mock.AssertExpectations(t) })
```

测试结束时自动验证所有预期的方法调用是否都已执行。

## 依赖关系

- `github.com/stretchr/testify/mock`: Mock 框架
- `go.skia.org/skia/bazel/exporter/interfaces.QueryCommand`: 被 mock 的接口

## 设计模式与设计决策

### Mock 对象模式

提供接口的测试替身,支持:
- 行为验证(方法是否被调用)
- 返回值控制(预设返回值)
- 参数匹配(验证调用参数)

### 代码生成

由 mockery 自动生成,确保:
- 与接口定义同步
- 类型安全
- 完整的方法覆盖

## 性能考量

Mock 对象的开销:
- **运行时**: 轻微的反射和类型断言开销
- **测试速度**: 比真实 Bazel 命令快数千倍
- **内存**: 只需存储预设的返回值

## 相关文件

- `bazel/exporter/interfaces/query_command.go`: 原始接口定义
- `bazel/exporter/interfaces/mocks/generate.go`: mock 生成配置
- `bazel/exporter/interfaces/mocks/FileSystem.go`: 另一个 mock 实现

**使用示例**:
```go
func TestExporter(t *testing.T) {
    // 创建 mock
    mockQry := mocks.NewQueryCommand(t)

    // 设置期望
    expectedData := []byte("mock query result")
    mockQry.On("Read").Return(expectedData, nil)

    // 使用 mock
    data, err := mockQry.Read()
    assert.NoError(t, err)
    assert.Equal(t, expectedData, data)

    // 自动验证(在测试结束时)
}
```

该 mock 实现显著简化了 Bazel 导出器的测试,使得单元测试可以快速运行且无需外部依赖。
