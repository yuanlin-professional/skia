# gen_types_test 单元测试

> 源文件: experimental/tskit/go/gen_types/gen_types_test.go

## 概述

`gen_types_test` 是 `gen_types` 工具的单元测试文件,使用 Go 的标准测试框架验证类型生成逻辑的正确性。该测试套件通过实际的输入输出对比、错误条件验证等方式,确保类型生成器能够正确处理各种 C++ 绑定模式,并在遇到非法输入时给出清晰的错误提示。

测试文件覆盖了以下场景:
1. 完整的绑定文件解析和生成(包括类、函数、值对象、常量)
2. 缺少类型注解的字段错误处理
3. 缺少类型注解的常量错误处理

这些测试保证了 `gen_types` 工具的健壮性和可靠性,是持续集成流程的重要组成部分。

## 架构位置

测试文件与被测试代码位于同一包中,遵循 Go 的测试约定:

```
experimental/tskit/go/gen_types/
├── gen_types.go          # 被测试的代码
├── gen_types_test.go     # 测试代码(当前文件)
└── testdata/             # 测试数据目录
    ├── bindings1.cpp                       # 完整的测试输入
    └── expectedambientnamespace1.d.ts      # 预期的输出
```

**测试执行:**
```bash
cd experimental/tskit/go/gen_types
go test -v
```

## 主要类与结构体

测试文件不定义新的类型,而是使用标准库和第三方测试库的类型:

- `*testing.T`: Go 标准测试类型,提供测试上下文
- `testutils`: Skia 项目的测试工具包,提供文件读取等辅助函数
- `assert` 和 `require`: testify 库提供的断言函数

## 公共 API 函数

### TestGenerateAmbientNamespace_ValidInput_Success(t *testing.T)

测试成功场景,验证完整的绑定文件解析和生成。

**测试策略:**
```go
func TestGenerateAmbientNamespace_ValidInput_Success(t *testing.T) {
    contents := testutils.ReadFile(t, "bindings1.cpp")
    expectedOutput := testutils.ReadFile(t, "expectedambientnamespace1.d.ts")
    output, err := generateAmbientNamespace("namespace_one", contents)
    require.NoError(t, err)
    assert.Equal(t, expectedOutput, output)
}
```

**测试步骤:**
1. 从 `testdata/bindings1.cpp` 读取输入内容
2. 从 `testdata/expectedambientnamespace1.d.ts` 读取预期输出
3. 调用 `generateAmbientNamespace` 生成实际输出
4. 断言没有错误发生(`require.NoError`)
5. 断言实际输出与预期输出完全一致(`assert.Equal`)

**测试覆盖的功能:**
- 私有和公共模块函数的提取
- 类定义的解析(包括构造函数和方法)
- 值对象的解析(包括可选字段)
- 常量定义的解析(包括可选常量)
- 字母顺序排序
- 格式化和缩进

**测试数据特点:**
`bindings1.cpp` 包含复杂的绑定模式:
- 多个类定义(`Something`, `AnotherClass`)
- 多个构造函数重载
- 私有和公共方法
- 值对象定义(带可选字段)
- 常量定义(带条件编译)
- 不同的函数导出形式

### TestGenerateAmbientNamespace_FieldMissingAnnotation_ReturnsError(t *testing.T)

测试字段缺少类型注解时的错误处理。

**测试策略:**
```go
func TestGenerateAmbientNamespace_FieldMissingAnnotation_ReturnsError(t *testing.T) {
    _, err := generateAmbientNamespace("namespace_one", `
value_object<SomeValueObject>("SomeValueObject")
    /**
        The number of columns that the frobulator needs.
        @type number
     */
    .field("columns",   &SomeValueObject::columns)
    /**
     * This is missing the type annotation!!!
     */
    .field("misbehaving_field",    &SomeValueObject::object)
    /** @type string */
    .field("name",      &SomeValueObject::slot)
    /**
      *  @type boolean
      */
    .field("isInteger", &SomeValueObject::isInteger);
`)
    require.Error(t, err)
    assert.Contains(t, err.Error(), `Line 11: field "misbehaving_field" must be preceded by a @type annotation.`)
}
```

**测试目的:**
- 验证工具能够检测到缺少类型注解的字段
- 验证错误消息包含正确的行号和字段名
- 确保错误信息清晰,有助于开发者定位问题

**错误场景:**
```cpp
/**
 * This is missing the type annotation!!!
 */
.field("misbehaving_field", &SomeValueObject::object)  // 缺少 @type
```

**预期错误消息:**
```
Line 11: field "misbehaving_field" must be preceded by a @type annotation.
```

**验证断言:**
1. `require.Error(t, err)`: 确保返回了错误
2. `assert.Contains(t, err.Error(), ...)`: 验证错误消息内容

### TestGenerateAmbientNamespace_ConstantMissingAnnotation_ReturnsError(t *testing.T)

测试常量缺少类型注解时的错误处理。

**测试策略:**
```go
func TestGenerateAmbientNamespace_ConstantMissingAnnotation_ReturnsError(t *testing.T) {
    _, err := generateAmbientNamespace("namespace_one", `
/**
 *  @type boolean
 */
constant("good_constant", true);
constant("bad_constant", 0x2);
`)
    require.Error(t, err)
    assert.Contains(t, err.Error(), `Line 6: constant "bad_constant" must be preceded by a @type annotation.`)
}
```

**测试目的:**
- 验证工具能够检测到缺少类型注解的常量
- 验证错误消息包含正确的行号和常量名
- 确保即使有正确的常量定义,工具仍能检测到错误的定义

**错误场景:**
```cpp
constant("bad_constant", 0x2);  // 缺少 @type 注解
```

**预期错误消息:**
```
Line 6: constant "bad_constant" must be preceded by a @type annotation.
```

**验证断言:**
1. `require.Error(t, err)`: 确保返回了错误
2. `assert.Contains(t, err.Error(), ...)`: 验证错误消息内容

## 内部实现细节

### 测试工具使用

#### testutils.ReadFile

```go
contents := testutils.ReadFile(t, "bindings1.cpp")
```

**功能:**
- 从 `testdata` 目录读取文件
- 自动处理文件路径
- 如果文件不存在,测试自动失败

#### require.NoError vs assert.Equal

**require.NoError:**
```go
require.NoError(t, err)
```
- 如果 `err != nil`,立即失败并停止测试
- 用于关键断言,后续逻辑依赖此条件

**assert.Equal:**
```go
assert.Equal(t, expected, actual)
```
- 如果不相等,记录失败但继续执行
- 用于非关键断言,有助于收集更多失败信息

### 测试数据组织

**testdata 目录约定:**
- Go 工具链自动识别 `testdata` 目录
- 该目录不会被编译为可执行代码
- 适合存放测试输入和输出文件

**文件命名:**
- `bindings1.cpp`: 输入文件
- `expectedambientnamespace1.d.ts`: 预期输出文件
- 使用数字后缀支持多个测试用例

### 错误消息验证

使用 `assert.Contains` 而非 `assert.Equal`:
```go
assert.Contains(t, err.Error(), `Line 11: field "misbehaving_field" must be preceded by a @type annotation.`)
```

**优点:**
- 只验证关键信息,忽略错误消息的其他部分
- 更灵活,允许错误消息格式变化
- 专注于行号和字段名的正确性

### 内联测试数据

对于简单的错误测试,直接在测试函数中内联 C++ 代码:
```go
_, err := generateAmbientNamespace("namespace_one", `
value_object<SomeValueObject>("SomeValueObject")
    .field("columns", &SomeValueObject::columns)
    ...
`)
```

**优点:**
- 测试代码自包含,易于阅读
- 不需要额外的文件
- 突出错误条件

## 依赖关系

### 依赖的 Go 包

```go
import (
    "testing"                           // Go 标准测试框架

    "github.com/stretchr/testify/assert"   // 断言库
    "github.com/stretchr/testify/require"  // 断言库(失败时停止)
    "go.skia.org/infra/go/testutils"       // Skia 测试工具
)
```

### 依赖的测试数据

1. **testdata/bindings1.cpp**
   - 完整的 C++ 绑定文件示例
   - 包含所有支持的绑定模式

2. **testdata/expectedambientnamespace1.d.ts**
   - 对应的预期 TypeScript 输出
   - 手动验证过的正确输出

### 被测试的代码

- `generateAmbientNamespace(namespace, contents string) (string, error)`
  - 核心生成函数
  - 所有测试的目标

## 设计模式与设计决策

### 1. 表驱动测试的简化版

虽然没有显式使用表驱动测试,但三个测试函数遵循相似的模式:
- 准备输入
- 调用被测试函数
- 验证输出或错误

**可以改进为表驱动:**
```go
tests := []struct {
    name          string
    input         string
    namespace     string
    expectError   bool
    errorContains string
}{
    {
        name:        "valid input",
        input:       testutils.ReadFile(t, "bindings1.cpp"),
        namespace:   "namespace_one",
        expectError: false,
    },
    {
        name:          "field missing annotation",
        input:         `...`,
        namespace:     "namespace_one",
        expectError:   true,
        errorContains: "must be preceded by a @type annotation",
    },
    // ...
}
```

### 2. 正向和负向测试结合

- **正向测试**: `TestGenerateAmbientNamespace_ValidInput_Success`
  - 验证正确的输入产生正确的输出

- **负向测试**: 其他两个测试
  - 验证错误的输入产生正确的错误

### 3. 快速失败原则

使用 `require.NoError` 而非 `assert.NoError`:
```go
require.NoError(t, err)  // 失败则停止
```
- 如果生成失败,后续的输出比较没有意义
- 节省时间,避免混乱的错误消息

### 4. 测试命名约定

函数名格式: `Test<FunctionName>_<Scenario>_<ExpectedOutcome>`
- `TestGenerateAmbientNamespace_ValidInput_Success`
- `TestGenerateAmbientNamespace_FieldMissingAnnotation_ReturnsError`

**优点:**
- 清晰表达测试意图
- 易于理解失败原因
- 符合 Go 社区的 best practice

### 5. 使用 testify 库

选择 `testify` 而非标准库的 `t.Errorf`:
- 更丰富的断言函数
- 更清晰的错误消息
- 更易读的测试代码

## 性能考量

### 1. 测试执行速度

- 三个测试函数的总执行时间通常 <10ms
- 文件 I/O 是主要开销(读取 testdata 文件)
- 正则表达式匹配开销很小(输入规模小)

### 2. 测试数据大小

**bindings1.cpp:**
- 112 行
- 约 3KB
- 足够复杂以测试所有功能
- 足够小以快速执行

### 3. 并行测试

当前测试不使用 `t.Parallel()`:
- 测试之间没有共享状态
- 可以添加 `t.Parallel()` 以加速执行

**改进建议:**
```go
func TestGenerateAmbientNamespace_ValidInput_Success(t *testing.T) {
    t.Parallel()  // 允许并行执行
    // ...
}
```

### 4. 内存使用

- 每个测试分配的内存 <1MB
- 主要是字符串和正则表达式对象
- 测试结束后自动释放

## 相关文件

1. **experimental/tskit/go/gen_types/gen_types.go**
   - 被测试的代码
   - 实现 `generateAmbientNamespace` 函数

2. **experimental/tskit/go/gen_types/testdata/bindings1.cpp**
   - 测试输入文件
   - 包含完整的绑定示例:
     - 私有和公共函数导出
     - 类定义(Something, AnotherClass)
     - 值对象定义(SomeValueObject)
     - 常量定义(hasBird, SOME_FLAG, optionalConst)

3. **experimental/tskit/go/gen_types/testdata/expectedambientnamespace1.d.ts**
   - 预期的输出文件
   - 包含生成的 TypeScript 定义:
     - Bindings 接口
     - 构造函数接口
     - 类实例接口
     - 值对象接口

4. **go.skia.org/infra/go/testutils**
   - Skia 项目的测试工具包
   - 提供 `ReadFile` 等辅助函数

5. **github.com/stretchr/testify**
   - 第三方测试库
   - 提供丰富的断言函数

6. **持续集成配置**
   - CI 系统会自动运行这些测试
   - 确保代码变更不破坏类型生成功能

7. **Makefile 或构建脚本**
   - 可能包含 `make test` 目标
   - 自动化测试执行
