# gn_meta_sln.py - Visual Studio 元解决方案生成器

> 源文件: `gn/gn_meta_sln.py`

## 概述
将多个 GN 生成的 Visual Studio 解决方案合并为一个包含所有配置的元解决方案,使开发者能在单个 VS 实例中切换不同构建配置。

## 架构位置
Skia Windows 开发工具链的一部分,增强 IDE 集成体验。

## 公共 API 函数
无,作为脚本直接执行。

## 内部实现细节
扫描 `out/` 目录下所有包含 `build.ninja.d` 的子目录作为配置。解析每个配置的 `all.sln` 文件提取项目信息,合并为单个 `out/sln/skia.sln`。项目文件被复制并修改以包含多配置的 `ItemDefinitionGroup`。

## 依赖关系
Python 标准库。需要先用 `--ide=vs` 生成各配置的 VS 文件。

## 设计模式与设计决策
以第一个配置的 GUID 作为基准,确保项目引用的一致性。

## 性能考量
仅在需要时手动运行。

## 相关文件
- GN 生成的 `out/*/all.sln` 文件
