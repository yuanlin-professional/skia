# SkCPURecorderImpl

> 源文件：src/core/SkCPURecorderImpl.h

## 概述

`SkCPURecorderImpl` 是 `skcpu::Recorder` 的私有实现类，继承自公共接口 `skcpu::Recorder`。它持有关联的 CPU 上下文指针，作为录制器的具体实现，是 Skia CPU 渲染后端的核心组件之一。

该类当前为极简设计，主要功能是维护与上下文的关联关系，为未来扩展（如命令缓冲、资源跟踪等）预留空间。

## 架构位置

```
skcpu::Recorder (公共接口)
  └── RecorderImpl (私有实现)
        └── 持有 -> const ContextImpl*
```

## 主要类与结构体

### RecorderImpl

**继承关系：**`skcpu::Recorder` -> `SkRecorder`

**关键成员变量：**

| 成员 | 类型 | 说明 |
|------|------|------|
| fCtx | const ContextImpl* const | 关联的上下文常量指针 |

**核心方法：**

| 方法 | 说明 |
|------|------|
| `RecorderImpl(const ContextImpl*)` | 构造函数 |
| `ctx()` | 获取上下文指针 |

## 公共 API 函数

### 1. 构造函数

```cpp
RecorderImpl(const ContextImpl* ctx) : fCtx(ctx) {}
```

**参数：**
- `ctx`: 上下文指针，必须在录制器生命周期内有效

**约束：**
- `ctx` 不能为 `nullptr`
- `ctx` 必须指向有效的 `ContextImpl` 对象

### 2. 上下文访问

```cpp
const ContextImpl* ctx() const { return fCtx; }
```

**功能：**获取关联的上下文指针。

**用途：**
- 访问共享资源（如缓存、线程池）
- 传递给需要上下文的内部函数

## 内部实现细节

### 1. 类定义

```cpp
namespace skcpu {
class RecorderImpl final : public skcpu::Recorder {
public:
    RecorderImpl(const ContextImpl* ctx) : fCtx(ctx) {}
    const ContextImpl* ctx() const { return fCtx; }
private:
    const ContextImpl* const fCtx;
};
}
```

**设计要点：**
- `final` 关键字防止进一步派生
- `fCtx` 为常量指针的常量成员（双重常量）
- 仅存储上下文指针，当前无其他状态

### 2. 类型转换辅助函数

```cpp
inline skcpu::RecorderImpl* asRRI(skcpu::Recorder* rr) {
    return static_cast<skcpu::RecorderImpl*>(rr);
}
```

**功能：**快速将公共接口转换为实现类（内部使用）。

**安全性：**假设传入的录制器确实是 `RecorderImpl`，无运行时检查。

### 3. 常量保证

```cpp
const ContextImpl* const fCtx;
```

**双重常量：**
- 第一个 `const`：指向的对象不可修改
- 第二个 `const`：指针本身不可修改

**原因：**
- 录制器不应修改上下文状态
- 上下文关联在构造时确定，运行时不应改变

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `skcpu::Recorder` | 基类接口 |
| `skcpu::ContextImpl` | 上下文实现 |

### 被依赖的模块

| 模块 | 使用方式 |
|-----|---------|
| `skcpu::Context` | 在 `makeRecorder()` 中构造 |
| 内部渲染模块 | 通过 `asRRI()` 访问实现 |

## 设计模式与设计决策

### 1. Pimpl（桥接）模式

公共接口 `Recorder` 与实现 `RecorderImpl` 分离：

**优势：**
- 隐藏实现细节
- 减少头文件依赖
- 保持 ABI 稳定

### 2. 最终类（Final Class）

使用 `final` 关键字禁止继承：

**原因：**
- 当前设计不支持多态扩展
- 简化类层次结构
- 编译器可优化虚函数调用

### 3. 不可变关联

```cpp
const ContextImpl* const fCtx;
```

录制器与上下文的关联在构造时固定，运行时不可改变：

**优势：**
- 简化生命周期管理
- 避免悬空指针
- 编译器可优化访问

### 4. 类型安全转换

```cpp
inline skcpu::RecorderImpl* asRRI(skcpu::Recorder* rr) { ... }
```

提供内部使用的快速转换函数，避免重复的 `static_cast`。

## 性能考量

### 1. 内存占用

```cpp
sizeof(RecorderImpl) = 8 字节 (64位) / 4 字节 (32位)
```

仅存储一个指针，内存占用极小。

### 2. 构造开销

```cpp
RecorderImpl(ctx) : fCtx(ctx) {}  // 仅指针赋值，零开销
```

### 3. 上下文访问开销

```cpp
ctx() const { return fCtx; }  // 直接返回指针，~0 ns
```

编译器通常内联此方法，实际为零开销。

### 4. 虚函数开销

作为 `Recorder` 的子类，继承了虚函数表：

```cpp
sizeof(vtable pointer) = 8 字节 (64位)
```

实际对象大小 = 8（vtable）+ 8（fCtx）= 16 字节。

### 5. 缓存友好性

```
[vtable ptr | fCtx] = 16 字节
```

适合单个缓存行（通常 64 字节），访问高效。

## 相关文件

| 文件 | 关系 | 说明 |
|-----|------|------|
| include/core/SkCPURecorder.h | 公共接口 | 录制器公共 API |
| src/core/SkCPUContextImpl.h | 关联对象 | 上下文实现类 |
| src/core/SkCPUContext.cpp | 创建者 | `makeRecorder()` 实现 |
| include/core/SkRecorder.h | 抽象基类 | 通用录制器接口 |
