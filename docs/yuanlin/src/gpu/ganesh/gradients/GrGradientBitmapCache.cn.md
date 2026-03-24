# GrGradientBitmapCache

> 源文件
> - src/gpu/ganesh/gradients/GrGradientBitmapCache.h
> - src/gpu/ganesh/gradients/GrGradientBitmapCache.cpp

## 概述

`GrGradientBitmapCache` 是渐变纹理位图的缓存管理器，负责根据渐变参数（颜色、位置、数量）生成 1D 纹理位图并缓存复用。该缓存避免重复生成相同渐变纹理，使用唯一键索引，支持线程安全访问。生成的位图可上传为 GPU 纹理，供渐变着色器采样，是 GPU 渐变渲染的性能优化关键组件。

## 架构位置

- **模块层级**：`src/gpu/ganesh/gradients/` - Ganesh 渐变处理
- **作用**：渐变纹理缓存
- **使用者**：`GrGradientShader` 及其子类
- **缓存策略**：基于渐变参数的唯一键

## 主要类与结构体

### GrGradientBitmapCache

**核心方法**：
```cpp
const SkBitmap& getGradient(const SkColor* colors, const SkScalar* positions,
                            int count, SkTileMode tileMode);
```

**功能**：
- 生成或查找渐变位图
- 缓存管理（LRU 驱逐）
- 线程安全保护

## 内部实现细节

### 唯一键生成

**键组成**：
- 颜色数组哈希
- 位置数组哈希
- 停止点数量
- 平铺模式

### 位图生成

**尺寸选择**：
- 少量停止点：256 像素
- 大量停止点：512 或 1024 像素

**插值**：
- 线性插值相邻颜色
- 预乘 Alpha
- 映射到位图像素

### 缓存策略

**LRU 驱逐**：
- 达到缓存限制时移除最少使用项
- 默认缓存大小限制（如 32 个位图）

**线程安全**：
- 使用互斥锁保护缓存访问
- 支持多线程并发查询

## 设计模式与设计决策

### 单例模式

全局单例缓存，跨上下文共享。

### 惰性生成

仅在首次请求时生成位图，后续复用。

### 键值缓存

基于哈希表的快速查找，O(1) 复杂度。

## 性能考量

### 缓存命中率

相同渐变参数复用位图，避免重复生成和上传。

### 内存占用

限制缓存大小，平衡内存和性能。

### 线程竞争

细粒度锁减少线程等待时间。

## 相关文件

- `src/gpu/ganesh/gradients/GrGradientShader.h` - 渐变着色器
- `src/core/SkBitmap.h` - 位图类
- `include/core/SkColor.h` - 颜色定义
