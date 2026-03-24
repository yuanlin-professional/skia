# SkCapabilities

> 源文件: include/core/SkCapabilities.h, src/core/SkCapabilities.cpp

## 概述

`SkCapabilities` 是 Skia 中表示渲染后端能力的类,用于描述特定后端(光栅、GPU)支持的功能特性,特别是 SkSL(Skia Shader Language)版本信息。该类采用引用计数设计,通过 `SkRefCnt` 基类管理生命周期,并提供了获取后端特定能力的静态工厂方法。

该类设计简洁,当前主要用于传递 SkSL 版本信息,为未来扩展预留了空间。

## 架构位置

`SkCapabilities` 在 Skia 架构中的位置:
- 位于公共 API 层(include/core),对外暴露
- 被 `SkSurface` 和 `SkImage` 使用,传递后端能力信息
- 与 SkSL 编译系统集成,提供版本兼容性信息
- 被 Graphite(skgpu::graphite::Caps)用于初始化能力信息
- 桥接前端 API 与后端实现

## 主要类与结构体

### SkCapabilities

表示渲染后端能力的引用计数类。

**继承关系:**
```
SkRefCnt
  └── SkCapabilities
```

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fSkSLVersion | SkSL::Version | 支持的 SkSL 版本,默认 k100 |

**访问控制:**
- `protected` 构造函数:仅允许友元类和子类创建
- `public` 静态工厂方法:标准创建方式
- 友元类:`skgpu::graphite::Caps`(Graphite 后端初始化)

## 公共 API 函数

### 静态工厂方法

```cpp
static sk_sp<const SkCapabilities> RasterBackend()
```
获取光栅后端的能力对象。

**实现细节:**
- 使用静态局部变量实现单例模式
- 首次调用时创建,后续返回相同实例
- 光栅后端固定支持 SkSL Version k100
- 返回 `sk_sp<const SkCapabilities>`,防止修改

**返回值:**
- 指向共享光栅能力对象的智能指针

### 查询方法

```cpp
SkSL::Version skslVersion() const
```
查询后端支持的 SkSL 版本。

**返回值:**
- `SkSL::Version` 枚举值(当前为 k100)

## 内部实现细节

### 光栅后端单例实现

```cpp
sk_sp<const SkCapabilities> SkCapabilities::RasterBackend() {
    static SkCapabilities* sCaps = []() {
        SkCapabilities* caps = new SkCapabilities;
        caps->fSkSLVersion = SkSL::Version::k100;
        return caps;
    }();

    return sk_ref_sp(sCaps);
}
```

设计要点:
1. **静态局部变量**:C++11 保证线程安全初始化
2. **Lambda 初始化**:清晰的初始化逻辑
3. **裸指针管理**:静态指针不需要释放(程序退出时自动回收)
4. **sk_ref_sp**:每次调用增加引用计数,返回智能指针
5. **const 限定**:返回类型为 `const SkCapabilities`,保证不可变性

### Graphite 初始化

```cpp
void SkCapabilities::initSkCaps(const SkSL::ShaderCaps* shaderCaps) {
    this->fSkSLVersion = shaderCaps->supportedSkSLVerion();
}
```

用于 Graphite GPU 后端:
- 由 `skgpu::graphite::Caps` 调用(友元类)
- 从着色器能力对象读取版本信息
- 允许不同 GPU 后端支持不同 SkSL 版本

### 受保护的构造函数

```cpp
protected:
    SkCapabilities() = default;
```

设计意图:
- 防止外部直接实例化
- 强制使用工厂方法创建
- 支持友元类(Graphite)创建实例
- 为未来的子类化预留空间

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| include/core/SkRefCnt.h | 引用计数基类 |
| include/core/SkTypes.h | 核心类型定义 |
| include/sksl/SkSLVersion.h | SkSL 版本枚举 |
| src/sksl/SkSLUtil.h | SkSL 工具函数(实现中) |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| SkSurface | 创建 Surface 时传递能力信息 |
| SkImage | 生成图像时查询能力 |
| SkSL 编译器 | 根据版本编译着色器 |
| skgpu::graphite::Caps | 初始化 Graphite 能力 |
| 客户端代码 | 查询后端特性 |

## 设计模式与设计决策

### 单例模式

光栅后端使用单例:
- **理由**:所有光栅后端实例能力相同
- **实现**:静态局部变量 + 引用计数
- **线程安全**:C++11 保证
- **优点**:节省内存,避免重复创建

### 工厂方法模式

```cpp
static sk_sp<const SkCapabilities> RasterBackend()
```

优点:
- 隐藏创建细节
- 控制实例数量(单例)
- 返回不可变对象(`const`)
- 统一的创建接口

### 不可变对象模式

返回 `sk_sp<const SkCapabilities>`:
- 防止客户端修改能力对象
- 多线程安全
- 允许自由共享
- 简化生命周期管理

### 策略模式变体

不同后端(光栅、Ganesh、Graphite)有不同的能力对象:
- 光栅:单例,固定 k100
- Graphite:动态创建,从 ShaderCaps 初始化
- 未来可扩展其他后端

### 最小接口原则

当前只暴露 SkSL 版本:
- 简化 API
- 为未来扩展预留空间
- 避免过度设计

## 性能考量

### 单例避免重复创建

```cpp
static SkCapabilities* sCaps = []() { ... }();
```

性能优势:
- 光栅能力对象只创建一次
- 后续调用仅增加引用计数(原子操作)
- 无内存分配开销

### 引用计数开销

```cpp
return sk_ref_sp(sCaps);
```

引用计数操作:
- 原子递增:`sCaps->ref()`
- 释放时原子递减
- 现代 CPU 原子操作开销很小(数个周期)

### 内联小对象

```cpp
class SK_API SkCapabilities : public SkRefCnt {
    // ...
    SkSL::Version fSkSLVersion = SkSL::Version::k100;
};
```

对象大小:
- 基类 `SkRefCnt`: 4 字节(引用计数)
- `fSkSLVersion`: 4 字节(枚举)
- 虚表指针: 8 字节
- 总计: ~16 字节

小对象优势:
- 缓存友好
- 拷贝智能指针开销小
- 适合频繁传递

### 常量折叠

```cpp
caps->fSkSLVersion = SkSL::Version::k100;
```

编译器优化:
- k100 是编译期常量
- 可能内联到调用点
- 查询操作可能编译期完成

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| include/core/SkRefCnt.h | 基类 | 引用计数实现 |
| include/sksl/SkSLVersion.h | 枚举定义 | SkSL 版本枚举 |
| src/sksl/SkSLUtil.h | 工具函数 | SkSL 工具 |
| src/gpu/graphite/Caps.h | 友元类 | Graphite 能力类 |
| include/core/SkSurface.h | 使用者 | Surface 创建 |
| include/core/SkImage.h | 使用者 | Image 生成 |
| src/sksl/SkSLCompiler.h | 使用者 | 着色器编译 |
