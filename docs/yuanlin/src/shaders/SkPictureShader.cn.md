# SkPictureShader

> 源文件
> - src/shaders/SkPictureShader.h
> - src/shaders/SkPictureShader.cpp

## 概述

`SkPictureShader` 是 Skia 中用于将 `SkPicture` 对象作为可平铺图案绘制的着色器。它首先将图片渲染到一个瓦片(tile)中,然后使用该瓦片根据指定的平铺规则(tile modes)对区域进行着色。这使得复杂的矢量图形可以作为重复的纹理图案使用,非常适合实现背景图案、装饰性填充等效果。

该着色器支持缓存机制,将渲染后的图片瓦片缓存为图像,避免重复的矢量绘制操作,从而提高性能。它还支持过滤模式、自定义瓦片区域和本地矩阵变换等高级功能。

## 架构位置

`SkPictureShader` 位于 Skia 的着色器模块中:

- **模块路径**: `src/shaders/`
- **基类**: `SkShaderBase`
- **公共接口**: 通过 `SkPicture::makeShader()` 创建
- **角色**: 将矢量图形转换为可平铺的着色器

在渲染流程中的位置:
```
SkPicture (矢量图形)
    ↓
SkPictureShader (平铺着色器)
    ↓
光栅化瓦片 → 缓存图像
    ↓
SkImageShader (图像着色器)
    ↓
平铺渲染
```

## 主要类与结构体

### SkPictureShader

将图片作为平铺图案的着色器。

**核心成员**:
```cpp
sk_sp<SkPicture> fPicture;     // 要渲染的图片
SkRect fTile;                   // 瓦片边界
SkTileMode fTmx, fTmy;         // X/Y方向的平铺模式
SkFilterMode fFilter;           // 过滤模式
```

**主要方法**:
- `static sk_sp<SkShader> Make()`: 工厂方法
- `SkPictureShader()`: 构造函数
- `bool appendStages()`: 添加到光栅管线
- `sk_sp<SkShader> rasterShader()`: 创建光栅化的图像着色器

### CachedImageInfo

缓存图像信息结构体,用于计算和管理瓦片渲染。

**成员**:
```cpp
bool success;                  // 是否成功
SkSize tileScale;              // 额外的缩放因子
SkMatrix matrixForDraw;        // 绘制图片的矩阵
SkImageInfo imageInfo;         // 图像信息
SkSurfaceProps props;          // 表面属性
```

**主要方法**:
- `static CachedImageInfo Make()`: 计算缓存信息
- `sk_sp<SkImage> makeImage()`: 从表面创建图像

### ImageFromPictureKey

资源缓存键,用于唯一标识渲染后的瓦片图像。

**成员**:
```cpp
uint32_t fColorSpaceXYZHash;        // 色彩空间XYZ哈希
uint32_t fColorSpaceTransferFnHash; // 传输函数哈希
uint32_t fColorType;                // 颜色类型
SkRect fSubset;                     // 子集矩形
SkSize fScale;                      // 缩放
SkSurfaceProps fSurfaceProps;       // 表面属性
```

### ImageFromPictureRec

资源缓存记录,存储渲染后的图像。

## 公共 API 函数

### SkPictureShader::Make()

```cpp
static sk_sp<SkShader> Make(sk_sp<SkPicture> picture,
                             SkTileMode tmx, SkTileMode tmy,
                             SkFilterMode filter,
                             const SkMatrix* lm,
                             const SkRect* tile)
```

创建图片着色器。

**参数**:
- `picture`: 要渲染的图片
- `tmx`, `tmy`: X和Y方向的平铺模式
- `filter`: 过滤模式(最近邻或双线性)
- `lm`: 可选的本地矩阵
- `tile`: 可选的自定义瓦片矩形,默认使用图片的 cullRect

**返回值**: 着色器智能指针,如果图片无效则返回空着色器

**验证**:
```cpp
if (!picture || picture->cullRect().isEmpty() || (tile && tile->isEmpty())) {
    return SkShaders::Empty();
}
```

**实现**: 使用 `SkLocalMatrixShader::MakeWrapped()` 包装,支持本地矩阵

### SkPicture::makeShader()

```cpp
sk_sp<SkShader> SkPicture::makeShader(SkTileMode tmx, SkTileMode tmy,
                                      SkFilterMode filter,
                                      const SkMatrix* localMatrix,
                                      const SkRect* tile) const
```

便捷方法,从图片对象创建着色器。

**参数**: 同 `SkPictureShader::Make()`

**返回值**: 着色器智能指针

**实现**: 验证矩阵可逆性后调用 `SkPictureShader::Make()`

## 内部实现细节

### 渲染策略

`SkPictureShader` 使用"光栅化-缓存-平铺"策略:

1. **光栅化**: 将矢量图片渲染到位图瓦片
2. **缓存**: 将渲染结果缓存到 `SkResourceCache`
3. **平铺**: 使用 `SkImageShader` 平铺缓存的图像

### appendStages() 实现

```cpp
bool appendStages(const SkStageRec& rec, const SkShaders::MatrixRec& mRec) const
```

核心渲染方法:

1. **应用矩阵**:
   ```cpp
   std::optional<SkShaders::MatrixRec> newMRec = mRec.apply(rec);
   ```

2. **创建光栅着色器**:
   ```cpp
   auto rs = rasterShader(newMRec->totalMatrix(),
                          rec.fDstColorType,
                          rec.fDstCS,
                          rec.fSurfaceProps);
   ```

3. **委托给图像着色器**:
   ```cpp
   return as_SB(rs)->appendStages(rec, SkShaders::MatrixRec(newMRec->localMatrix()));
   ```

### rasterShader() - 核心转换

```cpp
sk_sp<SkShader> rasterShader(const SkMatrix& viewMatrix,
                             SkColorType dstColorType,
                             SkColorSpace* dstColorSpace,
                             const SkSurfaceProps& props) const
```

将图片着色器转换为图像着色器:

1. **计算缓存信息**:
   ```cpp
   CachedImageInfo info = CachedImageInfo::Make(fTile, viewMatrix,
                                                dstColorType, dstColorSpace,
                                                maxTextureSize, props);
   ```

2. **查找缓存**:
   ```cpp
   ImageFromPictureKey key(...);
   sk_sp<SkImage> image;
   if (SkResourceCache::Find(key, ImageFromPictureRec::Visitor, &image)) {
       // 缓存命中
   }
   ```

3. **如果缓存未命中,渲染新瓦片**:
   ```cpp
   auto surface = SkSurfaces::Raster(info.imageInfo, &info.props);
   auto canvas = surface->getCanvas();
   canvas->concat(info.matrixForDraw);
   canvas->drawPicture(fPicture);
   image = info.makeImage(std::move(surface), fPicture.get());
   ```

4. **添加到缓存**:
   ```cpp
   SkResourceCache::Add(new ImageFromPictureRec(key, image));
   ```

5. **创建图像着色器**:
   ```cpp
   return image->makeShader(fTmx, fTmy,
                           SkSamplingOptions(fFilter),
                           &tileMatrix);
   ```

### CachedImageInfo::Make() - 瓦片计算

计算如何渲染瓦片以获得最佳质量和性能:

1. **计算边界和缩放**:
   - 考虑总变换矩阵
   - 限制最大纹理尺寸
   - 计算所需的瓦片缩放

2. **优化纹理大小**:
   - 避免过大的纹理(超过 `maxTextureSize`)
   - 根据缩放因子调整分辨率
   - 平衡质量和内存使用

3. **设置绘制矩阵**:
   - 计算从瓦片空间到像素空间的变换
   - 考虑缩放因子和边界偏移

### 资源缓存机制

使用 `SkResourceCache` 缓存渲染后的瓦片:

**缓存键**: 基于多个参数的组合:
- 图片ID (唯一标识图片)
- 色彩空间哈希
- 颜色类型
- 瓦片矩形
- 缩放因子
- 表面属性

**缓存优势**:
- 避免重复的矢量渲染
- 跨帧重用瓦片
- 内存和性能的平衡

**缓存失效**: 当任何参数改变时,需要新的缓存项

### 序列化

**写入**:
```cpp
void flatten(SkWriteBuffer& buffer) const {
    buffer.write32((unsigned)fTmx);
    buffer.write32((unsigned)fTmy);
    buffer.write32((unsigned)fFilter);
    buffer.writeRect(fTile);
    buffer.writePicture(fPicture);
}
```

**读取**:
- 支持多个版本格式
- 处理旧版本的本地矩阵
- 处理旧版本的过滤质量枚举

## 依赖关系

### 直接依赖

- **SkPicture**: 图片对象
- **SkShaderBase**: 基类
- **SkImageShader**: 实际的平铺实现
- **SkResourceCache**: 瓦片缓存
- **SkSurface**: 瓦片渲染表面
- **SkCanvas**: 绘制图片
- **SkMatrix**: 变换计算
- **SkLocalMatrixShader**: 本地矩阵支持

### 被依赖关系

- **SkPicture**: 通过 `makeShader()` 方法使用
- **用户代码**: 用于图案填充、背景等

## 设计模式与设计决策

### 代理模式

`SkPictureShader` 作为代理:
- 外部接口是着色器
- 内部将工作委托给 `SkImageShader`
- 管理矢量到光栅的转换

### 缓存策略

使用懒加载缓存:
- 首次使用时渲染
- 结果缓存以供后续使用
- 自动管理缓存生命周期

### 适配器模式

将矢量图形适配为着色器:
- `SkPicture` 本身不是着色器
- `SkPictureShader` 提供着色器接口
- 内部转换为图像着色器

### 优化优先设计

多层优化:
1. 瓦片缓存 - 避免重复渲染
2. 纹理尺寸限制 - 控制内存使用
3. 图像着色器委托 - 利用优化的平铺路径

## 性能考量

### 缓存效益

缓存命中时:
- 零矢量渲染开销
- 直接使用光栅化图像
- 与普通图像着色器性能相同

缓存未命中时:
- 一次矢量渲染成本
- 后续使用摊销成本

### 纹理尺寸管理

限制最大纹理尺寸:
- 防止过大的内存分配
- 在缩放很大时降低分辨率
- 权衡质量和资源

### 延迟渲染

不在创建时渲染:
- 创建着色器非常快
- 仅在实际使用时渲染
- 允许着色器创建和丢弃而无开销

### 瓦片重用

相同参数的着色器共享瓦片:
- 减少内存占用
- 减少渲染次数
- 提高多实例使用场景的性能

### 潜在优化

- **矢量化平铺**: 某些简单图片可能直接矢量平铺
- **分级纹理**: 为不同缩放级别缓存多个版本
- **增量渲染**: 对于大瓦片,可以增量渲染

## 相关文件

### 核心依赖
- `include/core/SkPicture.h` - 图片对象
- `src/shaders/SkShaderBase.h` - 着色器基类
- `src/shaders/SkImageShader.h` - 图像着色器(实际渲染)
- `src/shaders/SkLocalMatrixShader.h` - 本地矩阵支持

### 渲染相关
- `include/core/SkSurface.h` - 表面创建
- `include/core/SkCanvas.h` - 图片绘制
- `include/core/SkImage.h` - 图像对象
- `include/core/SkTileMode.h` - 平铺模式

### 缓存系统
- `src/core/SkResourceCache.h` - 资源缓存
- `src/core/SkResourceCache.cpp` - 缓存实现

### 矩阵和变换
- `include/core/SkMatrix.h` - 矩阵定义
- `src/core/SkMatrixPriv.h` - 矩阵私有工具

### 序列化
- `src/core/SkReadBuffer.h` - 反序列化
- `src/core/SkWriteBuffer.h` - 序列化
- `src/core/SkPicturePriv.h` - 图片私有API

### 颜色管理
- `include/core/SkColorSpace.h` - 色彩空间
- `include/core/SkColorType.h` - 颜色类型
- `src/core/SkImageInfoPriv.h` - 图像信息私有工具

### 其他
- `include/core/SkSurfaceProps.h` - 表面属性
- `include/core/SkSamplingOptions.h` - 采样选项
- `src/core/SkEffectPriv.h` - 效果私有工具
