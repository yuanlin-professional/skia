# builder_name_schema - 构建器名称解析模块

## 概述

`builder_name_schema` 模块负责解析 Skia CI 构建器（builder）的命名规范，从任务名称中提取平台、编译器、设备、GPU、架构、配置等信息。Skia 的作业名称遵循严格的命名模式，此模块将名称字符串分解为结构化数据。

## 目录结构

```
builder_name_schema/
├── __init__.py                # DEPS 依赖声明
├── api.py                     # API 实现
├── builder_name_schema.json   # 命名模式定义（JSON Schema）
├── builder_name_schema.py     # 名称解析核心逻辑
└── examples/                  # 使用示例和测试
```

## 关键文件

### builder_name_schema.json
定义了构建器名称的各个字段及其允许的值，用作名称解析的参考模式。

### builder_name_schema.py
核心解析逻辑，将形如 `Test-Ubuntu18-Clang-Golo-GPU-QuadroP400-x86_64-Debug-All-Vulkan` 的名称分解为各组成部分。

## 依赖关系

无外部 Recipe 模块依赖。

## 相关文档与参考

- 父目录 `recipe_modules/README.md`
