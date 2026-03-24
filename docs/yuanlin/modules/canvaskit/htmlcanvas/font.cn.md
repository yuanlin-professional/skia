# Font 字体管理

> 源文件: modules/canvaskit/htmlcanvas/font.js

## 概述

`font.js` 实现了 HTML Canvas 字体字符串的解析和字体缓存管理功能。该模块负责将 CSS 风格的字体字符串(如 `"italic bold 16px Arial"`)解析为结构化的字体描述符,并维护一个全局字体缓存,用于快速查找和复用字体对象。这是 CanvasKit 支持 Canvas 文本渲染 API 的关键组件。

## 架构位置

该文件位于 CanvasKit 的 HTML Canvas 兼容层:
- **上层**: 被 CanvasRenderingContext2D 的 `font` 属性和文本绘制方法使用
- **同层**: 与 htmlcanvas.js、imagedata.js 等并列
- **下层**: 调用 CanvasKit.Typeface API

作为字体管理层,它提供了字符串解析和缓存查找的双重功能。

## 主要类与结构体

### 字体描述符对象
结构化的字体属性对象:
```javascript
{
  'style': 'italic',      // normal, italic, oblique
  'variant': 'normal',    // normal, small-caps
  'weight': 'bold',       // normal, bold, bolder, lighter, 100-900
  'sizePx': 16,           // 像素单位的字体大小
  'family': 'Arial',      // 字体族名
  'typeface': <Typeface>  // Skia Typeface 对象(可选)
}
```

### 字体缓存结构
全局字体缓存是嵌套对象:
```javascript
fontCache = {
  'Arial': {
    'normal|normal|normal': <Typeface>,
    'italic|normal|bold': <Typeface>,
    '*': <Typeface>  // 默认回退
  },
  'Noto Mono': {
    '*': <DefaultTypeface>
  },
  // ...
}
```

## 公共 API 函数

### parseFontString(fontStr)
解析 CSS 字体字符串为结构化对象。

**参数**:
- `fontStr`: CSS 字体字符串,如 `"italic bold 16px Arial"`

**返回**:
- 字体描述符对象,包含 style、variant、weight、sizePx、family
- `null`: 字符串格式无效

**支持的格式**:
```
[style] [variant] [weight] <size><unit> <family>
```

**示例**:
```javascript
parseFontString("italic bold 16px Arial")
// 返回:
{
  style: 'italic',
  variant: 'normal',
  weight: 'bold',
  sizePx: 16,
  family: 'Arial'
}
```

**支持的单位**:
- `px`: 像素(1:1)
- `pt`: 点(1pt = 4/3px)
- `em`, `rem`: 相对单位(相对于 defaultHeight=16)
- `pc`: picas(1pc = 16px)
- `in`: 英寸(1in = 96px)
- `cm`: 厘米(1cm = 96/2.54px)
- `mm`: 毫米(1mm = 96/25.4px)
- `q`: 四分之一毫米(1q = 96/25.4/4px)
- `%`: 百分比(相对于 defaultHeight)

### getTypeface(fontstr)
获取字体字符串对应的 Typeface 对象。

**参数**:
- `fontstr`: CSS 字体字符串

**返回**:
- 字体描述符对象,包含 `typeface` 字段

**过程**:
1. 解析字体字符串
2. 从缓存查找对应的 Typeface
3. 将 Typeface 附加到描述符

### addToFontCache(typeface, descriptors)
将字体添加到全局缓存。

**参数**:
- `typeface`: CanvasKit.Typeface 对象
- `descriptors`: 字体描述符(family, style, variant, weight)

**副作用**:
- 初始化缓存(如果未初始化)
- 在缓存中注册字体
- 设置族回退(如果族不存在)

**缓存键格式**:
```
style|variant|weight
```
例如: `"italic|normal|bold"`

### getFromFontCache(descriptors)
从缓存查找字体。

**参数**:
- `descriptors`: 字体描述符

**返回**:
- Typeface 对象
- 如果找不到精确匹配,返回族回退(`*`)
- 如果族不存在,返回默认字体

**查找顺序**:
1. 精确匹配: `family[style|variant|weight]`
2. 族回退: `family['*']`
3. 默认字体: `Typeface.GetDefault()`

## 内部实现细节

### 字体字符串正则表达式
```javascript
var fontStringRegex = new RegExp(
  '(italic|oblique|normal|)\\s*' +              // style
  '(small-caps|normal|)\\s*' +                  // variant
  '(bold|bolder|lighter|[1-9]00|normal|)\\s*' + // weight
  '([\\d\\.]+)' +                               // size
  '(px|pt|pc|in|cm|mm|%|em|ex|ch|rem|q)' +      // unit
  '(.+)'                                        // family
);
```

该正则允许:
- 可选的 style、variant、weight
- 必需的 size 和 unit
- 必需的 family(贪婪匹配剩余部分)

### 单位转换实现
使用 switch 语句进行单位转换:
```javascript
switch (unit) {
  case 'px':
    sizePx = size;
    break;
  case 'pt':
    sizePx = size * 4/3;
    break;
  case 'in':
    sizePx = size * 96;
    break;
  // ...
}
```

默认高度设为 16px,用于相对单位计算。

### 缓存初始化
延迟初始化,仅在首次使用时创建:
```javascript
function initCache() {
  if (!fontCache) {
    fontCache = {
      'Noto Mono': {
        '*': CanvasKit.Typeface.GetDefault(),
      },
      'monospace': {
        '*': CanvasKit.Typeface.GetDefault(),
      }
    };
  }
}
```

预加载 'Noto Mono' 和 'monospace' 作为默认回退。

### 缓存键生成
使用管道符(`|`)连接属性:
```javascript
var key = (descriptors['style'] || 'normal') + '|' +
          (descriptors['variant'] || 'normal') + '|' +
          (descriptors['weight'] || 'normal');
```

这种简单的字符串键避免了复杂的哈希函数。

### 空值默认化
所有可选属性都有默认值:
```javascript
descriptors['style'] || 'normal'
```

确保键的一致性。

## 依赖关系

### 内部依赖
- **CanvasKit.Typeface**: Skia 字体对象
- **CanvasKit.Typeface.GetDefault()**: 默认字体

### 外部使用
- **htmlcanvas.js**: `loadFont()` 方法调用 `addToFontCache`
- **CanvasRenderingContext2D**: 文本绘制使用 `getTypeface`

## 设计模式与设计决策

### 1. 单例模式
全局字体缓存是隐式单例:
```javascript
var fontCache; // 模块级变量,所有调用者共享
```

### 2. 懒加载
缓存延迟初始化,避免不必要的开销:
```javascript
function initCache() {
  if (!fontCache) {
    // 初始化
  }
}
```

### 3. 回退机制
三层回退确保总能找到可用字体:
1. 精确匹配
2. 族回退(`*`)
3. 系统默认字体

### 4. 缓存键设计
使用字符串键而非对象键,简化实现:
- 优点: 简单、快速
- 缺点: 可能存在键冲突(实际很少)

### 设计决策

**为什么使用全局缓存**:
1. 字体对象可以跨 Canvas 共享
2. 避免重复加载相同字体
3. 减少内存占用

**为什么支持多种单位**:
CSS 标准要求支持多种单位,保证兼容性。

**为什么需要 sizePx**:
Skia 使用像素作为字体大小单位,统一转换简化后续处理。

**为什么不支持 line-height**:
CSS 字体字符串包含 line-height(如 `16px/1.5`),但 Canvas API 不使用它,解析时忽略。

**为什么族回退用 '*'**:
1. 简单易识别
2. 不与合法的字体名冲突
3. 字典序靠前,便于调试

## 性能考量

### 解析性能
- **正则匹配**: O(n),n 为字符串长度,通常很短
- **单次解析**: 约 1-10 微秒(现代 CPU)
- **缓存优化**: 相同字符串无需重复解析(由调用者缓存)

### 缓存查找
- **时间复杂度**: O(1),对象属性查找
- **空间复杂度**: O(m*n),m 为字体族数,n 为每族的变体数
- **实际开销**: 通常 < 1KB(数十个字体)

### 内存考量
- **字体对象**: 每个 Typeface 约几 KB
- **缓存结构**: 几百字节
- **回退共享**: 族回退和默认字体复用,节省内存

### 优化建议
1. **预加载常用字体**: 在应用启动时加载
2. **限制缓存大小**: 避免无限增长(当前未实现)
3. **字体压缩**: 使用 WOFF2 等压缩格式

## 相关文件

- **modules/canvaskit/htmlcanvas/htmlcanvas.js**: `loadFont()` 方法
- **modules/canvaskit/canvasrenderingcontext2d.js**: 文本绘制 API
- **modules/canvaskit/paragraph.js**: 高级文本排版
- **W3C CSS Fonts 规范**: 字体属性定义
