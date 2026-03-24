# malisc.py

> 源文件: tools/malisc/malisc.py

## 概述

`malisc.py` 是一个用于批量分析 ARM Mali GPU 着色器性能的 Python 脚本。该工具通过调用 ARM Mali 离线编译器（malisc）分析一个文件夹中的所有着色器文件（.frag 和 .spv 格式），提取每个着色器的指令发射统计信息，并以 CSV 格式输出结果。这对于比较不同着色器实现的性能、优化 GPU 着色器代码非常有用。

主要功能：
- 遍历指定文件夹中的 .frag（GLSL 片段着色器）和 .spv（SPIR-V）文件
- 对每个文件调用 malisc 编译器进行分析
- 解析编译器输出，提取"Instructions Emitted"统计数据
- 输出 CSV 格式的性能对比报告

## 架构位置

```
tools/
  └── malisc/
      └── malisc.py               # Mali 着色器分析工具（本文件）

相关工具：
  └── skslc/                      # SkSL 编译器
      └── Main.cpp
```

## 主要类与结构体

无类定义，使用字典存储数据。

### stats 字典

```python
stats = {}
```

**结构**：
```python
{
    'shader_basename': {
        '.frag': ['总指令数', '算术指令数', '加载存储指令数'],
        '.spv': ['总指令数', '算术指令数', '加载存储指令数']
    }
}
```

**示例**：
```python
{
    'my_shader': {
        '.frag': ['128', '96', '32'],
        '.spv': ['120', '92', '28']
    }
}
```

## 公共 API 函数

### 主程序逻辑

```python
if len(sys.argv) != 3:
    print(sys.argv[0], ' <compiler> <folder>')
    sys.exit(1)

compiler = sys.argv[1]  # malisc 编译器路径
folder = sys.argv[2]    # 着色器文件夹路径
```

**命令行参数**：
1. `compiler`：Mali 离线编译器可执行文件路径
2. `folder`：包含 .frag 和 .spv 文件的文件夹

**使用示例**：
```bash
python malisc.py /path/to/malisc ./shaders
```

## 内部实现细节

### 文件遍历逻辑

```python
for filename in os.listdir(folder):
    basename, ext = os.path.splitext(filename)
    if ext not in ['.frag', '.spv']:
        continue
```

**处理的文件类型**：
- `.frag`：GLSL 片段着色器源文件
- `.spv`：SPIR-V 二进制着色器文件

### 编译器调用

```python
cmdline = [compiler]
if ext == '.spv':
    cmdline.extend(['-f', '-p'])  # SPIR-V 需要额外参数
cmdline.append(os.path.join(folder, filename))

try:
    output = subprocess.check_output(cmdline)
except subprocess.CalledProcessError:
    continue  # 编译失败，跳过此文件
```

**参数说明**：
- 对于 `.frag` 文件：`malisc shader.frag`
- 对于 `.spv` 文件：`malisc -f -p shader.spv`
  - `-f`：指定格式
  - `-p`：SPIR-V 格式标志

### 输出解析

```python
stats.setdefault(basename, {})
for line in output.splitlines():
    if line.startswith('Instructions Emitted'):
        inst = line.split(':')[1].split()  # 提取冒号后的数字
        stats[basename][ext] = inst
```

**解析目标**：查找形如以下的输出行：
```
Instructions Emitted: 128 96 32
```

提取出三个数字：
1. 总指令数
2. 算术指令数
3. 加载/存储指令数

### CSV 输出

```python
for k, v in stats.iteritems():
    gl = v.get('.frag', ['', '', ''])
    vk = v.get('.spv', ['', '', ''])
    print('{0},{1},{2},{3},{4},{5},{6}'.format(
        k,       # 着色器名称
        gl[0], gl[1], gl[2],  # GLSL 统计
        vk[0], vk[1], vk[2])) # SPIR-V 统计
```

**输出格式**：
```
shader_name,gl_total,gl_arith,gl_ls,vk_total,vk_arith,vk_ls
my_shader,128,96,32,120,92,28
```

## 依赖关系

**Python 标准库**：
- `sys`：命令行参数和退出
- `os`：文件系统操作
- `subprocess`：调用外部编译器
- `json`：导入但未使用（可能为未来功能保留）

**外部工具**：
- ARM Mali 离线编译器（malisc）

## 设计模式与设计决策

### 简单脚本架构

无复杂类层次，直接使用过程式编程：
- 适合一次性批处理任务
- 易于理解和修改
- 快速开发

### 容错设计

```python
try:
    output = subprocess.check_output(cmdline)
except subprocess.CalledProcessError:
    continue
```

编译失败时继续处理其他文件，不中断整个批处理。

### 扩展名区分处理

对 .spv 文件使用特殊参数，体现了对不同输入格式的适配。

### 字典嵌套结构

使用 `stats[basename][ext]` 结构：
- 按着色器名称分组
- 同一着色器的不同格式数据关联
- 便于对比分析

## 性能考量

### 串行处理

文件按顺序处理，适合文件数量不多的场景。

**优化方案**（如需要）：
- 使用 `multiprocessing` 并行调用编译器
- 适合大量着色器的批处理

### 内存占用

所有统计数据保存在内存中：
- 对于典型项目（几十到几百个着色器）完全可行
- 如处理数千个文件，可考虑流式输出

### 子进程开销

每个文件启动一次子进程：
- 开销主要在编译器执行，而非进程创建
- 对于着色器分析这种 I/O 密集型任务可接受

## 相关文件

**输入文件**：
- `*.frag`：GLSL 片段着色器源文件
- `*.spv`：SPIR-V 二进制着色器文件

**外部工具**：
- ARM Mali Offline Compiler（malisc）

**相关 Skia 工具**：
- `tools/skslc/Main.cpp`：SkSL 编译器（可生成 SPIR-V）
- `tools/sksl-minify/SkSLMinify.cpp`：SkSL 压缩工具

**使用场景**：
- GPU 性能分析
- 着色器优化验证
- 跨 API（GLSL vs SPIR-V）性能对比

该脚本是 Skia GPU 性能优化工作流的一部分，帮助开发者量化着色器代码的性能特征。
