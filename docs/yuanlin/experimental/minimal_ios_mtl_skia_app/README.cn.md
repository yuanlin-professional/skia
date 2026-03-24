# minimal_ios_mtl_skia_app - iOS Metal 最小示例应用

## 概述

`experimental/minimal_ios_mtl_skia_app/` 是一个最小化的 iOS 应用示例，
展示如何使用 Metal 图形 API 在 iOS 设备上运行 Skia 渲染。这是一个完整可运行的
应用程序模板，适合作为 iOS 上集成 Skia 的起点。

## 目录结构

```
minimal_ios_mtl_skia_app/
├── BUILD.gn         # GN 构建配置
├── README.md        # 原始说明文档
└── main.mm          # Objective-C++ 应用入口
```

## 关键文件

- **main.mm**: 应用程序入口，使用 Objective-C++ 编写，初始化 Metal 设备
  和 Skia 渲染上下文

## 编译方法

```bash
cd $SKIA_ROOT_DIRECTORY
mkdir -p out/ios_arm64_mtl
cat > out/ios_arm64_mtl/args.gn <<EOM
target_os="ios"
target_cpu="arm64"
skia_use_metal=true
skia_use_expat=false
skia_enable_pdf=false
EOM

tools/git-sync-deps
bin/gn gen out/ios_arm64_mtl
ninja -C out/ios_arm64_mtl minimal_ios_mtl_skia_app
```

编译完成后安装 `out/ios_arm64_mtl/minimal_ios_mtl_skia_app.app` 到设备。

## 依赖关系

- iOS SDK（arm64）
- Metal 图形框架
- Skia 核心库（Metal 后端）

## 相关文档与参考

- Skia Metal 后端: `include/gpu/mtl/`
- iOS 平台工具: `platform_tools/ios/`
