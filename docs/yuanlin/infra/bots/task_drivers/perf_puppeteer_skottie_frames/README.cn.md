# perf_puppeteer_skottie_frames - Puppeteer Skottie 帧性能驱动

## 概述

使用 Puppeteer 测量 Skottie（Lottie 动画播放器）在浏览器中的帧渲染性能。评估 Lottie 动画的播放流畅度。

## 目录结构

```
perf_puppeteer_skottie_frames/
├── perf_puppeteer_skottie_frames.go        # 主程序
├── perf_puppeteer_skottie_frames_test.go   # 单元测试
├── make_lotties_with_assets/               # Lottie 资源准备工具
└── BUILD.bazel                             # Bazel 构建文件
```

## 关键文件

### make_lotties_with_assets/
准备带有嵌入资源的 Lottie 动画文件，供性能测试使用。

## 依赖关系

- Node.js 和 Puppeteer
- Lottie 样本数据

## 相关文档与参考

- `infra/bots/assets/lottie-samples/` - Lottie 样本数据
- `infra/lottiecap/` - Lottie 捕获工具
