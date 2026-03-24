# Skia Mali Shader Compiler 工具

## 概述

`tools/malisc` 提供了一个 Python 脚本，用于使用 ARM Mali 离线着色器编译器分析 Skia 生成的着色器代码的性能特征。该工具将 GLSL 片段着色器和 SPIR-V 着色器编译为 Mali GPU 指令，并收集指令数等性能统计数据，帮助开发者优化 Skia 在 Mali GPU 上的着色器效率。

## 目录结构

```
tools/malisc/
└── malisc.py    # Mali 着色器编译和分析脚本
```

## 功能说明

### malisc.py

脚本接受两个参数：Mali 编译器路径和着色器文件目录。

**用法：**

```bash
python tools/malisc/malisc.py <compiler> <folder>
```

**参数：**

| 参数 | 说明 |
|------|------|
| `<compiler>` | Mali 离线着色器编译器（malisc）的路径 |
| `<folder>` | 包含着色器文件的目录 |

### 支持的着色器格式

| 扩展名 | 格式 | 编译选项 |
|--------|------|---------|
| `.frag` | GLSL 片段着色器 | 直接编译 |
| `.spv` | SPIR-V 二进制着色器 | 使用 `-f -p` 选项 |

### 工作流程

1. 扫描指定目录中的 `.frag` 和 `.spv` 文件
2. 使用 Mali 编译器编译每个着色器
3. 从编译输出中提取 "Instructions Emitted" 统计行
4. 将同一着色器的 GLSL 和 SPIR-V 版本指令数配对
5. 输出 CSV 格式的统计结果

### 输出格式

```csv
shader_name,gl_total,gl_shortest,gl_longest,vk_total,vk_shortest,vk_longest
```

各列含义：
- **shader_name**: 着色器文件名（不含扩展名）
- **gl_total/shortest/longest**: GLSL 版本的总指令数/最短路径/最长路径
- **vk_total/shortest/longest**: SPIR-V 版本的总指令数/最短路径/最长路径

## 使用场景

### 着色器性能对比

对比同一着色器在 OpenGL (GLSL) 和 Vulkan (SPIR-V) 后端的编译效率：

```bash
# 导出 Skia 生成的着色器
# 使用 malisc 分析
python tools/malisc/malisc.py /path/to/malisc /path/to/shaders/

# 输出示例
# shader_a,120,80,150,115,75,140
# shader_b,200,140,250,190,130,240
```

### GPU 优化分析

- 对比不同版本 Skia 生成的着色器复杂度变化
- 识别指令数异常高的着色器进行优化
- 评估新的着色器优化 pass 的效果

## 依赖项

- **Python 2/3**: 脚本运行环境
- **Mali Offline Compiler (malisc)**: ARM 提供的离线编译工具
  - 可从 ARM Developer 网站下载
  - 支持 Mali-T600/T700/T800/G71/G72 等系列 GPU

## 与其他模块的关系

- **src/sksl/**: SkSL 着色器编译器生成 GLSL 和 SPIR-V 着色器代码
- **src/gpu/ganesh/glsl/**: Ganesh GL 着色器生成
- **tools/skslc/**: SkSL 编译器命令行工具
- **tools/viewer/**: Viewer 可导出当前场景使用的着色器
