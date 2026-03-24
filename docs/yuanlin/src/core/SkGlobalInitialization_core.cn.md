# SkGlobalInitialization_core

> 源文件
> - src/core/SkGlobalInitialization_core.cpp

## 概述

`SkGlobalInitialization_core.cpp` 是 Skia 核心模块的全局初始化文件,负责注册所有可序列化对象(flattenables)到 Skia 的类型注册系统。该文件通过 `SkFlattenable::PrivateInitializer` 类的静态初始化机制,在程序启动时自动注册图像滤镜和特效相关的工厂函数,使得这些对象可以通过 `SkFlattenable::Deserialize()` 从二进制数据重建。

这是 Skia 核心库支持序列化/反序列化的基础设施,确保绘制命令、滤镜效果等可以跨进程传输或持久化存储。

## 架构位置

该文件位于 Skia 初始化架构的最底层:

- **执行时机**: 程序启动时,在 main() 之前通过静态初始化执行
- **上游触发**: `SkGraphics::Init()` 或 `SkFlattenable::RegisterFlattenablesIfNeeded()` 确保初始化
- **下游影响**: 所有需要序列化的效果和滤镜
- **协作模块**: `SkFlattenable` 类型系统、`SkReadBuffer`/`SkWriteBuffer` 序列化框架

## 主要类与结构体

### SkFlattenable::PrivateInitializer (外部类)

虽然未在此文件定义,但该文件调用其静态方法:

| 静态方法 | 说明 |
|---------|------|
| InitEffects() | 注册所有特效类型(path effects, mask filters, shader 等) |
| InitImageFilters() | 注册所有图像滤镜类型 |
| Finalize() | 完成初始化流程 |

## 公共 API 函数

```cpp
void SkFlattenable::RegisterFlattenablesIfNeeded();
```

该函数确保所有 flattenables 已注册。内部使用 `SkOnce` 保证线程安全和幂等性。

## 内部实现细节

### 初始化流程

```cpp
void SkFlattenable::RegisterFlattenablesIfNeeded() {
    static SkOnce once;
    once([]{
        SkFlattenable::PrivateInitializer::InitEffects();        // 注册特效
        SkFlattenable::PrivateInitializer::InitImageFilters();   // 注册滤镜
        SkFlattenable::Finalize();                               // 完成初始化
    });
}
```

关键特性:
- **`SkOnce`**: 确保初始化代码仅执行一次,即使多线程并发调用
- **延迟初始化**: 首次调用时才执行,避免静态初始化顺序问题
- **幂等性**: 多次调用安全,不会重复注册

### 注册的对象类型

虽然文件本身不包含注册代码,但它触发的初始化包括:

**InitEffects() 注册**:
- `SkPathEffect` 派生类(dash、corner、discrete 等)
- `SkMaskFilter` 派生类(blur、table 等)
- `SkShader` 派生类(gradient、bitmap、blend 等)
- `SkColorFilter` 派生类(matrix、table、lighting 等)

**InitImageFilters() 注册**:
- `SkBlurImageFilter`
- `SkMatrixTransformImageFilter`
- `SkColorFilterImageFilter`
- `SkComposeImageFilter`
- `SkMergeImageFilter`
- 以及其他所有图像滤镜实现

### 注册机制原理

每个可序列化类使用宏 `SK_REGISTER_FLATTENABLE` 注册:

```cpp
// 在类的 .cpp 文件中
SK_REGISTER_FLATTENABLE(SkBlurImageFilter);

// 宏展开为类似以下代码:
static SkFlattenable::Register reg("SkBlurImageFilter",
    SkBlurImageFilter::CreateProc,
    SkBlurImageFilter::GetFlattenableType());
```

注册表将类名映射到工厂函数,用于反序列化。

### 静态初始化与 SkOnce 的关系

为什么需要两层初始化:

1. **静态初始化**: 每个类的 `SK_REGISTER_FLATTENABLE` 在静态初始化时注册
2. **SkOnce 保护**: `RegisterFlattenablesIfNeeded()` 确保主初始化逻辑仅执行一次

这种设计解决了:
- 静态初始化顺序不确定问题
- 多线程竞争问题
- 允许显式调用 `SkGraphics::Init()` 控制初始化时机

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkFlattenable | 序列化基类和注册系统 |
| SkOnce | 线程安全的一次性初始化 |
| 各种 effects 和 image filters | 被注册的实际类型 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| SkGraphics | 调用 `RegisterFlattenablesIfNeeded()` 初始化 |
| SkPicture | 反序列化绘制命令时需要注册的类型 |
| SkReadBuffer | 使用注册的工厂函数创建对象 |
| 跨进程通信 | 远程渲染、IPC 场景需要序列化支持 |

## 设计模式与设计决策

### 单例模式(通过 SkOnce)

```cpp
static SkOnce once;
once([]{...});
```

使用 `SkOnce` 实现懒加载单例模式:
- 线程安全
- 无需显式单例类
- 自动处理双重检查锁定

### 工厂模式

注册系统实现抽象工厂模式:
- **产品**: 各种 `SkFlattenable` 子类
- **工厂**: 注册的 `CreateProc` 函数指针
- **工厂注册**: `SkFlattenable::Register` 将类名映射到工厂

### 模块化初始化

将初始化分为多个阶段:
1. `InitEffects()`: 特效相关
2. `InitImageFilters()`: 滤镜相关
3. `Finalize()`: 完成初始化

优点:
- 清晰的职责分离
- 便于扩展新的类别
- 方便调试初始化问题

### 设计决策: 显式调用 vs 自动初始化

Skia 选择混合策略:
- **自动**: 静态初始化注册各个类
- **显式**: 通过 `SkGraphics::Init()` 触发主初始化

权衡:
- 允许在非标准环境(无静态初始化)手动控制
- 避免完全自动初始化的不确定性
- 兼容嵌入式平台和特殊构建配置

### 设计决策: 为何需要 Finalize()

`Finalize()` 步骤的作用:
- 锁定注册表,防止后续修改
- 验证所有必需类型已注册
- 触发依赖的初始化(如验证注册表完整性)

## 性能考量

### 一次性开销

初始化开销仅在首次调用时发生:
- 注册数百个类型
- 构建内部查找表
- 总耗时通常 < 1ms

### 延迟初始化优势

不使用 Skia 序列化功能的应用:
- 初始化可能永不发生(如果未调用 `SkGraphics::Init()`)
- 减少启动延迟
- 节省内存(未分配注册表)

### 线程安全开销

`SkOnce` 使用原子操作:
- 首次调用: 需要同步
- 后续调用: 快速原子检查(几乎无开销)

### 缓存友好性

注册表通常实现为哈希表:
- 反序列化时快速查找类名
- O(1) 平均复杂度
- 热路径(常用类型)缓存友好

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| include/core/SkFlattenable.h | 基础 | 序列化基类定义 |
| include/private/base/SkOnce.h | 工具 | 一次性初始化原语 |
| src/effects/* | 被注册 | 各种特效实现 |
| src/core/SkImageFilter_Base.h | 被注册 | 图像滤镜基类 |
| src/core/SkReadBuffer.h | 使用者 | 反序列化读取器 |
| src/core/SkWriteBuffer.h | 使用者 | 序列化写入器 |
| include/core/SkGraphics.h | 触发者 | 调用初始化函数 |
| src/core/SkPictureData.cpp | 使用者 | 绘制命令反序列化 |
