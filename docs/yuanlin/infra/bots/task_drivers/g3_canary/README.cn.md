# g3_canary - Google3 金丝雀测试驱动

## 概述

触发和监控 Google3（Google 内部代码库）中的 Skia 金丝雀测试。在 Skia 代码合入前验证其对 Google 内部项目的兼容性。

## 目录结构

```
g3_canary/
├── g3_canary.go   # 主程序
├── PROD.md        # 生产环境注意事项
└── BUILD.bazel    # Bazel 构建文件
```

## 依赖关系

- Google 内部构建系统
- Skia 金丝雀服务账户

## 相关文档与参考

- `PROD.md` - 生产环境操作指南
