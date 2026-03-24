# GrGLCoreFunctions

> 源文件: src/gpu/ganesh/gl/GrGLCoreFunctions.h

## 概述

`GrGLCoreFunctions.h` 是 Skia 图形库 Ganesh OpenGL 后端的核心函数清单文件,通过宏定义的方式列举了 Skia 使用的所有 OpenGL/EGL 核心函数名称。该文件不包含函数声明或定义,而是提供一个可被其他宏展开的函数名列表,用于批量生成函数指针、函数表、或动态加载代码。

该文件的设计源于 EGL 规范中的一个限制:根据 `EGL_KHR_get_all_proc_addresses` 扩展文档,`eglGetProcAddress()` 不保证支持查询非扩展的 EGL 核心函数,因此需要通过其他方式(如 `dlsym`)获取这些核心函数的地址。

## 架构位置

`GrGLCoreFunctions.h` 位于 Skia GPU 渲染架构的 OpenGL 函数加载层:

```
skia/
└── src/gpu/ganesh/gl/
    ├── GrGLCoreFunctions.h        <- 本模块
    ├── GrGLInterface.h            <- 使用本模块生成函数指针
    ├── GrGLAssembleInterface.cpp  <- 使用本模块加载函数
    └── GrGLFunctions.h            <- 完整函数声明
```

该文件在 OpenGL 接口构建时使用,通过宏展开技术批量处理函数加载。

## 主要宏定义

### GR_GL_CORE_FUNCTIONS_EACH

```cpp
#define GR_GL_CORE_FUNCTIONS_EACH(M) \
    M(eglGetCurrentDisplay) \
    M(eglQueryString) \
    M(glActiveTexture) \
    M(glAttachShader) \
    // ... 共约 124 个函数
    M(glViewport)
```

**功能**: 将宏 `M` 应用到每个核心函数名

**用途**: 支持宏元编程,批量生成代码

## 包含的核心函数

### 1. EGL 函数 (2 个)

| 函数名 | 说明 |
|--------|------|
| `eglGetCurrentDisplay` | 获取当前 EGL 显示 |
| `eglQueryString` | 查询 EGL 字符串信息 |

### 2. 纹理操作 (9 个)

| 函数名 | 说明 |
|--------|------|
| `glActiveTexture` | 激活纹理单元 |
| `glBindTexture` | 绑定纹理对象 |
| `glGenTextures` | 生成纹理对象 |
| `glDeleteTextures` | 删除纹理对象 |
| `glTexImage2D` | 设置 2D 纹理图像 |
| `glTexSubImage2D` | 更新 2D 纹理子区域 |
| `glCompressedTexImage2D` | 设置压缩纹理图像 |
| `glCompressedTexSubImage2D` | 更新压缩纹理子区域 |
| `glCopyTexSubImage2D` | 从帧缓冲复制到纹理 |

### 3. 纹理参数设置 (4 个)

| 函数名 | 说明 |
|--------|------|
| `glTexParameterf` | 设置浮点纹理参数 |
| `glTexParameterfv` | 设置浮点向量纹理参数 |
| `glTexParameteri` | 设置整数纹理参数 |
| `glTexParameteriv` | 设置整数向量纹理参数 |

### 4. 着色器与程序 (14 个)

| 函数名 | 说明 |
|--------|------|
| `glCreateShader` | 创建着色器对象 |
| `glDeleteShader` | 删除着色器对象 |
| `glShaderSource` | 设置着色器源代码 |
| `glCompileShader` | 编译着色器 |
| `glGetShaderiv` | 获取着色器参数 |
| `glGetShaderInfoLog` | 获取着色器日志 |
| `glGetShaderPrecisionFormat` | 获取着色器精度格式 |
| `glCreateProgram` | 创建程序对象 |
| `glDeleteProgram` | 删除程序对象 |
| `glAttachShader` | 附加着色器到程序 |
| `glLinkProgram` | 链接程序 |
| `glUseProgram` | 使用程序 |
| `glGetProgramiv` | 获取程序参数 |
| `glGetProgramInfoLog` | 获取程序日志 |

### 5. Uniform 操作 (16 个)

| 函数名 | 说明 |
|--------|------|
| `glGetUniformLocation` | 获取 uniform 位置 |
| `glUniform1f` / `glUniform1fv` | 设置标量浮点 uniform |
| `glUniform2f` / `glUniform2fv` | 设置 2D 向量 uniform |
| `glUniform3f` / `glUniform3fv` | 设置 3D 向量 uniform |
| `glUniform4f` / `glUniform4fv` | 设置 4D 向量 uniform |
| `glUniform1i` / `glUniform1iv` | 设置标量整数 uniform |
| `glUniform2i` / `glUniform2iv` | 设置 2D 整数向量 uniform |
| `glUniform3i` / `glUniform3iv` | 设置 3D 整数向量 uniform |
| `glUniform4i` / `glUniform4iv` | 设置 4D 整数向量 uniform |
| `glUniformMatrix2fv` | 设置 2x2 矩阵 uniform |
| `glUniformMatrix3fv` | 设置 3x3 矩阵 uniform |
| `glUniformMatrix4fv` | 设置 4x4 矩阵 uniform |

### 6. 顶点属性 (7 个)

| 函数名 | 说明 |
|--------|------|
| `glBindAttribLocation` | 绑定属性位置 |
| `glEnableVertexAttribArray` | 启用顶点属性数组 |
| `glDisableVertexAttribArray` | 禁用顶点属性数组 |
| `glVertexAttribPointer` | 设置顶点属性指针 |
| `glVertexAttrib1f` | 设置标量顶点属性 |
| `glVertexAttrib2fv` | 设置 2D 向量顶点属性 |
| `glVertexAttrib3fv` | 设置 3D 向量顶点属性 |
| `glVertexAttrib4fv` | 设置 4D 向量顶点属性 |

### 7. 缓冲区对象 (8 个)

| 函数名 | 说明 |
|--------|------|
| `glGenBuffers` | 生成缓冲区对象 |
| `glDeleteBuffers` | 删除缓冲区对象 |
| `glBindBuffer` | 绑定缓冲区对象 |
| `glBufferData` | 设置缓冲区数据 |
| `glBufferSubData` | 更新缓冲区子数据 |
| `glGetBufferParameteriv` | 获取缓冲区参数 |

### 8. 帧缓冲对象 (11 个)

| 函数名 | 说明 |
|--------|------|
| `glGenFramebuffers` | 生成帧缓冲对象 |
| `glDeleteFramebuffers` | 删除帧缓冲对象 |
| `glBindFramebuffer` | 绑定帧缓冲对象 |
| `glFramebufferTexture2D` | 附加纹理到帧缓冲 |
| `glFramebufferRenderbuffer` | 附加渲染缓冲到帧缓冲 |
| `glCheckFramebufferStatus` | 检查帧缓冲完整性 |
| `glGetFramebufferAttachmentParameteriv` | 获取帧缓冲附件参数 |
| `glGenRenderbuffers` | 生成渲染缓冲对象 |
| `glDeleteRenderbuffers` | 删除渲染缓冲对象 |
| `glRenderbufferStorage` | 设置渲染缓冲存储 |
| `glGetRenderbufferParameteriv` | 获取渲染缓冲参数 |

### 9. 绘制命令 (4 个)

| 函数名 | 说明 |
|--------|------|
| `glDrawArrays` | 绘制数组 |
| `glDrawElements` | 绘制索引元素 |
| `glGenerateMipmap` | 生成 mipmap |

### 10. 状态管理 (20+ 个)

| 函数名 | 说明 |
|--------|------|
| `glEnable` / `glDisable` | 启用/禁用功能 |
| `glBlendFunc` | 设置混合函数 |
| `glBlendColor` | 设置混合颜色 |
| `glBlendEquation` | 设置混合方程 |
| `glColorMask` | 设置颜色掩码 |
| `glDepthMask` | 设置深度掩码 |
| `glStencilFunc` | 设置模板测试函数 |
| `glStencilFuncSeparate` | 分别设置正反面模板函数 |
| `glStencilMask` | 设置模板掩码 |
| `glStencilMaskSeparate` | 分别设置正反面模板掩码 |
| `glStencilOp` | 设置模板操作 |
| `glStencilOpSeparate` | 分别设置正反面模板操作 |
| `glCullFace` | 设置面剔除 |
| `glFrontFace` | 设置正面方向 |
| `glLineWidth` | 设置线宽 |
| `glScissor` | 设置裁剪矩形 |
| `glViewport` | 设置视口 |

### 11. 清除与同步 (7 个)

| 函数名 | 说明 |
|--------|------|
| `glClear` | 清除缓冲区 |
| `glClearColor` | 设置清除颜色 |
| `glClearStencil` | 设置清除模板值 |
| `glFlush` | 刷新命令缓冲 |
| `glFinish` | 等待命令完成 |

### 12. 查询与错误 (4 个)

| 函数名 | 说明 |
|--------|------|
| `glGetError` | 获取错误码 |
| `glGetIntegerv` | 获取整数状态 |
| `glGetString` | 获取字符串信息 |
| `glIsTexture` | 判断是否为纹理对象 |

### 13. 像素操作 (2 个)

| 函数名 | 说明 |
|--------|------|
| `glPixelStorei` | 设置像素存储模式 |
| `glReadPixels` | 读取像素数据 |

## 使用示例

### 1. 生成函数指针结构

```cpp
struct GrGLFunctions {
#define DECLARE_FUNCTION_PTR(name) PFN##name name;
    GR_GL_CORE_FUNCTIONS_EACH(DECLARE_FUNCTION_PTR)
#undef DECLARE_FUNCTION_PTR
};
```

展开后:
```cpp
struct GrGLFunctions {
    PFNeglGetCurrentDisplay eglGetCurrentDisplay;
    PFNeglQueryString eglQueryString;
    PFNglActiveTexture glActiveTexture;
    // ... 所有核心函数
};
```

### 2. 动态加载函数

```cpp
void loadCoreFunctions(GrGLFunctions* functions, void* library) {
#define LOAD_FUNCTION(name) \
    functions->name = (PFN##name)dlsym(library, #name);
    GR_GL_CORE_FUNCTIONS_EACH(LOAD_FUNCTION)
#undef LOAD_FUNCTION
}
```

### 3. 验证函数指针

```cpp
bool validateCoreFunctions(const GrGLFunctions* functions) {
#define CHECK_FUNCTION(name) \
    if (!functions->name) return false;
    GR_GL_CORE_FUNCTIONS_EACH(CHECK_FUNCTION)
#undef CHECK_FUNCTION
    return true;
}
```

## 依赖关系

### 依赖的模块

无,该文件为纯宏定义,不依赖其他模块。

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrGLInterface.h` | 使用宏生成函数指针成员 |
| `GrGLAssembleInterface.cpp` | 使用宏批量加载核心函数 |
| 平台相关加载代码 | 使用宏生成平台特定的加载逻辑 |

## 设计模式与设计决策

### 1. 宏元编程 (Macro Metaprogramming)

使用宏作为"高阶函数":

```cpp
#define GR_GL_CORE_FUNCTIONS_EACH(M) \
    M(func1) \
    M(func2)
```

**优点**:
- 单一数据源(Single Source of Truth)
- 自动生成重复代码
- 易于维护(添加函数只需修改一处)

**权衡**: 降低代码可读性,调试困难。

### 2. X-Macro 模式

这是经典的 X-Macro 设计模式:

1. 定义数据列表(函数名)
2. 使用宏将数据应用到不同上下文
3. 生成类型声明、函数加载、验证等代码

**适用性**: 适合需要对大量同类项目执行相同操作的场景。

### 3. 仅核心函数清单

只包含核心函数,扩展函数另行处理:

**原因**:
- 核心函数必须存在,加载失败应报错
- 扩展函数可选,需要运行时检测

**设计理念**: 分离必需和可选功能。

### 4. 函数名即字符串

宏参数直接使用函数名,可通过 `#name` 转为字符串:

```cpp
#define LOAD_FUNCTION(name) \
    functions->name = dlsym(lib, #name);  // #name 转为 "glActiveTexture"
```

**优点**: 避免重复定义函数名字符串,减少错误。

### 5. 反斜杠续行

使用 `\` 进行宏续行:

```cpp
#define GR_GL_CORE_FUNCTIONS_EACH(M) \
    M(glActiveTexture) \
    M(glAttachShader)
```

**注意事项**: 反斜杠后不能有空格,否则编译错误。

## 性能考量

### 1. 零运行时开销

宏在预处理阶段展开,不影响运行时性能:

- 无函数调用开销
- 无数据结构开销
- 编译器可完全优化

### 2. 编译时间影响

宏展开会增加编译时间:

- 每次使用宏都会生成大量代码
- 预处理器需要处理重复文本

**权衡**: 编译时开销换取运行时效率和代码维护性。

### 3. 代码膨胀

多次使用宏会生成重复代码:

```cpp
GR_GL_CORE_FUNCTIONS_EACH(LOAD_FUNCTION)    // 生成 124 行
GR_GL_CORE_FUNCTIONS_EACH(CHECK_FUNCTION)   // 再生成 124 行
```

**影响**: 增加可执行文件大小,但每个实例通常只有几千字节。

### 4. 调试困难

宏展开后的代码难以调试:

- 调试器显示展开后的代码
- 错误信息指向宏定义行
- 难以单步调试

**缓解策略**: 提供预处理后的代码查看(`gcc -E`)。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/gpu/ganesh/gl/GrGLInterface.h` | OpenGL 函数接口结构定义 |
| `include/gpu/ganesh/gl/GrGLFunctions.h` | 完整的 OpenGL 函数声明 |
| `src/gpu/ganesh/gl/GrGLAssembleInterface.cpp` | 动态加载 OpenGL 函数实现 |
| `src/gpu/ganesh/gl/GrGLUtil.h` | OpenGL 工具函数 |
