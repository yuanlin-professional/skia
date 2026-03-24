# minify_sksl.py - SkSL 着色器模块压缩脚本

> 源文件: `gn/minify_sksl.py`

## 概述

`minify_sksl.py` 是 Skia 构建系统中的一个 Python 脚本，用于对 SkSL（Skia Shading Language）模块文件进行压缩（minification）处理。SkSL 是 Skia 自有的着色器语言，该脚本通过调用 `sksl-minify` 工具生成两个版本的模块数据：一个是完全优化和压缩的版本（用于 release 构建），另一个是未优化的版本（用于 debug 构建，便于调试阅读）。

脚本在 GN 构建系统中作为构建步骤被调用，处理 Skia 内置的 SkSL 模块（如 `sksl_shared`、`sksl_gpu`、`sksl_frag` 等）。

## 架构位置

```
Skia 构建系统
├── gn/
│   ├── minify_sksl.py          <-- 本文件：SkSL 压缩脚本
│   └── sksl.gni                <-- SkSL GN 构建定义
├── src/sksl/
│   ├── sksl_shared.sksl        <-- SkSL 共享模块（输入）
│   ├── sksl_gpu.sksl           <-- SkSL GPU 模块（输入）
│   └── ...
└── tools/sksl-minify           <-- SkSL 压缩工具（被调用的可执行文件）
```

## 主要类与结构体

本文件没有定义类，是纯过程式脚本。

### 模块依赖表

```python
dependencies = {
    'sksl_compute':       ['sksl_gpu', 'sksl_shared'],
    'sksl_gpu':           ['sksl_shared'],
    'sksl_frag':          ['sksl_gpu', 'sksl_shared'],
    'sksl_vert':          ['sksl_gpu', 'sksl_shared'],
    'sksl_graphite_frag': ['sksl_frag', 'sksl_gpu', 'sksl_shared'],
    'sksl_graphite_vert': ['sksl_vert', 'sksl_gpu', 'sksl_shared'],
    'sksl_public':        ['sksl_shared'],
    'sksl_rt_shader':     ['sksl_public', 'sksl_shared'],
    'sksl_shared':        [],
}
```

此依赖表确保 `sksl-minify` 在压缩某个模块时能够引用其依赖模块中已定义的标识符，从而保证压缩后的标识符在全局作用域内唯一。

## 公共 API 函数

本脚本通过命令行参数调用：

```
python minify_sksl.py <sksl-minify-path> <target-dir> <module1.sksl> [module2.sksl ...]
```

参数说明：
- `sys.argv[1]`: `sksl-minify` 可执行文件路径
- `sys.argv[2]`: 输出目标目录
- `sys.argv[3:]`: 待处理的 SkSL 模块文件路径列表

## 内部实现细节

### 处理流程

对于每个输入模块文件：

1. **解析模块名**：从文件路径中提取模块名（去掉目录和扩展名）
2. **确定程序类型**：根据模块名中的关键字确定 SkSL 程序类型
   - 包含 `_compute` -> `--compute`
   - 包含 `_vert` -> `--vert`
   - 其他 -> `--frag`
3. **组装依赖列表**：查找依赖表，将依赖模块的文件路径添加到参数列表
4. **生成优化版本**：调用 `sksl-minify --stringify` 生成 `.minified.sksl`
5. **生成未优化版本**：调用 `sksl-minify --unoptimized --stringify` 生成 `.unoptimized.sksl`

### 生成的文件

对于每个输入模块 `module.sksl`，在目标目录下生成：
- `module.minified.sksl`：完全优化和压缩的版本，用于 release/optimize-for-size 构建
- `module.unoptimized.sksl`：未优化版本，用于 debug 构建（保持可读性）

### 依赖解析

依赖列表的作用是为 `sksl-minify` 提供上下文，使其知道哪些标识符已在依赖模块中定义。这样在压缩时可以安全地重命名当前模块中的局部标识符，而不与全局可见的标识符冲突。

```python
moduleList = [module]
for dependent in dependencies[moduleName]:
    moduleList.append(os.path.join(moduleDir, dependent) + ".sksl")
```

### 错误处理

捕获 `subprocess.CalledProcessError` 异常，输出编译错误信息并以退出码 1 终止。对于未在依赖表中注册的模块，输出错误信息并终止。

## 依赖关系

- **Python 标准库**：`os`, `subprocess`, `sys`
- **外部工具**：`sksl-minify`（Skia 构建产物，SkSL 压缩器）
- **输入文件**：`src/sksl/*.sksl`（SkSL 模块源文件）

## 设计模式与设计决策

1. **硬编码依赖图**：模块依赖关系直接在脚本中以字典形式硬编码，简单直接。这要求在添加新的 SkSL 模块时更新此脚本。

2. **双版本输出**：同时生成优化和未优化两个版本，使得 debug 和 release 构建可以使用不同的模块数据，兼顾了可调试性和性能。

3. **基于文件名的类型推断**：通过模块文件名中的关键字（`_compute`、`_vert`）推断程序类型，避免了额外的配置文件。

4. **`--stringify` 输出**：使用 `--stringify` 选项将压缩结果转换为 C++ 字符串字面量格式，便于直接嵌入到 Skia 源代码中。

## 性能考量

- 脚本本身的执行开销很小，主要时间花在调用 `sksl-minify` 工具上。
- 每个模块需要调用 `sksl-minify` 两次（优化版 + 未优化版），构建时间随模块数量线性增长。
- 压缩后的模块文件更小，可以减少 Skia 库的最终二进制大小。
- `--unoptimized` 版本保持了可读性，但在 release 构建中不会被使用，不影响运行时性能。

## 相关文件

- `src/sksl/sksl_shared.sksl` - SkSL 共享模块（基础类型和函数）
- `src/sksl/sksl_gpu.sksl` - SkSL GPU 模块
- `src/sksl/sksl_frag.sksl` - SkSL 片段着色器模块
- `src/sksl/sksl_vert.sksl` - SkSL 顶点着色器模块
- `src/sksl/sksl_compute.sksl` - SkSL 计算着色器模块
- `src/sksl/sksl_graphite_frag.sksl` - Graphite 片段着色器模块
- `src/sksl/sksl_graphite_vert.sksl` - Graphite 顶点着色器模块
- `gn/sksl.gni` - SkSL 构建定义
