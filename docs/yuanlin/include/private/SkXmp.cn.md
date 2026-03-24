# SkXmp

> 源文件: `include/private/SkXmp.h`

## 概述
SkXmp 是一个抽象接口类,用于从 XMP (Extensible Metadata Platform) 元数据中提取信息,特别是用于处理图像增益图(gainmap)相关的元数据。该类主要用于支持 HDR 图像的元数据解析,包括 Adobe 和 Apple 的 HDR 增益图格式。

## 架构位置
该接口位于 Skia 私有头文件中,属于图像编解码子系统的元数据处理层。它为图像解码器提供统一的 XMP 元数据访问接口,用于提取 HDR 相关的参数信息。

## 主要类与结构体

### SkXmp
这是一个抽象基类,定义了从 XMP 元数据中提取信息的标准接口。

**继承关系**: 无基类 → SkXmp

**关键成员变量**:
该类作为抽象接口,不包含成员变量,所有数据存储由子类实现。

## 公共 API 函数

### `static std::unique_ptr<SkXmp> Make(sk_sp<SkData> xmpData)`
- **功能**: 从单一的 XMP 数据创建 SkXmp 实例
- **参数**: `xmpData` - 包含 XMP 元数据的数据块
- **返回值**: 指向 SkXmp 对象的智能指针,解析失败时可能为空

### `static std::unique_ptr<SkXmp> Make(sk_sp<SkData> xmpStandard, sk_sp<SkData> xmpExtended)`
- **功能**: 从标准 XMP 和扩展 XMP 数据创建实例,用于处理 JPEG 中的扩展 XMP
- **参数**:
  - `xmpStandard` - 标准 XMP 数据
  - `xmpExtended` - 扩展 XMP 数据
- **返回值**: 指向 SkXmp 对象的智能指针
- **说明**: 遵循 XMP Specification Part 3: Storage in files, Section 1.1.3.1 规范

### `virtual bool getGainmapInfoAdobe(SkGainmapInfo* info) const = 0`
- **功能**: 提取 Adobe HDR 增益图参数(命名空间: http://ns.adobe.com/hdr-gain-map/1.0/)
- **参数**: `info` - 输出参数,用于接收增益图信息
- **返回值**: 成功提取返回 true,否则返回 false

### `virtual bool getGainmapInfoApple(float exifHdrHeadroom, SkGainmapInfo* info) const = 0`
- **功能**: 提取 Apple HDR 增益图参数并计算近似参数
- **参数**:
  - `exifHdrHeadroom` - EXIF 中的 HDR 余量值
  - `info` - 输出参数,用于接收计算后的增益图信息
- **返回值**: 如果图像包含 Apple HDR 元数据返回 true
- **说明**: 处理 Apple 的 HDR 效果元数据,包括命名空间 http://ns.apple.com/pixeldatainfo/1.0/ 和 http://ns.apple.com/HDRGainMap/1.0/

### `virtual bool getContainerGainmapLocation(size_t* offset, size_t* size) const = 0`
- **功能**: 获取 GContainer 中增益图的位置信息
- **参数**:
  - `offset` - 输出增益图相对于主 JPEG 图像 EndOfImage 的偏移量
  - `size` - 输出增益图的大小
- **返回值**: 如果存在 GContainer 增益图元数据返回 true
- **说明**: 用于处理容器格式中嵌入的 JPEG 增益图

### `virtual const char* getExtendedXmpGuid() const = 0`
- **功能**: 获取扩展 XMP 的 GUID 标识符
- **返回值**: 扩展 XMP 的 GUID 字符串,不存在时返回 null

### `bool getGainmapInfoHDRGM(SkGainmapInfo* info) const`
- **功能**: 已弃用的函数,内部调用 `getGainmapInfoAdobe`
- **说明**: 保留用于向后兼容,计划在未来移除(TODO: b/338342146)

## 内部实现细节

### 不可拷贝设计
类通过显式删除拷贝构造函数和拷贝赋值运算符,确保 XMP 对象的唯一性:
- 删除 `SkXmp(const SkXmp&)`
- 删除 `SkXmp& operator=(const SkXmp&)`

### 工厂方法模式
使用静态 `Make` 方法创建实例,而非公开构造函数,提供两种重载:
1. 单一 XMP 数据源
2. 标准 + 扩展 XMP 数据源(用于大型 JPEG 文件)

### 虚析构函数
声明了虚析构函数 `virtual ~SkXmp() = default`,确保通过基类指针删除派生类对象时能正确调用析构函数。

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/core/SkRefCnt.h | 引用计数管理,用于 sk_sp 智能指针 |
| include/private/base/SkAPI.h | SK_API 宏定义,用于符号导出 |
| SkData | 存储 XMP 原始数据 |
| SkGainmapInfo | 存储解析后的增益图参数 |

### 被依赖的模块
- 图像编解码器(JPEG、PNG 等)
- HDR 图像处理模块
- 图像元数据读取器

## 设计模式与设计决策

### 抽象工厂模式
SkXmp 采用抽象工厂模式,通过工厂方法 `Make` 创建具体实现类的实例,隐藏了实现细节。这使得:
- 客户端代码不需要知道具体的 XMP 解析实现
- 可以根据运行时条件选择不同的解析器实现
- 便于添加新的 XMP 格式支持

### 接口隔离原则
将不同来源的增益图元数据提取方法分离:
- `getGainmapInfoAdobe` - Adobe 格式
- `getGainmapInfoApple` - Apple 格式
- `getContainerGainmapLocation` - 容器格式

这种设计允许实现类选择性地支持不同的格式,而不是强制实现所有格式的通用接口。

### 不可拷贝对象
XMP 对象被设计为不可拷贝,原因包括:
- XMP 数据通常较大,避免不必要的拷贝开销
- 确保元数据的唯一性和一致性
- 使用智能指针管理生命周期更安全

## 性能考量

### 延迟解析
接口设计为按需提取元数据,而非在构造时解析所有内容:
- 减少初始化开销
- 只解析实际需要的元数据字段
- 适合处理大型 XMP 文档

### 内存管理
使用 `sk_sp<SkData>` 进行数据共享:
- 避免数据拷贝
- 通过引用计数管理内存生命周期
- 多个对象可以共享相同的 XMP 数据

### 虚函数开销
所有提取方法都是虚函数,这会带来轻微的性能开销,但提供了实现灵活性。考虑到 XMP 解析通常不在性能关键路径上,这是可接受的权衡。

## 平台相关说明
该接口本身不包含平台特定代码,但处理的元数据格式可能有平台差异:
- **Adobe 格式**: 跨平台通用标准
- **Apple 格式**: 主要用于 Apple 生态系统(iOS/macOS)的 HDR 照片

实现类需要根据不同平台的 XMP 库(如 libexpat、libxml2)提供具体实现。

## 相关文件
| 文件 | 关系 |
|------|------|
| include/core/SkData.h | 提供数据存储容器 |
| src/codec/SkGainmapInfo.h | 定义增益图参数结构 |
| src/codec/*Codec.cpp | 图像编解码器实现,使用此接口解析元数据 |
| src/codec/SkXmp*.cpp | SkXmp 的具体实现类 |

## 使用示例场景
1. **JPEG HDR 图像解码**: 解码器读取 JPEG 文件中的 XMP 段,创建 SkXmp 对象,提取增益图参数用于 HDR 渲染
2. **元数据检查工具**: 分析图像文件是否包含 HDR 元数据,并显示相关参数
3. **格式转换**: 在不同 HDR 格式之间转换时,读取源格式的 XMP 元数据并转换为目标格式
