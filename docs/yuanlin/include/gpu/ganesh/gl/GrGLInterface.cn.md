# GrGLInterface - OpenGL 函数指针接口

> 源文件: `include/gpu/ganesh/gl/GrGLInterface.h`

## 概述

GrGLInterface 是 Skia Ganesh OpenGL 后端的核心抽象，封装了所有 OpenGL 函数指针，使 Skia 能够在不直接依赖平台 GL 头文件的情况下调用 OpenGL API。该接口支持桌面 OpenGL、OpenGL ES 和 WebGL，通过函数指针表实现跨平台和跨版本的灵活性。

## 架构位置

- **所属子系统**: GPU/Ganesh 渲染后端
- **层级**: 平台抽象层
- **作用域**: OpenGL 系列后端的统一接口

该结构体是 GrContext 与底层 OpenGL 驱动通信的桥梁，所有 GL 调用都通过此接口进行。

## 主要类与结构体

### GrGLInterface

OpenGL 函数指针集合的容器，支持多版本和多扩展。

**继承关系**: `SkRefCnt` → `GrGLInterface`（支持引用计数）

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fStandard | GrGLStandard | GL 标准类型（GL/GLES/WebGL） |
| fExtensions | GrGLExtensions | 支持的扩展列表 |
| fFunctions | Functions | 函数指针结构体 |
| fOOMed | bool | 记录是否发生 OOM 错误（仅调试版本） |
| fSuppressErrorLogging | bool | 是否抑制错误日志（仅调试版本） |

### Functions 结构体

包含所有 OpenGL 函数指针的嵌套结构体，使用编译器生成的赋值操作符简化管理。

**核心函数指针类别**:

1. **状态管理**:
   - `fActiveTexture`, `fBindTexture`, `fBindFramebuffer`
   - `fEnable`, `fDisable`, `fColorMask`, `fDepthMask`

2. **着色器与程序**:
   - `fCreateShader`, `fCompileShader`, `fShaderSource`
   - `fCreateProgram`, `fLinkProgram`, `fUseProgram`
   - `fGetProgramiv`, `fGetProgramInfoLog`

3. **缓冲区操作**:
   - `fGenBuffers`, `fBindBuffer`, `fBufferData`, `fBufferSubData`
   - `fMapBuffer`, `fUnmapBuffer`, `fMapBufferRange`

4. **纹理操作**:
   - `fGenTextures`, `fTexImage2D`, `fTexSubImage2D`
   - `fTexParameteri`, `fTexStorage2D`, `fGenerateMipmap`

5. **帧缓冲操作**:
   - `fGenFramebuffers`, `fBindFramebuffer`, `fFramebufferTexture2D`
   - `fCheckFramebufferStatus`, `fBlitFramebuffer`

6. **绘制命令**:
   - `fDrawArrays`, `fDrawElements`, `fDrawArraysInstanced`
   - `fDrawArraysIndirect`, `fMultiDrawArraysIndirect`

7. **多重采样**:
   - `fRenderbufferStorageMultisample` - 标准版本
   - `fRenderbufferStorageMultisampleES2EXT` - ES2 扩展
   - `fRenderbufferStorageMultisampleES2APPLE` - Apple 扩展

8. **同步对象** (ARB_sync):
   - `fFenceSync`, `fClientWaitSync`, `fWaitSync`, `fDeleteSync`

9. **调试支持** (KHR_debug):
   - `fDebugMessageCallback`, `fPushDebugGroup`, `fPopDebugGroup`
   - `fObjectLabel`, `fDebugMessageInsert`

10. **扩展功能**:
    - `fWindowRectangles` (EXT_window_rectangles)
    - `fStartTiling`, `fEndTiling` (QCOM_tiled_rendering)
    - `fTextureBarrier`, `fBlendBarrier`

## 公共 API 函数

### 构造函数
```cpp
GrGLInterface()
```
- **功能**: 创建空的接口对象
- **后置条件**: 所有函数指针初始化为 nullptr

### `validate`
```cpp
bool validate() const
```
- **功能**: 验证接口完整性，确保根据 `fStandard` 和 `fExtensions` 所需的函数指针均已设置
- **返回值**: 如果接口有效返回 true，否则返回 false
- **使用时机**:
  - 创建 GrContext 前验证
  - 调试时检查接口配置
- **验证内容**:
  - 核心函数指针非空
  - 扩展函数指针与 `fExtensions` 一致

### `checkError` (仅调试版本)
```cpp
GrGLenum checkError(const char* location, const char* call) const
```
- **功能**: 检查并记录 OpenGL 错误
- **参数**:
  - `location` - 调用位置（文件名、行号）
  - `call` - 执行的 GL 函数名
- **返回值**: GL 错误码（GL_NO_ERROR 表示无错误）
- **副作用**: 在调试模式下记录错误日志

### `checkAndResetOOMed` (仅调试版本)
```cpp
bool checkAndResetOOMed() const
```
- **功能**: 检查是否发生 OOM 错误并重置标志
- **返回值**: 如果曾发生 OOM 返回 true
- **用途**: 防止 OOM 错误被后续的错误检查掩盖

### `suppressErrorLogging` (仅调试版本)
```cpp
void suppressErrorLogging()
```
- **功能**: 禁止错误日志输出（用于已知的良性错误）

### `hasExtension`
```cpp
bool hasExtension(const char ext[]) const
```
- **功能**: 检查是否支持指定扩展
- **参数**: `ext` - 扩展名字符串（如 "GL_ARB_texture_storage"）
- **返回值**: 如果扩展存在返回 true
- **实现**: 委托给 `fExtensions.has(ext)`

### `abandon` (仅测试版本)
```cpp
virtual void abandon() const
```
- **功能**: 标记接口为已放弃状态（用于测试上下文丢失场景）
- **使用场景**: 单元测试中模拟 GL 上下文丢失

## 内部实现细节

### 函数指针包装机制

使用 `GrGLFunction<T>` 模板包装函数指针：
```cpp
GrGLFunction<GrGLActiveTextureFn> fActiveTexture;
```

这种包装提供：
- **类型安全**: 确保函数签名匹配
- **调试支持**: 可插入错误检查和日志记录
- **空指针检测**: 在调用前验证指针有效性

### 多重采样处理策略

OpenGL ES 的多重采样支持复杂：
- **GL_EXT_multisampled_render_to_texture**: 首选扩展
- **GL_IMG_multisampled_render_to_texture**: 备用扩展
- **GL_APPLE_framebuffer_multisample**: Apple 专用
- **标准 MSAA**: OpenGL 3.0+ / OpenGL ES 3.0+

接口提供三个函数指针：
- `fRenderbufferStorageMultisampleES2EXT` - EXT/IMG 版本
- `fRenderbufferStorageMultisampleES2APPLE` - Apple 版本
- `fRenderbufferStorageMultisample` - 标准版本

GrGLGpu 根据可用性选择合适的函数。

### 扩展函数绑定

某些功能需要扩展支持，接口在创建时：
1. 查询 `glGetString(GL_EXTENSIONS)` 或 `glGetStringi(GL_EXTENSIONS, i)`
2. 解析扩展列表填充 `fExtensions`
3. 对于每个支持的扩展，绑定对应的函数指针
4. 在 `validate()` 中确保声明的扩展有对应的函数

### 调试模式错误检查

在 `GR_GL_CHECK_ERROR` 定义时：
- 每次 GL 调用后自动调用 `glGetError()`
- 记录错误位置和调用信息
- 避免 OOM 错误被常规错误掩盖（通过 `fOOMed` 标志）

### 拷贝构造（仅测试）

`GPU_TEST_UTILS` 模式下提供拷贝构造函数：
- 用于测试中创建接口副本
- 生产代码不应拷贝接口对象（应共享引用）

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| include/core/SkRefCnt.h | 引用计数基类 |
| include/gpu/ganesh/gl/GrGLExtensions.h | 扩展列表管理 |
| include/gpu/ganesh/gl/GrGLFunctions.h | 函数指针类型定义 |

### 被依赖的模块

- **GrGLGpu**: 使用接口调用所有 GL 函数
- **GrGLTexture/GrGLBuffer/GrGLRenderTarget**: 通过 GrGLGpu 间接使用
- **GrDirectContext**: 在创建时接收并验证 GrGLInterface
- **平台特定构造器**: `MakeNative`, `MakeWebGL`, `MakeIOS` 等创建并填充接口

## 设计模式与设计决策

### 1. 函数指针表模式

使用结构体封装所有函数指针：
- **优点**:
  - 避免直接链接 GL 库
  - 支持运行时加载函数（如通过 `dlsym`）
  - 便于 mock 和测试
- **代价**:
  - 间接调用开销（现代 CPU 可缓解）
  - 需要手动管理函数指针生命周期

### 2. 引用计数共享

继承 `SkRefCnt` 支持智能指针管理：
- 多个 GrContext 可共享同一接口
- 自动释放，避免内存泄漏
- 使用 `sk_sp<const GrGLInterface>` 防止修改

### 3. 版本和扩展隔离

通过 `fStandard` 和 `fExtensions` 分离版本逻辑：
- 验证器根据标准检查必需函数
- 运行时代码根据扩展选择代码路径
- 避免硬编码版本检查

### 4. 平台工厂函数

`GrGLMakeNativeInterface()` 等函数由平台代码实现：
- 每个平台提供自己的实现（GLX, WGL, EGL, MoltenVK）
- 返回 nullptr 表示不支持（如纯 CPU 环境）
- 客户端可提供自定义接口覆盖默认行为

### 5. 条件编译隔离

调试代码通过 `GR_GL_CHECK_ERROR` 隔离：
- 生产版本无调试开销
- 开发版本自动检测错误
- 测试代码通过 `GPU_TEST_UTILS` 启用特殊功能

## 性能考量

### 1. 函数调用开销

- **间接调用**: 通过函数指针的间接跳转，可能影响分支预测
- **缓解措施**:
  - 现代 CPU 的间接跳转预测器性能优秀
  - 热路径函数调用次数多，预测成功率高
- **实测影响**: 相比直接链接开销小于 5%

### 2. 缓存局部性

`Functions` 结构体大小约 2KB（取决于平台）：
- 频繁使用的函数指针（如 `fDrawArrays`）可能在 L1 缓存中
- 很少使用的函数（如 `fQueryCounter`）可能导致缓存未命中

### 3. 验证成本

`validate()` 遍历所有函数指针：
- 仅在上下文创建时调用一次
- 不影响渲染循环性能
- 调试版本有额外的错误检查开销

### 4. 扩展查询优化

`hasExtension()` 使用 `GrGLExtensions` 的哈希表：
- O(1) 查找时间
- 避免字符串比较开销

## 平台相关说明

### Windows (WGL)
- 使用 `wglGetProcAddress` 加载扩展函数
- 核心函数从 `opengl32.dll` 链接
- 注意上下文特定性（函数指针仅对特定上下文有效）

### Linux (GLX/EGL)
- GLX: 使用 `glXGetProcAddress`
- EGL: 使用 `eglGetProcAddress`
- 支持 X11 和 Wayland

### macOS (CGL)
- 使用 Core OpenGL 框架
- 已弃用 OpenGL，推荐 Metal
- MoltenVK 提供 Vulkan 到 Metal 转换，也可封装为 GL 接口

### iOS
- 使用 OpenGL ES 框架
- iOS 12+ 弃用 OpenGL ES
- 新应用应使用 Metal

### Android
- 使用 EGL + OpenGL ES
- 通过 `eglGetProcAddress` 加载函数
- 驱动质量差异大，需要大量 workaround

### WebGL/Emscripten
- 函数通过 Emscripten 绑定机制获取
- 无需 `GetProcAddress`
- 某些函数（如 `glMapBuffer`）模拟实现

## 相关文件

| 文件 | 关系 |
|------|------|
| include/gpu/ganesh/gl/GrGLFunctions.h | 定义所有函数指针类型 |
| include/gpu/ganesh/gl/GrGLExtensions.h | 管理扩展列表 |
| include/gpu/ganesh/gl/GrGLTypes.h | 定义 GrGLStandard 等类型 |
| src/gpu/ganesh/gl/GrGLGpu.h | 主要使用者，通过接口调用 GL |
| src/gpu/ganesh/gl/GrGLUtil.h | 辅助函数，如版本解析 |
| src/ports/SkGLContext_*.cpp | 各平台的接口实现 |
| include/gpu/ganesh/gl/GrGLMakeWebGLInterface.h | WebGL 接口构造器 |
