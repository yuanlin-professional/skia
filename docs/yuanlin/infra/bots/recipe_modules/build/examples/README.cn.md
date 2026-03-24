# build/examples - 构建模块使用示例

## 概述

`examples/` 目录包含 `build` Recipe 模块的使用示例和模拟测试。示例代码演示了如何调用构建模块进行编译，同时作为回归测试来验证模块行为的正确性。

## 目录结构

```
examples/
└── full.expected/    # 模拟测试预期结果（JSON 文件）
```

## 说明

`full.expected/` 目录中的 JSON 文件记录了在各种输入配置下，构建模块应该执行的步骤序列。这些文件由 `recipes.py test train` 命令自动生成和更新。

## 相关文档与参考

- 父目录 `build/api.py` 中的 API 实现
