# win_lcid - Windows LCID 枚举工具

> 源文件: `tools/win_lcid.cpp`

## 概述

`win_lcid` 枚举 Windows 系统上所有已安装的区域设置(locale),输出每个区域的 LCID 值、名称和英文语言名称。LCID 大于 0x8000 的区域以注释形式输出。

## 架构位置

属于 Skia 的 Windows 平台字体/区域设置工具。

## 公共 API 函数

- **`main()`**: 调用 `EnumSystemLocalesEx` 枚举区域设置
- **`MyFuncLocaleEx()`**: 回调函数,输出每个区域的信息

## 内部实现细节

- 使用 `GetLocaleInfoEx` 获取英文语言名称
- 使用 `LocaleNameToLCID` 获取 LCID 值
- 输出格式: `{ 0xXXXX, "locale_name" }, //EnglishName`

## 依赖关系

- Windows API: `EnumSystemLocalesEx`, `GetLocaleInfoEx`, `LocaleNameToLCID`

## 性能考量

一次性枚举,开销极小。

## 相关文件

- Skia 的 Windows 字体管理代码
