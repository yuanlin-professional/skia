# RefCntedCallback

> 源文件: src/gpu/RefCntedCallback.h

## 概述

`RefCntedCallback` 模块提供了两种自动回调管理机制:`AutoCallback`(移动语义)和 `RefCntedCallback`(引用计数)。这些类在析构时自动调用注册的回调函数,广泛用于 GPU 资源的生命周期管理、异步操作完成通知和错误处理。

该模块支持多种回调签名:简单回调、带统计信息的回调、带结果的回调以及同时带结果和统计信息的回调。通过 RAII(Resource Acquisition Is Initialization)机制,确保回调在对象销毁时必然执行,防止资源泄漏和回调遗漏。

## 架构位置

`RefCntedCallback` 位于 GPU 层的基础设施:

- 命名空间: `skgpu`
- 模块位置: `src/gpu/`
- 类型: 头文件,模板类和工具类
- 依赖层级: GPU 基础设施层
- 服务对象: 纹理代理、GPU 操作、异步读取、资源释放

该模块是 GPU 资源生命周期管理的核心组件,被广泛用于 Ganesh 和 Graphite 两个渲染引擎。

## 主要类与结构体

### 继承关系

```
SkNVRefCnt<RefCntedCallback> (基类)
└── RefCntedCallback (引用计数回调)

AutoCallback (独立类,移动语义)
```

### 关键成员变量

#### AutoCallback

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fReleaseProc` | `Callback` | 简单回调函数指针 |
| `fReleaseWithStatsProc` | `CallbackWithStats` | 带统计信息的回调函数指针 |
| `fResultReleaseProc` | `ResultCallback` | 带结果的回调函数指针 |
| `fResultReleaseWithStatsProc` | `ResultCallbackWithStats` | 带结果和统计的回调函数指针 |
| `fReleaseCtx` | `Context` | 回调的上下文指针 |
| `fResult` | `CallbackResult` | 回调结果(成功/失败) |
| `fGpuStats` | `GpuStats` | GPU 统计信息 |

#### RefCntedCallback

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fCallback` | `AutoCallback` | 内部持有的 AutoCallback 对象 |

### 类型定义

```cpp
using Context                 = void*;
using Callback                = void (*)(Context);
using CallbackWithStats       = void (*)(Context, const GpuStats&);
using ResultCallback          = void (*)(Context, CallbackResult);
using ResultCallbackWithStats = void (*)(Context, CallbackResult, const GpuStats&);
```

## 公共 API 函数

### AutoCallback 接口

#### 构造函数

```cpp
// 默认构造(无回调)
AutoCallback();

// 简单回调
AutoCallback(Callback proc, Context ctx);

// 带统计信息的回调
AutoCallback(CallbackWithStats proc, Context ctx);

// 带结果的回调
AutoCallback(ResultCallback proc, Context ctx);

// 带结果和统计的回调
AutoCallback(ResultCallbackWithStats proc, Context ctx);

// 移动构造
AutoCallback(AutoCallback&& that);
```

#### 核心方法

```cpp
// 获取上下文
Context context() const;

// 检查是否接收 GPU 统计信息
bool receivesGpuStats() const;

// 设置失败结果
void setFailureResult();

// 设置统计信息
void setStats(const GpuStats& stats);

// 检查是否有效
explicit operator bool() const;

// 移动赋值
AutoCallback& operator=(AutoCallback&& that);
```

#### 析构函数

```cpp
~AutoCallback();  // 自动调用注册的回调
```

### RefCntedCallback 接口

#### 静态工厂方法

```cpp
// 创建简单回调
static sk_sp<RefCntedCallback> Make(Callback proc, Context ctx);

// 创建带统计信息的回调
static sk_sp<RefCntedCallback> Make(CallbackWithStats proc, Context ctx);

// 创建带结果的回调
static sk_sp<RefCntedCallback> Make(ResultCallback proc, Context ctx);

// 创建带结果和统计的回调
static sk_sp<RefCntedCallback> Make(ResultCallbackWithStats proc, Context ctx);

// 从 AutoCallback 创建
static sk_sp<RefCntedCallback> Make(AutoCallback&& callback);
```

#### 成员方法

```cpp
// 获取上下文
Context context() const;

// 检查是否接收 GPU 统计信息
bool receivesGpuStats() const;

// 设置失败结果
void setFailureResult();

// 设置统计信息
void setStats(const GpuStats& stats);
```

## 内部实现细节

### 析构时回调执行

`AutoCallback` 的析构函数检查并调用注册的回调:

```cpp
~AutoCallback() {
    SkASSERT(this->operator bool() || true);  // 验证状态

    if (fResultReleaseWithStatsProc) {
        fResultReleaseWithStatsProc(fReleaseCtx, fResult, fGpuStats);
    } else if (fReleaseWithStatsProc) {
        fReleaseWithStatsProc(fReleaseCtx, fGpuStats);
    } else if (fResultReleaseProc) {
        fResultReleaseProc(fReleaseCtx, fResult);
    } else if (fReleaseProc) {
        fReleaseProc(fReleaseCtx);
    }
}
```

**执行顺序**(按优先级):
1. 带结果和统计的回调
2. 仅带统计的回调
3. 带结果的回调
4. 简单回调

### 移动语义实现

```cpp
AutoCallback& operator=(AutoCallback&& that) {
    // 复制所有成员
    fReleaseCtx                 = that.fReleaseCtx;
    fReleaseProc                = that.fReleaseProc;
    fReleaseWithStatsProc       = that.fReleaseWithStatsProc;
    fResultReleaseProc          = that.fResultReleaseProc;
    fResultReleaseWithStatsProc = that.fResultReleaseWithStatsProc;
    fResult                     = that.fResult;
    fGpuStats                   = that.fGpuStats;

    // 清空源对象的回调指针
    that.fReleaseProc                = nullptr;
    that.fReleaseWithStatsProc       = nullptr;
    that.fResultReleaseProc          = nullptr;
    that.fResultReleaseWithStatsProc = nullptr;
    return *this;
}
```

**关键点**:
- 转移所有数据
- 源对象的回调指针置空,防止双重调用
- 上下文指针不清空(允许查询)

### 有效性检查

```cpp
explicit operator bool() const {
    auto toInt = [](auto p) { return p ? 1U : 0U; };
    auto total = toInt(fReleaseProc) + toInt(fReleaseWithStatsProc) +
                 toInt(fResultReleaseProc);
    SkASSERT(total <= 1);  // 最多一个回调有效
    return total == 1;
}
```

确保同一时刻最多只有一个回调函数指针非空。

### RefCntedCallback 实现

```cpp
class RefCntedCallback : public SkNVRefCnt<RefCntedCallback> {
private:
    RefCntedCallback(AutoCallback callback) : fCallback(std::move(callback)) {}

    AutoCallback fCallback;  // 内部持有 AutoCallback
};
```

**设计**:
- 私有构造,强制使用工厂方法
- 继承 `SkNVRefCnt`,提供引用计数
- 内部持有 `AutoCallback`,析构时自动触发回调

### 工厂方法实现

```cpp
template <typename R, typename... Args>
static sk_sp<RefCntedCallback> MakeImpl(R proc(Args...), Context ctx) {
    if (!proc) {
        return nullptr;  // 空指针返回 nullptr
    }
    return sk_sp<RefCntedCallback>(new RefCntedCallback({proc, ctx}));
}
```

- 模板化设计,支持多种回调签名
- 空指针检查,避免无效对象
- 返回智能指针,自动管理生命周期

## 依赖关系

### 依赖的模块

| 模块 | 用途 | 头文件 |
|------|------|--------|
| SkRefCnt | 引用计数基类 | `include/core/SkRefCnt.h` |
| GpuTypes | 回调结果和统计信息类型 | `include/gpu/GpuTypes.h` |

### 被依赖的模块

| 模块 | 关系 | 说明 |
|------|------|------|
| GrTexture | 使用方 | 纹理释放回调 |
| GrSurface | 使用方 | 表面释放回调 |
| GrAsyncReadContext | 使用方 | 异步读取完成回调 |
| graphite::TextureProxy | 使用方 | Graphite 纹理代理 |
| GrFlushInfo | 使用方 | Flush 完成回调 |

## 设计模式与设计决策

### 1. RAII 模式

通过析构函数自动执行回调:
- **优点**: 异常安全,防止回调遗漏
- **保证**: 无论正常返回还是异常,回调必然执行

### 2. 移动语义(AutoCallback)

使用移动语义而非拷贝:
- **防止双重调用**: 源对象的回调被清空
- **性能**: 无深拷贝开销
- **语义**: 表达"所有权转移"

### 3. 引用计数(RefCntedCallback)

适用于需要共享的场景:
- 多个对象可以持有同一个回调
- 最后一个持有者析构时触发回调
- 类似 `std::shared_ptr`

### 4. 工厂模式

强制使用静态工厂方法创建:
- 返回智能指针,防止内存泄漏
- 统一创建接口
- 空指针安全

### 5. 类型安全的回调签名

通过类型系统区分不同的回调:
```cpp
Callback                = void (*)(Context);
CallbackWithStats       = void (*)(Context, const GpuStats&);
ResultCallback          = void (*)(Context, CallbackResult);
ResultCallbackWithStats = void (*)(Context, CallbackResult, const GpuStats&);
```

编译期检查,避免错误调用。

### 6. 状态管理

- `fResult`: 默认 `kSuccess`,可通过 `setFailureResult()` 设置为 `kFailed`
- `fGpuStats`: 通过 `setStats()` 设置
- 状态在对象生命周期内累积,析构时传递给回调

## 性能考量

### 1. 内存布局

`AutoCallback` 大小:
```cpp
sizeof(AutoCallback) =
    sizeof(void*) * 4 +  // 4 个函数指针
    sizeof(void*) +      // fReleaseCtx
    sizeof(CallbackResult) +  // fResult
    sizeof(GpuStats)     // fGpuStats
```

通常约 48-64 字节(64 位平台)。

### 2. 无虚函数开销

- `AutoCallback` 无虚函数,无 vtable 开销
- `RefCntedCallback` 继承 `SkNVRefCnt`("NV" = No Virtual),同样无虚函数

### 3. 移动成本

移动操作仅涉及成员变量复制:
- 48-64 字节的内存拷贝
- 无堆分配
- 可内联

### 4. 引用计数成本

`RefCntedCallback` 的引用计数:
- 原子操作(线程安全)
- 每次 ref/unref 约 1-2 个原子指令
- 权衡: 安全性 vs 性能

### 5. 回调调用开销

- 间接函数调用(通过指针)
- 无法内联
- 典型开销: 几个 CPU 周期

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkRefCnt.h` | 依赖 | 引用计数基类 |
| `include/gpu/GpuTypes.h` | 依赖 | 回调结果和统计类型 |
| `src/gpu/ganesh/GrTexture.h` | 使用方 | 纹理释放回调 |
| `src/gpu/ganesh/GrSurface.h` | 使用方 | 表面释放回调 |
| `src/gpu/ganesh/SurfaceContext.cpp` | 使用方 | 异步操作回调 |
| `src/gpu/graphite/Texture.h` | 使用方 | Graphite 纹理 |
| `include/gpu/GrFlushInfo.h` | 使用方 | Flush 完成回调 |

## 使用示例

### 示例 1: 简单回调

```cpp
void MyCleanup(void* ctx) {
    delete static_cast<MyResource*>(ctx);
}

AutoCallback callback(MyCleanup, myResource);
// 离开作用域时自动调用 MyCleanup
```

### 示例 2: 带结果的回调

```cpp
void OnComplete(void* ctx, CallbackResult result) {
    if (result == CallbackResult::kSuccess) {
        // 处理成功
    } else {
        // 处理失败
    }
}

AutoCallback callback(OnComplete, userData);
if (operationFailed) {
    callback.setFailureResult();
}
// 析构时调用 OnComplete,传递结果
```

### 示例 3: 引用计数回调

```cpp
auto callback = RefCntedCallback::Make(MyCleanup, resource);

// 多个对象可以持有
textureProxy->setCallback(callback);
surface->setCallback(callback);

// 最后一个持有者释放时,回调执行
```

### 示例 4: 带统计信息

```cpp
void OnFlushComplete(void* ctx, CallbackResult result, const GpuStats& stats) {
    LogGpuStats(stats);
}

auto callback = RefCntedCallback::Make(OnFlushComplete, logContext);
// ... 执行 GPU 操作 ...
callback->setStats(gpuStats);
// 析构时传递统计信息
```
