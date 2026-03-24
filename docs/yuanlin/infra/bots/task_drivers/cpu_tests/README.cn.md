# cpu_tests - CPU 测试执行驱动

## 概述

执行 Skia 的 CPU 相关测试任务。使用 Bazel 构建并运行 CPU 渲染后端的测试套件。

## 目录结构

```
cpu_tests/
├── cpu_tests.go   # 主程序
└── BUILD.bazel    # Bazel 构建文件
```

## 依赖关系

- `common/` - 共享的 Bazel 工具函数
- Bazel 构建系统

## 相关文档与参考

- 父目录 `task_drivers/` 说明
