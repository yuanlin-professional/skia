# codesign_ios.py - iOS 代码签名脚本

> 源文件: `gn/codesign_ios.py`

## 概述
自动化 iOS 应用程序的代码签名流程,查找签名身份和配置文件,提取应用标识符前缀,生成权限文件并执行 `codesign` 命令。

## 架构位置
Skia iOS 构建部署工具链。

## 公共 API 函数
无,通过命令行参数执行: `codesign_ios.py <pkg> <identstr> <profile>`

## 内部实现细节
使用 `security find-identity` 查找签名证书,在 `~/Library/MobileDevice/Provisioning Profiles/` 中搜索匹配的 mobileprovision 文件。从配置文件提取 `ApplicationIdentifierPrefix`,生成最小化的 entitlements plist。

## 依赖关系
- macOS security 和 codesign 命令行工具

## 相关文件
- GN 构建配置中的 iOS 目标定义
