# recreate_skps - SKP 文件重新生成驱动

## 概述

使用最新版本的 Chromium 重新生成 SKP（Skia Picture）测试文件。SKP 文件需要定期更新以反映最新的网页渲染模式。

## 目录结构

```
recreate_skps/
├── recreate_skps.go   # 主程序
└── BUILD.bazel        # Bazel 构建文件
```

## 依赖关系

- Chromium 浏览器
- SKP 资源存储

## 相关文档与参考

- `infra/bots/assets/skp/` - SKP 数据资源
