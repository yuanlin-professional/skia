# platform_tools/debugging - 调试辅助工具

## 概述

`debugging/` 包含帮助开发者调试 Skia 代码的工具和扩展，支持 LLDB 和
Visual Studio 调试器。

## 目录结构

```
debugging/
├── lldb/            # LLDB 调试器扩展
└── vs/              # Visual Studio 调试可视化器
```

## 关键文件

- **lldb/**: LLDB 调试器的数据类型格式化脚本，可以在调试时以可读格式显示
  Skia 内部数据类型（如 SkMatrix、SkRect、SkPath 等）
- **vs/**: Visual Studio 的 natvis 文件，提供类似的调试可视化功能

## 使用方法

### LLDB
在 `.lldbinit` 中加载扩展：
```
command script import /path/to/skia/platform_tools/debugging/lldb/skia_lldb.py
```

### Visual Studio
将 `.natvis` 文件复制到 Visual Studio 的可视化器目录。

## 相关文档与参考

- LLDB 文档: https://lldb.llvm.org/
- Visual Studio 调试: https://docs.microsoft.com/en-us/visualstudio/debugger/
