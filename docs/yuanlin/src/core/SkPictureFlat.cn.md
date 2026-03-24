# SkPictureFlat

> 源文件
> - src/core/SkPictureFlat.h
> - src/core/SkPictureFlat.cpp

## 概述

`SkPictureFlat.h` 定义了 Skia Picture 序列化和反序列化的核心数据结构与枚举类型。该文件包含操作码（DrawType）、序列化标志和辅助类，用于在记录、序列化和回放阶段统一数据格式。它是 Picture 子系统的基础架构文件，为所有 Picture 相关类提供共同的数据定义。

主要包含绘图操作的枚举定义、裁剪参数的打包/解包函数，以及 `SkTypefacePlayback` 和 `SkFactoryPlayback` 辅助类，用于管理字体和可序列化对象工厂。

## 架构位置

`SkPictureFlat` 位于 Picture 子系统的核心位置：

- 被 `SkPictureRecord`、`SkPictureData` 和 `SkPicturePlayback` 共同使用
- 定义了 Picture 序列化格式的操作码
- 提供序列化过程中的辅助数据结构
- 与 `SkReadBuffer`/`SkWriteBuffer` 配合完成序列化

## 主要类与结构体

### DrawType 枚举

**关键枚举值**

| 枚举值 | 描述 |
|-------|------|
| SAVE | 保存 Canvas 状态 |
| RESTORE | 恢复 Canvas 状态 |
| SAVE_LAYER_SAVELAYERREC | 保存图层（使用 SaveLayerRec） |
| TRANSLATE | 平移变换 |
| SCALE | 缩放变换 |
| CONCAT | 矩阵连接 |
| CONCAT44 | 4x4 矩阵连接 |
| SET_M44 | 设置 4x4 矩阵 |
| CLIP_RECT | 矩形裁剪 |
| CLIP_PATH | 路径裁剪 |
| CLIP_RRECT | 圆角矩形裁剪 |
| CLIP_REGION | 区域裁剪 |
| CLIP_SHADER_IN_PAINT | 着色器裁剪 |
| RESET_CLIP | 重置裁剪 |
| DRAW_PAINT | 绘制整个画布 |
| DRAW_RECT | 绘制矩形 |
| DRAW_PATH | 绘制路径 |
| DRAW_IMAGE2 | 绘制图像（带采样选项） |
| DRAW_IMAGE_RECT2 | 绘制图像矩形（带采样） |
| DRAW_TEXT_BLOB | 绘制文本块 |
| DRAW_SLUG | 绘制 GPU 文本块 |
| DRAW_VERTICES_OBJECT | 绘制顶点对象 |
| DRAW_SHADOW_REC | 绘制阴影 |
| DRAW_EDGEAA_QUAD | 绘制边缘抗锯齿四边形 |
| DRAW_EDGEAA_IMAGE_SET2 | 绘制图像集合 |

**注意事项**
- 新增操作码必须添加到枚举末尾以保持向后兼容
- `LAST_DRAWTYPE_ENUM` 标记最后一个有效操作码
- 包含许多已废弃的操作码（标记为 REMOVED 或 obsolete）

### DrawVertexFlags

顶点绘制标志：

| 标志 | 值 | 描述 |
|-----|---|------|
| DRAW_VERTICES_HAS_TEXS | 0x01 | 包含纹理坐标 |
| DRAW_VERTICES_HAS_COLORS | 0x02 | 包含顶点颜色 |
| DRAW_VERTICES_HAS_INDICES | 0x04 | 包含顶点索引 |
| DRAW_VERTICES_HAS_XFER | 0x08 | 包含混合模式 |

### DrawAtlasFlags

图集绘制标志：

| 标志 | 值 | 描述 |
|-----|---|------|
| DRAW_ATLAS_HAS_COLORS | 1 << 0 | 包含颜色数组 |
| DRAW_ATLAS_HAS_CULL | 1 << 1 | 包含裁剪矩形 |
| DRAW_ATLAS_HAS_SAMPLING | 1 << 2 | 包含采样选项 |

### SaveLayerRecFlatFlags

SaveLayer 记录的序列化标志：

| 标志 | 值 | 描述 |
|-----|---|------|
| SAVELAYERREC_HAS_BOUNDS | 1 << 0 | 包含边界矩形 |
| SAVELAYERREC_HAS_PAINT | 1 << 1 | 包含画笔 |
| SAVELAYERREC_HAS_BACKDROP | 1 << 2 | 包含背景滤镜 |
| SAVELAYERREC_HAS_FLAGS | 1 << 3 | 包含保存标志 |
| SAVELAYERREC_HAS_BACKDROP_SCALE | 1 << 6 | 包含背景缩放因子 |
| SAVELAYERREC_HAS_MULTIPLE_FILTERS | 1 << 7 | 包含多个滤镜 |
| SAVELAYERREC_HAS_BACKDROP_TILEMODE | 1 << 8 | 包含背景平铺模式 |

### SkTypefacePlayback

字体回放辅助类。

**关键成员变量**

| 成员变量 | 类型 | 描述 |
|---------|------|------|
| fCount | size_t | 字体数量 |
| fArray | unique_ptr<sk_sp<SkTypeface>[]> | 字体数组 |

**主要方法**

```cpp
// 设置字体数量并分配数组
void setCount(size_t count);

// 获取字体数量
size_t count() const;

// 数组访问
sk_sp<SkTypeface>& operator[](size_t index);

// 设置缓冲区的字体数组
void setupBuffer(SkReadBuffer& buffer) const;
```

### SkFactoryPlayback

可序列化对象工厂回放类。

**关键成员变量**

| 成员变量 | 类型 | 描述 |
|---------|------|------|
| fCount | int | 工厂数量 |
| fArray | SkFlattenable::Factory* | 工厂函数数组 |

**主要方法**

```cpp
// 构造函数
SkFactoryPlayback(int count);

// 获取工厂数组基址
SkFlattenable::Factory* base() const;

// 设置缓冲区的工厂数组
void setupBuffer(SkReadBuffer& buffer) const;
```

## 公共 API 函数

### 裁剪参数打包/解包

```cpp
// 打包裁剪操作和抗锯齿标志为 uint32_t
static inline uint32_t ClipParams_pack(SkClipOp op, bool doAA);

// 解包裁剪操作（返回 Region::Op 以支持旧版本）
static inline SkRegion::Op ClipParams_unpackRegionOp(
    SkReadBuffer* buffer, uint32_t packed);

// 解包抗锯齿标志
static inline bool ClipParams_unpackDoAA(uint32_t packed);
```

打包格式：
- 低4位：裁剪操作（SkClipOp）
- 第5位：抗锯齿标志（doAA）

## 内部实现细节

### 裁剪参数编码

裁剪参数使用5位编码：

```cpp
// 编码
uint32_t ClipParams_pack(SkClipOp op, bool doAA) {
    unsigned doAABit = doAA ? 1 : 0;
    return (doAABit << 4) | static_cast<int>(op);
}

// 解码操作码
SkRegion::Op ClipParams_unpackRegionOp(SkReadBuffer* buffer, uint32_t packed) {
    uint32_t unpacked = packed & 0xF;
    // 验证并支持旧版本的扩展裁剪操作
    if (buffer->validate(...)) {
        return static_cast<SkRegion::Op>(unpacked);
    }
    return SkRegion::kIntersect_Op;
}

// 解码抗锯齿标志
bool ClipParams_unpackDoAA(uint32_t packed) {
    return SkToBool((packed >> 4) & 1);
}
```

### 字体序列化

`SkTypefacePlayback` 管理字体的序列化：

```cpp
void SkTypefacePlayback::setCount(size_t count) {
    fCount = count;
    fArray = std::make_unique<sk_sp<SkTypeface>[]>(count);
}
```

- 字体按顺序存储在数组中
- 通过索引引用字体，避免重复序列化
- 反序列化时重建字体数组

### 工厂序列化

`SkFactoryPlayback` 用于可序列化对象：

- 存储 `SkFlattenable` 对象的工厂函数
- 通过工厂名称字符串序列化
- 反序列化时查找对应的工厂函数
- 支持自定义序列化类型的扩展

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| SkFlattenable | 可序列化对象基类 |
| SkTypeface | 字体类型 |
| SkRegion | 区域类型 |
| SkReadBuffer | 反序列化缓冲区 |
| SkPicturePriv | Picture 版本信息 |

### 被依赖的模块

| 模块 | 关系 |
|-----|------|
| SkPictureRecord | 使用 DrawType 记录操作 |
| SkPictureData | 使用辅助类进行序列化 |
| SkPicturePlayback | 使用 DrawType 解析操作 |

## 设计模式与设计决策

### 枚举驱动架构

使用 `DrawType` 枚举统一定义所有操作：
- 记录和回放使用相同的操作码
- 便于添加新操作和维护兼容性
- 清晰的操作分类

### 位域标志

使用位域标志表示可选参数：
- 节省空间（只序列化存在的数据）
- 便于扩展（添加新标志不影响旧版本）
- 快速检查特性存在性

### 版本兼容性

设计考虑向后兼容：
- 废弃的操作码保留以支持旧文件
- `ClipParams_unpackRegionOp` 支持旧版本的扩展裁剪操作
- 版本检查确保正确解析旧格式

### 辅助类封装

`SkTypefacePlayback` 和 `SkFactoryPlayback` 封装复杂逻辑：
- 简化主序列化代码
- 集中管理相关状态
- 便于测试和维护

## 性能考量

### 紧凑编码

- 裁剪参数打包为5位，节省空间
- 标志使用位域，最小化序列化大小
- 操作码使用单字节表示

### 数组访问

- 字体和工厂使用连续数组存储
- 索引访问效率高（O(1)）
- 缓存友好的内存布局

### 最小化序列化

- 只序列化存在的可选数据
- 使用标志位指示数据存在性
- 避免不必要的序列化开销

## 相关文件

| 文件路径 | 描述 |
|---------|------|
| src/core/SkPictureRecord.h/cpp | 使用 DrawType 记录操作 |
| src/core/SkPictureData.h/cpp | 使用辅助类进行数据管理 |
| src/core/SkPicturePlayback.h/cpp | 使用 DrawType 解析回放 |
| src/core/SkPicturePriv.h | Picture 版本和兼容性定义 |
| src/core/SkReadBuffer.h | 反序列化读取器 |
| src/core/SkWriteBuffer.h | 序列化写入器 |
| include/core/SkFlattenable.h | 可序列化对象基类 |
| include/core/SkTypeface.h | 字体类型定义 |
