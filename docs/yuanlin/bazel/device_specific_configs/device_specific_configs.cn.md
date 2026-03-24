# device_specific_configs.go

> 源文件: bazel/device_specific_configs/device_specific_configs.go

## 概述

device_specific_configs.go 是 Skia 项目中用于管理设备特定 Bazel 配置的核心模块。该模块定义了测试设备的配置信息,包括设备的硬件特征(CPU、GPU)、操作系统、架构以及 Swarming 调度维度等元数据。这些配置用于生成 //bazel/devicesrc 文件,为 Skia 的基准测试和 GM(Golden Master)测试提供设备上下文信息。

模块包含了大量预定义的设备配置,涵盖 Windows、Linux、Android 等多个平台的物理设备和 Google Compute Engine(GCE)虚拟机实例。每个配置定义了设备的标识信息和测试运行时所需的命令行参数,确保测试结果能够正确地关联到特定的硬件环境。

## 架构位置

该文件位于 Skia 构建系统的 Bazel 配置层,是设备特定配置管理的中心:

- **路径**: bazel/device_specific_configs/
- **角色**: Bazel 配置生成器的数据源
- **消费者**:
  - generate/generate.go 生成 //bazel/devicesrc 文件
  - CI/CD 系统用于调度测试到正确的设备
  - 测试运行器使用配置参数运行设备特定测试
- **集成**: 与 Swarming(Google 的分布式任务调度系统)集成,通过 SwarmingDimensions 字段指定设备选择标准

## 主要类与结构体

### Config

表示 Bazel 配置的结构体,包含设备特定信息。

**字段**:

- `Name string`: 配置名称,通过 `--config=<Name>` 传递给 Bazel
- `Keys map[string]string`: 设备特定的键值对,用于 Gold 和 Perf 跟踪,不包括 "cpu_or_gpu" 和 "cpu_or_gpu_value"
  - 必需键: "arch"(架构)、"model"(型号)、"os"(操作系统)
- `CPU string`: 设备的 CPU 名称,用于 CPU 绑定测试的 "cpu_or_gpu_value" 键
- `GPU string`: 设备的 GPU 名称,用于 GPU 绑定测试的 "cpu_or_gpu_value" 键
- `SwarmingDimensions map[string]string`: Swarming 任务调度维度,用于匹配正确的测试机器

**方法**:

```go
func (d Config) Model() string
```
返回配置中的 "model" 键值。如果键不存在会触发 panic(有单元测试确保所有配置都包含此键)。

```go
func (d Config) TestRunnerArgs() []string
```
返回应传递给 Bazel 测试目标的命令行参数列表。包括:
- `--device-specific-bazel-config <Name>`: 配置名称,Android 测试用此推断设备型号
- `--key <key1> <value1> <key2> <value2> ...`: 所有键值对(按字母顺序排序以确保确定性)
- `--cpuName <CPU>`: CPU 名称(如果定义)
- `--gpuName <GPU>`: GPU 名称(如果定义)

### Configs 变量

全局 map,包含所有已知的设备特定 Bazel 配置。

**类型**: `map[string]Config`
**用途**: 生成 //bazel/devicesrc 文件的数据源

## 公共 API 函数

该文件主要通过导出的 `Configs` 变量和 `Config` 类型提供 API。

### Config.Model()

获取设备型号。

**返回**: 配置中 "model" 键的值
**错误处理**: 如果 "model" 键不存在,触发 panic(不应该发生,有测试保证)

### Config.TestRunnerArgs()

生成测试运行器命令行参数。

**返回**: 字符串切片,包含所有测试运行器参数
**特性**:
- 键按字母顺序排序,确保输出确定性
- 自动处理可选的 CPU 和 GPU 字段
- 遵循测试运行器的参数格式约定

## 内部实现细节

### 配置数据结构

Configs 变量定义了 50+ 个设备配置,主要类别包括:

1. **Windows 物理设备**: AlphaR2(RadeonR9M470X)
2. **Android 设备**: AndroidOne(Mali400MP2)
3. **GCE Debian10 实例**:
   - AVX2 CPU 配置
   - AVX512 CPU 配置
   - Rome CPU 配置
   - 各种架构(x86_64, x86, arm)
4. **GCE Windows 实例**: Win2019 系列
5. **GCE Ubuntu 实例**: Ubuntu20 系列
6. **其他平台**: MacMini 系列(Intel/Apple Silicon)、iPhone、iPad 等

### 示例配置

```go
"GCE_Debian10_AVX2": {
    Name: "GCE_Debian10_AVX2",
    Keys: map[string]string{
        "arch":  "x86_64",
        "model": "GCE",
        "os":    "Debian10",
    },
    CPU: "AVX2",
    GPU: "SwiftShader",
}
```

### 参数生成逻辑

TestRunnerArgs() 方法的实现细节:

1. **固定参数**: 始终包含 `--device-specific-bazel-config` 标志
2. **键排序**: 使用 `sort.Strings()` 确保确定性输出
3. **格式化**: 键值对以 `--key key1 value1 key2 value2 ...` 格式传递
4. **条件添加**: CPU 和 GPU 名称只在非空时添加

### 设计约定

- **必需键**: 所有配置必须包含 "arch"、"model"、"os" 键(通过单元测试强制)
- **命名约定**: 配置名称通常格式为 `<Platform>_<OS>_<特征>`
- **GPU 优先**: 大多数配置包含 GPU 信息,反映 Skia 的图形渲染重点
- **SwiftShader**: GCE 实例通常使用 SwiftShader 作为软件 GPU 实现

## 依赖关系

### 标准库依赖

- **fmt**: 格式化字符串,用于错误消息
- **sort**: 对键进行排序以确保确定性

### 项目依赖

- 被 `generate/generate.go` 使用来生成 Bazel 配置文件
- 被测试运行器(如 adb_test_runner.go)使用来设置设备特定行为

### 外部系统依赖

- **Swarming**: Google 的分布式任务调度系统,通过 SwarmingDimensions 字段集成
- **Bazel**: 构建系统,通过 --config 标志使用这些配置
- **Gold**: Skia 的像素级测试验证系统,使用键值对标记测试结果
- **Perf**: Skia 的性能基准测试系统,使用键值对标记性能数据

## 设计模式与设计决策

### 数据驱动配置

使用 Go map 和 struct 定义配置数据,而不是硬编码在多个地方。这使得:
- 添加新设备配置只需修改一个文件
- 配置可以被工具自动处理和生成
- 易于测试和验证配置的一致性

### 分离关注点

配置定义与配置使用分离:
- 本文件只定义数据结构和配置
- generate/generate.go 负责生成 Bazel 文件
- 测试运行器负责解释和使用这些配置

### 方法接收器模式

Config 类型使用值接收器方法,因为:
- Config 结构体相对较小
- 方法不修改接收器
- 符合 Go 的最佳实践

### 确定性输出

TestRunnerArgs() 对键进行排序,确保:
- 生成的参数顺序固定
- 便于测试和调试
- 生成的文件可以进行版本控制(差异清晰)

### 错误处理策略

Model() 方法在缺少 "model" 键时 panic,而不是返回错误,因为:
- 这种情况不应该发生(有测试保证)
- 如果发生,表明数据结构有严重问题,应该立即暴露
- 简化了调用者的错误处理

### TODO 标记

代码中包含 TODO 注释:

```go
// TODO(lovisolo): Populate field SwarmingDimensions for all configs.
```

这表明 SwarmingDimensions 字段的填充工作仍在进行中,反映了渐进式开发策略。

## 性能考量

### 内存使用

Configs map 在程序启动时加载到内存,包含约 50 个配置,每个配置约 200-300 字节,总共约 10-15KB。这对现代系统来说微不足道。

### 运行时效率

- **Model()**: O(1) map 查找
- **TestRunnerArgs()**: O(n log n) 排序,其中 n 是键的数量(通常 n=3),因此实际上是 O(1)
- **参数生成**: 简单的字符串拼接,非常快

### 无动态分配优化

Config 结构使用 map 而不是切片,允许 O(1) 键查找,尽管对于只有 3 个键的情况差异不大。

## 相关文件

### 生成器

- **generate/generate.go**: 使用 Configs 数据生成 //bazel/devicesrc Bazel 配置文件

### 测试文件

- **device_specific_configs_test.go**: 单元测试,验证:
  - Map 键与 Config.Name 字段匹配
  - 所有配置包含必需的键("arch", "model", "os")

### 生成的文件

- **//bazel/devicesrc**: 由 generate.go 生成的 Bazel 配置文件,包含所有设备特定的 Bazel 标志

### 测试运行器

- **adb_test_runner.go**: Android 测试运行器,根据配置名称执行设备特定的设置和清理步骤
- 各种 C++ 测试运行器,解析 --key、--cpuName、--gpuName 参数

### CI/CD 系统

- **Swarming 任务定义**: 使用 SwarmingDimensions 字段选择正确的测试机器
- **Gold 和 Perf 上传器**: 使用键值对标记测试结果和性能数据

该模块是 Skia 测试基础设施的关键组成部分,通过集中管理设备配置,确保测试结果能够准确地关联到特定的硬件环境。其设计充分考虑了可维护性、可扩展性和与外部系统的集成需求。
