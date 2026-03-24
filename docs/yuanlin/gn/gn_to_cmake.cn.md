# gn_to_cmake.py - GN 到 CMake 转换器

> 源文件: `gn/gn_to_cmake.py`

## 概述
将 GN 的 JSON 项目描述转换为 CMakeLists.txt 文件,使 Skia 可在 CLion 等 CMake 兼容 IDE 中开发和浏览。这是一个功能完整的转换器,处理了源文件分类、编译标志、链接依赖、自定义命令等多种目标类型。

## 架构位置
Skia IDE 集成工具,将 GN 构建元数据映射到 CMake 项目结构。

## 主要类与结构体

- **`CMakeTargetType`**: 描述 CMake 目标类型(executable、library、custom_target 等)
- **`Project`**: 封装 GN 项目 JSON 数据,提供路径解析和依赖遍历方法
- **`Target`**: 封装单个 GN 目标的属性和 CMake 映射

## 公共 API 函数

- **`WriteProject(project, ninja_executable)`**: 生成 CMakeLists.txt 和 CMakeLists.ext
- **`WriteTarget(out, target, project)`**: 为单个目标生成 CMake 指令

## 内部实现细节

源文件按扩展名分类(cxx/c/asm/objc/objcc/obj/input/other)。OBJECT 库依赖通过 `$<TARGET_OBJECTS:...>` 引用。编译标志使用 `SHELL:` 模式传递,需要三层转义(CMake string、generator expression、UNIX_COMMAND)。自定义目标(action/copy)通过 `add_custom_command` 实现。

## 依赖关系
- GN 生成的 `project.json`
- ninja 可执行文件(用于构建更新)

## 设计模式与设计决策
- 生成 CMakeLists.txt(入口)和 CMakeLists.ext(完整内容)的分离设计
- 自动包含 Emscripten 头文件路径以支持 CanvasKit CLion 开发
- 支持增量更新:追踪 build.ninja.d 依赖

## 性能考量
生成过程为一次性操作。自动更新通过 ninja 检查最小化重新生成。

## 相关文件
- GN `--ide=json --json-ide-script` 参数
