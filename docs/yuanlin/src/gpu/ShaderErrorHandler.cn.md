# ShaderErrorHandler

> 源文件
> - include/gpu/ShaderErrorHandler.h
> - src/gpu/ShaderErrorHandler.cpp

## 概述

`ShaderErrorHandler` 是 Skia GPU 模块中的抽象错误处理器类,用于在编译着色器时报告错误。该类提供了一个可扩展的接口,允许客户端自定义着色器编译错误的处理方式。Skia 提供了默认实现,通过 `SkDebugf` 和断言来报告编译失败。

该类属于 `skgpu` 命名空间,为不同的 GPU 后端(OpenGL、Vulkan、Metal 等)提供统一的错误处理抽象。

## 架构位置

`ShaderErrorHandler` 位于 Skia GPU 基础设施层,为所有 GPU 后端的着色器编译提供错误处理机制:

```
skia/
  include/gpu/
    ShaderErrorHandler.h        # 公共接口
  src/gpu/
    ShaderErrorHandler.cpp      # 默认实现
    [各 GPU 后端调用此接口报告错误]
```

该类被 GPU 着色器编译系统使用,在编译失败时调用错误处理回调。

## 主要类与结构体

### ShaderErrorHandler

抽象错误处理器基类。

**继承关系:**
- 基类: 无
- 派生类: `DefaultShaderErrorHandler`(内部实现)

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| 无成员变量 | - | 纯接口类 |

**关键方法:**

| 方法名 | 返回类型 | 说明 |
|--------|----------|------|
| `compileError(const char*, const char*)` | `void` | 兼容性接口,报告编译错误 |
| `compileError(const char*, const char*, bool)` | `void` | 报告编译错误,包含缓存信息 |

### DefaultShaderErrorHandler (内部类)

默认错误处理器实现,使用 `SkDebugf` 输出错误并触发断言。

## 公共 API 函数

### ShaderErrorHandler 虚函数

```cpp
virtual void compileError(const char* shader, const char* errors);
```
**功能:** 报告着色器编译错误(向后兼容版本)
**参数:**
- `shader` - 编译失败的着色器源码
- `errors` - 编译器返回的错误信息

```cpp
virtual void compileError(const char* shader,
                         const char* errors,
                         bool shaderWasCached);
```
**功能:** 报告着色器编译错误,包含缓存状态信息
**参数:**
- `shader` - 编译失败的着色器源码
- `errors` - 编译器返回的错误信息
- `shaderWasCached` - 着色器是否来自缓存

### 工厂函数

```cpp
ShaderErrorHandler* DefaultShaderErrorHandler();
```
**功能:** 获取默认错误处理器的单例实例
**返回:** 指向默认处理器的指针
**特点:** 线程安全的静态单例

## 内部实现细节

### 默认错误处理器实现

默认实现 `DefaultShaderErrorHandler` 继承自 `ShaderErrorHandler`,实现如下:

```cpp
class DefaultShaderErrorHandler : public ShaderErrorHandler {
public:
    void compileError(const char* shader, const char* errors) override {
        std::string message = SkShaderUtils::BuildShaderErrorMessage(shader, errors);
        SkShaderUtils::VisitLineByLine(message, [](int, const char* lineText) {
            SkDebugf("%s\n", lineText);
        });
        SkDEBUGFAILF("Shader compilation failed!\n\n%s", message.c_str());
    }
};
```

**实现特点:**
1. 使用 `SkShaderUtils::BuildShaderErrorMessage` 格式化错误信息
2. 逐行输出到调试输出(通过 `SkDebugf`)
3. 触发调试断言 `SkDEBUGFAILF`,在调试构建中中断执行
4. 静态单例模式确保全局唯一实例

### 错误处理流程

1. GPU 后端编译着色器失败
2. 调用 `ShaderErrorHandler::compileError`
3. 默认实现格式化并输出错误信息
4. 在调试模式下触发断言,帮助开发者定位问题

### 向后兼容性

提供两个版本的 `compileError` 方法:
- 旧版本:仅接收 shader 和 errors
- 新版本:额外接收 `shaderWasCached` 参数
- 默认实现中,新版本调用旧版本,忽略缓存标志

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkTypes.h` | 基础类型定义 |
| `include/private/base/SkDebug.h` | 调试输出和断言宏 |
| `src/utils/SkShaderUtils.h` | 着色器工具函数,格式化错误信息 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| GPU 后端编译器 | 着色器编译失败时调用错误处理器 |
| GrContext | 创建上下文时可以设置自定义错误处理器 |
| 测试工具 | 单元测试中验证着色器编译错误 |

## 设计模式与设计决策

### 设计模式

1. **策略模式 (Strategy Pattern)**
   - `ShaderErrorHandler` 是抽象策略接口
   - 默认实现和自定义实现是具体策略
   - 允许客户端替换错误处理行为

2. **单例模式 (Singleton Pattern)**
   - `DefaultShaderErrorHandler` 使用静态局部变量实现单例
   - 确保默认处理器全局唯一,避免重复创建

3. **模板方法模式 (Template Method)**
   - 新版本 `compileError` 调用旧版本
   - 提供默认行为,子类可以覆盖

### 设计决策

1. **抽象接口设计**
   - 使用纯虚函数定义接口,客户端可以完全自定义行为
   - 默认实现使用空函数,避免强制实现

2. **向后兼容性**
   - 保留旧版本 `compileError` 接口
   - 新参数默认被忽略,确保旧代码继续工作

3. **错误处理策略**
   - 默认实现在调试模式下触发断言
   - 发布模式下仅输出错误,不中断程序
   - 帮助开发者快速定位着色器问题

4. **不可复制设计**
   - 删除拷贝构造和赋值操作符
   - 防止错误处理器被意外复制
   - 确保处理器生命周期管理正确

## 性能考量

1. **单例优化**
   - 默认处理器使用静态局部变量,无额外分配开销
   - 线程安全初始化(C++11 保证)

2. **错误路径开销**
   - 错误处理仅在编译失败时触发,属于异常路径
   - 字符串格式化和输出开销可接受

3. **虚函数调用**
   - 使用虚函数实现多态,单次调用开销极小
   - 错误情况下性能不是关键考量

## 相关文件

| 文件路径 | 说明 |
|----------|------|
| `include/gpu/ShaderErrorHandler.h` | 公共接口定义 |
| `src/gpu/ShaderErrorHandler.cpp` | 默认实现 |
| `src/utils/SkShaderUtils.h` | 着色器工具函数 |
| `src/gpu/ganesh/GrGpu.cpp` | GPU 后端调用错误处理器 |
| `include/gpu/ganesh/GrContextOptions.h` | 上下文选项,可设置自定义处理器 |
