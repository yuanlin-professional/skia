# platform_tools/ios - iOS 平台工具

## 概述

`ios/` 包含在 iOS 平台上构建和部署 Skia 应用所需的工具和模板。

## 目录结构

```
ios/
├── app/             # iOS 应用模板
└── bin/             # iOS 命令行工具
```

## 关键文件

- **app/**: iOS 应用项目模板，包含必要的 Xcode 项目配置
- **bin/**: 用于自动化 iOS 构建和部署的脚本

## 依赖关系

- macOS 操作系统
- Xcode 及 iOS SDK
- Apple Developer 证书（部署到设备时需要）

## 相关文档与参考

- iOS Metal 示例: `experimental/minimal_ios_mtl_skia_app/`
- Skia Metal 后端: `include/gpu/mtl/`
