# find_msvc.py - MSVC 编译器查找工具

> 源文件: `gn/find_msvc.py`

## 概述
在 Windows 系统上自动查找 Microsoft Visual Studio 的 VC 目录路径,支持 2017-2022 的多个版本和版本类型(Enterprise/Professional/Community/BuildTools/Preview)。

## 架构位置
Skia Windows 构建系统的编译器发现工具。

## 公共 API 函数
- **`find_msvc()`**: 返回 MSVC VC 目录路径,未找到返回 None

## 内部实现细节
优先在标准安装路径(`C:\Program Files` 和 `C:\Program Files (x86)`)中搜索。回退到使用 `vswhere.exe` 工具查找非标准安装路径。版本优先级: 2022 > 2019 > 2017。

## 依赖关系
- Windows 文件系统
- vswhere.exe (固定位置安装)

## 相关文件
- GN BUILDCONFIG.gn 中的 Windows 工具链配置
