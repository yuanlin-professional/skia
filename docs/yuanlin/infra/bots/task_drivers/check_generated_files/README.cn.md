# check_generated_files - 生成文件检查驱动

## 概述

检查仓库中自动生成的文件是否与生成脚本的输出保持一致。确保开发者在修改生成逻辑后重新运行了生成步骤。

## 目录结构

```
check_generated_files/
├── check_generated_files.go   # 主程序
└── BUILD.bazel                # Bazel 构建文件
```

## 依赖关系

- 检查 `tasks.json` 等自动生成文件的一致性

## 相关文档与参考

- 父目录 `task_drivers/` 说明
