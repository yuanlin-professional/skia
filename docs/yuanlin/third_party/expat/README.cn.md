# third_party/expat - XML 解析库

## 概述

`third_party/expat/` 包含 Expat XML 解析库的 Skia 构建配置。Expat 是一个
快速的流式 XML 解析器，Skia 使用它来解析 SVG 文件和其他 XML 格式的数据。

## 目录结构

```
expat/
├── BUILD.gn                         # GN 构建配置
├── include/                         # 自定义配置头文件
├── LICENSE                          # 许可证
├── roll-expat.sh                    # 版本更新脚本
├── 0001-Do-not-claim-getrandom.patch    # 补丁文件
└── 0002-Do-not-claim-arc4random_buf.patch # 补丁文件
```

## 关键文件

- **BUILD.gn**: Expat 的 Skia 构建配置
- **roll-expat.sh**: 自动化版本更新脚本
- **补丁文件**: 针对特定平台的兼容性修复

## 依赖关系

- Expat 源码（通过 DEPS 拉取）

## 相关文档与参考

- Expat 官网: https://libexpat.github.io/
- Skia SVG 模块: `modules/svg/`
- Skia XML 解析: `src/xml/`
