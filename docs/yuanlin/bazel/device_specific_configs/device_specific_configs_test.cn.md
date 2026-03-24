# device_specific_configs_test.go

> 源文件: bazel/device_specific_configs/device_specific_configs_test.go

## 概述

device_specific_configs_test.go 是针对 device_specific_configs 包的单元测试文件。该测试文件使用 Go 的标准测试框架和 testify/assert 库,对 Configs 变量中定义的所有设备配置进行验证,确保配置数据的一致性和完整性。测试覆盖了配置命名约定和必需字段的存在性检查。

## 架构位置

该文件位于与被测模块相同的目录中,是标准 Go 测试文件:

- **路径**: bazel/device_specific_configs/
- **角色**: 质量保证,验证配置数据的正确性
- **运行方式**: 通过 `go test` 或 Bazel 测试命令执行

## 主要类与结构体

该文件不定义新的类或结构体,而是包含测试函数。

## 公共 API 函数

### TestConfigs_MapKeyMatchesConfigName(t *testing.T)

验证 Configs map 的键与对应 Config 结构体的 Name 字段匹配。

**测试逻辑**:
- 遍历 Configs map 的所有条目
- 对每个配置,使用 `t.Run(config.Name, ...)` 创建子测试
- 使用 `assert.Equal(t, config.Name, key)` 验证 map 键与 Name 字段相等

**目的**: 防止配置定义中的拼写错误或不一致

### TestConfigs_ConfigsHaveExpectedKeyValuePairs(t *testing.T)

验证所有配置包含预期的键值对。

**测试逻辑**:
- 遍历 Configs map 的所有配置
- 对每个配置,提取 Keys map 的所有键
- 使用 `assert.ElementsMatch()` 验证键集合恰好为 ["arch", "model", "os"]

**目的**: 确保所有配置包含必需的元数据字段,防止遗漏

## 内部实现细节

### 测试框架

使用 testify/assert 库提供更清晰的断言语法:
- `assert.Equal()`: 验证相等性,失败时提供清晰的差异输出
- `assert.ElementsMatch()`: 验证切片包含相同的元素(忽略顺序)

### 子测试

两个测试函数都使用 `t.Run()` 为每个配置创建子测试,好处:
- 单个配置失败不影响其他配置的测试
- 测试输出清楚地标识哪个配置失败
- 可以使用 `-run` 标志运行特定配置的测试

## 依赖关系

### 标准库依赖

- **testing**: Go 标准测试框架

### 第三方依赖

- **github.com/stretchr/testify/assert**: 提供丰富的断言函数

### 被测试模块

- 同包中的 Configs 变量和 Config 类型

## 设计模式与设计决策

### 表驱动测试

使用 Configs map 作为测试数据源,自动测试所有配置,新增配置无需修改测试代码。

### 详细的失败信息

使用 testify/assert 确保测试失败时提供清晰的诊断信息,包括期望值和实际值的差异。

### 最小化测试

只测试关键的不变性,不测试每个配置的具体值(这会使测试脆弱且难以维护)。

## 性能考量

测试非常快速,因为只进行简单的字符串比较和切片比较,没有 I/O 或复杂计算。

## 相关文件

- **device_specific_configs.go**: 被测试的模块
- **generate/generate.go**: 使用 Configs 数据的生成器
