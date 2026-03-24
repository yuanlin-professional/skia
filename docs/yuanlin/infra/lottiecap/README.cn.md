# lottiecap - Lottie 动画捕获工具

## 概述

`lottiecap/` 目录包含用于捕获 Lottie 动画渲染结果的工具和 Docker 配置。支持使用 Puppeteer（无头 Chrome）运行 lottie-web 动画并捕获帧图像，用于 Gold 视觉回归测试。

## 目录结构

```
lottiecap/
├── docker/
│   ├── gold-lottie-web-puppeteer/   # Gold 集成版 Lottie 捕获
│   │   └── Dockerfile
│   ├── lottie-web-puppeteer/        # Puppeteer Lottie 捕获
│   │   └── Dockerfile
│   ├── lottiecap_gold.sh            # Gold 测试脚本
│   └── README.md                    # Docker 说明
├── gold/
│   └── lottie-web-aggregator.go     # Gold 结果聚合器
└── Makefile                         # 便捷构建命令
```

## 关键文件

### docker/lottie-web-puppeteer/
基础的 Lottie-web Puppeteer 捕获环境，使用 Chrome 渲染 Lottie 动画。

### docker/gold-lottie-web-puppeteer/
集成了 Gold 上传功能的 Lottie 捕获环境。

### gold/lottie-web-aggregator.go
Go 程序，聚合 Lottie 动画的渲染结果并格式化为 Gold 可接受的格式。

## 依赖关系

- lottie-web JavaScript 库
- Puppeteer / Chrome
- Skia Gold 服务
- `infra/bots/assets/lottie-samples/` - Lottie 样本数据

## 相关文档与参考

- [Lottie](https://airbnb.design/lottie/)
- [Skia Gold](https://gold.skia.org/)
