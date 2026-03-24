# SkMipmapBuilder

> 源文件: src/core/SkMipmapBuilder.h, src/core/SkMipmapBuilder.cpp

## 概述

`SkMipmapBuilder` 是一个用于构建和管理 mipmap 层级的辅助类。它提供了一个简洁的接口来创建 mipmap 层级数据结构，并将其附加到现有的图像对象上。该类主要用于手动构建 mipmap 金字塔，允许用户直接访问和填充各个 mipmap 层级的像素数据。

Mipmap（多级纹理映射）是一种预先计算的图像序列，每个层级的尺寸是上一层级的一半，用于提高纹理采样的性能和质量。`SkMipmapBuilder` 简化了 mipmap 金字塔的创建流程，使得用户可以逐层构建并最终将其与源图像关联。

## 架构位置

`SkMipmapBuilder` 位于 Skia 核心模块 `src/core` 中，是图像处理基础设施的一部分。它作为 mipmap 系统的前端接口，内部依赖 `SkMipmap` 类来实际存储和管理 mipmap 层级数据。该类是连接用户代码和底层 mipmap 实现之间的桥梁。

在 Skia 的纹理管理体系中，`SkMipmapBuilder` 扮演着构建器模式的角色，与 `SkMipmap`（存储）、`SkImage`（图像表示）协同工作，共同支持高效的纹理映射功能。

## 主要类与结构体

### SkMipmapBuilder

| **特性** | **说明** |
|---------|---------|
| **继承关系** | 无继承关系，独立类 |
| **类型** | 辅助构建器类 |
| **生命周期** | 栈分配或堆分配，负责管理内部 `SkMipmap` 的生命周期 |

**关键成员变量：**

| **成员变量** | **类型** | **说明** |
|------------|---------|---------|
| `fMM` | `sk_sp<SkMipmap>` | 内部持有的 mipmap 对象智能指针，管理所有层级数据 |

## 公共 API 函数

### 构造与析构

```cpp
explicit SkMipmapBuilder(const SkImageInfo&);
~SkMipmapBuilder();
```

- **构造函数**：根据给定的 `SkImageInfo` 创建 mipmap 构建器，自动计算所需的层级数量并分配存储空间，但不计算像素内容
- **析构函数**：释放内部持有的 mipmap 资源

### 层级访问

```cpp
int countLevels() const;
SkPixmap level(int index) const;
```

- **`countLevels`**：返回 mipmap 的层级数量（不包括基础层级）
- **`level`**：获取指定索引的 mipmap 层级的 `SkPixmap`，用户可以通过该对象直接写入像素数据

### 附加操作

```cpp
sk_sp<SkImage> attachTo(const sk_sp<const SkImage>& src);
```

- **功能**：将构建好的 mipmap 层级附加到源图像上
- **兼容性检查**：如果 mipmap 层级与源图像不兼容（如尺寸、格式不匹配），返回 `nullptr`
- **返回值**：成功时返回一个新的带有 mipmap 的图像对象，失败时返回空指针

## 内部实现细节

### 初始化流程

构造函数调用 `SkMipmap::Build` 创建 mipmap 对象：

```cpp
fMM = sk_sp<SkMipmap>(SkMipmap::Build({info, nullptr, 0},
                                      /* factoryProc= */ nullptr,
                                      /* computeContents= */ false));
```

- 传递 `computeContents = false` 表示只分配内存结构而不计算像素内容
- 这允许用户通过 `level()` 函数获取各层级的可写 `SkPixmap` 来手动填充数据

### 层级访问实现

`level()` 函数通过调用底层 `SkMipmap::getLevel()` 获取指定层级：

```cpp
SkPixmap SkMipmapBuilder::level(int index) const {
    SkPixmap pm;
    SkMipmap::Level level;
    if (fMM && fMM->getLevel(index, &level)) {
        pm = level.fPixmap;
    }
    return pm;
}
```

返回的 `SkPixmap` 提供对像素缓冲区的直接访问，用户可以填充自定义的 mipmap 内容。

### 附加机制

`attachTo()` 通过调用 `SkImage::withMipmaps()` 实现 mipmap 的附加：

```cpp
sk_sp<SkImage> SkMipmapBuilder::attachTo(const sk_sp<const SkImage>& src) {
    return src->withMipmaps(fMM);
}
```

图像对象内部会验证 mipmap 的兼容性（通过 `SkMipmap::validForRootLevel()`），确保层级尺寸、颜色类型和 alpha 类型匹配。

## 依赖关系

### 依赖的模块

| **模块** | **用途** |
|---------|---------|
| `SkMipmap` | 底层 mipmap 数据存储和管理 |
| `SkImage` | 图像对象，接受 mipmap 附加操作 |
| `SkPixmap` | 提供像素数据访问接口 |
| `SkImageInfo` | 描述图像格式和尺寸信息 |

### 被依赖的模块

| **模块** | **关系** |
|---------|---------|
| 图像工具库 | 用于手动构建自定义 mipmap 层级 |
| 测试框架 | 验证 mipmap 构建和附加功能 |
| 高级图像处理 | 需要精细控制 mipmap 内容的场景 |

## 设计模式与设计决策

### 构建器模式

`SkMipmapBuilder` 采用构建器模式，提供分步构建 mipmap 的能力：

1. 构造时分配所有层级的存储空间
2. 用户通过 `level()` 逐个访问和填充层级
3. 完成后通过 `attachTo()` 将 mipmap 附加到图像

这种设计将 mipmap 的构建过程与图像对象解耦，增强了灵活性。

### 延迟计算策略

构造时设置 `computeContents = false`，采用延迟计算策略：

- 优势：避免不必要的自动下采样计算，用户可以填充自定义内容
- 应用场景：预计算的 mipmap 数据、特殊过滤算法、从外部加载的 mipmap 层级

### 智能指针管理

内部使用 `sk_sp<SkMipmap>` 智能指针管理 mipmap 生命周期：

- 自动引用计数，避免内存泄漏
- 可以安全地在多个图像对象间共享 mipmap 数据

## 性能考量

### 内存分配

- **一次性分配**：构造时一次性分配所有层级所需的内存，避免多次动态分配
- **内存布局**：连续内存布局有利于缓存友好性和访问效率

### 零拷贝附加

`attachTo()` 操作不会复制 mipmap 数据，而是通过智能指针共享：

- 多个图像实例可以共享同一个 mipmap 数据
- 减少内存占用和拷贝开销

### 使用建议

- 适用于需要自定义 mipmap 内容的场景
- 如果只需要标准的下采样 mipmap，直接使用 `SkMipmap::Build()` 更高效
- 确保在调用 `attachTo()` 前填充所有层级的像素数据

## 相关文件

| **文件路径** | **说明** |
|-------------|---------|
| `src/core/SkMipmap.h` | mipmap 核心数据结构和算法实现 |
| `src/core/SkMipmap.cpp` | mipmap 构建和管理的实现细节 |
| `include/core/SkImage.h` | 图像对象接口，支持附加 mipmap |
| `include/core/SkPixmap.h` | 像素映射接口，用于访问层级数据 |
| `src/core/SkMipmapAccessor.h` | mipmap 访问器，用于纹理采样时选择层级 |
