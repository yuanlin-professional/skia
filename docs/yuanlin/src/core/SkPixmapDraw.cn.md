# SkPixmapDraw

> 源文件
> - src/core/SkPixmapDraw.cpp

## 概述

`SkPixmapDraw.cpp` 是 Skia 中 `SkPixmap` 的绘制扩展实现，提供了需要 CPU 渲染后端的高级像素操作功能。该文件实现了 `SkPixmap::scalePixels` 方法，用于在两个 pixmap 之间进行缩放和采样。

`SkPixmap` 是 Skia 的核心像素容器，但其基础功能（如简单拷贝）无需 CPU 渲染后端。`SkPixmapDraw.cpp` 分离出需要完整渲染管线的高级操作，包括：
- 高质量图像缩放
- 插值采样（最近邻、双线性、双三次）
- 未预乘 alpha 像素的特殊处理

该实现利用 Skia 的着色器和表面系统，将缩放操作转换为标准的绘制流程。

## 架构位置

`SkPixmapDraw` 位于 Skia 核心图像处理模块（`src/core`）中，连接低级像素操作和高级渲染系统。

在 Skia 架构中的位置：
```
像素存储层 → SkPixmap → SkPixmapDraw（缩放） → 渲染管线 → CPU光栅化
```

依赖关系：
```
SkPixmap (基础) → SkPixmapDraw (扩展) → SkCanvas/SkShader/SkSurface
```

应用场景：
- **图像缩略图生成**：高质量缩小图像
- **图像放大**：插值放大
- **像素格式转换**（结合缩放）
- **批量图像处理**

## 主要类与结构体

该文件不定义新类，而是扩展 `SkPixmap` 的功能。

### 扩展的 SkPixmap 方法

**scalePixels**
```cpp
bool SkPixmap::scalePixels(const SkPixmap& actualDst,
                           const SkSamplingOptions& sampling) const;
```

## 公共 API 函数

### SkPixmap::scalePixels

**函数签名**
```cpp
bool SkPixmap::scalePixels(const SkPixmap& actualDst,
                           const SkSamplingOptions& sampling) const;
```

**参数**
- `actualDst`：目标 pixmap（输出）
- `sampling`：采样选项，控制插值质量

**返回值**
- `true`：缩放成功
- `false`：失败（空 pixmap、无效参数等）

**采样选项（SkSamplingOptions）**
- **最近邻**：`SkSamplingOptions()` 或 `SkFilterMode::kNearest`
- **双线性**：`SkSamplingOptions(SkFilterMode::kLinear)`
- **双三次**：`SkSamplingOptions(SkCubicResampler::Mitchell())`

**功能描述**
将源 pixmap（`this`）的像素缩放并复制到目标 pixmap（`actualDst`），根据采样选项进行插值。

## 内部实现细节

### 算法流程

**scalePixels 实现步骤**

1. **输入验证**
   ```cpp
   if (src.width() <= 0 || src.height() <= 0 ||
       dst.width() <= 0 || dst.height() <= 0) {
       return false;  // 空 pixmap
   }
   ```

2. **相同尺寸优化**
   ```cpp
   if (src.width() == dst.width() && src.height() == dst.height()) {
       return src.readPixels(dst);  // 直接拷贝，无需缩放
   }
   ```

3. **未预乘 alpha 特殊处理**
   ```cpp
   bool clampAsIfUnpremul = false;
   if (src.alphaType() == kUnpremul_SkAlphaType &&
       dst.alphaType() == kUnpremul_SkAlphaType) {
       // 临时伪装为预乘和不透明
       src.reset(src.info().makeAlphaType(kPremul_SkAlphaType), ...);
       dst.reset(dst.info().makeAlphaType(kOpaque_SkAlphaType), ...);
       clampAsIfUnpremul = true;
   }
   ```
   - **目的**：避免预乘/反预乘导致的精度损失
   - **原理**：将未预乘 alpha 像素视为预乘处理，但不执行实际预乘

4. **构建源位图**
   ```cpp
   SkBitmap bitmap;
   bitmap.installPixels(src);
   bitmap.setImmutable();  // 防止拷贝
   ```

5. **计算缩放矩阵**
   ```cpp
   SkMatrix scale = SkMatrix::RectToRectOrIdentity(
       SkRect::Make(src.bounds()),
       SkRect::Make(dst.bounds())
   );
   ```
   - 将源矩形映射到目标矩形

6. **创建着色器**
   ```cpp
   sk_sp<SkShader> shader = SkImageShader::Make(
       bitmap.asImage(),
       SkTileMode::kClamp,      // 边缘夹紧
       SkTileMode::kClamp,
       sampling,
       &scale,
       clampAsIfUnpremul        // 特殊夹紧模式
   );
   ```

7. **创建目标表面**
   ```cpp
   sk_sp<SkSurface> surface = SkSurfaces::WrapPixels(
       dst.info(),
       dst.writable_addr(),
       dst.rowBytes()
   );
   ```

8. **绘制**
   ```cpp
   SkPaint paint;
   paint.setBlendMode(SkBlendMode::kSrc);  // 直接覆盖
   paint.setShader(std::move(shader));
   surface->getCanvas()->drawPaint(paint);
   ```

### 未预乘 alpha 处理机制

**问题背景**

未预乘 alpha 像素格式：`(R, G, B, A)`，其中 RGB 未乘以 alpha。

标准缩放流程：
1. 反预乘：`(R, G, B) /= A`
2. 插值
3. 重新预乘：`(R, G, B) *= A`

**问题**：反预乘和重新预乘会损失精度，尤其是低 alpha 值时。

**解决方案**

`scalePixels` 的特殊处理：
- 源：标记为预乘（`kPremul_SkAlphaType`）
- 目标：标记为不透明（`kOpaque_SkAlphaType`）
- 着色器：启用 `clampAsIfUnpremul` 标志

**效果**：
- 跳过反预乘/重新预乘步骤
- 直接对未预乘值进行插值
- 双三次插值时夹紧到 `[0, 1]` 而非 `[0, alpha]`

**测试覆盖**：`scalepixels_unpremul` GM 测试

### 缩放矩阵计算

**RectToRectOrIdentity**
```cpp
SkMatrix::RectToRectOrIdentity(src_rect, dst_rect)
```

生成矩阵将 `src_rect` 映射到 `dst_rect`：
```
scale_x = dst.width() / src.width()
scale_y = dst.height() / src.height()
translate_x = dst.left - src.left * scale_x
translate_y = dst.top - src.top * scale_y
```

**应用于着色器**：
- 着色器在源像素坐标系中定义
- 矩阵将目标坐标映射回源坐标
- 支持任意缩放比例（放大/缩小）

### 混合模式选择

**SkBlendMode::kSrc**
- 直接覆盖目标像素，忽略目标原有内容
- 等价于 `dst = src`
- 避免 alpha 合成开销

### 边缘处理

**SkTileMode::kClamp**
- 超出边界时使用边缘像素
- 避免采样伪影
- 适用于大多数图像缩放场景

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkPixmap` | 像素容器 |
| `SkBitmap` | 可变像素容器 |
| `SkImage` | 不可变图像 |
| `SkShader` | 着色器（纹理映射） |
| `SkImageShader` | 图像着色器 |
| `SkSurface` | 绘制表面 |
| `SkCanvas` | 绘制接口 |
| `SkPaint` | 绘制属性 |
| `SkMatrix` | 变换矩阵 |
| `SkSamplingOptions` | 采样配置 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| 图像解码器 | 调用 `scalePixels` 生成缩略图 |
| 图像编码器 | 调用 `scalePixels` 调整大小后编码 |
| 应用程序 | 自定义图像处理管线 |

## 设计模式与设计决策

### 设计模式

1. **适配器模式**
   - 将缩放操作适配到绘制管线
   - `SkPixmap` → `SkBitmap` → `SkImage` → `SkShader`

2. **策略模式**
   - `SkSamplingOptions` 封装不同的采样策略
   - 最近邻、双线性、双三次等

### 设计决策

**为何使用绘制管线而非专用算法**
- **代码复用**：利用现有的高质量采样实现
- **统一性**：与其他绘制操作保持一致
- **优化**：自动获得渲染管线的优化（SIMD、GPU 回退等）

**为何特殊处理未预乘 alpha**
- **精度保持**：避免反预乘/重新预乘的精度损失
- **兼容性**：支持未预乘工作流（常见于某些图像格式）
- **性能**：跳过不必要的除法和乘法

**为何使用 kSrc 混合模式**
- **语义明确**：缩放是覆盖操作，不需要合成
- **性能**：避免 alpha 混合计算

**为何使用 kClamp 边缘模式**
- **避免伪影**：重复或镜像模式不适合图像缩放
- **直观**：边缘像素延伸到边界外

**为何不在 SkPixmap.h 中实现**
- **依赖隔离**：基础 `SkPixmap` 不依赖渲染管线
- **编译优化**：减小头文件依赖
- **模块分离**：CPU 后端可选

**为何 setImmutable**
```cpp
bitmap.setImmutable();
```
- **性能**：防止 `asImage()` 创建拷贝
- **安全**：确保源像素不被修改

## 性能考量

### 时间复杂度

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| 相同尺寸 | O(n) | 直接内存拷贝 |
| 最近邻缩放 | O(m) | m = 目标像素数 |
| 双线性缩放 | O(4m) | 每像素 4 次采样 |
| 双三次缩放 | O(16m) | 每像素 16 次采样 |

### 性能优化

1. **相同尺寸快速路径**
   ```cpp
   if (src.width() == dst.width() && src.height() == dst.height()) {
       return src.readPixels(dst);  // O(n) 拷贝
   }
   ```

2. **避免不必要的对象创建**
   ```cpp
   bitmap.setImmutable();  // 防止 asImage() 拷贝
   ```

3. **内联表面包装**
   ```cpp
   SkSurfaces::WrapPixels(...)  // 零拷贝包装
   ```

4. **SIMD 加速**
   - Skia 内部使用 SIMD 优化采样和混合

### 性能陷阱

- **频繁缩放**：每次调用都重建着色器和表面
- **双三次采样**：高质量但慢（16 次采样/像素）
- **大图缩放**：内存带宽瓶颈

### 使用建议

**批量缩放优化**
```cpp
// 错误：重复构建着色器
for (auto& pixmap : pixmaps) {
    pixmap.scalePixels(dst, sampling);
}

// 正确：复用着色器（需要自定义实现）
// 或者使用 SkImage::makeShader 和手动绘制
```

**采样质量选择**
```cpp
// 缩小：使用双三次避免失真
if (dst.width() < src.width()) {
    sampling = SkSamplingOptions(SkCubicResampler::Mitchell());
}

// 放大：双线性通常足够
else {
    sampling = SkSamplingOptions(SkFilterMode::kLinear);
}
```

**尺寸检查**
```cpp
// 提前检查避免不必要的设置
if (src.bounds() == dst.bounds()) {
    src.readPixels(dst);  // 快速路径
} else {
    src.scalePixels(dst, sampling);
}
```

**未预乘 alpha 处理**
```cpp
// 如果源和目标都是未预乘，scalePixels 会自动优化
// 无需手动预乘/反预乘
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `include/core/SkPixmap.h` | 扩展 | Pixmap 基础类 |
| `include/core/SkBitmap.h` | 依赖 | 可变像素容器 |
| `include/core/SkImage.h` | 依赖 | 不可变图像 |
| `src/shaders/SkImageShader.h` | 依赖 | 图像着色器 |
| `include/core/SkSurface.h` | 依赖 | 绘制表面 |
| `include/core/SkCanvas.h` | 依赖 | 绘制接口 |
| `include/core/SkSamplingOptions.h` | 依赖 | 采样配置 |
| `gm/scalepixels.cpp` | 测试 | 缩放测试 GM |
| `gm/scalepixels_unpremul.cpp` | 测试 | 未预乘 alpha 测试 |
| `src/core/SkPixmap.cpp` | 相关 | Pixmap 其他实现 |
