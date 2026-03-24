# specs/ - 规范提案

## 概述

`specs/` 包含 Skia 团队提出的 Web 平台等技术规范提案。这些提案旨在改进
现有 Web API，使图像处理等常见操作更加简洁高效。

## 目录结构

```
specs/
├── README.md                # 本文档
└── web-img-decode/          # Web 图像解码 API 提案
    ├── README.md            # 提案说明
    ├── current/             # 现有方案演示
    │   └── index.html       # 当前（繁琐的）图像解码方式
    └── proposed/            # 提议方案演示
        └── index.html       # 提议的新 API 方式
```

## 关键提案

### web-img-decode
提议简化浏览器中从编码图像数据（Blob/ArrayBuffer）到 ImageData 的转换过程。
当前方案需要多个步骤（创建 Image 元素、Canvas 等），提案建议提供原生的直接解码
API。概念验证使用 CanvasKit WASM 库实现，最终目标是浏览器原生支持。

## 相关文档与参考

- CanvasKit 模块: `modules/canvaskit/`
- W3C Web API: https://www.w3.org/
