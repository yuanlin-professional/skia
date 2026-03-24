# FileSystem

> 源文件: bazel/exporter/interfaces/file_system.go

## 概述

`file_system.go` 文件定义了文件系统操作的抽象接口,用于在 Bazel 导出器中执行文件读写操作。`FileSystem` 接口提供了打开文件进行写入和读取文件内容的功能,通过抽象底层操作系统的文件系统,使得导出器代码更易于测试和移植。该接口遵循依赖倒置原则,允许在测试环境中使用内存文件系统或 mock 实现替代真实的文件系统操作。

## 架构位置

该文件位于 `bazel/exporter/interfaces` 包中,在 Bazel 导出系统的架构层次中担任 I/O 抽象层的角色:

- **上层**: 导出器实现类,需要通过此接口进行文件读写操作
- **同层**: 其他接口定义(`Exporter`、`QueryCommand`、`Writer`)
- **下层**: 操作系统的文件系统 API,通过具体实现类访问

**在导出流程中的位置**:
```
导出器 → FileSystem 接口 → 具体实现 → OS 文件系统
         ↓
         Writer 接口 → 写入输出文件
```

该接口使得导出器的核心逻辑与具体的文件系统实现分离,提高了代码的模块化程度和可测试性。

## 主要类与结构体

### FileSystem 接口

```go
type FileSystem interface {
    OpenFile(path string) (Writer, error)
    ReadFile(filename string) ([]byte, error)
}
```

**功能**: 定义文件系统操作的统一接口,提供文件打开和读取的抽象方法。

**设计原则**:
- **最小接口**: 只包含导出器必需的文件操作
- **抽象化**: 隐藏底层文件系统的实现细节
- **可测试性**: 便于在单元测试中使用 mock 实现

## 公共 API 函数

### OpenFile 方法

```go
OpenFile(path string) (Writer, error)
```

**功能**: 打开指定路径的文件用于写入操作。

**参数**:
- `path string`: 文件的绝对路径

**返回值**:
- `Writer`: 实现了 `io.Writer` 和 `io.StringWriter` 的接口,用于写入数据
- `error`: 打开文件失败时的错误信息,成功则返回 `nil`

**典型使用场景**:
- 创建导出的项目配置文件(如 CMakeLists.txt)
- 写入构建脚本
- 生成依赖关系文件

**可能的错误**:
- 路径不存在
- 权限不足
- 磁盘空间不足
- 文件已被其他进程占用

### ReadFile 方法

```go
ReadFile(filename string) ([]byte, error)
```

**功能**: 读取指定文件的全部内容。

**参数**:
- `filename string`: 要读取的文件路径

**返回值**:
- `[]byte`: 文件的完整内容
- `error`: 读取失败时的错误信息,成功则返回 `nil`

**典型使用场景**:
- 读取模板文件
- 加载配置文件
- 读取缓存的 Bazel 查询结果

**可能的错误**:
- 文件不存在
- 权限不足
- I/O 错误
- 文件过大导致内存不足

## 内部实现细节

该文件只包含接口定义,具体实现由实现类提供。典型的实现方式包括:

### 1. 真实文件系统实现

```go
type OSFileSystem struct{}

func (fs *OSFileSystem) OpenFile(path string) (Writer, error) {
    // 创建父目录(如果不存在)
    if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
        return nil, err
    }
    // 打开文件用于写入
    return os.OpenFile(path, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0644)
}

func (fs *OSFileSystem) ReadFile(filename string) ([]byte, error) {
    return os.ReadFile(filename)
}
```

### 2. 内存文件系统实现(测试用)

```go
type MemoryFileSystem struct {
    files map[string][]byte
}

func (fs *MemoryFileSystem) OpenFile(path string) (Writer, error) {
    buf := &bytes.Buffer{}
    fs.files[path] = buf.Bytes()
    return buf, nil
}

func (fs *MemoryFileSystem) ReadFile(filename string) ([]byte, error) {
    if data, exists := fs.files[filename]; exists {
        return data, nil
    }
    return nil, os.ErrNotExist
}
```

### 3. Mock 实现(通过 mockery 生成)

用于单元测试,可以预设返回值和验证调用参数。

## 依赖关系

**直接依赖**:
- `Writer` 接口(定义在同包的 `exporter.go` 中)

**被依赖关系**:
- 导出器实现需要使用 `FileSystem` 接口进行文件操作
- 测试代码使用 mock 实现验证文件操作行为

**相关接口**:
```
FileSystem 接口
    ├── OpenFile() → Writer 接口
    └── ReadFile() → []byte
```

## 设计模式与设计决策

### 1. 适配器模式 (Adapter Pattern)

`FileSystem` 接口作为适配器,将各种文件系统实现(OS 文件系统、内存文件系统、网络文件系统)统一为相同的接口。

**优势**:
- 调用代码无需关心底层实现
- 易于切换不同的文件系统实现
- 支持多种存储后端

### 2. 门面模式 (Facade Pattern)

接口简化了复杂的文件系统操作,只暴露必要的方法。

**优势**:
- 降低使用难度
- 减少错误使用的可能
- 提供统一的错误处理

### 3. 依赖倒置原则 (DIP)

导出器依赖于 `FileSystem` 抽象而非具体的文件系统实现。

**优势**:
- 提高可测试性
- 降低耦合度
- 支持依赖注入

### 4. 单一职责原则 (SRP)

接口只负责文件读写操作,不包含其他职责(如网络请求、数据库操作)。

**优势**:
- 职责明确
- 易于理解和维护
- 减少变更影响范围

## 性能考量

### 1. ReadFile 方法的限制

`ReadFile` 一次性读取整个文件到内存:
- **优点**: 使用简单,适合小文件
- **缺点**: 大文件可能导致内存溢出
- **建议**: 对于大文件,考虑扩展接口支持流式读取

### 2. OpenFile 的缓冲

建议实现类返回带缓冲的 Writer:
```go
func (fs *OSFileSystem) OpenFile(path string) (Writer, error) {
    f, err := os.OpenFile(path, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0644)
    if err != nil {
        return nil, err
    }
    return bufio.NewWriter(f), nil  // 使用缓冲提高性能
}
```

### 3. 并发安全性

接口本身不保证线程安全,实现类需要根据使用场景决定是否需要加锁:
- 单线程使用:无需考虑并发
- 多线程使用:需要同步机制

### 4. 错误处理

实现类应该:
- 提供详细的错误信息
- 使用 `fmt.Errorf` 包装底层错误
- 区分不同类型的错误(权限错误、I/O 错误等)

## 相关文件

**同包接口文件**:
- `bazel/exporter/interfaces/exporter.go` - 定义 `Writer` 接口,被本接口使用
- `bazel/exporter/interfaces/query_command.go` - 查询命令接口
- `bazel/exporter/interfaces/mocks/generate.go` - mock 生成配置

**Mock 实现**:
- `bazel/exporter/interfaces/mocks/FileSystem.go` - 由 mockery 生成的 mock 实现

**使用示例**:
```go
// 典型使用场景
func ExportToCMake(fs FileSystem, targets []Target) error {
    // 创建输出文件
    w, err := fs.OpenFile("/path/to/CMakeLists.txt")
    if err != nil {
        return fmt.Errorf("failed to open file: %w", err)
    }
    defer w.Close()  // 实现类应支持 Close

    // 写入 CMake 配置
    for _, target := range targets {
        fmt.Fprintf(w, "add_library(%s ...)\n", target.Name)
    }

    return nil
}

// 单元测试示例
func TestExport(t *testing.T) {
    mockFS := &MemoryFileSystem{files: make(map[string][]byte)}
    targets := []Target{{Name: "foo"}}

    err := ExportToCMake(mockFS, targets)
    assert.NoError(t, err)

    // 验证生成的内容
    content := mockFS.files["/path/to/CMakeLists.txt"]
    assert.Contains(t, string(content), "add_library(foo")
}
```

该接口设计简洁实用,为 Bazel 导出系统提供了文件系统操作的抽象层,是实现可测试和可维护代码的关键组成部分。
