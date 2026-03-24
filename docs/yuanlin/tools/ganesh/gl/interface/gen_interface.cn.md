# gen_interface.go - OpenGL 接口代码生成器

> 源文件: `tools/ganesh/gl/interface/gen_interface.go`

## 概述

`gen_interface.go` 是一个用 Go 语言编写的代码生成工具，用于根据 JSON5 格式的接口描述文件（`interface.json5`）自动生成 Skia Ganesh OpenGL 后端的接口组装（assemble）和验证（validate）C++ 源代码文件。

该工具为三种 OpenGL 标准（OpenGL、OpenGL ES、WebGL）分别生成接口组装代码，并生成一个统一的接口验证文件。生成的代码负责在运行时根据设备支持的 GL 版本和扩展动态加载函数指针，以及验证加载的函数指针是否完整。

## 架构位置

```
Skia Ganesh GL 接口系统
├── tools/ganesh/gl/interface/
│   ├── gen_interface.go        <-- 本文件：代码生成器
│   ├── interface.json5         <-- GL 接口描述文件（输入）
│   └── README                  <-- 使用说明
├── src/gpu/ganesh/gl/          <-- 生成代码的输出目录
│   ├── GrGLAssembleGLInterfaceAutogen.cpp      <-- 生成：OpenGL 接口组装
│   ├── GrGLAssembleGLESInterfaceAutogen.cpp    <-- 生成：OpenGL ES 接口组装
│   ├── GrGLAssembleWebGLInterfaceAutogen.cpp   <-- 生成：WebGL 接口组装
│   └── GrGLInterfaceAutogen.cpp                <-- 生成：接口验证
```

## 主要类与结构体

### `FeatureSet`
表示一组 GL 功能的需求定义，包含在三种 GL 标准下的要求和关联的函数列表。

```go
type FeatureSet struct {
    GLReqs    []Requirement          // OpenGL 需求
    GLESReqs  []Requirement          // OpenGL ES 需求
    WebGLReqs []Requirement          // WebGL 需求
    Functions         []string       // 标准函数列表
    HardCodeFunctions []HardCodeFunction  // 硬编码函数
    OptionalFunctions []string       // 可选函数（验证时不检查）
    TestOnlyFunctions []string       // 仅测试时组装/验证
    Required bool                    // 是否为必需功能
}
```

### `Requirement`
描述一个函数存在的条件。

```go
type Requirement struct {
    Extension      string      // GL 扩展名称（或 "<core>" 表示核心功能）
    MinVersion     *GLVersion  // 最低版本要求（可选）
    SuffixOverride *string     // 扩展后缀覆盖（可选）
}
```

### `HardCodeFunction`
不使用标准 C++ 宏加载的特殊函数。

```go
type HardCodeFunction struct {
    PtrName  string  // 结构体中的指针名
    CastName string  // 类型转换名
    GetName  string  // dlsym/eglGetProcAddress 的查找名
}
```

### `GLVersion`
GL 版本号，表示为两个整数的数组（主版本号和次版本号）。

```go
type GLVersion [2]int
```

### `RequirementGetter`
函数类型，用于从 `FeatureSet` 中提取特定标准的需求列表。

```go
type RequirementGetter func(FeatureSet) []Requirement
```

## 公共 API 函数

### `main()`
程序入口，读取 JSON5 描述文件，解析后调用代码生成函数。

命令行参数：
- `--out_dir`：输出目录，默认 `../../src/gpu/ganesh/gl`
- `--in_table`：输入 JSON5 文件，默认 `./interface.json5`
- `--dryrun`：仅打印输出不写入文件

### `generateAssembleInterface(features []FeatureSet)`
为三种 GL 标准分别生成接口组装代码文件。

### `generateValidateInterface(features []FeatureSet)`
生成统一的接口验证代码文件。

### `fillAssembleTemplate(template string, features []FeatureSet, getReqs RequirementGetter) string`
填充单个标准的组装模板，生成具体的 C++ 代码。

## 内部实现细节

### 代码生成策略

#### 组装代码生成

对于每个 `FeatureSet`，生成类似如下的 C++ 代码：

```cpp
if (glVer >= GR_GL_VER(3,0)) {
    GET_PROC(bindVertexArray);
}
// 或带扩展检查
if (extensions.has("GL_ARB_vertex_array_object")) {
    GET_PROC_SUFFIX(BindVertexArray, ARB);
}
```

- 核心功能使用 `GET_PROC(funcName)` 宏
- 扩展功能使用 `GET_PROC_SUFFIX(funcName, suffix)` 宏
- 多个需求用 `else if` 链接，按优先级尝试

#### 验证代码生成

验证代码检查加载的函数指针是否为非空：

```cpp
if (!fFunctions.fBindVertexArray || !fFunctions.fDeleteVertexArrays) {
    RETURN_FALSE_INTERFACE;
}
```

验证会根据当前 GL 标准和版本/扩展条件有选择地进行检查。

### 扩展后缀推导

```go
func deriveSuffix(ext string) string {
    ext = strings.TrimPrefix(ext, "GL_")
    return strings.Split(ext, "_")[0]
}
```

从扩展名自动推导函数后缀，例如 `GL_EXT_disjoint_timer_query` -> `EXT`。特殊情况：`ARB` 后缀被视为空（因为 ARB 扩展通常与核心功能同名）。

### 确定性输出

```go
sort.Strings(feature.Functions)
sort.Strings(feature.TestOnlyFunctions)
```

函数列表在生成前排序，确保相同输入始终产生相同输出，使生成的代码可以稳定地进行版本控制。

### 测试专用函数

使用 `#if defined(GPU_TEST_UTILS)` 条件编译包裹仅在测试中使用的函数，避免在发布版本中暴露不必要的函数。

### 必需功能的断言

如果一个功能标记为 `Required` 且不是核心功能，当所有扩展检查都失败时会生成 `SkASSERT(false)` 和 `return nullptr`。

## 依赖关系

- **Go 标准库**：`flag`（命令行参数）, `fmt`, `os`, `io/ioutil`, `path/filepath`, `sort`, `strings`
- **第三方库**：`github.com/flynn/json5`（JSON5 解析）
- **输入文件**：`interface.json5`（GL 接口描述）

## 设计模式与设计决策

1. **代码生成模式**：通过数据驱动的代码生成，避免手动编写和维护数百个 GL 函数的加载和验证代码。JSON5 描述文件是单一事实源（single source of truth）。

2. **模板方法**：`fillAssembleTemplate` 使用字符串模板和内容替换生成最终文件，分离了文件框架和动态内容。

3. **三标准统一处理**：OpenGL、OpenGL ES 和 WebGL 共享同一个功能描述文件，通过 `RequirementGetter` 函数类型多态地处理不同标准。

4. **可选的 DryRun 模式**：支持 `--dryrun` 标志，便于开发时预览生成结果而不修改文件。

5. **输入验证**：`validateFeatures` 函数检查是否有重复的函数名注册，在生成前发现错误。

## 性能考量

- 代码生成是离线操作，运行时性能不是关注点。
- 生成的 C++ 代码中使用了 `if-else if` 链而非查表，在运行时具有较好的分支预测性能。
- 函数列表排序确保了确定性输出，避免了不必要的代码审查差异。
- 生成的代码使用宏来保持简洁性和一致性，编译器会将宏展开为高效的函数指针赋值。

## 相关文件

- `tools/ganesh/gl/interface/interface.json5` - GL 接口描述文件（输入）
- `tools/ganesh/gl/interface/README` - 使用说明
- `src/gpu/ganesh/gl/GrGLAssembleGLInterfaceAutogen.cpp` - 生成的 OpenGL 组装代码
- `src/gpu/ganesh/gl/GrGLAssembleGLESInterfaceAutogen.cpp` - 生成的 OpenGL ES 组装代码
- `src/gpu/ganesh/gl/GrGLAssembleWebGLInterfaceAutogen.cpp` - 生成的 WebGL 组装代码
- `src/gpu/ganesh/gl/GrGLInterfaceAutogen.cpp` - 生成的接口验证代码
- `include/gpu/ganesh/gl/GrGLInterface.h` - GL 接口类定义
