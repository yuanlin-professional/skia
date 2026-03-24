# toolchain_layering_check - 工具链分层检查驱动

## 概述

检查 Skia 代码中的头文件包含关系是否符合工具链分层规则。确保模块之间的依赖关系正确，防止不允许的跨层引用。

## 目录结构

```
toolchain_layering_check/
├── toolchain_layering_check.go   # 主程序
└── BUILD.bazel                   # Bazel 构建文件
```

## 依赖关系

- Skia 源代码的头文件分析

## 相关文档与参考

- 父目录 `task_drivers/` 说明
