# codesize - 代码体积分析驱动

## 概述

分析 Skia 构建产物的代码体积，追踪二进制大小变化趋势。结果上传到 Skia Perf 服务用于可视化和回归检测。

## 目录结构

```
codesize/
├── codesize.go        # 主程序
├── codesize_test.go   # 单元测试
└── BUILD.bazel        # Bazel 构建文件
```

## 依赖关系

- `bloaty` 资源 - 二进制体积分析工具
- Skia Perf 服务

## 相关文档与参考

- `infra/bots/buildstats/` - 构建统计脚本
- [Skia Perf](https://perf.skia.org/)
