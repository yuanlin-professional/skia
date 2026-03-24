---
title: '代码风格指南'
linkTitle: 'Coding Style Guidelines'
---

这些约定是随着时间演变而来的。两个项目中的一些早期代码并未严格遵守这些指南。然而，随着代码的演进，我们希望使现有代码符合这些指南。

## 文件

我们使用 .cpp 和 .h 作为 C++ 源文件和头文件 (Header File) 的扩展名。

不打算对外公开的头文件应放在 src 目录中，这样它们就不在客户端的搜索路径中；或者放在 include/private 中（如果它们需要被公共头文件使用）。

我们倾向于尽量减少 include。如果在头文件中进行前向声明 (Forward Declaration) 就足够了，则优先于 include。

前向声明和文件 include 应按字母顺序排列。

### 在 sktypes 之前不要使用 define

不要在包含 "SkTypes.h"（直接或间接）之前使用 #if/#ifdef。大多数您想要 #if 判断的内容在 SkTypes.h 之前尚未确定。

我们使用 4 个空格，不使用制表符 (Tab)。

我们使用 Unix 风格的换行符 (LF)。

我们倾向于没有尾随空格，但对此并不十分严格。

我们在 100 列处换行，除非换行会导致代码非常丑陋（请自行判断）。

## 命名

大多数外部可见的类型和函数使用 Sk- 前缀来表示它们是 Skia 的一部分，但 Ganesh 中的代码使用 Gr-。嵌套类型不需要前缀。

<!--?prettify?-->

```
class SkClass {
public:
    class HelperClass {
        ...
    };
};
```

结构体 (Struct)、类 (Class) 和联合体 (Union) 中具有方法的数据字段以小写 f 开头，然后使用驼峰命名法 (CamelCase)，以区分这些字段和其他变量。主要用于直接字段访问的类型不需要 f- 装饰。

<!--?prettify?-->

```
struct GrCar {
    float milesDriven;
    Color color;
};

class GrMotorcyle {
public:
    float getMilesDriven() const { return fMilesDriven; }
    void  setMilesDriven(float milesDriven) { fMilesDriven = milesDriven; }

    Color getColor() const { return fColor; }
private:
    float fMilesDriven;
    Color fColor;
};
```

全局变量类似，但以 g 为前缀并使用驼峰命名法。

<!--?prettify?-->

```
bool gLoggingEnabled;
```

局部变量和参数使用驼峰命名法，首字母小写。

<!--?prettify?-->

```
int herdCats(const Array& cats) {
    int numCats = cats.count();
}
```

声明为 `constexpr` 或 `const` 且其值在程序运行期间固定不变的变量，以前导 "k" 命名，然后使用驼峰命名法。

<!--?prettify?-->

```
int drawPicture() {
    constexpr SkISize kPictureSize = {100, 100};
    constexpr float kZoom = 1.0f;
}
```

枚举值 (Enum Value) 也以 k 为前缀。未限定作用域的枚举值以下划线和枚举名称的单数形式为后缀。枚举本身对于互斥值应使用单数形式，对于位域 (Bitfield) 应使用复数形式。如果需要计数，应为 `k<枚举名称单数形式>Count` 且不是枚举的成员（见示例），或者枚举中的 kLast 成员也是可以的。

<!--?prettify?-->

```
// Enum class does not need suffixes.
enum class SkPancakeType {
     kBlueberry,
     kPlain,
     kChocolateChip,
};
```

<!--?prettify?-->

```
// Enum should have a suffix after the enum name.
enum SkDonutType {
     kGlazed_DonutType,
     kSprinkles_DonutType,
     kChocolate_DonutType,
     kMaple_DonutType,

     kLast_DonutType = kMaple_DonutType
};

static const SkDonutType kDonutTypeCount = kLast_DonutType + 1;
```

<!--?prettify?-->

```
enum SkSausageIngredientBits {
    kFennel_SausageIngredientBit = 0x1,
    kBeef_SausageIngredientBit   = 0x2
};
```

<!--?prettify?-->

```
enum SkMatrixFlags {
    kTranslate_MatrixFlag = 0x1,
    kRotate_MatrixFlag    = 0x2
};
```

宏 (Macro) 全部大写，单词之间用下划线分隔。作用域超出文件范围的宏应以 SK 或 GR 为前缀。

实现文件中的静态非类函数使用小写字母，单词之间用下划线分隔：

<!--?prettify?-->

```
static inline bool tastes_like_chicken(Food food) {
    return kIceCream_Food != food;
}
```

外部函数或静态类函数使用驼峰命名法，首字母大写：

<!--?prettify?-->

```
bool SkIsOdd(int n);

class SkFoo {
public:
    static int FooInstanceCount();

    // Not static.
    int barBaz();
};
```

## 宏

Ganesh 中 GL 特定的宏应以 GR_GL 为前缀。

<!--?prettify?-->

```
#define GR_GL_TEXTURE0 0xdeadbeef
```

Ganesh 倾向于宏始终被定义，并使用 `#if MACRO` 而非 `#ifdef MACRO`。

<!--?prettify?-->

```
#define GR_GO_SLOWER 0
...
#if GR_GO_SLOWER
    Sleep(1000);
#endif
```

Skia 的其他部分倾向于对布尔标志使用 `#ifdef SK_MACRO`。

## 花括号

左花括号不另起一行。`else` 和 `else if` 与开闭花括号在同一行，除非预处理器条件编译干扰。`if`、`else`、`while`、`for` 和 `do` 始终使用花括号。

<!--?prettify?-->

```
if (...) {
    oneOrManyLines;
}

if (...) {
    oneOrManyLines;
} else if (...) {
    oneOrManyLines;
} else {
    oneOrManyLines;
}

for (...) {
    oneOrManyLines;
}

while (...) {
    oneOrManyLines;
}

void function(...) {
    oneOrManyLines;
}

if (!error) {
    proceed_as_usual();
}
#if HANDLE_ERROR
else {
    freak_out();
}
#endif
```

## 流程控制

流程控制关键字和圆括号之间，以及圆括号和花括号之间有空格：

<!--?prettify?-->

```
while (...) {
}

do {
} while (...);

switch (...) {
...
}
```

switch 语句中的 case 和 default 相对于 switch 缩进。

<!--?prettify?-->

```
switch (color) {
    case kBlue:
        ...
        break;
    case kGreen:
        ...
        break;
    ...
    default:
       ...
       break;
}
```

从一个 case 贯穿 (Fallthrough) 到下一个用 `[[fallthrough]]` 标注。但是，当多个 case 语句连续使用时，不需要 `[[fallthrough]]` 标注。

<!--?prettify?-->

```
switch (recipe) {
    ...
    case kSmallCheesePizza_Recipe:
    case kLargeCheesePizza_Recipe:
        ingredients |= kCheese_Ingredient | kDough_Ingredient | kSauce_Ingredient;
        break;
    case kCheeseOmelette_Recipe:
        ingredients |= kCheese_Ingredient;
        [[fallthrough]]
    case kPlainOmelette_Recipe:
        ingredients |= (kEgg_Ingredient | kMilk_Ingredient);
        break;
    ...
}
```

当需要在 case 中声明变量的代码块时，请遵循以下模式：

<!--?prettify?-->

```
switch (filter) {
    ...
    case kGaussian_Filter: {
        Bitmap srcCopy = src->makeCopy();
        ...
    } break;
    ...
};
```

## 类

除非需要前向声明某些内容，否则类声明应按 `public`、`protected`、`private` 顺序排列。每个部分前应有一个空行。在每个可见性部分（`public`、`private`）内，字段不应与方法混合。最好将所有数据字段放在末尾。

<!--?prettify?-->

```
class SkFoo {

public:
    ...

protected:
    ...

private:
    void barHelper(...);
    ...

    SkBar fBar;
    ...
};
```

在派生类中重写的虚函数 (Virtual Function) 应使用 override，并省略 virtual 关键字。

<!--?prettify?-->

```
void myVirtual() override {
}
```

如果您调用父类型上的方法且必须明确指出是父类版本的方法，例如 `Parent::method()`。使用作用域限定符时，通常在当前对象上调用方法所需的 `this->` 不是必需的。

<!--?prettify?-->

```
class GrDillPickle : public GrPickle {
    ...
    bool onTasty() const override {
        return GrPickle::onTasty()
            && fFreshDill;
    }
    ...
private:
    bool fFreshDill;
};
```

构造函数初始化列表 (Constructor Initializer List) 如果能放下，应与构造函数放在同一行。否则，每个初始化器应在自己的行上，缩进，标点符号放在初始化器之前。

<!--?prettify?-->

```
GrDillPickle::GrDillPickle() : GrPickle(), fSize(kDefaultPickleSize) {}

GrDillPickle::GrDillPickle(float size, float crunchiness, const PickleOptions* options)
        : GrPickle(options)
        , fSize(size)
        , fCrunchiness(crunchiness) {}
```

接受一个参数的构造函数几乎总是应该声明为 explicit，仅对（罕见的）自动兼容类例外。

<!--?prettify?-->

```
class Foo {
    explicit Foo(int x);  // Good.
    Foo(float y);         // Spooky implicit conversion from float to Foo.  No no no!
    ...
};
```

方法调用中嵌套的方法调用应以 'this' 指针的解引用为前缀。例如：

<!--?prettify?-->

```
this->method();
```

Skia 中虚方法的一个常见模式是包含一个公共的非虚（或 final）方法，配对一个名为 "onMethodName" 的私有虚方法。这确保基类方法始终被调用，并使其能够控制虚方法的使用方式，而不是依赖每个子类调用 `Parent::onMethodName()`。例如：

<!--?prettify?-->

```
class SkSandwich {
public:
    void assemble() {
        // All sandwiches must have bread on the top and bottom.
        this->addIngredient(kBread_Ingredient);
        this->onAssemble();
        this->addIngredient(kBread_Ingredient);
    }
    bool cook() {
        return this->onCook();
    }

private:
    // All sandwiches must implement onAssemble.
    virtual void onAssemble() = 0;
    // Sandwiches can remain uncooked by default.
    virtual bool onCook() { return true; }
};

class SkGrilledCheese : public SkSandwich {
private:
    void onAssemble() override {
        this->addIngredient(kCheese_Ingredient);
    }
    bool onCook() override {
        return this->toastOnGriddle();
    }
};

class SkPeanutButterAndJelly : public SkSandwich {
private:
    void onAssemble() override {
        this->addIngredient(kPeanutButter_Ingredient);
        this->addIngredient(kGrapeJelly_Ingredient);
    }
};
```

## 整数类型

我们遵循 Google C++ 指南中关于整数的规定，并正在逐步使旧代码符合此规范

(https://google.github.io/styleguide/cppguide.html#Integer_Types)

总结：使用 `int`，除非您需要位数保证，那么使用 `stdint.h` 类型（`int32_t` 等）。使用断言 (Assert) 验证计数等不为负数，而不是使用无符号类型。位域使用 `uint32_t`，除非出于打包或性能原因需要更短的类型。

## 函数参数

必需的常量对象参数通过 const 引用传递给函数。可选的常量对象参数通过 const 指针传递给函数。可变对象参数通过指针传递给函数。我们很少通过非 const 引用传递任何内容。

<!--?prettify?-->

```
// src and paint are optional
void SkCanvas::drawBitmapRect(const SkBitmap& bitmap, const SkIRect* src,
                              const SkRect& dst, const SkPaint* paint = nullptr);

// metrics is mutable (it is changed by the method)
SkScalar SkPaint::getFontMetrics(FontMetric* metrics, SkScalar scale) const;

```

如果函数参数无法全部放在一行，溢出的参数可以在下一行与第一个参数对齐

<!--?prettify?-->

```
void drawBitmapRect(const SkBitmap& bitmap, const SkRect& dst,
                    const SkPaint* paint = nullptr) {
    this->drawBitmapRectToRect(bitmap, nullptr, dst, paint,
                               kNone_DrawBitmapRectFlag);
}
```

或者所有参数放在下一行并缩进八个空格

<!--?prettify?-->

```
void drawBitmapRect(
        const SkBitmap& bitmap, const SkRect& dst, const SkPaint* paint = nullptr) {
    this->drawBitmapRectToRect(
            bitmap, nullptr, dst, paint, kNone_DrawBitmapRectFlag);
}
```

## Python

Python 代码遵循 [Google Python 风格指南](https://google.github.io/styleguide/pyguide.html)。

## 文件夹组织

Skia 的公共 API 应位于 `include` 目录中。Skia 的私有头文件和实现文件应位于 `src` 目录中。`modules` 目录包含在 Skia 之上构建的额外功能（`modules/skcms` 是例外），可供客户端使用。测试 Skia 的私有工具位于 `tools` 中，可作为参考但不应被客户端使用。

`include` 中的任何头文件都不应依赖其他目录中的文件（`modules/skcms` 是例外）。这是为了防止私有符号通过传递依赖泄露到客户端代码中。
