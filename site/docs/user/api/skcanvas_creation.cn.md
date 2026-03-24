---
title: 'SkCanvas 创建'
linkTitle: 'SkCanvas Creation'

weight: 250
---

首先，请阅读 [SkCanvas API](../skcanvas_overview)。

Skia 有多个后端 (backend) 来接收 SkCanvas 绘图命令。每个后端都有其独特的方式来创建 SkCanvas。本页面为每种后端提供了一个示例：

## 光栅 (Raster)

---

光栅后端绘制到一块内存中。这块内存可以由 Skia 管理，也可以由客户端管理。

为光栅和 Ganesh 后端创建画布的推荐方式是使用 `SkSurface`，它是一个管理画布命令绘制目标内存的对象。

<!--?prettify lang=cc?-->

    #include "include/core/SkData.h"
    #include "include/core/SkImage.h"
    #include "include/core/SkStream.h"
    #include "include/core/SkSurface.h"
    void raster(int width, int height,
                void (*draw)(SkCanvas*),
                const char* path) {
        sk_sp<SkSurface> rasterSurface =
                SkSurfaces::Raster(SkImageInfo::MakeN32Premul(width, height));
        SkCanvas* rasterCanvas = rasterSurface->getCanvas();
        draw(rasterCanvas);
        sk_sp<SkImage> img(rasterSurface->makeImageSnapshot());
        if (!img) { return; }
        sk_sp<SkData> png = SkPngEncoder::Encode(nullptr, img, {});
        if (!png) { return; }
        SkFILEWStream out(path);
        (void)out.write(png->data(), png->size());
    }

或者，我们也可以显式指定表面 (surface) 的内存，而不是让 Skia 来管理。

<!--?prettify lang=cc?-->

    #include <vector>
    #include "include/core/SkSurface.h"
    std::vector<char> raster_direct(int width, int height,
                                    void (*draw)(SkCanvas*)) {
        SkImageInfo info = SkImageInfo::MakeN32Premul(width, height);
        size_t rowBytes = info.minRowBytes();
        size_t size = info.getSafeSize(rowBytes);
        std::vector<char> pixelMemory(size);  // allocate memory
        sk_sp<SkSurface> surface =
                SkSurfaces::WrapPixels(
                        info, &pixelMemory[0], rowBytes);
        SkCanvas* canvas = surface->getCanvas();
        draw(canvas);
        return pixelMemory;
    }

## GPU

---

GPU 表面 (Surface) 必须有一个 `GrContext` 对象来管理 GPU 上下文以及纹理和字体的相关缓存。GrContext 与 OpenGL 上下文或 Vulkan 设备是一一对应的。也就是说，所有将使用同一个 OpenGL 上下文或 Vulkan 设备进行渲染的 SkSurface 应该共享一个 GrContext。Skia 不会为你创建 OpenGL 上下文或 Vulkan 设备。在 OpenGL 模式下，它还假定在进行 Skia 调用时，正确的 OpenGL 上下文已被设为当前线程的活跃上下文。

<!--?prettify lang=cc?-->

    #include "include/gpu/ganesh/GrDirectContext.h"
    #include "include/gpu/ganesh/gl/GrGLInterface.h"
    #include "include/gpu/ganesh/SkSurfaceGanesh.h"
    #include "include/core/SkData.h"
    #include "include/core/SkImage.h"
    #include "include/core/SkStream.h"
    #include "include/core/SkSurface.h"

    void gl_example(int width, int height, void (*draw)(SkCanvas*), const char* path) {
        // You've already created your OpenGL context and bound it.
        sk_sp<const GrGLInterface> interface = nullptr;
        // Leaving interface as null makes Skia extract pointers to OpenGL functions for the current
        // context in a platform-specific way. Alternatively, you may create your own GrGLInterface
        // and initialize it however you like to attach to an alternate OpenGL implementation or
        // intercept Skia's OpenGL calls.
        sk_sp<GrDirectContext> context = GrDirectContexts::MakeGL(interface);
        SkImageInfo info = SkImageInfo:: MakeN32Premul(width, height);
        sk_sp<SkSurface> gpuSurface(
                SkSurfaces::RenderTarget(context.get(), skgpu::Budgeted::kNo, info));
        if (!gpuSurface) {
            SkDebugf("SkSurfaces::RenderTarget returned null\n");
            return;
        }
        SkCanvas* gpuCanvas = gpuSurface->getCanvas();
        draw(gpuCanvas);
        sk_sp<SkImage> img(gpuSurface->makeImageSnapshot());
        if (!img) { return; }
        // Must pass non-null context so the pixels can be read back and encoded.
        sk_sp<SkData> png = SkPngEncoder::Encode(context.get(), img, {});
        if (!png) { return; }
        SkFILEWStream out(path);
        (void)out.write(png->data(), png->size());
    }

## SkPDF

---

SkPDF 后端使用 `SkDocument` 而不是 `SkSurface`，因为文档必须包含多个页面。

<!--?prettify lang=cc?-->

    #include "include/docs/SkPDFDocument.h"
    #include "include/core/SkStream.h"
    void skpdf(int width, int height,
               void (*draw)(SkCanvas*),
               const char* path) {
        SkFILEWStream pdfStream(path);
        auto pdfDoc = SkPDF::MakeDocument(&pdfStream);
        SkCanvas* pdfCanvas = pdfDoc->beginPage(SkIntToScalar(width),
                                                SkIntToScalar(height));
        draw(pdfCanvas);
        pdfDoc->close();
    }

## SkPicture

---

SkPicture 后端使用 SkPictureRecorder 而不是 SkSurface。

<!--?prettify lang=cc?-->

    #include "include/core/SkPictureRecorder.h"
    #include "include/core/SkPicture.h"
    #include "include/core/SkStream.h"
    void picture(int width, int height,
                 void (*draw)(SkCanvas*),
                 const char* path) {
        SkPictureRecorder recorder;
        SkCanvas* recordingCanvas = recorder.beginRecording(SkIntToScalar(width),
                                                            SkIntToScalar(height));
        draw(recordingCanvas);
        sk_sp<SkPicture> picture = recorder.finishRecordingAsPicture();
        SkFILEWStream skpStream(path);
        // Open SKP files with `viewer --skps PATH_TO_SKP --slide SKP_FILE`
        picture->serialize(&skpStream);
    }

## NullCanvas

---

空画布 (null canvas) 是一个忽略所有绘图命令且不执行任何操作的画布。

<!--?prettify lang=cc?-->

    #include "include/utils/SkNullCanvas.h"
    void null_canvas_example(int, int, void (*draw)(SkCanvas*), const char*) {
        std::unique_ptr<SkCanvas> nullCanvas = SkMakeNullCanvas();
        draw(nullCanvas.get());  // NoOp
    }

## SkXPS

---

（_仍处于实验阶段的_）SkXPS 画布写入 XPS 文档。

<!--?prettify lang=cc?-->

    #include "include/core/SkDocument.h"
    #include "include/core/SkStream.h"
    #ifdef SK_BUILD_FOR_WIN
    void skxps(IXpsOMObjectFactory* factory;
               int width, int height,
               void (*draw)(SkCanvas*),
               const char* path) {
        SkFILEWStream xpsStream(path);
        sk_sp<SkDocument> xpsDoc = SkDocument::MakeXPS(&pdfStream, factory);
        SkCanvas* xpsCanvas = xpsDoc->beginPage(SkIntToScalar(width),
                                                SkIntToScalar(height));
        draw(xpsCanvas);
        xpsDoc->close();
    }
    #endif

## SkSVG

---

（_仍处于实验阶段的_）SkSVG 画布写入 SVG 文档。

<!--?prettify lang=cc?-->

    #include "include/core/SkStream.h"
    #include "include/svg/SkSVGCanvas.h"
    #include "SkXMLWriter.h"
    void sksvg(int width, int height,
               void (*draw)(SkCanvas*),
               const char* path) {
        SkFILEWStream svgStream(path);
        std::unique_ptr<SkXMLWriter> xmlWriter(
                new SkXMLStreamWriter(&svgStream));
        SkRect bounds = SkRect::MakeIWH(width, height);
        std::unique_ptr<SkCanvas> svgCanvas =
            SkSVGCanvas::Make(bounds, xmlWriter.get());
        draw(svgCanvas.get());
    }

## 示例

---

要试用此代码，请按照[此处的说明创建一个新的单元测试](/docs/dev/testing/tests)，并将这些函数组合在一起：

<!--?prettify lang=cc?-->

    #include "include/core/SkCanvas.h"
    #include "include/core/SkPath.h"
    #include "tests/Test.h"
    void example(SkCanvas* canvas) {
        const SkScalar scale = 256.0f;
        const SkScalar R = 0.45f * scale;
        const SkScalar TAU = 6.2831853f;
        SkPath path;
        for (int i = 0; i < 5; ++i) {
            SkScalar theta = 2 * i * TAU / 5;
            if (i == 0) {
                path.moveTo(R * cos(theta), R * sin(theta));
            } else {
                path.lineTo(R * cos(theta), R * sin(theta));
            }
        }
        path.close();
        SkPaint p;
        p.setAntiAlias(true);
        canvas->clear(SK_ColorWHITE);
        canvas->translate(0.5f * scale, 0.5f * scale);
        canvas->drawPath(path, p);
    }
    DEF_TEST(FourBackends, r) {
        raster(     256, 256, example, "out_raster.png" );
        gl_example( 256, 256, example, "out_gpu.png"    );
        skpdf(      256, 256, example, "out_skpdf.pdf"  );
        picture(    256, 256, example, "out_picture.skp");
    }
