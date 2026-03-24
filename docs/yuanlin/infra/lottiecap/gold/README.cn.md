# lottiecap/gold - Lottie Gold 结果聚合器

## 概述

包含将 Lottie 动画捕获结果格式化并上传到 Skia Gold 的聚合工具。

## 目录结构

```
gold/
└── lottie-web-aggregator.go   # Go 语言结果聚合器
```

## 关键文件

### lottie-web-aggregator.go
将 Lottie-web 的渲染输出聚合为 Gold 服务可接受的格式，用于视觉回归检测。

## 依赖关系

- Skia Gold 服务 API

## 相关文档与参考

- [Skia Gold](https://gold.skia.org/)
