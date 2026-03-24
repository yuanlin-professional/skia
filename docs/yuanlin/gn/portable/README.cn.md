# gn/portable/ - 可移植 GN 编译配置

## 概述

`gn/portable/` 目录包含可移植的 GN 编译配置，这些配置设计为可在 Skia 项目外部安全使用。与 `gn/skia/BUILD.gn` 中针对 Skia 内部使用的配置不同，此处的配置是通用的、不依赖 Skia 特定构建变量的编译选项。

该目录目前包含两个关键配置：`add_exceptions` 和 `add_rtti`。Skia 默认禁用 C++ 异常处理和运行时类型信息（RTTI），但某些第三方依赖或特定模块可能需要这些功能。通过将这些配置独立到 `portable/` 目录中，Skia 提供了一种干净的方式来为特定目标重新启用这些 C++ 特性。

这些配置在跨平台方面做了适配：在 Windows (MSVC) 平台上使用 `/EHsc` 和 `/GR` 编译器标志，在 GCC/Clang 平台上使用 `-fexceptions` 和 `-frtti` 标志。这种平台抽象使得构建文件无需关心底层编译器的具体标志语法。

## 目录结构

```
gn/portable/
└── BUILD.gn    # 可移植编译配置定义
```

## 关键文件

### BUILD.gn - 可移植编译配置

文件内容简洁，定义了两个配置：

```gn
config("add_exceptions") {
  if (is_win) {
    cflags_cc = [ "/EHsc" ]
  } else {
    cflags_cc = [ "-fexceptions" ]
  }
}

config("add_rtti") {
  if (is_win) {
    cflags_cc = [ "/GR" ]
  } else {
    cflags_cc = [ "-frtti" ]
  }
}
```

#### config("add_exceptions") - 启用 C++ 异常处理

- **Windows (MSVC)**：使用 `/EHsc` 标志，启用 C++ 异常处理模型（同步异常）
- **GCC/Clang**：使用 `-fexceptions` 标志，启用异常处理支持

此配置用于覆盖 `//gn/skia:no_exceptions` 中设置的全局禁用。Skia 默认禁用异常处理以减小二进制体积并提高性能，但第三方库（如 Lua 绑定等）可能需要异常支持。

#### config("add_rtti") - 启用运行时类型信息

- **Windows (MSVC)**：使用 `/GR` 标志，启用运行时类型信息
- **GCC/Clang**：使用 `-frtti` 标志，启用 RTTI

此配置用于覆盖 `//gn/skia:no_rtti` 中设置的全局禁用。RTTI 提供 `dynamic_cast` 和 `typeid` 运算符支持。Skia 核心代码不使用 RTTI，但某些集成场景可能需要。

## 构建配置说明

### 使用方法

在 `BUILD.gn` 文件中，可以将这些配置添加到特定目标的 `configs` 列表中：

```gn
# 为某个需要异常处理的库启用异常
source_set("my_library_with_exceptions") {
  sources = [ "my_source.cpp" ]
  configs += [ "//gn/portable:add_exceptions" ]
}

# 为某个需要 RTTI 的库启用 RTTI
source_set("my_library_with_rtti") {
  sources = [ "my_source.cpp" ]
  configs += [ "//gn/portable:add_rtti" ]
}
```

### 与默认配置的交互

由于 `BUILDCONFIG.gn` 中的 `default_configs` 包含 `//gn/skia:no_exceptions` 和 `//gn/skia:no_rtti`，直接添加 `add_exceptions` 或 `add_rtti` 可能会导致编译器标志冲突。正确的做法是先移除禁用配置，再添加启用配置：

```gn
source_set("need_exceptions_and_rtti") {
  sources = [ "source.cpp" ]
  configs -= [
    "//gn/skia:no_exceptions",
    "//gn/skia:no_rtti",
  ]
  configs += [
    "//gn/portable:add_exceptions",
    "//gn/portable:add_rtti",
  ]
}
```

## 依赖关系

- 依赖 `gn/BUILDCONFIG.gn` 中定义的 `is_win` 平台检测变量
- 与 `gn/skia/BUILD.gn` 中的 `no_exceptions` 和 `no_rtti` 配置形成互补关系
- 被 Skia 的第三方依赖构建规则（`third_party/` 下）使用

## 相关文档与参考

- `gn/skia/BUILD.gn` - 包含对应的禁用配置（`no_exceptions`、`no_rtti`）
- `gn/BUILDCONFIG.gn` - 全局构建配置，定义了默认配置列表
- [MSVC /EHsc 文档](https://learn.microsoft.com/en-us/cpp/build/reference/eh-exception-handling-model)
- [GCC -fexceptions 文档](https://gcc.gnu.org/onlinedocs/gcc/Code-Gen-Options.html)
