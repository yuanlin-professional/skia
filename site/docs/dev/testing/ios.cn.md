---
title: '在 iOS 上测试'
linkTitle: '在 iOS 上测试'
---

在设置 Skia 从命令行进行自动化测试之前，请先按照说明使用主流 iOS 工具链运行 Skia 测试（_dm_、_nano-bench_）。请参阅 [iOS 快速入门指南](/docs/user/build/)。

iOS 不太适合从命令行编译和运行。以下是如何安装一组使此成为可能的工具的说明。要了解它们在自动化测试中的使用方式，请参阅 buildbot 配方使用的 bash 脚本：
<https://github.com/google/skia/tree/main/platform_tools/ios/bin>。

## 安装

关键工具包括：

- libimobiledevice <http://www.libimobiledevice.org/>，
  <https://github.com/libimobiledevice/libimobiledevice>

- ios-deploy <https://github.com/phonegap/ios-deploy>

按照以下步骤安装：

- 在 <http://brew.sh/> 安装 Brew
- 安装 _libimobiledevice_（注意：以下所有组件都是 _libimobiledevice_
  项目的一部分，但在不同名称下打包/开发。_brew_ 的 _cask_ 扩展是安装 _osxfuse_ 和 _ifuse_ 所必需的，它允许挂载 iOS 设备上的应用程序目录）。

```
brew install libimobiledevice
brew install ideviceinstaller
brew install caskroom/cask/brew-cask
brew install Caskroom/cask/osxfuse
brew install ifuse
```

- 安装 node.js 和 ios-deploy

```
$ brew update
$ brew install node
$ npm install ios-deploy
```
