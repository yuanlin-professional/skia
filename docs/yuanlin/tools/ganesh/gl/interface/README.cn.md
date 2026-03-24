# tools/ganesh/gl/interface - GrGLInterface 代码生成工具

## 概述

`tools/ganesh/gl/interface` 目录包含了用于自动生成 `GrGLInterface` 函数指针组装（Assemble）和验证（Validate）代码的工具。`GrGLInterface` 是 Skia 中封装 OpenGL/OpenGL ES/WebGL 函数指针的核心数据结构，Skia 通过此接口调用底层 GL 函数而非直接链接 GL 库。

本工具的核心是 `interface.json5` 配置文件，它以结构化的方式定义了每个 GL 函数应该在哪种标准（GL、GLES、WebGL）下可用，以及它们依赖的扩展或核心版本。代码生成器读取此配置后，自动生成对应的 C++ 代码，确保在不同 GL 标准和扩展环境下正确地加载和验证函数指针。

代码生成器使用 Go 语言编写（`gen_interface.go` 和 `templates.go`），通过 Go 的模板引擎将 JSON5 配置转换为 C++ 源代码。生成过程通过 Makefile 驱动，开发者在修改 `interface.json5` 后只需执行 `make -C tools/ganesh/gl/interface generate` 即可重新生成代码。

当前配置假设的最低版本为 GL 2.0、GLES 2.0 和 WebGL 1.0。每个函数条目可以指定多种获取策略，例如核心函数（`<core>`）、特定扩展（如 `GL_EXT_framebuffer_object`）或特定版本要求。

这种自动化的代码生成方式确保了 GL 函数绑定代码的一致性和可维护性，避免了手动维护大量函数指针映射时容易出现的遗漏和错误。

## 目录结构

```
tools/ganesh/gl/interface/
├── BUILD.bazel          # Bazel 构建配置
├── interface.json5      # GL 函数接口规范定义文件
├── gen_interface.go     # Go 语言代码生成器主程序
├── templates.go         # Go 模板，定义 C++ 代码输出格式
├── Makefile             # 构建命令，驱动代码生成流程
└── README.md            # 官方使用说明
```

## 关键类与函数

### interface.json5 配置格式
- 每个条目包含 `GL`、`GLES`、`WebGL` 三个标准的函数获取策略列表
- 策略可指定 `ext`（扩展名）、`min_version`（最低版本）等条件
- `<core>` 表示函数属于核心 API，始终应可用
- `functions` 数组列出该条目中的所有 GL 函数名（不含 `gl` 前缀由生成器补充）
- 支持可选函数（`optional: true`），当不可用时不视为错误

### gen_interface.go
- 解析 `interface.json5` 配置文件
- 根据模板生成 Assemble 函数（用于组装 GrGLInterface 的函数指针）
- 根据模板生成 Validate 函数（用于验证 GrGLInterface 的完整性）

### 核心 GL 函数分类
- **核心函数**: `ActiveTexture`、`BindBuffer`、`DrawElements`、`CreateShader` 等基础 GL 命令
- **扩展函数**: Framebuffer 对象、顶点数组对象、Instanced rendering 等
- **平台特定函数**: EGL/WGL/GLX 特定的上下文管理函数

## 依赖关系

- **工具依赖**: Go 语言运行时（用于代码生成）
- **输入**: `interface.json5`（函数规范定义）
- **输出**: 生成的 C++ 代码供 `src/gpu/ganesh/gl/` 使用
- **上游引用**: `include/gpu/ganesh/gl/GrGLInterface.h`（生成代码的目标接口）
- **参考资料**: [EECS 487 GL/GLES API 对照表](http://web.eecs.umich.edu/~sugih/courses/eecs487/common/notes/APITables.xml)

## 代码生成流程

```
interface.json5  -->  gen_interface.go  -->  生成的 C++ 代码
                      templates.go
```

1. 开发者修改 `interface.json5`，添加或修改 GL 函数规范
2. 执行 `make -C tools/ganesh/gl/interface generate`
3. Go 生成器读取 JSON5 配置，应用模板生成 C++ 代码
4. 生成的代码包括：
   - Assemble 函数：根据当前 GL 标准和扩展加载函数指针
   - Validate 函数：验证 GrGLInterface 中所有必需的函数指针是否已设置

## JSON5 配置示例

```json5
{
  "GL":    [{"ext": "<core>"}],
  "GLES":  [{"ext": "<core>"}],
  "WebGL": [{"ext": "<core>"}],
  "functions": [
    "ActiveTexture", "BindBuffer", "DrawArrays", ...
  ],
}
```

每个条目可以为不同标准指定不同的获取策略：
- `{"ext": "<core>"}` - 核心函数，始终应可用
- `{"ext": "GL_EXT_framebuffer_object"}` - 需要特定扩展
- `{"min_version": [3, 0]}` - 需要最低版本
- `{"optional": true}` - 可选函数，不可用时不报错

## 相关文档与参考

- `include/gpu/ganesh/gl/GrGLInterface.h` - GrGLInterface 数据结构定义
- `src/gpu/ganesh/gl/GrGLAssembleInterface.cpp` - 生成的 Assemble 代码
- `tools/ganesh/gl/README.md` - OpenGL 测试上下文文档
- `interface.json5` 文件头部注释中包含使用说明和最低版本要求
