# SkBitmapKey

> 源文件
> - src/pdf/SkBitmapKey.h

## 概述

`SkBitmapKey` 是 Skia PDF 模块中用于位图去重的轻量级键类型。它通过组合位图的子集矩形和唯一标识符，提供了一种高效的方式来识别和比较位图及其子集。

在 PDF 文档生成过程中，相同的位图可能被多次引用，或者同一个位图的不同子集可能被使用。`SkBitmapKey` 使得 PDF 生成器能够有效地去重这些图像资源，减小文件大小并提高性能。

## 架构位置

`SkBitmapKey` 是 PDF 模块资源管理的基础组件：

```
src/pdf/
├── SkBitmapKey.h           // 位图键（当前模块）
├── SkKeyedImage.h/cpp      // 使用 SkBitmapKey
├── SkPDFDocument.cpp       // 使用键进行图像去重
├── SkPDFBitmap.cpp         // 位图处理
└── SkPDFDevice.cpp         // PDF 设备
```

## 主要结构体

### SkBitmapKey

```cpp
struct SkBitmapKey {
    SkIRect fSubset;      // 子集矩形（相对于原始位图）
    uint32_t fID;         // 位图的唯一标识符

    bool operator==(const SkBitmapKey& rhs) const {
        return fID == rhs.fID && fSubset == rhs.fSubset;
    }

    bool operator!=(const SkBitmapKey& rhs) const {
        return !(*this == rhs);
    }
};
```

**成员变量：**

**fSubset:**
- 类型：`SkIRect`（整数矩形）
- 含义：位图的子集区域
- 坐标：相对于原始位图的全局坐标
- 用途：区分同一位图的不同子集

**fID:**
- 类型：`uint32_t`
- 含义：位图的唯一标识符
- 来源：
  - 对于 `SkBitmap`：`getGenerationID()`
  - 对于 `SkImage`：`uniqueID()`
- 用途：标识底层像素数据

## 相等性语义

### operator==

```cpp
bool operator==(const SkBitmapKey& rhs) const {
    return fID == rhs.fID && fSubset == rhs.fSubset;
}
```

**相等条件：**
1. **ID 相同**：引用同一个底层像素数据
2. **子集相同**：子集矩形完全一致

**示例：**
```cpp
// 相同的键
SkBitmapKey key1 = {{10, 10, 50, 50}, 123};
SkBitmapKey key2 = {{10, 10, 50, 50}, 123};
// key1 == key2 为 true

// 不同的键（不同子集）
SkBitmapKey key3 = {{20, 20, 60, 60}, 123};
// key1 == key3 为 false

// 不同的键（不同位图）
SkBitmapKey key4 = {{10, 10, 50, 50}, 456};
// key1 == key4 为 false
```

### operator!=

```cpp
bool operator!=(const SkBitmapKey& rhs) const {
    return !(*this == rhs);
}
```

简单地反转 `operator==` 的结果。

## 使用场景

### 1. 图像去重

```cpp
std::unordered_map<SkBitmapKey, PDFImageResource*> imageCache;

void addImage(const SkBitmapKey& key, const SkImage* image) {
    if (imageCache.find(key) == imageCache.end()) {
        // 第一次使用，创建新资源
        imageCache[key] = createPDFResource(image);
    }
    // 否则重用现有资源
}
```

### 2. 子集识别

```cpp
// 原始位图：bounds = (0, 0, 100, 100), ID = 123
SkBitmapKey fullKey = {{0, 0, 100, 100}, 123};

// 子集1：(10, 10, 50, 50)
SkBitmapKey subset1 = {{10, 10, 50, 50}, 123};

// 子集2：(20, 20, 60, 60)
SkBitmapKey subset2 = {{20, 20, 60, 60}, 123};

// 所有键都有相同的 ID，但子集不同
// 可以分别缓存和重用
```

### 3. SkKeyedImage 的核心

```cpp
class SkKeyedImage {
    sk_sp<SkImage> fImage;
    SkBitmapKey fKey;  // 使用 SkBitmapKey 作为键
};
```

## 设计模式与设计决策

### 1. 值语义

`SkBitmapKey` 是一个简单的 POD（Plain Old Data）结构：
- 可以按值传递
- 可以直接复制
- 无需手动管理内存
- 适合用作哈希表的键

### 2. 最小化设计

只包含必要的两个字段：
- 避免不必要的开销
- 保持结构紧凑（8 字节用于矩形，4 字节用于 ID）
- 易于理解和使用

### 3. 坐标一致性

子集坐标相对于原始位图的全局坐标：
- 避免嵌套子集的混乱
- 简化比较逻辑
- 支持多级子集

### 4. ID 的来源多样性

支持多种 ID 来源：
- `SkBitmap::getGenerationID()`：基于 pixelRef 的生成 ID
- `SkImage::uniqueID()`：Image 的唯一 ID

这使得键可以跨越 Bitmap 和 Image 的边界。

## 性能考量

### 1. 轻量级比较

```cpp
return fID == rhs.fID && fSubset == rhs.fSubset;
```

比较操作非常快：
- 一次 32 位整数比较（ID）
- 四次坐标比较（矩形）
- 所有字段都是 POD 类型

### 2. 哈希友好

可以轻松为 `SkBitmapKey` 实现哈希函数：
```cpp
size_t hash(const SkBitmapKey& key) {
    return key.fID ^ key.fSubset.left() ^ key.fSubset.top() ^
           key.fSubset.right() ^ key.fSubset.bottom();
}
```

### 3. 缓存友好

结构紧凑（约 20 字节），多个键可以存储在单个缓存行中。

### 4. 快速失败

```cpp
return fID == rhs.fID && fSubset == rhs.fSubset;
```

短路求值：如果 ID 不同，立即返回 false，无需比较矩形。

## 限制与注意事项

### 1. 无法区分像素格式

键不包含像素格式信息（RGB、RGBA、灰度等）：
- 假设相同 ID 的位图具有相同格式
- 如果格式可能不同，需要额外信息

### 2. 子集边界不验证

键不验证子集是否在原始位图范围内：
- 调用者需要确保子集有效
- 无效子集可能导致错误

### 3. 依赖 ID 的唯一性

假设 ID 能够唯一标识位图：
- `getGenerationID()` 在 pixelRef 不变时保持不变
- `uniqueID()` 对每个 Image 实例唯一
- ID 回收可能导致误判（极少见）

## 相关文件

| 文件路径 | 说明 | 关系 |
|---------|------|------|
| `include/core/SkRect.h` | 矩形定义 | fSubset 类型 |
| `include/core/SkBitmap.h` | 位图类 | getGenerationID 来源 |
| `include/core/SkImage.h` | 图像类 | uniqueID 来源 |
| `src/pdf/SkKeyedImage.h` | 带键图像 | 主要使用者 |
| `src/pdf/SkPDFDocument.cpp` | PDF 文档 | 使用键去重 |
| `src/pdf/SkPDFBitmap.cpp` | PDF 位图 | 处理位图资源 |
| `src/pdf/SkPDFDevice.cpp` | PDF 设备 | 使用键管理图像 |
