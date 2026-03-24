# third_party/lua - Lua 脚本引擎

## 概述

`third_party/lua/` 包含 Lua 脚本语言的 Skia 构建配置。Lua 被集成到 Skia 的
某些工具中，允许通过脚本方式控制绘图操作和自动化测试。

## 目录结构

```
lua/
└── BUILD.gn             # GN 构建配置
```

## 关键文件

- **BUILD.gn**: 配置 Lua 的编译选项

## 依赖关系

- Lua 源码（通过 DEPS 拉取）

## 相关文档与参考

- Lua 官网: https://www.lua.org/
- Skia Lua 绑定: `src/utils/SkLua.cpp`
