---
title: '编写 Skia 测试'
linkTitle: '编写 Skia 测试'
---

我们假设你已经同步了 Skia 的依赖项并设置了 Skia 的构建系统。

<!--?prettify lang=sh?-->

    python3 tools/git-sync-deps
    bin/gn gen out/Debug
    bin/gn gen out/Release --args='is_debug=false'

## 编写单元测试

1.  添加文件 `tests/NewUnitTest.cpp`：

    <!--?prettify lang=cc?-->

        /*
         * Copyright ........
         *
         * Use of this source code is governed by a BSD-style license
         * that can be found in the LICENSE file.
         */
        #include "Test.h"
        DEF_TEST(NewUnitTest, reporter) {
            if (1 + 1 != 2) {
                ERRORF(reporter, "%d + %d != %d", 1, 1, 2);
            }
            bool lifeIsGood = true;
            REPORTER_ASSERT(reporter, lifeIsGood);
        }

2.  将 `NewUnitTest.cpp` 添加到 `gn/tests.gni`。

3.  重新编译并运行测试：

    <!--?prettify lang=sh?-->

        ninja -C out/Debug dm
        out/Debug/dm --match NewUnitTest

## 编写渲染测试

1.  添加文件 `gm/newgmtest.cpp`：

    <!--?prettify lang=cc?-->

        /*
         * Copyright ........
         *
         * Use of this source code is governed by a BSD-style license
         * that can be found in the LICENSE file.
         */
        #include "gm.h"
        DEF_SIMPLE_GM(newgmtest, canvas, 128, 128) {
            canvas->clear(SK_ColorWHITE);
            SkPaint p;
            p.setStrokeWidth(2);
            canvas->drawLine(16, 16, 112, 112, p);
        }

2.  将 `newgmtest.cpp` 添加到 `gn/gm.gni`。

3.  重新编译并运行测试：

    <!--?prettify lang=sh?-->

        ninja -C out/Debug dm
        out/Debug/dm --match newgmtest

4.  在 Viewer 中运行 GM：

    <!--?prettify lang=sh?-->

        ninja -C out/Debug viewer
        out/Debug/viewer --slide GM_newgmtest

## 编写基准测试

1.  添加文件 `bench/FooBench.cpp`：

    <!--?prettify lang=cc?-->

        /*
         * Copyright ........
         *
         * Use of this source code is governed by a BSD-style license
         * that can be found in the LICENSE file.
         */
        #include "Benchmark.h"
        #include "SkCanvas.h"
        namespace {
        class FooBench : public Benchmark {
        public:
            FooBench() {}
            virtual ~FooBench() {}
        protected:
            const char* onGetName() override { return "Foo"; }
            SkIPoint onGetSize() override { return SkIPoint{100, 100}; }
            void onDraw(int loops, SkCanvas* canvas) override {
                while (loops-- > 0) {
                    canvas->drawLine(0.0f, 0.0f, 100.0f, 100.0f, SkPaint());
                }
            }
        };
        }  // namespace
        DEF_BENCH(return new FooBench;)

2.  将 `FooBench.cpp` 添加到 `gn/bench.gni`。

3.  重新编译并运行 nanobench：

    <!--?prettify lang=sh?-->

        ninja -C out/Release nanobench
        out/Release/nanobench --match Foo
