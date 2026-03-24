# templates.go - GL 接口代码生成模板

> 源文件: `tools/ganesh/gl/interface/templates.go`

## 概述

`templates.go` 是一个 Go 语言代码生成器的模板文件,用于自动生成 Skia Ganesh GPU 后端的 OpenGL 接口组装和验证代码。该文件包含四个主要的 C++ 代码模板,分别用于生成 GL ES、GL、WebGL 接口的组装函数以及接口验证函数。

## 架构位置

该文件位于 Skia 构建工具链中,属于代码生成基础设施的一部分。它在构建时被 Go 程序读取,通过填充 `[[content]]` 占位符来生成完整的 C++ 源文件。这些生成的文件最终编译为 Ganesh GL 后端的核心组件。

## 主要类与结构体

模板中引用的关键类型:
- **`GrGLInterface`**: Ganesh GL 接口的核心类,包含所有 GL 函数指针
- **`GrGLInterface::Functions`**: 存储所有 GL 函数指针的内部结构体
- **`GrGLExtensions`**: GL 扩展管理类,用于查询和管理已加载的扩展

## 公共 API 函数

模板生成的公共函数:
- **`GrGLMakeAssembledGLESInterface(void*, GrGLGetProc)`**: 组装 GL ES 接口,要求 GL ES 2.0+
- **`GrGLMakeAssembledGLInterface(void*, GrGLGetProc)`**: 组装桌面 GL 接口,要求 GL 2.0+
- **`GrGLMakeAssembledWebGLInterface(void*, GrGLGetProc)`**: 组装 WebGL 接口(仅 Emscripten 环境)
- **`GrGLInterface::validate()`**: 验证 GL 接口的完整性和正确性
- **`GrGLInterface::checkError()`**: 检查 GL 错误状态(仅在 `GR_GL_CHECK_ERROR` 启用时)

## 内部实现细节

每个模板使用宏来获取 GL 函数指针:
- `GET_PROC(F)`: 通过 `get` 回调获取标准 GL 函数
- `GET_PROC_SUFFIX(F, S)`: 获取带后缀的扩展函数(如 ARB、EXT)
- `GET_PROC_LOCAL(F)`: 获取局部使用的函数指针

WebGL 模板特殊之处在于它直接使用 `emscripten_gl*` 前缀函数,而非通过 `get` 回调获取。验证模板中包含 GL 错误检查机制和 OOM 检测逻辑。

## 依赖关系

- **Go 代码生成器**: 读取此模板并填充自动生成的内容
- **GrGLAssembleHelpers / GrGLUtil**: GL 版本解析和 EGL 查询辅助
- **GrGLExtensions**: 扩展字符串解析和管理
- **Emscripten WebGL headers**: WebGL 模板依赖 `<webgl/*.h>` 头文件

## 设计模式与设计决策

1. **代码生成模式**: 将大量重复的函数指针获取逻辑通过代码生成自动完成,避免手动维护
2. **条件编译**: 每个接口可通过 `SK_DISABLE_GL_*_INTERFACE` 宏禁用,返回 nullptr
3. **扩展容错**: 对 `GL_KHR_debug` 等已知问题扩展做特殊处理,缺少函数时移除扩展声明
4. **模板占位符**: 使用 `[[content]]` 标记自动生成内容的插入点

## 性能考量

- 接口组装仅在初始化时执行一次,非性能关键路径
- 验证函数在调试构建中使用,可快速定位缺失的 GL 函数
- WebGL 模板直接绑定 Emscripten 函数,省去运行时查找开销

## 相关文件

- `tools/ganesh/gl/interface/` 目录下的 Go 生成器主程序
- `include/gpu/ganesh/gl/GrGLInterface.h`: 接口头文件
- `include/gpu/ganesh/gl/GrGLAssembleInterface.h`: 组装函数声明
- `src/gpu/ganesh/gl/GrGLUtil.h`: GL 工具函数
