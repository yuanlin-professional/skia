# SkDiscardableMemory

> 源文件: `include/private/chromium/SkDiscardableMemory.h`

## 概述
SkDiscardableMemory 是一个抽象接口,用于管理可丢弃的内存块。这种内存可以被系统在内存压力下自动清除,而无需显式释放。该接口由嵌入器(如 Chromium)提供具体实现,允许 Skia 使用平台特定的可丢弃内存机制来优化内存使用。

## 架构位置
该文件位于 Skia 的 Chromium 私有接口层,是 Skia 与 Chromium 集成的桥梁。它定义了内存管理的抽象接口,位于资源缓存和平台内存管理之间。Skia 内部使用此接口来缓存可以重新生成的数据(如解码后的图像),而具体实现由 Chromium 提供。

## 主要类与结构体

### SkDiscardableMemory
可丢弃内存的抽象接口,定义了锁定、解锁和数据访问操作。

**继承关系**: 无基类(纯接口)

**关键特性**:
- 不可拷贝、不可赋值(删除了拷贝构造和赋值操作符)
- 需要通过工厂方法创建
- 使用锁定/解锁机制控制访问

### Factory
可丢弃内存的工厂接口,用于创建 SkDiscardableMemory 实例。

**继承关系**: SkRefCnt → Factory

## 公共 API 函数

### 工厂方法

#### `static SkDiscardableMemory* Create(size_t bytes)`
- **功能**: 创建、初始化并锁定一个可丢弃内存对象
- **参数**: `bytes` - 要分配的内存字节数
- **返回值**: 成功返回已锁定的 SkDiscardableMemory 指针,失败返回 nullptr
- **失败情况**: 创建、初始化或锁定任一步骤失败都会返回 nullptr

### 生命周期管理

#### `virtual ~SkDiscardableMemory()`
- **功能**: 虚析构函数,释放可丢弃内存
- **参数**: 无
- **返回值**: 无
- **前提条件**: 必须在未锁定状态下调用

### 锁定机制

#### `[[nodiscard]] virtual bool lock() = 0`
- **功能**: 锁定内存,防止被系统丢弃
- **参数**: 无
- **返回值**:
  - `true`: 锁定成功,内存数据完整
  - `false`: 底层内存已被丢弃,锁定失败
- **使用约束**: 不允许嵌套锁定(不能在已锁定状态再次调用)
- **属性**: 使用 `[[nodiscard]]` 强制调用者检查返回值

#### `virtual void unlock() = 0`
- **功能**: 解锁内存,允许系统在需要时丢弃
- **参数**: 无
- **返回值**: 无
- **使用约束**: 必须在每次成功的 lock() 调用后调用

### 数据访问

#### `virtual void* data() = 0`
- **功能**: 获取可丢弃内存的数据指针
- **参数**: 无
- **返回值**: 指向内存数据的指针
- **使用约束**: 仅在内存处于锁定状态时有效调用

## 内部实现细节

### 锁定/解锁协议
可丢弃内存使用严格的锁定协议:

1. **创建时状态**: 通过 Create() 创建的对象处于锁定状态
2. **使用模式**: 锁定 → 访问数据 → 解锁
3. **重新锁定**: unlock() 后可以再次 lock(),但可能失败(数据已丢弃)
4. **析构约束**: 析构前必须确保处于解锁状态

### 数据丢弃检测
锁定操作的返回值指示内存状态:
```cpp
if (!memory->lock()) {
    // 数据已被系统丢弃,需要重新生成
    regenerateData();
}
```

### 嵌套锁定禁止
接口明确禁止嵌套锁定:
- 简化实现复杂性
- 避免引用计数开销
- 清晰的所有权语义

### Factory 抽象
嵌套的 Factory 类允许定制内存创建策略:
```cpp
class Factory : public SkRefCnt {
public:
    virtual SkDiscardableMemory* create(size_t bytes) = 0;
};
```
这支持注入不同的可丢弃内存实现。

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| SkRefCnt | Factory 的引用计数基类 |
| SkTypes | 类型定义和 SK_SPI 宏 |

### 被依赖的模块
- SkResourceCache: 使用可丢弃内存缓存图像数据
- SkScaledImageCache: 缓存缩放后的图像
- SkBitmapCache: 缓存位图数据
- Chromium 的 SkDiscardableMemory 实现
- 其他需要可重新生成数据缓存的 Skia 模块

## 设计模式与设计决策

### 工厂方法模式
提供静态工厂方法 Create() 和 Factory 接口:
- 允许嵌入器提供自定义实现
- 隐藏具体实现细节
- 支持依赖注入

### 资源获取即初始化(RAII)的变体
虽然不是完整的 RAII,但使用了类似思想:
- 创建即锁定(获取资源)
- 显式解锁(释放资源)
- 析构检查状态(必须已解锁)

### 策略模式
通过 Factory 接口实现不同的内存分配策略:
- Chromium 可以使用操作系统的可丢弃内存
- 测试可以使用模拟实现
- 其他嵌入器可以提供自定义策略

### 不可拷贝设计
禁用拷贝操作防止资源管理问题:
```cpp
SkDiscardableMemory(const SkDiscardableMemory&) = delete;
SkDiscardableMemory& operator=(const SkDiscardableMemory&) = delete;
```

### 接口隔离原则
接口只包含最少的必要方法:
- lock/unlock: 状态管理
- data: 数据访问
- 无其他冗余操作

## 性能考量

### 内存压力响应
可丢弃内存允许系统在内存压力下自动回收缓存:
- 避免 OOM(内存不足)崩溃
- 动态适应系统内存状态
- 不需要手动清理缓存

### 锁定开销
锁定/解锁操作有一定开销:
- 通常涉及系统调用
- 可能需要检查页表状态
- 建议减少锁定/解锁频率,保持锁定期间完成所有操作

### 数据重新生成成本
锁定失败意味着需要重新生成数据:
- 解码图像的 CPU 开销
- 可能的磁盘 I/O
- 应该针对重要或常用数据使用可丢弃内存

### 页对齐优化
可丢弃内存通常以页为单位管理:
- 实现可能返回页对齐的内存
- 小对象可能浪费空间
- 适合较大的缓存数据(如完整图像)

## 使用场景

### 图像解码缓存
最典型的使用场景:
```cpp
// 首次解码
auto memory = SkDiscardableMemory::Create(imageSize);
if (memory) {
    memcpy(memory->data(), decodedPixels, imageSize);
    memory->unlock();
    cache->store(imageKey, memory);
}

// 后续使用
auto memory = cache->lookup(imageKey);
if (memory && memory->lock()) {
    // 使用缓存的数据
    drawImage(memory->data());
    memory->unlock();
} else {
    // 数据已丢弃,重新解码
    redecodeImage();
}
```

### 缩放图像缓存
缓存不同尺寸的图像:
- 原始大小图像存储在可丢弃内存
- 缩放版本也可以缓存
- 系统内存紧张时自动清理

### 字体光栅化缓存
缓存渲染后的字形位图:
- 光栅化一次,多次使用
- 内存不足时可以重新光栅化
- 平衡内存和 CPU 开销

## 平台相关说明

### Chromium 实现
在 Chromium 中,SkDiscardableMemory 映射到:
- **Linux**: `madvise(MADV_FREE)` 或 ashmem
- **Windows**: 可丢弃内存 API (DiscardVirtualMemory)
- **macOS/iOS**: `madvise(MADV_FREE_REUSABLE)`
- **Android**: ashmem (匿名共享内存)

### 其他嵌入器
非 Chromium 嵌入器可能:
- 提供简单的堆内存实现(不真正丢弃)
- 使用 LRU 缓存模拟丢弃行为
- 返回 nullptr 禁用此功能

## 相关文件
| 文件 | 关系 |
|------|------|
| src/core/SkResourceCache.h | 主要使用者,资源缓存实现 |
| src/core/SkScaledImageCache.h | 缩放图像缓存 |
| src/core/SkBitmapCache.h | 位图缓存 |
| chromium/SkDiscardableMemoryChromium.cpp | Chromium 具体实现 |
| include/core/SkRefCnt.h | Factory 的基类 |
| include/core/SkTypes.h | 类型定义 |
