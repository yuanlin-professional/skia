Skia Graphics Release Notes

This file includes a list of high level updates for each milestone release.

Milestone 147
-------------
  * `SkCodec::getEncodedData()` has been removed from the public API
  * Direct3D-specific calls are removed from GrBackendSurface.h. Clients should use the equivalents found in `include/gpu/ganesh/d3d/GrD3DBackendSurface.h"`
  *  `GrDirectContext::MakeDirect3D` has been replaced with `GrDirectContexts::MakeD3D` located in `include/gpu/ganesh/d3d/GrD3DDirectContext.h`
  *  `GrBackendSemaphore::initDirect3D`, and `GrBackendSemaphore::getD3DFenceInfo` have been replaced with `GrBackendSemaphores::MakeD3D` and `GrBackendSemaphores::GetD3DFenceInfo`, defined in `include/gpu/ganesh/d3d/GrD3DBackendSemaphore.h`.
  * Priority-based log filtering is now supported at a core Skia level. This update includes moving
    LoggingPriority out of Graphite and into core Skia. SKGPU_GRAPHITE_LOWEST_ACTIVE_LOG_PRIORITY is
    still supported for backwards compatibility, but new users are encouraged to use
    SKIA_LOWEST_ACTIVE_LOG_PRIORITY in their config file.
  * SK_SUPPORT_UNSPANNED_APIS has been removed.
  * `VulkanBackendContext::fMemoryAllocator` is no longer optional.

* * *

Milestone 146
-------------
  * `skgpu::graphite::ContextOptions.fClientWillExternallySynchronizeAllThreads` has been removed in
    preparation for removing the legacy Vulkan Memory Allocator behavior.
  * `GrContextOptions.fVulkanVMALargeHeapBlockSize` and `skgpu::graphite::ContextOptions.fVulkanVMALargeHeapBlockSize` have been removed in preparation for removing the legacy Vulkan Memory Allocator behavior.
  * As an undocumented feature, `SK_FONT_FILE_PREFIX` could be defined to override how the Android fontmgr searched for system fonts. This has been removed as it was untested and believed to be unused.
  * `SkSurfaces::WrapBackendTexture` no longer requires providing an `SkColorType`. A closest
       compatible SkColorType will be chosen, so long as the backend texture's format is supported as
       renderable.
  * Graphite's InsertStatus now has an additional kOutOfOrderRecording to differentiate this
      unrecoverable error from programming errors that would lead to kInvalidRecording. Out of order
      recordings can currently arise "naturally" if prior dependent recordings failed due to resource
      creation or update errors from the GPU driver.
  * Add SkColorSpacePrimaries::operator==.
  * SkDeserialProcs::fTypefaceProc has been replaced with SkDeserialProcs::fTypefaceStreamProc.
  * The header `include/effects/SkGradientShader.h` and the functions that it declared have been removed.
    The factory functions in `include/effects/SkGradient.h` should now be used to create gradient shaders.
  * More public path utilities now take SkPathBuilder instead of SkPath. This allows the caller to avoid a potential extra copy of path data when calling these functions. This affects SkContourMeasure::getSegment, SkPathEffect::filterPath, SkPathMeasure::getSegment, and skpathutils::FillPathWithPaint.
  * Add VK_ANDROID_EXTERNAL_MEMORY_ANDROID_HARDWARE_BUFFER_EXTENSION (and VK_EXT_QUEUE_FAMILY_FOREIGN
    which it depends on) to VulkanPreferredFeatures when building for Android.

* * *

Milestone 145
-------------
  * Add `skhdr::Agtm` interface.

    Provide an interface to to create SMPTE ST 2094-50 (also known as Adaptive
    Global Tone Mapping) metadata. This interface includes parsing, serialization,
    and tone mapping (via an SkColorFilter).

    Add interface to set and get serialized AGTM metadata to `skhdr::Metadata`.
  * Backend specific texture infos, e.g. `DawnTextureInfo`,
    `VulkanTextureInfo`, and `MtlTextureInfo`'s `fSampleCount` field, and the
    `ContextOptions::fInternalMultisampleCount` field are now `SampleCount`. A helper
    function, `ToSampleCount(uint32_t) -> SampleCount` is provided if needing to convert a variable value vs. just updating a constant.
  * `SkCodec::Options` now contains `fMaxDecodeMemory`. If Skia detects or estimates it would use more
    than that amount of memory (in aggregate) for decoding the image, it will return nullptr instead
    of attempting to decode it. Failures in this way will result in returning the new
    `SkCodec::Result::kOutOfMemory`.
  * Add the function `SkData::Equals`.

    This function can compare two `SkData`s, even when both are nullptr.

* * *

Milestone 144
-------------
  * `SkSerialProcs` now are expected to return a pointer-to-const data. This was implied before, but
    is now made explicit.
  * `SkImage::refEncodedData()` and `SkImageGenerator::refEncodedData()` now returns a pointer to
    const SkData to more explicitly signal that this is a read-only view into the data.
  * Define a new public enum, `SampleCount`, that enforces the valid sample count values that Graphite
    supports (1, 2, 4, 8, 16). `TextureInfo::numSamples() -> uint8_t` is replaced with
    `TextureInfo::sampleCount() -> SampleCount`.

    Backend specific texture infos, e.g. `DawnTextureInfo`,
    `VulkanTextureInfo`, and `MtlTextureInfo` still represent sample count as a `uint8_t` for
    convience with the backend APIs. This `uint8_t` value is validated when wrapping the backend info
    into a `TextureInfo`; if it's not a `SampleCount` value, then an empty `TextureInfo` is returned.
  * The existing ContextOptions `PipelineCallback` has been deprecated in favor of the new `PipelineCachingCallback`.

    The new callback provides extra information to the user allowing determination of how often a Pipeline is used and if any Precompiled Pipelines were unused. This information can be used to create a more effective set of Precompile PaintOptions.
  * New `SkSVGCanvas::Make` overload allows explicitly specifying which PNG encoder
    should be used.  This enables avoiding a hardcoded, transitive dependency on
    either `libpng` or Rust PNG.
  * `kR16_unorm_SkColorType` added to `SkColorType`.
  * `include/docs/SkXPSLibpngHelpers.h` and `include/docs/SkXPSRustPngHelpers.h`
    have been removed - please use a small lambda instead (e.g. see
    https://crrev.com/c/7090470).

* * *

Milestone 143
-------------
  * Added `detachAsVector` method to `SkDynamicMemoryStream`.
  * Added new public APIs to `SkPngRustEncoder` for
    encoding an `SkImage` or `SkPixmap` into `SkData`.
  * A new persistent pipeline storage feature has been added to Graphite. For now, it is only relevant to Graphite's native Vulkan backend. The API consists of:

    1) A new PersistentPipelineStorage abstract base class which can be implemented to persist Pipeline data across Context lifetimes.

    2) A matching ContextOptions::fPersistentPipelineStorage member variable which can be used to pass the PersistentPipelineStorage-derived object to Graphite.

    3) A Context::syncPipelineData method that, when possible, passes the current Pipeline data to the ContextOptions::fPersistentPipelineStorage object.
  * `SkMemoryStream` now takes in a `const SkData`, as it's a read-only view into that data.
    `SkMemory::getData()` now returns a `const sk_sp<SkData>`.
  * SkPath is migrating to become immutable (its geometry).

    In this new version, SkPath will lose all of its methds like moveTo(), lineTo(), etc. and rely on SkPathBuilder for creating paths. Additionally, there are now additional Factories for creating paths in one-call, so often a pathbuilder object may not be needed.

        static SkPath Raw(...);
        static SkPath Rect(...);
        static SkPath Oval(...);
        static SkPath Circle(...);
        static SkPath RRect(...);
        static SkPath Polygon(...);
        static SkPath Line(...);

    Clients that create or edit paths need to switch over to using these factories and/or SkPathBuilder.

    The flag that triggers this is SK_HIDE_PATH_EDIT_METHODS. This means that for now Skia can be built in either way -- but in a subsequent release, this flag will be removed, and SkPath will permanently be in its immutable form.
  * The `SkPathBuilder::rArcTo` (relative arc to) method has been updated to align with
    the absolute version (`SkPathBuilder::arcTo`).
  * `SkPixmap::addrN` and `SkImageInfo::computeOffset` will now assert for negative values of x and y in debug mode.
  * New `SkXPS::MakeDocument` overload allows explicitly specifying which
    PNG encoder should be used.  This enables avoiding a hardcoded, transitive
    dependency on either `libpng` or Rust PNG.  To ease the transition, two
    new helper functions have been added to the `SkXPS` namespace:
    `EncodePngUsingLibpng` and `EncodePngUsingRust`.

* * *

Milestone 142
-------------
  * Add enum class `skgpu::graphite::MarkFrameBoundary` to be used to specify whether a submission is the last logical submission for a frame.

    Add struct `skgpu::graphite::SubmitInfo` to hold metadata used for submitting workloads for execution. Allow specifying through `skgpu::graphite::SubmitInfo` whether submission is a frame boundary (last logical submission for a frame) and frameID (uint64_t) with default values to match prior behavior.

    Use struct `skgpu::graphite::SubmitInfo` in `skgpu::graphite::QueueManager::submitToGpu`, `skgpu::graphite::QueueManager::onSubmitToGpu` and all derived classes.
  * Change `SkNamedTransferFn::kRec709` to match the pure gamma 2.4 definition from
    ITU-R BT.1886.

    Apply this to transfer characteristics values 1, 6, 11, 14, and 16, since they
    use the same definition.

    Add reference text to the comments to clarify that this comes from the EOTF
    definition, and that the ITU-T H.273 table 3 function definitions are not
    necessarily inverse EOTFs, but are sometimes OETFs (as is the case for
    `kRec709`).
  * `SkPngRustDecoder` and `SkPngRustEncoder` APIs are now part of the official,
    non-experimental public API surface of Skia.
  * Remove the members `fICCProfile` and `fICCProfileDescription` from
    `SkPngEncoder::Options`, `SkJpegEncoder::Options`, and
    `SkWebpEncoder::Options`.
  * Add HDR metadata support to `SkPngDecoder`, `SkPngRustDecoder`, and
    `SkPngEncoder`.
  * Add the `skhdr::Metadata` structure that contains all HDR metadata that can be
    attached to an image.

    Add `skhdr::ContentLightLevelInfo` and `skhdr::MasteringDisplayColorVolume`
    structures.

* * *

Milestone 141
-------------
  * `GrAHardwareBufferUtils::GetSkColorTypeFromBufferFormat` is replaced by
    `AHardwareBufferUtils::GetSkColorTypeFromBufferFormat`, which is shared between Graphite and Ganesh.
  * Graphite's `ContextOptions` struct now has an `fExecutor` member. This allows clients to give Graphite threads on which it can perform work. Initially, this facility will be used to compile Pipelines in parallel.
  * Change `SkNamedTransferFn::kHLG` and `SkNamedTransferFn::kPQ` to use the
    new skcms representations.

    This will have the side-effect of changing `SkColorSpace::MakeCICP` to
    use the new representations.
  * ##`SkPath::asArc() removed`

    This method reported true if the path was internally recognized as an "Arc" segment.
    This functionality is now removed, so the method has also been removed.
  * `SkShader::makeWithWorkingColorSpace()` now accepts an optional output
    colorspace parameter. If it is null (the default), it's assumed to be the same
    as the input or working colorspace parameter. This allows shaders to actively
    participate in colorspace conversion and inform Skia about the space changes
    that they apply.

* * *

Milestone 140
-------------
  * `Context::insertRecording` now returns an object that behaves like an enum or a true/false bool
    to assist migrating from the old bool return type to something that provides more details as
    to why the Recording couldn't be played back.

    This shouldn't break any existing usage of `insertRecording` but migrating to check against
    `InsertStatus::kSuccess` is recommended to avoid future breaking changes.
  * `SkImage::isValid(GrRecordingContext*)` has been deprecated in favor of the `SkRecorder*` version.
    To migrate do something like `image->isValid(ctx->asRecorder())`.

    `SkImage::makeSubset(GrDirectContext*, ...)` has been deprecated in favor of the `SkRecorder*`
    version. To migrate, do something like `image->makeSubset(ctx->asRecorder, ..., {})`

    `SkImage::makeColorSpace(GrDirectContext*, ...)` has been deprecated in favor of the `SkRecorder*`
    version. To migrate, do something like `image->makeColorSpace(ctx->asRecorder, ..., {})`

    `SkImage::makeColorTypeAndColorSpace(GrDirectContext*, ...)` has been deprecated in favor of the
    `SkRecorder*` version. To migrate, do something like
    `image->makeColorTypeAndColorSpace(ctx->asRecorder, ..., {})`

    In the case you are working with CPU-backed images, `skcpu::Recorder::TODO()` should work until
    a `skcpu::Context` and `skcpu::Recorder` can be used properly.
  * `skia_ports_fontmgr_android_sources` has been split with the new `skia_ports_fontmgr_android_parser_sources` containing the parser sources.
    `skia_ports_fontmgr_android_ndk_sources` now depends on `skia_ports_fontmgr_android_parser_sources`.
  * Virtuals in `SkTypeface` subclasses (5 of them) now take SkSpan instead of ptr/count. This
    is part of the larger change where public APIs are being converted to take SkSpan where
    applicable.

    No real functionality change, but this new signature allows some of the methods to perform
    range-checking, whereas before they could not.

* * *

Milestone 139
-------------
  * A new `kAnalyticClip` value has been added to the `DrawTypeFlags` enum.
    This allows Precompilation clients to have an analytic clip added to
    the Pipeline generated from the PaintOptions.
  * SK_DNG_VERSION has been added to SkUserConfig.h to indicate the dng_sdk version
    being compiled against. SkRawCodec has been updated to support both DNG SDK versions
    1.4 and 1.7.1
  * `SkFontMgr_New_FontConfig` with 1 parameter has been deprecated and will be removed in a future
    release. Clients will need to call the other version providing an SkFontScanner (e.g.
    `SkFontScanner_Make_FreeType()`)
  * The Vulkan implementation of Ganesh now requires Vulkan 1.1 as the minimum Vulkan version.
  * Support for iOS12 is removed.
  * Support for macOS 10.15 is removed.
  * New public API: `VulkanPreferredFeatures` to automatically query and add Vulkan extensions and features that Skia would benefit from having available. Clients that use this API to allow Skia to enable its preferred extensions and features are then automatically opted in to future Skia support for leveraging more of these and do not need to manually turn on newly-supported features. This class is found in `VulkanBackendContext.h`.

* * *

Milestone 138
-------------
  * The Precompile API has been extended to support Vulkan YCbCr Images.
    To use the new API one should use the PrecompileShaders::VulkanYCbCrImage factory function.
    An example usage can be found in PrecompileTestUtils.cpp.

* * *

Milestone 137
-------------
  * `RecorderOptions.fRequireOrderedRecordings` can now be used to specify a per-`Recorder` ordering
    policy for how its `Recordings` must be inserted into a `Context`. If not provided, the `Recorder`
    will default to the value in `ContextOptions`.

* * *

Milestone 136
-------------
  * The Fontations SkTypeface backend has a new factory method to create a typeface from `SkData`,
    not only from `SkStreamAsset`. The new signature is
    `sk_sp<SkTypeface> SkTypeface_Make_Fontations(sk_sp<SkData> fontData, const SkFontArguments& args)`.
  * `SkColorPriv.h` has been removed from the public API

* * *

Milestone 135
-------------
  * The `SkCodec` class has a new `isAnimated` method which helps to disambiguate
    the meaning of `codec->getRepetitionCount()` returning `0`.
  * The `PrecompileContext` now has a `getPipelineLabel` method that will return a human-readable version of a serialized Pipeline key. Relatedly, `SkRuntimeEffect::Options` now has an `fName` member variable
    which allows clients to provide names for their created runtime effects. The latter API addition is particularly appropriate for user-defined known runtime effects.
  * Graphite's backend specific headers are being renamed to be more consistent between backends:
       * DawnTypes.h -> DawnGraphiteTypes.h
       * DawnUtils.h's content moved to DawnBackendContext.h
       * MtlGraphiteTypesUtils.h -> DwnGraphiteTypes_cpp.h (the non-Obj-C portion of
         MtlGraphiteTypes.h).
       * MtlGraphiteUtils.h's content moved to MtlBackendContext.h
       * VulkanGraphiteUtils.h -> VulkanGraphiteContext.h (there is a shared
         VulkanBackendContext.h header for both Ganesh and Graphite already).

    The deprecated headers now just forward to the new header names and will be removed in a future
    release.
  * `SkPDF::MakeDocument(SkWStream*)` [one argument] has been deprecated and will be removed. This is because SkPDFMetdata has added 2 required fields `jpegDecoder` and `jpegEncoder`. In order to make a reasonable PDF, those must be supplied (using the two argument factory). To make these easier to supply `include/docs/SkPDFJpegHelpers.h` has been added, which will use Skia's built-in jpeg encoder and decoder.
  * The `PrecompileContext` now allows clients to precompile previously serialized Pipelines via the `PrecompileContext::precompile` entry point. Serialized keys can be obtained by implementing a `ContextOptions::PipelineCallback` handler.
  * `ContextOptions` now contains an `fUserDefinedKnownRuntimeEffects` member variable.
    Clients can add `SkRuntimeEffects` to this `SkSpan` and have them be registered as *known*
    runtime effects. Such runtime effects can then be represented in the serialized Pipeline keys.

* * *

Milestone 134
-------------
  * `SkShaders::Color(SkColor4f, sk_sp<SkColorSpace>)` now always applies the color
    space to the color, even if rendering to a legacy `SkSurface` that is not
    color managed. In this case, the target color space is assumed to be sRGB.
  * The A98 RGB, ProPhoto RGB, Display P3 and Rec2020 color spaces can now be used
    for gradient interpolation.
  * The `PrecompileContext` now allows client timed-based purging of Pipelines via
    the new `PrecompileContext::purgePipelinesNotUsedInMs` call.

* * *

Milestone 133
-------------
  * Graphite's `Context` now provides an interface to report the GPU time spent processing a recording. The client provides
    a different finished proc of type `skgpu::graphite::GpuFinishedWithStatsProc` using
    `skgpu::graphite::InsertRecordingInfo::fFinishedWithStatsProc` and sets the flag
    `skgpu::graphite::InsertRecordingInfo::fGpuStatsFlag` to `skgpu::GpuStatsFlags::kElapsedTime`. The new callback takes a
    new struct, `skgpu::GpuStats`, which has an `elapsedTime` field that will indicate the amount of GPU time used by the
    recording. This is implemented for the Dawn backend only. In WASM on WebGPU the reported time excludes any GPU transfers
    that occur before the first render/compute pass or after the last pass because of limitations in the WebGPU timestamp
    query API.

    `GrDirectContext` provides a similar interface to report the GPU time spent in a flush. The client uses a new callback
    type, `GrGpuFinishedWithStatsProc` and sets the same flag on `GrFlushInfo`. This is implemented for GL
    (including GLES and WebGL).
  * Graphite's logging priority can now be adjusted by defining
    `SKGPU_GRAPHITE_LOWEST_ACTIVE_LOG_PRIORITY` in `SkUserConfig.h` to a value specified by the
    `skgpu::graphite::LogPriority` enum.

    For example:
    ```
    #define SKGPU_GRAPHITE_LOWEST_ACTIVE_LOG_PRIORITY skgpu::graphite::LogPriority::kWarning
    ```

    Would cause Graphite to log warnings, non-fatal errors, and fatal errors. However, debug logs would
    be omitted.

    `SKGPU_GRAPHITE_LOWEST_ACTIVE_LOG_PRIORITY` will default to `kWarning` in debug builds, and `kError`
    in release builds.
  * Split MtlGraphiteTypes.h into two files. MtlGraphiteTypes.h defines MtlTextureInfo, which is only available in Objective-C++. MtlGraphiteTypesUtils.h declares the utility functions that are callable from C++.
  * `SK_CANVAS_SAVE_RESTORE_PREALLOC_COUNT` has been added to SkUserConfig.h and SkCanvas.h to let clients control
    how much space is allocated for calls to `SkCanvas::save()`. Clients that don't make many calls can reduce the RAM used by `SkCanvas` by setting this (defaults to about 3kb).
  * New public API: `SkColorSpace::MakeCICP` to create an `SkColorSpace` from code
    points specified in Rec. ITU-T H.273.
  * The ability to dump a SkSL::DebugTrace to JSON has been removed from the public API.
  * `approximateFilteredBounds` has been removed from SkMaskFilter.
  * A new PrecompileContext object has been added to assist Precompilation. The old API of the form:\
        bool Precompile(Context*, ...);\
    has been deprecated and replaced with the API:\
        bool Precompile(PrecompileContext*, ...)\
    The new PrecompileContext object can be obtained via the Context::makePrecompileContext call.

    As an example of a possible Compilation/Precompilation threading model, one could employ 4 threads:

    2 for creating Recordings (\<r1\> and \<r2\>) \
    1 for precompiling (\<p1\>) \
    and the main thread - which owns the Context and submits Recordings.

    Start up for this scenario would look like:

      the main thread moves a PrecompileContext to <p1> and begins precompiling there\
      the main thread creates two Recorders and moves them to <r1> and <r2> to create Recordings\
      the main thread continues on - calling Context::insertRecording on the posted Recordings.

    The PrecompileContext can safely outlive the Context that created it, but it will
    effectively be shut down at that point.
  * Graphite has a new `ContextOptions::fRequiredOrderedRecordings` flag that enables certain optimizations when the
    client knows that recordings are played back in order. Otherwise Graphite will need to clear some caches at the
    start of each recording to ensure proper playback, which can significantly affect performance.

    This replaces the old `ContextOptions::fDisableCachedGlyphUploads` flag.

* * *

Milestone 132
-------------
  * A new `SkCodec` method has been added: `hasHighBitDepthEncodedData`.
  * `GrGLInterface` completeness requirements are modified to support using timer queries when available in the GL context.
    The interface must have relevant functions initialized on OpenGL 3.3 or with GL_EXT_timer_query or GL_ARB_timerquery, on OpenGL ES with
    GL_EXT_disjoint_timer_query, and on WebGL with GL_EXT_disjoint_timer_query or GL_EXT_disjoint_timer_query_webgl2.
  * `GrGLInterface` now expects functions that take two `GLuints` instead of one `GLuint64` for `glWaitSync` and `glClientWaitSync`
    when building with Emscripten. `GrGLMakeAssembledWebGLInterface` binds directly to the `emscipten_gl*` functions declared in the `<webgl/*>` headers rather than the functions declared
    in `GLES3/gl32.h` and `GLES3/gl2ext.h`.
  * `SkPathEffect::DashType`, `SkPathEffect::DashInfo` and `SkPathEffect::asADash` have been removed from the public API.

* * *

Milestone 131
-------------
  * `SkCanvas::SaveLayerRec` can optionally specify a tilemode to apply to backdrop
    content when the new layer's effects would sample outside of the previous
    layer's image.
  * GrContextOptions::fSharpenMipmappedTextures has been restored. It is now enabled
    by default but allows clients to disable this feature if desired.

* * *

Milestone 130
-------------
  * Add version of `SkAndroidCodec::getGainmapAndroidCodec` which returns an `SkAndroidCodec` instead
    of an `SkStream`. Mark as deprecated the version that returns an `SkStream`.
  * `SkColorFilter::filterColor` has been removed. Please use `SkColorFilter::filterColor4f` instead.
  * SkFourByteTag has been moved to its own file: `include/core/SkFourByteTag.h`
  * Ganesh files have been moved out of include/gpu/ into include/gpu/ganesh/. Shims have been left in place, but clients should migrate to the new paths.
  * GR_GL_CUSTOM_SETUP_HEADER will be removed. Configuration in a client provided
    SkUserConfig.h file (or defines set during compilation) are sufficient to affect
    settings in GrGLConfig.h
  * `GR_MAKE_BITFIELD_CLASS_OPS` and `GR_DECL_BITFIELD_CLASS_OPS_FRIENDS` have been removed
    from the public API
  * `SkMSec` has been removed from the public API, including `SkParse::FindMSec`
  * A noop change to our SkSL runtime effect builder APIs. Moved make functions from subclasses
    SkRuntimeShaderBuilder, SkRuntimeColorFilterBuilder, and SkRuntimeBlendBuilder to the base class
    SkRuntimeEffectBuilder.

* * *

Milestone 129
-------------
  * The Dawn-specific constructors and methods on `skgpu::graphite::TextureInfo`,
    `skgpu::graphite::BackendTexture`, have been deprecated and
    moved to be functions in `DawnTypes.h`
  * `SkImageFilters::DropShadow` and `SkImageFilters::DropShadowOnly` now accept
    `SkColor4f` and `SkColorSpace` for the shadow color.
  * `SkScalerContext::MakeRecAndEffects` now converts `SkFont::isEmbolden` to the `kEmbolden_Flag`.
    It no longer automatically converts embolden requests into (more) stroking.
    This can now (optionally) be done in `SkTypeface::onFilterRec` by calling the new `SkScalerContextRec::useStrokeForFakeBold()`.
  * Skia no longer tests building against iOS 11.
    The minimum deployment target is now iOS 12 as this is the minimum deplyment target for Xcode 15.
  * The Vulkan-specific constructors and methods on `skgpu::graphite::TextureInfo`,
    `skgpu::graphite::BackendTexture`, `skgpu::graphite::BackendSemaphore` have been deprecated and
    moved to be functions in `VulkanGraphiteTypes.h`

* * *

Milestone 128
-------------
  * SkSL now properly reports an error if user code includes various GLSL reserved keywords.
    Previously, Skia would correctly reject keywords that were included in "The OpenGL ES
    Shading Language, Version 1.00," but did not detect reserved keywords added in more modern
    GLSL versions. Instead, Skia would allow such code to compile during the construction of a
    runtime effect, but actually rendering the effect using a modern version of OpenGL would
    silently fail (or assert) due to the presence of the reserved name in the the code.

    Examples of reserved names which SkSL will now reject include `dmat3x3`, `atomic_uint`,
    `isampler2D`, or `imageCubeArray`.

    For a more thorough list of reserved keywords, see the "3.6 Keywords" section of the
    OpenGL Shading Language documentation.
  * The following symbols (and their files) have been deleted in favor of their
    GPU-backend-agnostic form:
     - `GrVkBackendContext` -> `skgpu::VulkanBackendContext`
     - `GrVkExtensions` -> `skgpu::VulkanExtensions`
     - `GrVkMemoryAllocator` = `skgpu::VulkanMemoryAllocator`
     - `GrVkBackendMemory` = `skgpu::VulkanBackendMemory`
     - `GrVkAlloc` = `skgpu::VulkanAlloc`
     - `GrVkYcbcrConversionInfo` = `skgpu::VulkanYcbcrConversionInfo`
     - `GrVkGetProc` = `skgpu::VulkanGetProc`
  * The Metal-specific constructors and methods on `skgpu::graphite::TextureInfo`,
    `skgpu::graphite::BackendTexture`, `skgpu::graphite::BackendSemaphore` have been deprecated and
    moved to be functions in `MtlGraphiteTypes.h`
  * SkImage now has a method makeScaled(...) which returns a scaled version of
    the image, retaining its original "domain"
    - raster stays raster
    - ganesh stays ganesh
    - graphite stays graphite
    - lazy images become raster (just like with makeSubset)

* * *

Milestone 127
-------------
  * SkSL now properly recognizes the types `uvec2`, `uvec3` or `uvec4`.

    Unsigned types are not supported in Runtime Effects, as they did not exist in GLSL ES2; however,
    SkSL should still recognize these typenames and reject them if they are used in a program.
    That is, we should not allow `uvec3` to be used as a variable or function name. We will now properly
    detect and reject this as an error.
  * The following deprecated fields have been removed from `GrVkBackendContext`:
     - `fMinAPIVersion`. Use `fMaxAPIVersion` instead.
     - `fInstanceVersion`. Use `fMaxAPIVersion` instead.
     - `fFeatures`. Use `fDeviceFeatures` or `fDeviceFeatures2` instead.
     - `fOwnsInstanceAndDevice`. No replacement, as it had no effect.

    `GrVkBackendContext` is now an alias for `skgpu::VulkanBackendContext`. Clients should use the latter, as the former will be eventually removed.
  * SkShaderMaskFilters and SkTableMaskFilters have been deprecated. They will be removed entirely in an upcoming Skia release.

* * *

Milestone 126
-------------
  * Skia's internal array class (`skia_private::TArray<T>`) now protects its unused capacity when
    [Address Sanitizer (ASAN)](https://clang.llvm.org/docs/AddressSanitizer.html) is enabled. Code which
    inadvertently writes past the end of a Skia internal structure is now more likely to trigger an ASAN
    error.
  * `SkFloat2Bits` and `SkBits2Float` have been removed from the Skia public headers. These were always
    private API (since they lived in `/include/private`) but they had leaked into some example code, and
    tended to be available once a handful of Skia headers were #included.
  * SkSL now allows the ++ and -- operators on vector and matrix variables.

    Previously, attempting to use these operators on a vector or matrix would lead to an error. This was
    a violation of the GLSL expression rules (5.9): "The arithmetic unary operators negate (-), post-
    and pre-increment and decrement (-- and ++) operate on integer or floating-point values (including
    vectors and matrices)."
  * `SkScalarIsFinite`, `SkScalarsAreFinite`, and `SkScalarIsNaN` have been removed from the Skia API.
    These calls can be replaced with the functionally-equivalent `std::isfinite` and `std::isnan`.
  * Clients can explicitly make a Ganesh GL backend for iOS with
    `GrGLInterfaces::MakeIOS` from `include/gpu/ganesh/gl/ios/GrGLMakeIOSInterface.h`
  * Clients can explicitly make a Ganesh GL backend for Mac with
    `GrGLInterfaces::MakeMac` from `include/gpu/ganesh/gl/mac/GrGLMakeMacInterface.h`
  * The following headers have been relocated (notice "ganesh" in the filepath):
     - include/gpu/gl/egl/GrGLMakeEGLInterface.h -> include/gpu/ganesh/gl/egl/GrGLMakeEGLInterface.h
     - include/gpu/gl/glx/GrGLMakeGLXInterface.h -> include/gpu/ganesh/gl/glx/GrGLMakeGLXInterface.h
     - include/gpu/gl/epoxy/GrGLMakeEpoxyEGLInterface.h -> include/gpu/ganesh/gl/epoxy/GrGLMakeEpoxyEGLInterface.h

* * *

Milestone 125
-------------
  * The size of the GPU memory cache budget can now be queried using member `maxBudgetedBytes` of `skgpu::graphite::Context` and `skgpu::graphite::Recorder`.
  * Added `skgpu::graphite::Context::maxTextureSize()`, which exposes the maximum
    texture dimension supported by the underlying backend.
  * Using a MTLBinaryArchive to pre-load the MSL shader cache is no longer
    supported in Ganesh, and the fBinaryArchive member of GrMtlBackendContext
    has been removed.
  * The `sksl-minify` tool can now eliminate unnecessary braces. For instance,
    given the following SkSL code:

    ```
    if (condition) {
        return 1;
    } else {
        return 2;
    }
    ```

    The minifier will now emit:

    ```
    if(a)return 1;else return 2;
    ```
  * Added `SkBitmap::setColorSpace`. This API allows the colorspace of an existing
    `SkBitmap` to be reinterpreted. The pixel data backing the bitmap will be left
    as-is. The colorspace will be honored when the bitmap is accessed via APIs which
    support colorspace conversion, like `readPixels`.
  * `SkDrawLooper` has been removed completely from Skia. It was previously deprecated.
  * Metal-specific constructors and methods have been removed from `GrBackendFormat`,
    `GrBackendTexture`, and `GrBackendRenderTarget` and moved to
    `include/gpu/ganesh/mtl/GrMtlBackendSurface.h`
  * By default, //modules/skottie and //modules/svg will use primitive text shaping.
    Clients that wish to use harfbuzz/icu for more correct shaping will need to
    use one of the builders and call `setTextShapingFactory` with a newly-created
    `SkShapers::Factory` implementation during construction.

    For ease of configuration, `modules/skshaper/utils/FactoryHelpers.h` can be used
    to provide this, but only if the client is depending on the correct skshaper
    and skunicode modules (which should set defines such as `SK_SHAPER_HARFBUZZ_AVAILABLE`).

    For example `builder.setTextShapingFactory(SkShapers::BestAvailable())` will use
    Harfbuzz or CoreText for shaping if they were compiled in to the clients binary.

* * *

Milestone 124
-------------
  * `SkColorFilter::filterColor` is now deprecated and will eventually be removed in favor of `filterColor4f`.
  * The Perlin noise shaders (`MakeFractalNoise` and `MakeTurbulence`) will now properly rotate when
    transformed. On raster surfaces, the performance of Perlin noise has also been significantly
    improved.
  * Graphite's `SkImages::WrapTexture` now takes an additional parameter that indicates whether
    a mipmapped texture should be used as is or whether Graphite should generate the upper level
    contents from the base level contents.
  * `GrBackendSemaphore::initMetal`, `GrBackendSemaphore::mtlSemaphore`, and
    `GrBackendSemaphore::mtlValue` have been replaced with `GrBackendSemaphores::MakeMtl`,
    `GrBackendSemaphores::GetMtlHandle`, and `GrBackendSemaphores::GetMtlValue`, defined in
    `include/gpu/ganesh/mtl/GrMtlBackendSemaphore.h`
  * `GrDirectContext::MakeMetal` has been moved to `GrDirectContexts::MakeMetal`, located in
    `include/gpu/ganesh/mtl/GrMtlDirectContext.h`. The APIs that passed in void* have been removed
    in that change, so clients who use those need to create a `GrMtlBackendContext` themselves.

    `include/gpu/mtl/GrMtlTypes.h` and `include/gpu/mtl/GrMtlBackendContext.h` have been relocated to
    `include/gpu/ganesh/mtl/GrMtlTypes.h` and `include/gpu/ganesh/mtl/GrMtlBackendContext.h`
    respectively.
  * Added `SkCodecs::DeferredImage` which is similar to `SkImages::DeferredFromEncodedData` except it
    allows the caller to pass in a `SkCodec` directly instead of depending on compiled-in codecs.
  * The following SkShaper functions have been moved or deleted:
      - SkShaper::MakePrimitive() -> SkShapers::Primitive()
      - SkShaper::MakeShaperDrivenWrapper() -> SkShapers::HB::ShaperDrivenWrapper()
      - SkShaper::MakeShapeThenWrap() -> SkShapers::HB::ShapeThenWrap()
      - SkShaper::MakeShapeDontWrapOrReorder() -> SkShapers::HB::ShapeDontWrapOrReorder()
      - SkShaper::MakeCoreText() -> SkShapers::CT::CoreText()
      - SkShaper::Make() -> deleted, use one of the above directly,
      - SkShaper::MakeSkUnicodeBidiRunIterator() -> SkShapers::unicode::BidiRunIterator()
      - SkShaper::MakeBiDiRunIterator() -> deleted, use SkShapers::unicode::BidiRunIterator() or SkShapers::TrivialBiDiRunIterator()
      - SkShaper::MakeIcuBiDiRunIterator() -> deleted, use SkShapers::unicode::BidiRunIterator()
      - SkShaper::MakeSkUnicodeHbScriptRunIterator() -> SkShapers::HB::ScriptRunIterator()
      - SkShaper::MakeHbIcuScriptRunIterator() -> SkShapers::HB::ScriptRunIterator()
      - SkShaper::MakeScriptRunIterator() -> deleted, use SkShapers::HB::ScriptRunIterator() or SkShapers::TrivialScriptRunIterator

    Additionally, two `SkShaper::shape` method overloads have been removed - clients now need to
    specify all 10 arguments (although it is common to pass in nullptr for features).
  * `SkStream::getData()` has been added as a virtual. Subclasses can implement this if it is efficient
    to turn the underlying contents into an SkData (e.g. SkStreamMemory). `SkStreamMemory::asData()`
    has been renamed to `getData()` as a result of this change and will be removed in a future release.

* * *

Milestone 123
-------------
  * When `SkCodec::SelectionPolicy::kPreferStillImage` is passed to `SkWuffsCodec`/`SkGifDecoder`
    creation, and the input stream cannot be rewound, the resulting `SkWuffsCodec` will no longer copy
    the stream. Because it will now have a non-seekable stream, it no longer supports `getFrameCount`,
    which will now simply report `1`, or `getFrameInfo`, which is useful only for animation anyway.
    Chromium uses `kPreferStillImage`, simply because it is the default, but will not be affected by
    this change because it always supplies a seekable stream.
  * A `kDefault_Flag = 0` value has been added to the `SkSurfaceProps::Flags` enum. This is just a
    self-documenting zero-value that aims to improve code readability, e.g.:

    ```
    // The two lines below are equivalent.

    SkSurfaceProps(/* surfaceFlags= */ 0, kRGB_H_SkPixelGeometry);

    SkSurfaceProps(SkSurfaceProps::kDefault_Flag, kRGB_H_SkPixelGeometry);
    ```
  * In native builds the default use of `wgpu::Device::Tick` to detect GPU progress has been updated
    to use `wgpu::Instance::ProcessEvents` instead. To simulate the non-yielding behavior of `Context`
    in native `DawnBackendContext::fTick` may still be explicitly set to `nullptr`.
  * The Vulkan backend for both Ganesh and Graphite will now invoke an optional client-provided callback
    function when a `VK_ERROR_DEVICE_LOST` error code is returned from the Vulkan driver. Additional
    debugging information will be passed from the driver to this callback if the `VK_EXT_device_fault`
    extension is supported and enabled.

    This optional callback can be be provided via the `fDeviceLostContext` and `fDeviceLostProc` fields
    on `GrVkBackendContext` (Ganesh) and `VulkanBackendContext` (Graphite).
  * `SkAnimCodecPlayer` has been removed from the public API.
  * `SkCodec::getImage()` will now respect the origin in the metadata (e.g. Exif metadata that
    rotates the image). This may mean callers who provide an SkImageInfo may need to rotate it,
    e.g. via `SkPixmapUtils::SwapWidthHeight`.

* * *

Milestone 122
-------------
  * `graphite::BackendTexture` can be created from a `WGPUTextureView`. This comes with a
    perfomance cost when reading pixels to or writing pixels from the CPU. An intermediate
    WGPUTexture is created to support these operations. However, this enables creating
    `SkSurface` or `SkImage` from `wgpu::SwapChain::GetCurrentTextureView`.
  * SkSL now properly reports an error if the body of a for-loop declares a variable which shadows the
    for-loop induction variable.

    In other words, SkSL code like this will now generate an error:

    ```
        for (int x = 0; x < 10; ++x) {
            int x = 123;  // error: symbol 'x' was already defined
        }
    ```

    Previously, the declaration of `x` would be allowed, in violation of the GLSL scoping rules (6.3):
    "For both for and while loops, the sub-statement does not introduce a new scope for variable names."
  * The PDF code now directly depends on Skia's JPEG decoder and encoder. The build
    time shims to avoid using a JPEG decoder and encoder have been removed. In the
    future these may be made optional again by allowing the user to supply them at
    runtime.
  * SkSL variables declared inside of a switch statement will now properly fall out of scope after the
    closing brace of the switch-block, as one would expect.

    In other words, SkSL code like this will now generate an error:

    ```
        switch (n) {
            case 1:
                int x = 123;
        }
        return x; // error: unknown identifier 'x'
    ```

    Previously, `x` would remain accessible after the switch's closing brace.
  * `skgpu::graphite::ContextOptions::fNeverYieldToWebGPU` is removed. Instead, yielding in an
    Emscripten build is controlled by installing a client-provided function on
    `skgpu::graphite::DawnBackendContext`. The client may install a function that uses Asyncify to
    yield to the main thread loop. If no function is installed then the Context has the same
    restrictions as with the old option.

    In native builds the default is to use `wgpu::Device::Tick` to detect GPU progress. To simulate the
    non-yielding behavior of `Context` in native `DawnBackendContext::fTick` may be explicitly set to
    to `nullptr`.

    By externalizing the use of Asyncify it is possible to build Skia without generated JS
    code that relies on Asyncify.
  * SkSL will now properly report an error if a function contains a top-level variable with the same
    name as a function parameter. SkSL intends to match the scoping rules of GLSL, in particular: "A
    function’s parameter declarations and body together form a single scope nested in the global scope."

    A program like this will now be rejected:

    ```
        void func(int var) {
            int var;
        }

        error: 2: symbol 'var' was already defined
            int var;
            ^^^^^^^
    ```
  * `SkFont::getTypeface()` will no longer return a nullptr to indicate "the default typeface".
    If left unspecified, SkFonts will use an empty typeface (e.g. no glyphs).
  * `SkFontMgr::RefDefault()` has been deleted. Clients should instantiate and manage their own
    `SkFontMgr`s and use them to explicitly create `SkTypeface`s
  * `GrGLMakeNativeInterface` has been deprecated and will eventually be removed. Clients should
    be calling the precise factory (e.g. `GrGLInterfaces::makeGLX`) they need. Some APIs that currently allow a nullptr GrGLInterface will be stop allowing this (e.g. `GrDirectContexts::MakeGL`).
  * `SkFontArguments::Palette::Override`'s index member is changing from an `int`
    type to `uint16_t` to make the size exact and remove an unneeded
    signedness. This avoids platform/compiler-specific size ambiguiity and more
    closely matches the OpenType CPAL table.

* * *

Milestone 121
-------------
  * `SkFontConfigInterface::makeTypeface` now has a required `sk_sp<SkFontMgr>` parameter to be used for
    parsing the font data from the stream.
  * `skgpu::graphite::ContextOptions` has a new field, `fNeverYieldToWebGPU`. This new option
    is only valid with the Dawn backend. It indicates that `skgpu::graphite::Context` should never yield
    to Dawn. In native this means `wgpu::Device::Tick()` is never called. In Emscripten it
    means `Context` never yields to the main thread event loop.

    When the option is enabled, `skgpu::SyncToCpu::kYes` is ignored when passed to
    `Context::submit()`. Moreover, it is a fatal error to have submitted but unfinished
    GPU work before deleting `Context`. A new method, `hasUnfinishedGpuWork()` is added
    to `Context` that can be used to test this condition.

    The intent of this option is to be able to use Graphite in WASM without requiring Asyncify.
  * Deprecated `GrMipmapped` and `GrMipMapped` alias have been removed in favor of `skgpu::Mipmapped`.
  * Harfbuzz-backed SkShaper instances will no longer treat a null SkFontMgr as meaning "use the
    default SkFontMgr for fallback" and instead will *not* do fallback for glyphs missing from a font.
  * `GrBackendSemaphore::initVk` and `GrBackendSemaphore::vkSemaphore` have been replaced with
    `GrBackendSemaphores::MakeVk` and `GrBackendSemaphores::GetVkSemaphore`, defined in
    `include/gpu/ganesh/vk/GrVkBackendSemaphore.h`
  * The Vulkan-specific methods and constructor of `MutableTextureState` have been deprecated in favor
    of those found in `include/gpu/vk/VulkanMutableTextureState.h`.

* * *

Milestone 120
-------------
  * `SkBase64.h` has been removed from the public API.
  * `SkFont::refTypefaceOrDefault` and `SkFont::getTypefaceOrDefault()` have been removed from the
    public API.
  * `GrBackendSemaphore::initGL` and `GrBackendSemaphore::glSync` have been removed
    from the public API.
  * For Graphite, `SkImages::AdoptTextureFrom` has been renamed to `SkImages::WrapTexture` to
    better reflect what is happening to the passed in texture.
  * `GrSurfaceInfo.h` has been removed from the public API.
  * SkMesh now allows shaders, color filters, and blenders to be used in the mesh-fragment program.
    Pass in effects using the `children` parameter of `SkMesh::Make` or `SkMesh::MakeIndexed`.
    For a working example, see `gm/mesh.cpp`.
  * The behavior for SkPicture deserialization (via SkReadBuffer) to fallback to
    `SkImages::DeferredFromEncodedData` when `SkDeserialImageProc` is not set or returns null is
    deprecated and will be removed shortly.

    `SkDeserialImageFromDataProc` has been added to SkDeserialProcs to allow clients to *safely*
    avoid a copy when decoding image data in SkPictures.

    `SkDeserialImageProc` now takes in an optional AlphaType which can be used to override the
    AlphaType that an image was serialized with, if desired.
  * skgpu::graphite::RecorderOptions::kDefaultRecorderBudget is now a static data member.
  * `SkTypeface::MakeFromName`, `SkTypeface::MakeFromFile`, `SkTypeface::MakeFromStream`, and
    `SkTypeface::MakeFromData` are deprecated and will be removed eventually. These should be replaced
    with calls directly to the SkFontMgr that can provide the appropriate typefaces.

    `SkTypeface::MakeDefault()` has been deprecated. Soon it will return an empty typeface and
    eventually be removed.

    `SkTypeface::UniqueID()` has been removed - clients should use the method instead of this static
    function.
  * `GrDirectContext::MakeVulkan...` has been moved to `GrDirectContexts::MakeVulkan...` which are defined
    in `include/gpu/ganesh/vk/GrVkDirectContext.h`
  * The various GPU wait calls on GrDirectContext, SkSurface, and GrVkSecondaryCBContext which take
    a client supplied semaphore, now only guarantee to block the gpu transfer and fragment stages
    instead of all gpu commands. This shouldn't affect any client since client provided gpu resources
    (e.g. textures) are only ever used by Skia in the fragment stages.

* * *

Milestone 119
-------------
  * Added new `SkImageFilters::Crop(SkRect, SkTileMode, sk_sp<SkImageFilter>)` image filter effect that crops the output from the wrapped SkImageFilter and optionally applies the SkTileMode when sampling outside of the crop rect.
  * `GrDirectContext::MakeGL...` has been moved to `GrDirectContexts::MakeGL...` which are defined
    in `include/gpu/ganesh/gl/GrGLDirectContext.h`
  * `GrDirectContext::submit` and `GrDirectContext::flushAndSubmit` calls now take a GrSyncCpu enum
    instead of a error-prone boolean.

    Similarly, calls to `GrDirectContext::performDeferredCleanup` and
    `GrDirectContext::purgeUnlockedResources` take a GrPurgeResourceOptions enum.
  * SkMeshSpecification no longer rejects fragment programs which include `uniform shader`, `uniform
    colorFilter` or `uniform blender`. However, `SkMesh::Make` will not allow the mesh specification
    to be used.
  * `SkMesh::Make` and `SkMesh::MakeIndexed` now require a span of child effects as a new parameter.
    This functionality is still a work in progress; for now, always pass an empty span.
  * `sksl-minify` can now minify SkMesh programs. Pass `--meshvert` or `--meshfrag` to indicate
    that the input program is an SkMesh vertex or fragment program. When minifying a mesh program,
    you must supply `struct Varyings` and `struct Attributes` which correspond to the
    SkMeshSpecification; these will be eliminated from the minified output.
  * `SkMergePathEffect`, `SkMatrixPathEffect`, `SkStrokePathEffect`, and
    `SkStrokeAndFillPathEffect` have been removed from the public API.
    These effects can be implemented on the SkPath objects directly using other means and clients
    will likely find performance boosts by doing so.
  * `SkShadowFlags` are now visible in `include/utils/SkShadowUtils.h`
  * `SkPicture`s no longer serialize `SkImage`s to PNG encoded data by default. Clients who wish to
    preserve this should make use of `SkSerialProcs`, specifically the `fImageProc` field.

* * *

里程碑 118
-------------
  * `GrDirectContext::flush` 的各种变体现在仅接受一个 SkSurface 指针，而不是 sk_sp<SkSurface>。
  * `SkImage::makeWithFilter` 已被弃用。它已被三个工厂函数取代：

    Ganesh：  `SkImages::MakeWithFilter(GrRecordingContext*, ...);`         -- 在 SkImageGanesh.h 中声明

    Graphite：`SkImages::MakeWithFilter(skgpu::graphite::Recorder*, ...);`  -- 在 Image.h 中声明

    Raster：  `SkImages::MakeWithFilter(...);`                              -- 在 SkImage.h 中声明

    新的工厂函数要求关联的后端上下文对象必须有效。例如，Graphite 版本在未提供 `Recorder` 对象时会返回 nullptr。
  * SkSL 和运行时效果（Runtime Effects）不再是 Skia 的可选功能；它们始终可用。GN 标志 `skia_enable_sksl` 已被移除。
  * SkSL 现在会正确拒绝包含数组的序列表达式，或包含含有数组的结构体的序列表达式。此前，只检查了序列左侧表达式，而右侧没有被检查。在 GLSL ES 1.0 中（因此在 SkSL 中也一样），唯一允许对数组进行操作的运算符是数组下标运算符（`[]`）。
  * Ganesh 的 Dawn 后端已被移除。Dawn 将继续在 Graphite 后端中得到支持。
  * 我们计划从公共 API 中移除 SkTime.h。目前，SkAutoTime 已被删除，因为它未被使用。
  * 与 Vulkan 相关的调用正在从 GrBackendSurface.h 中移除。客户端应使用 `include/gpu/ganesh/vk/GrVkBackendSurface.h"` 中的等效接口。

* * *

里程碑 117
-------------
  * `SkGraphics::AllowJIT()` 已被移除。它此前已被弃用（且不执行任何操作）。
  * 为 `SkImage`、`SkSurface` 和 `skgpu::graphite::context` 添加了名为 `asyncRescaleAndReadPixeksYUVA420` 的新方法。这些方法的功能与现有的 `asyncRescaleAndReadPixelsYUV420` 方法完全相同，但会返回第四个平面，其中包含全分辨率的 Alpha 值。
  * `SkAutoGraphics` 已被移除。这是一个简单调用 `SkGraphics::Init` 的辅助结构体。任何 `SkAutoGraphics` 的实例都可以替换为对 `SkGraphics::Init` 的调用。
  * `SkCanvas::flush()` 已被移除。可以用以下代码替换：
    ```
        if (auto dContext = GrAsDirectContext(canvas->recordingContext())) {
            dContext->flushAndSubmit();
        }
    ```

    `SkCanvas::recordingContext()` 和 `SkCanvas::recorder()` 现在是 const 的。它们此前隐式为 const，但现在已显式声明为 const。
  * `SkCanvas::recordingContext()` 和 `SkCanvas::recorder()` 现在是 const 的。它们此前隐式为 const，但现在已显式声明为 const。
  * `SkMesh::MakeIndexBuffer`、`SkMesh::CopyIndexBuffer`、`SkMesh::MakeVertexBuffer` 和 `SkMesh::CopyVertexBuffer` 已被移至 `SkMeshes` 命名空间。Ganesh 特定的版本已在 `include/gpu/ganesh/SkMeshGanesh.h` 中创建。
  * SkPath 现在强制执行 7.15 亿个路径动词的上限。
  * `SkRuntimeEffectBuilder::uniforms()`、`SkRuntimeEffectBuilder::children()`、`SkRuntimeShaderBuilder::makeShader()`、`SkRuntimeColorFilterBuilder::makeColorFilter()` 和 `SkRuntimeBlendBuilder::makeBlender()` 现在标记为 const。内部没有功能变化，只是将原来隐式的 const 变为显式。
  * `SkRuntimeEffect::makeImage` 和 `SkRuntimeShaderBuilder::makeImage` 已被移除。
  * GL 相关的调用已从 GrBackendSurface.h 中移除。客户端应使用 `include/gpu/ganesh/gl/GrGLBackendSurface.h` 中的等效接口。
  * 新的 `SkTiledImageUtils` 命名空间（在 `SkTiledImageUtils.h` 中）提供了 `DrawImage` 和 `DrawImageRect` 方法，它们直接对应 `SkCanvas` 的 `drawImage` 和 `drawImageRect` 调用。

    这些新的入口点会将基于 `SkBitmap` 的大型 `SkImages` 分解为瓦片（tile），并在它们作为单个纹理上传到 GPU 时会过大的情况下进行分块绘制。

    如果不需要或无法进行分块绘制，它们将退回到对应的 `SkCanvas` 方法。

* * *

里程碑 116
-------------
  * `SkPromiseImageTexture` 已从公共 API 中移除，同时移除的还有 `SkImages::PromiseTextureFrom` 和 `SkImages::PromiseTextureFromYUVA`——这些是该数据类型的公共使用者。
  * `SkDeferredDisplayList`、`SkDeferredDisplayListRecorder` 和 `SkSurfaceCharacterization` 已从公共 API 中移除。
  * `SkBlenders::Arithmetic` 计算的中间颜色现在始终被限制在 0 到 1 之间（含边界），然后当 `enforcePremul` 参数为 true 时应用预乘处理。
  * 添加了一个新的公共类型 `SkColorTable`，用于持有传递给 `SkColorFilters::Table` 的查找表。这允许客户端和返回的 `SkColorFilter` 共享表内存，而无需在任何延迟创建 Skia 表示的包装类型中复制它。
  * 已弃用的*不*接受镜头边界参数的 `SkImageFilters::Magnifier` 工厂方法已被移除。
  * `SkImageFilters::RuntimeShader` 增加了接受最大采样半径的变体，该半径用于为运行时效果提供带有填充的输入图像，以避免边界条件问题。
  * `SkImageFilters::AlphaThreshold` 已被移除。其唯一的使用场景是在 ChromeOS 中，该用法已被替换为 `Blend(kSrcIn, input, Picture(region))` 滤镜图来实现相同效果。
  * 单参数的 `SkImageFilters::Image(sk_sp<SkImage>)` 工厂方法已被移除。在过滤期间渲染图像时必须提供 `SkSamplingOptions`。建议使用 `SkFilterMode::kLinear` 替代之前默认的双三次（bicubic）采样。
  * `GrTextureGenerator` 现在有一个子类 `GrExternalTextureGenerator`，客户端可以对其进行子类化，并与 `SkImages::DeferredFromTextureGenerator` 一起使用，以便从 Skia 外部创建的纹理创建图像。`GrTextureGenerator` 已从公共 API 中移除，取而代之的是 `GrExternalTextureGenerator`。
  * SkPoint 现在使用 float 作为其坐标类型。这开启了从 Skia 中移除 SkScalar 的进程。SkScalar 原本就是 float 的类型别名，因此这对使用 Skia 的代码没有实际影响。
  * `SkSamplingOptions(SkFilterMode)` 和 `SkSamplingOptions(SkCubicResampler)` 不再标记为 `explicit`，因此可以更简洁地内联创建采样选项。
  * `SkShaders` 现在是一个命名空间（此前是一个仅包含静态函数的不可构造类）。`SkPerlinNoiseShader::MakeFractalNoise` 和 `SkPerlinNoiseShader::MakeTurbulence` 已被移至 `SkShaders` 命名空间，而 `SkPerlinNoiseShader`（公共的不可构造类）已被计划移入 Skia 的私有内部实现中。移动后的函数没有功能差异，但 `include/core/SkShader.h`、`include/effects/SkGradientShader.h` 和 `include/effects/SkPerlinNoiseShader.h` 中某些 #includes 的更改可能导致依赖于传递依赖的客户端编译失败。
  * 以下方法已从 SkSurface 中移除，并重新定位到其他方法/函数中：
      - `SkSurface::asImage` -> `SkSurfaces::AsImage` (include/gpu/graphite/Surface.h)
      - `SkSurface::flushAndSubmit` -> `GrDirectContext::flushAndSubmit`
      - `SkSurface::flush` -> `GrDirectContext::flush`
      - `SkSurface::makeImageCopy` -> `SkSurfaces::AsImageCopy` (include/gpu/graphite/Surface.h)
      - `SkSurface::resolveMSAA` -> `SkSurfaces::ResolveMSAA()` (include/gpu/ganesh/SkSurfaceGanesh.h)

    此外，`SkSurface::BackendSurfaceAccess` 现在位于 `SkSurfaces` 命名空间中。
  * 已弃用的 `SkTableColorFilter` 类及其方法已被移除。客户端应使用 `SkColorFilters::Table` 和 `SkColorFilters::TableARGB`（定义在 include/core/SkColorFilter.h 中）。
  * `SkYUVAPixmapInfo::SupportedDataTypes(const GrImageContext&)` 构造函数已从公共 API 中移除。

* * *

里程碑 115
-------------
  * 客户端现在需要注册 Skia 应使用的编解码器来解码原始字节。例如：`SkCodecs::Register(SkJpegDecoder::Decoder());`。Skia 仍然提供许多受支持的格式（参见 `include/codec/*Decoder.h`）。客户端可以自由指定自己的编解码器，既可以补充现有集合，也可以使用自定义版本替代 Skia 之前默认提供的版本。使用自定义解码器时需要提供的数据，请参见 `SkCodecs::Decoder`（在 `include/codec/SkCodec.h` 中）。

    为了简化过渡，Skia 将在短时间内继续注册编解码器，除非定义了 `SK_DISABLE_LEGACY_INIT_DECODERS`。
  * `SkDrawable::newPictureSnapshot` 已被移除。请改为调用 `SkDrawable::makePictureSnapshot`。旧方法返回一个裸（但引用计数的）指针，客户端容易出错。新方法返回 `sk_sp<SkPicture>`，更容易处理，也与 Skia 的其余部分保持一致。
  * `SkGraphics::PurgePinnedFontCache()` 已被添加，允许客户端显式触发对带有 pinner 的 `SkStrikes` 的 `SkStrikeCache` 清除检查。在用户配置中定义 `SK_STRIKE_CACHE_DOESNT_AUTO_CHECK_PINNERS` 现在可以禁用对带有 pinner 的 strike 的自动清除检查。
  * 以下 SkImage 工厂方法已移至 `include/gpu/graphite/Image.h`：
     - `SkImage::MakeGraphiteFromBackendTexture -> SkImages::AdoptTextureFrom`
     - `SkImage::MakeGraphiteFromYUVABackendTextures -> SkImages::TextureFromYUVATextures`
     - `SkImage::MakeGraphiteFromYUVAPixmaps -> SkImages::TextureFromYUVAPixmaps`
     - `SkImage::MakeGraphitePromiseTexture -> SkImages::PromiseTextureFrom`

    SkImage 方法 `makeTextureImage` 已移至 `SkImages::TextureFromImage`。

    `SkImage::RequiredImageProperties` 已重命名为 `SkImage::RequiredProperties`，其中 fMipmapped 从 GPU 枚举改为布尔值。
  * `SkImage::makeColorSpace` 和 `SkImage::makeColorTypeAndColorSpace` 现在以 `GrDirectContext` 作为第一个参数。在处理基于纹理的图像时应提供此参数，否则可以为 `nullptr`。
  * `SkImage::subset` 现在以 `GrDirectContext*` 作为第一个参数（对于非 GPU 支持的图像，此参数可以为 `nullptr`）。基于编解码器或图片的图像在被读取前不会被转换为 GPU 纹理。这应该只会影响基于图片（picture）的图像——如果图片本身包含嵌套的基于纹理的图像，则可能无法正确读取。要强制转换为纹理，客户端应调用 `SkImages::TextureFromImage` 传入图像，然后对结果调用 subset。文档已澄清，如果源图像不是基于纹理的，`SkImage::subset` 将返回基于光栅的图像，否则返回基于纹理的图像。

    `SkImages::SubsetTextureFrom` 已被添加，用于对图像进行子集操作并显式返回基于纹理的图像。这允许一些优化，特别是对于超出 GPU 最大纹理大小的大型图像。

    `SkImage::makeRasterImage` 和 `SkImage::makeNonTextureImage` 现在接受一个 `GrDirectContext*` 参数，客户端在从基于纹理的图像回读像素时应提供此参数。
  * `SkImageFilters::Image` 现在在输入的 `sk_sp<SkImage>` 为 null 或源矩形为空或与图像不重叠时返回非空的图像滤镜。返回的滤镜计算结果为透明黑色，这等同于空图像。此前返回空图像滤镜意味着动态源图像可能会在非预期的情况下被意外注入到滤镜计算中。
  * `SkImageFilters::Magnifier(srcRect, inset)` 已被弃用。这些参数无法提供足够的信息让实现正确响应画布变换或准确参与图层边界规划。

    添加了一个新的 `SkImageFilters::Magnifier` 函数，它接受额外的参数：外部镜头边界和实际缩放量（而不是像之前那样不一致地重构目标缩放量）。此外，新工厂方法接受 SkSamplingOptions 来控制采样质量。
  * `SkImageFilters::Picture` 现在在输入的 `sk_sp<SkPicture>` 为 null 时返回非空的图像滤镜。返回的滤镜计算结果为透明黑色，这等同于空图片。此前返回空图像滤镜意味着动态源图像可能会在非预期的情况下被意外注入到滤镜计算中。
  * `SkImageFilters::Shader` 现在在输入的 `sk_sp<SkShader>` 为 null 时返回非空的图像滤镜。返回的滤镜计算结果为透明黑色，这等同于空着色器。此前返回空图像滤镜意味着动态源图像可能会在非预期的情况下被意外注入到滤镜计算中。
  * `SkImageGenerator::MakeFromEncoded` 已从公共 API 中移除。应改用 `SkImage::DeferredFromEncoded` 或 `SkCodec::MakeFromData`。
  * `SkSurface::getBackendTexture` 和 `SkSurface::getBackendRenderTarget` 已被弃用，分别由 `SkSurfaces::GetBackendTexture` 和 `SkSurfaces::GetBackendRenderTarget` 取代。这些位于 `include/gpu/ganesh/SkSurfaceGanesh.h` 中。支持的枚举 `BackendHandleAccess` 也已移至 `SkSurfaces::BackendHandleAccess` 作为枚举类（enum class），并使用了更短的成员名称。
  * SkSurface 工厂方法已移至 SkSurfaces 命名空间。许多方法已被重命名以更简洁或更自洽。Ganesh GPU 后端特定的工厂方法在 include/gpu/ganesh/SkSurfaceGanesh.h 中公开定义。Metal Ganesh 后端有一些特定的工厂方法在 include/gpu/ganesh/mtl/SkSurfaceMetal.h 中。
      * SkSurface::MakeFromAHardwareBuffer -> SkSurfaces::WrapAndroidHardwareBuffer
      * SkSurface::MakeFromBackendRenderTarget -> SkSurfaces::WrapBackendRenderTarget
      * SkSurface::MakeFromBackendTexture -> SkSurfaces::WrapBackendTexture
      * SkSurface::MakeFromCAMetalLayer -> SkSurfaces::WrapCAMetalLayer
      * SkSurface::MakeFromMTKView -> SkSurfaces::WrapMTKView
      * SkSurface::MakeGraphite -> SkSurfaces::RenderTarget
      * SkSurface::MakeGraphiteFromBackendTexture -> SkSurfaces::WrapBackendTexture
      * SkSurface::MakeNull -> SkSurfaces::Null
      * SkSurface::MakeRaster -> SkSurfaces::Raster
      * SkSurface::MakeRasterDirect -> SkSurfaces::WrapPixels
      * SkSurface::MakeRasterDirectReleaseProc -> SkSurfaces::WrapPixels
      * SkSurface::MakeRasterN32Premul -> SkSurfaces::Raster（客户端应创建 SkImageInfo）
      * SkSurface::MakeRenderTarget -> SkSurfaces::RenderTarget

* * *

里程碑 114
-------------
  * 运行时效果的 CPU 后端已被重写。当运行时效果绑定到光栅表面上绘制时，这可能导致性能和图像质量的细微差异。
  * 渐变着色器支持在多种不同的色彩空间中进行插值，通过向着色器工厂函数传递 `SkGradientShader::Interpolation` 结构体来实现。色彩空间和色相方法选项基于 CSS Color Level 4 规范：
    * https://www.w3.org/TR/css-color-4/#interpolation-space
    * https://www.w3.org/TR/css-color-4/#hue-interpolation
  * `SkImages::GetBackendTextureFromImage` 已重命名为 `SkImages::MakeBackendTextureFromImage`。
  * `SkImage::getBackendTexture()` 已移至 `SkImageGanesh.h` 中的 `SkImages::GetBackendTextureFromImage()`。
  * `SkImage::makeTextureImage()` 已移至 `SkImageGanesh.h` 中的 `SkImages::TextureFromImage()`。
  * `SkImage::flush()` 和 `SkImage::flushAndSubmit()` 已移至 `SkImageGanesh.h` 中的 `GrDirectContext::flush()` 和 `GrDirectContext::flushAndSubmit()`。
  * `SkSurfaceProperties::kAlwaysDither_Flag` 已添加，用于为特定 `SkSurface` 目标全局启用抖动。
  * `SkSerialImageProc` 和 `SkDeserialImageProc` 现在也用于编码/解码某些 SkImages 的 SkMipmap 层级。
  * 定义 `SK_USE_WIC_ENCODER` 和 `SK_USE_CG_ENCODER` 已被移除，以及使用 Windows Image Codecs 和 Core Graphics 让 Skia 编码 PNG、JPEG 和 WEBP 格式文件的代码。Skia 继续支持在 Android 上使用 NDK 编解码器，以及使用外部 C++ 库（例如 libpng、libjpeg-turbo）来*编码*图像。WIC 和 CG 在相应平台上仍然用于*解码*图像。
  * `SkImage::encodeToData` 已被弃用。客户端应使用 `refEncodedData`（如果图像来自编码的字节流）或直接使用 `SkPngEncoder::Encode`、`SkJpegEncoder::Encode`、`SkWebpEncoder::Encode` 之一。
  * 以下定义不再起作用。GN 客户端应根据需要设置提供的参数（来自 gn/skia.gni）：
      - `SK_ENCODE_PNG` -> `skia_use_libjpeg_turbo_encode`
      - `SK_ENCODE_JPEG` -> `skia_use_libpng_encode`
      - `SK_ENCODE_WEBP` -> `skia_use_libwebp_encode`
    其他客户端应确保在构建中包含来自 `src/encode` 的相应 `*EncoderImpl.cpp` 文件。
  * `SkImageEncoder` 已被移除。客户端应直接使用 `SkPngEncoder::Encode`、`SkJpegEncoder::Encode` 或 `SkWebpEncoder::Encode` 之一。
  * `SkImageGenerator` 有一个新的子类 `GrTextureGenerator`，如果客户端想要提供创建 Ganesh 纹理支持的图像的专用方法，可以使用它。
  * `SkImageGenerator::MakeFromPicture` 已从公共 API 中移除。客户端应直接绘制图片，而不是先将其转换为图像。


* * *

里程碑 113
-------------
  * 定义 SK_SUPPORT_GPU 现在改为 SK_GANESH。它不再被检测为 0 或 1，而是检测该定义是否存在。因此，如果未定义，它默认为关闭（未定义）（SK_SUPPORT_GPU 如果未定义则默认为 SK_SUPPORT_GPU=1）。
  * SkStrSplit 不再是公共 API 的一部分。
  * SkImage::encodeToData 现在接受一个 GrDirectContext。不带该参数的版本已被弃用，将在未来某个时间点移除。
  * SkMatrix::Scale、preScale、setScale 等当任何缩放因子为 0 时，`rectStaysRect()` 现在正确地不再返回 true，这与 `rectStaysRect()` 意味着非零缩放的语义一致。
  * `SkImage::CompressionType` 已重命名为 `SkTextureCompressionType` 并移至 `include/core/SkTextureCompressionType.h`。
  * `SkEncodedImageFormat.h` 和 `SkPngChunkReader.h` 现在位于 include/codec 中。
  * `SkICC.h` 现在位于 include/encode 中。
  * SkImage 工厂方法已移至 SkImages 命名空间。许多方法已被重命名以更简洁或更自洽。Ganesh GPU 后端特定的工厂方法在 include/gpu/ganesh/SkImageGanesh.h 中公开定义。
      * SkImage::MakeBackendTextureFromSkImage -> SkImages::GetBackendTextureFromImage
      * SkImage::MakeCrossContextFromPixmap -> SkImages::CrossContextTextureFromPixmap
      * SkImage::MakeFromAdoptedTexture -> SkImages::AdoptTextureFrom
      * SkImage::MakeFromBitmap -> SkImages::RasterFromBitmap
      * SkImage::MakeFromCompressedTexture -> SkImages::TextureFromCompressedTexture
      * SkImage::MakeFromEncoded -> SkImages::DeferredFromEncodedData
      * SkImage::MakeFromGenerator -> SkImages::DeferredFromGenerator
      * SkImage::MakeFromPicture -> SkImages::DeferredFromPicture
      * SkImage::MakeFromRaster -> SkImages::RasterFromPixmap
      * SkImage::MakeFromTexture -> SkImages::BorrowTextureFrom
      * SkImage::MakeFromYUVAPixmaps -> SkImages::TextureFromYUVAPixmaps
      * SkImage::MakeFromYUVATextures -> SkImages::TextureFromYUVATextures
      * SkImage::MakePromiseTexture -> SkImages::PromiseTextureFrom
      * SkImage::MakePromiseYUVATexture -> SkImages::PromiseTextureFromYUVA
      * SkImage::MakeRasterCopy -> SkImages::RasterFromPixmapCopy
      * SkImage::MakeRasterData -> SkImages::RasterFromData
      * SkImage::MakeRasterFromCompressed -> SkImages::RasterFromCompressedTextureData
      * SkImage::MakeTextureFromCompressed -> SkImages::TextureFromCompressedTextureData
    为了帮助过渡，有一些临时的桥接代码（例如别名），最终会被移除。

* * *

里程碑 112
-------------
  * SkImage::CubicResampler 已被移除。客户端应改用 include/core/SkSamplingOptions.h 中的 SkCubicResampler（前者是后者的别名）。
  * SkRuntimeColorFilterBuilder 已被添加。这是一个用于设置颜色滤镜的辅助类，类似于 SkRuntimeShaderBuilder。
  * SkShaders::CoordClamp 已被添加。它将与另一个着色器一起使用的坐标限制在一个矩形内。
  * SkRandom 不再是公共 API 的一部分。
  * SK_ARRAY_COUNT 不再是公共 API 的一部分。客户端应使用 std::size。
  * SK_SCALAR_IS_FLOAT 不再被设置。SkScalar 始终是 float（自 2017 年起就是如此）。
  * sk_realloc_throw（一个内部 API）现在在传入大小为 0 时释放内存。这对使用默认分配器的客户端应该没有用户可见的影响，但要求自定义分配器也实现此更改。
  * 粒子模块（particles module）已被删除。
  * SkJpegEncoder::Options 包含一个 XMP 元数据参数。
  * SkJpegEncoder 增加了对直接编码 SkYUVAPixmaps 的支持。

* * *

里程碑 111
-------------
  * SkToBool 不再是公共 API 的一部分。
  * 现在存在一个 float 版本的 SkCanvas::saveLayerAlpha，即 SkCanvas::saveLayerAlphaf。
  * SkAbs32 和 SkTAbs 不再是公共 API 的一部分。
  * SkAlign2、SkAlign4、SkAlign8、SkIsAlign2、SkIsAlign4、SkIsAlign8、SkAlignPtr、SkIsAlignPtr 和 SkAlignTo 不再是公共 API 的一部分。
  * GrContextOptions::fSkipGLErrorChecks 不再跳过着色器编译和程序链接成功的检查。
  * SkBackingFit 不再是公共 API 的一部分。
  * SkBudgeted 已从 include/core/SkTypes.h 移至 include/gpu/GpuTypes.h，并移入 skgpu 命名空间。
  * include/gpu/GrConfig.h 已被移除；其内容已合并到其他文件中。
  * SkLeftShift 不再是公共 API 的一部分。
  * SK_MaxS32 及相关常量不再是公共 API 的一部分。
  * include/core/SkMath.h 不再是公共 API 的一部分。

* * *

里程碑 110
-------------
  * SkParsePath::ToSVGString 现在返回字符串，而不是修改传入的字符串。
  * 移除了之前已弃用的 SkImageFilters::Paint 工厂方法。请改用 SkImageFilters::Shader。
  * SkMesh::Make 和 SkMesh::MakeIndexed 现在返回一个 SkMesh 和错误消息字符串。
  * SkPaint::getFillPath 已被 include/core/SkPathUtils.h 中的 skpathutils::FillPathWithPaint 取代。功能应保持不变。

* * *

里程碑 109
-------------
  * SkMesh 顶点和片段的 main() 签名已更改。请参见 SkMeshSpecification 上的文档。
  * 添加了 SkImage::RescaleMode::kLinear，使得异步缩放/回读 API 无论总缩放因子如何都可以在单个步骤中进行缩放（比 kRepeatedLinear 更快但质量更低）。
  * 添加了 SkMesh 缓冲区工厂方法，用于复制 CPU 支持的缓冲区。
  * Skia 中添加了一个运行时效果代码压缩工具。在 gn 参数中添加 "skia_compile_modules = true"，一个名为 "sksl-minify" 的新工具将作为 Skia 构建的一部分被编译。运行命令：
      `skia-minify output-file.sksl input-file.sksl`
    可将运行时着色器 "input-file.sksl" 的压缩版本写入名为 "output-file.sksl" 的文件。默认情况下，sksl-minify 期望输入为着色器，但如果你的程序是颜色滤镜或混合器，也可以传递命令行选项 `--colorfilter` 或 `--blender`。如果程序中发现编译错误，将打印到标准输出。
  * SkShader 局部矩阵串联的顺序已被反转。参见 skbug.com/40044836
  * Promise 图像（PromiseImages）已添加到 Graphite 中。这支持易失性和非易失性的 Promise 图像。更多详情请参见 SkImage::MakeGraphitePromiseTexture 的注释。
  * Graphite 放宽了 SkImages 的不可变性要求——通过新的 SkSurface API 和细致的同步机制，客户端现在可以修改支持 SkImage 的后端对象。新的 API 由 SkSurface::asImage 和 SkSurface::makeImageCopy 组成。我们有一份文档涵盖了预期的使用场景以及每个场景所需的同步机制。

* * *

里程碑 108
-------------
  * SkShader::asAGradient() 已被移除。
  * SkMesh 和 SkMeshSpecification 对引用计数类型分别提供了 sk_sp 和裸指针的 getter 方法。
  * 为 SkJpegEncoder、SkPngEncoder 和 SkWebpEncoder 添加了指定自定义 ICC 配置文件的支持。

* * *

里程碑 107
-------------
  * 导出了 SkColor4f::toBytes_RGBA() 和 SkColor4f::FromBytes_RGBA。
  * SkWebpEncoder：添加了对动画 WebP 图像编码的支持。
  * SkRuntimeEffect 着色器效果无意中允许了签名为 `half4 main(float2 coords, half4 color)` 的函数。这在里程碑 87 中被禁止，但在后续里程碑中该限制被无意放宽。今后，我们将只接受 `half4 main(float2 coords)` 的着色器签名。

* * *

里程碑 106
-------------
  * sk_sp 在支持的地方标记了 [[clang::trivial_abi]] 属性。
  * SkMesh API：允许用户使用自定义属性和 varying，通过 SkSL 绘制顶点网格。网格数据（顶点和索引）可以在 GrDirectContext 上创建，以避免每次绘制时重新上传数据。目前不支持 SkPicture 或 GPU 以外的后端。
  * 添加了 SkColorFilters::Blend(const SkColor4f&, sk_sp<SkColorSpace>, SkBlendMode) 以补充现有的 SkColorFilters::Blend(SkColor, SkBlendMode) 工厂方法。
  * 实验性 C API 已被移除。
  * 添加了使用 libavif 进行 AVIF 解码的支持。

* * *

里程碑 104
-------------
  * 新函数 SkBitmap::getColor4f 和 SkPixmap::getColor4f 返回浮点颜色。
  * SkRuntimeEffect 接受并返回 const SkData。
  * SkRasterHandleAllocator::MakeCanvas 现在接受可选的 SkSurfaceProps。
  * SkImage::MakeFromPicture 和 SkImageGenerator::MakeFromPicture 现在接受可选的 SkSurfaceProps，用于光栅化图片时使用。
  * SkRuntimeEffect::Uniform 现在将 uniform 名称存储为 string_view，而不是 SkString。相关方法 SkRuntimeEffect::findUniform 和 SkRuntimeEffectBuilder::uniform 也接受 std::string_view 而不是 const char*。
  * SkRuntimeEffect::Child 现在将子节点名称存储为 string_view，而不是 SkString。相关方法 SkRuntimeEffect::findChild 和 SkRuntimeEffectBuilder::child 也接受 std::string_view 而不是 const char*。此外，SkImageFilters::RuntimeShader 现在接受 std::string_view 而不是 const char* 作为子节点名称。
  * skcms.h 已从 //include/third_party/skcms/skcms.h 迁移到 //modules/skcms/skcms.h。
  * 新函数 SkCanvas::getBaseProps 和 SkCanvas::getTopProps；SkCanvas::getBaseProps 是（现已弃用的）SkCanvas::getProps 函数的直接替代，而 getTopProps 是返回当前层中活动的 SkSurfaceProps 的变体。
  * 新函数 SkEventTracer::newTracingSection(const char* name) 允许将追踪拆分为不同的部分，适用于一组后端追踪框架（Perfetto、SkDebugf）。

* * *

里程碑 103
-------------
  * SkSamplingOptions 现在包含各向异性过滤。仅在 GPU 上实现。
  * SkBitmap::clear 和 SkBitmap::clearColor 接受 SkColor4fs。

* * *

里程碑 102
-------------
  * 向 GrGLInterface 添加了 glGetFloatv 和 glSamplerParameterf。
  * GrGLCreateNativeInterface 已被移除。请使用 GrGLMakeNativeInterface。
  * GrContextOptions::fSharpenMipmappedTextures 已被移除。MIP LOD 在 GPU 后端上现在始终应用偏移。CPU 后端实现已修改以匹配此行为。
  * 传递 SkCanvas::kStrict_SrcRectConstraint 会禁用 mipmap。旧行为在 GPU 和 CPU 之间有所不同。CPU 始终基于子集计算新的 mipmap 集合。GPU 在基础层级中将采样坐标限制在子集内，但上层像素（映射到基础层级中子集之外的像素）仍然被使用。要获得之前的 CPU 行为，可以使用 SkImage::makeSubset() 创建子集图像并绘制它。之前的 GPU 行为类似（但不完全等同于）从原始图像创建 mipmap 图像着色器并将其应用于矩形。
  * 完全禁用了对硬件曲面细分着色器的实验性支持。GrContextOptions::fEnableExperimentalHardwareTessellation 被忽略，其行为如同设为 false。优化后的路径渲染器不再需要硬件曲面细分，当绘制到使用 MSAA 创建的 SkSurface 或当 GrContextOptions::fInternalMultisampleCount 设为非零值时，它会自动启用。

* * *

里程碑 101
-------------
  * 在 GrContextThreadSafeProxy 中添加了 maxSurfaceSampleCountForColorType(SkColorType ct)。
  * 枚举 SkAlphaType 和 SkColorType 已分离到 include/core/ 中各自独立的头文件中。

* * *

里程碑 100
-------------
  * Skia 现在要求 C++17 及对应的标准库（或更新版本）。
  * iOS 上的 Skia 现在需要 iOS 11 才能构建；更早版本的 iOS 不支持 C++17。
  * Skia 的 skstd::string_view 和 skstd::optional 类已被 C++17 原生的 std::string_view 和 std::optional 替代。
  * 添加了 SkSurface::resolveMSAA API 以强制 Skia 解析 MSAA 绘制。当 Skia 将客户端的纹理作为解析目标包装时非常有用。
  * 与 `SkRuntimeEffect` 关联的所有 `makeShader` 函数不再接受 `isOpaque` 参数。这些函数现在会尽最大努力判断你的着色器是否始终产生不透明输出，并相应进行优化。如果你确实希望着色器产生不透明输出，请在着色器的 SkSL 代码中实现。这可以通过在着色器的任何 `return` 语句中使用 swizzle 来完成：`return color.rgb1;`。
    https://review.skia.org/506462
  * SkRSXform 现在已导出到 DLL/.so 文件。
* * *

里程碑 99
------------
  * 为 SkSL 添加了两个新的内置函数，用于运行时效果：
      vec3 toLinearSrgb(vec3 color)
      vec3 fromLinearSrgb(vec3 color)
    这些函数在工作色彩空间（目标表面的色彩空间）和已知的固定色彩空间之间转换 RGB 颜色值。`toLinearSrgb` 将颜色转换到具有线性传输函数的 sRGB 色域。`fromLinearSrgb` 从该色彩空间转换颜色。这些函数对于需要在特定色彩空间中工作的效果，或希望应用在线性色彩空间中效果最佳的效果（如光照）非常有帮助。注意，如果目标表面没有色彩空间（色彩空间为 `nullptr`），这些内置函数不会进行任何转换，并返回未更改的输入颜色。
    https://review.skia.org/481416
  * 添加了 SkImageFilters::RuntimeShader 的新变体，支持多个子节点。
    https://review.skia.org/489536
  * 添加了在 SkFontArguments 中指定调色板覆盖的功能。已在基于 FreeType 的 SkFontMgrs 中实现。

* * *

里程碑 98
------------
  * 当 SK_SUPPORT_GPU 为 0 时，以下函数和方法不在 SkSurface 中定义：MakeFromBackendTexture、MakeFromBackendRenderTarget、MakeRenderTarget、getBackendTexture、getBackendRenderTarget、replaceBackendTexture。带参数的 flush() 也被移除了。当仅编译了 CPU 后端时，这些本来就是空操作（注意 flush() 和 flushAndSubmit() 在 CPU 后端上仍然是空操作）。
  * GrBackendSemaphore 仅包含与 Skia 编译时的 GPU 后端匹配的方法。例如，除非 Vulkan 后端被编译进 Skia，否则 initVulkan 和 vkSemaphore 不会被定义。
  * 表面和图像现在被限制为总大小略小于 2GB。此前可以创建更大的图像，但 CPU 后端无法正确索引它们。
  * 不接受 SkBlendMode 的 SkCanvas::drawVertices 和 SkCanvas::drawPatch 变体已被移除。
  * SkImageFilters::RuntimeShader 是一个新的公共 API，允许将 RuntimeShaderEffects 添加到图像滤镜图中。
  * SkImage::makeRawShader 是一个新的公共 API，用于创建"原始"图像着色器。makeRawShader 的功能类似于 SkImage::makeShader，但用于包含非颜色数据的图像。这包括编码法线、材质属性（如粗糙度）、高度图或其他恰好存储在图像中的纯数学数据的图像。这些类型的图像与某些可编程着色器（即 SkRuntimeEffect）配合使用很有用。原始图像着色器的工作方式类似于常规图像着色器（包括过滤和平铺），但有几个主要区别：
      - 不会应用任何色彩空间转换（图像的色彩空间被忽略）。
      - Alpha 类型为 kUnpremul 的图像不会自动进行预乘。
      - 不支持双三次过滤。如果 SkSamplingOptions::useCubic 为 true，这些工厂方法将返回 nullptr。
  * 移除了 SkCanvas::markCTM 和 SkCanvas::findMarkedCTM。这些是为配合其他功能而创建的，但那些功能已被删除，因此它们不再有用途。
  * 添加了有限的 JPEGXL 支持。

* * *

里程碑 97
------------
  * 添加了对 Vulkan DRM 修饰符的基本支持。所有这些在内部都被视为只读纹理（而不是查询特定的修饰符支持）。客户端可以向 Vulkan GrBackendFormat 传递标志以表示它使用修饰符，或通过 GrVkImageInfo 结构体向 GrBackendTexture 传递 VK_IMAGE_TILING_DRM_FORMAT_MODIFIER_EXT。
  * 当 SK_SUPPORT_GPU 为 0 时，以下函数和方法不在 SkImage 中定义：MakeTextureFromCompressed、MakeFromTexture、MakeFromCompressedTexture、MakeCrossContextFromPixmap、MakeFromAdoptedTexture、MakeFromYUVATextures、MakeFromYUVAPixmaps、MakePromiseTexture、MakePromiseYUVATexture、MakeBackendTextureFromSkImage、flush、flushAndSubmit、getBackendTexture、makeTextureImage。当仅编译了 CPU 后端时，这些本来就是空操作。

* * *

里程碑 96
------------
  * SkRuntimeEffect 不再将效果输出的 RGB 值限制在 0..A 范围内。这使得更容易使用 SkSL 着色器的层级结构，其中中间值不代表颜色，例如作为光照模型的非颜色输入。
    http://review.skia.org/452558

* * *

里程碑 95
------------
  * 最低支持的 iOS 版本从 8 提升到 11。Skia 可能可以在 iOS 9 上构建，但 11 以下的版本未经测试。社区贡献的对 iOS 9 和 10 版本的支持可能会被考虑，但不能太复杂，因为无法进行测试。

* * *

里程碑 94
------------
  * Metal 后端已更改为手动跟踪命令缓冲区资源，而不是使用保留资源。
    https://review.skia.org/432878

  * 为 Android Framework 向 SkCanvas 添加了虚函数 onResetClip()，以模拟即将被移除的、由 SK_SUPPORT_DEPRECATED_CLIPOPS 保护的扩展裁剪操作。
    https://review.skia.org/430897

  * 移除了 SK_SUPPORT_DEPRECATED_CLIPOPS 构建标志。裁剪操作只能是交集（intersect）和差集（difference）。
    https://review.skia.org/436565

  * SkSL 中调用（采样）子效果有了新的语法。此前，子效果（着色器、颜色滤镜、混合器）通过 `sample` 的不同重载来调用。该语法已被弃用（但仍然支持）。现在，子效果的行为类似于对象，带有名为 `eval` 的方法。这些 `eval` 方法的参数与旧的 `sample` 内置函数中的参数相同。例如：
      // 旧语法：
        sample(shader, xy)
        sample(colorFilter, color)
        sample(blender, srcColor, dstColor)
      // 新语法：
        shader.eval(xy)
        colorFilter.eval(color)
        blender.eval(srcColor, dstColor)
    https://review.skia.org/444735

* * *

里程碑 93
------------
  * 移除了 SkPaint::getHash
    https://review.skia.org/419336

  * 移除了 SkShaders::Lerp。它未被使用（且可以使用 SkRuntimeEffect 轻松复制）。
    https://review.skia.org/419796

  * GrContextOptions::fReduceOpsTaskSplitting 的默认值现在为启用。
    https://review.skia.org/419836

  * 移除了 SkMatrix44

* * *

里程碑 92
------------
  * 将 SkPathEffect::computeFastBounds() 从公共 API 中隐藏；SkPathEffect 的外部子类必须实现 onComputeFastBounds()，但可以返回 false 以表示无法计算。
    https://review.skia.org/406140

  * 添加了 SkM44::RectToRect 构造函数（SkM44 对应 SkMatrix::RectToRect 的等效物）
    https://review.skia.org/402957

  * Metal 支持已移除对 iOS 10.0 以下版本和 MacOS 10.14 以下版本的支持。
    https://review.skia.org/401816

  * 从 SkVertices 中移除了自定义属性以及 SkRuntimeEffect 中对应的 `varying` 功能。
    https://review.skia.org/398222

  * 放弃了对混合采样（mixed samples）的支持。混合采样对 Ganesh 不再相关。DMSAA 和新的 Ganesh 架构都依赖于完整的 MSAA，任何支持混合采样的平台最终都不会使用旧架构。

  * SkRuntimeEffect::Make 已被移除。它被 MakeForShader 和 MakeForColorFilter 替代。这些函数对 SkSL 进行更严格的错误检查，以确保它对 Skia 管线的特定阶段有效。
    https://review.skia.org/402156

* * *

里程碑 91
------------
  * SkSL DSL API 已移至公共头文件中，尽管它仍在积极开发中，还没有完全准备好正式使用。
    https://review.skia.org/378496

  * Skia 的 GPU 后端不再支持 NVPR。我们更新的路径渲染器性能更优，且不限于 nVidia 硬件。

  * SkRuntimeEffect 现在支持 int、int2、int3 和 int4 类型的 uniform。根据 OpenGL ES Shading Language Version 1.00 规范，对整数类型的表示或范围几乎没有保证，且假设整数表示的操作（例如位运算）不被支持。
    https://review.skia.org/391856

  * SkRuntimeEffect 要求 'shader' 变量声明为 'uniform'。已弃用的 'in shader' 语法不再受支持。
    https://review.skia.org/393081

* * *

里程碑 90
------------
  * 将外部 Metal 类型中 sk_cf_obj 的使用重命名为 sk_cfp。
    https://review.skia.org/372556

  * GrDirectContext::ComputeImageSize() 已被移除。请改用 SkImage::textureSize()。
    https://review.skia.org/368621
    https://review.skia.org/369317
    https://review.skia.org/371958

  * 移除了 SkImageFilter::MakeMatrixFilter，因为它未被使用且已被 SkImageFilters::MatrixTransform 取代。
    https://review.skia.org/366318

  * 重构了粒子系统，使用包含 Effect 和 Particle 代码的单个代码字符串。Uniform API 现在对所有程序入口点共享，不再以 'Effect' 或 'Particle' 为前缀。例如，`SkParticleEffect::effectUniformInfo` 和 `SkParticleEffect::particleUniformInfo` 被替换为 `SkParticleEffect::uniformInfo`。

  * 从公共 API 中移除了 SkImageFilter::CropRect，因为它不再可用。所有工厂方法使用 'SkRect'、'SkIRect' 或可为空的 'Sk[I]Rect' 指针。
    https://review.skia.org/361496

  * 移除了已弃用的 SkImageFilter 工厂函数和支持类型。所有默认提供的 SkImageFilters 现在仅通过 'include/effects/SkImageFilters.h' 构造。
    https://review.skia.org/357285

  * 添加了 SkRuntimeEffect::makeImage()，用于将 SkRuntimeEffect 的输出捕获到 SkImage 中。
    https://review.skia.org/357284

  * 更新了 SkRuntimeEffect::Make()，使其接受一个 Options 结构体。它现在还返回一个 Results 结构体而不是元组。
    https://review.skia.org/363785
    https://review.skia.org/367060

  * 更改了 SkRuntimeEffect::Varying，使成员名称为小写且不带 'f' 前缀。
    https://review.skia.org/365656

  * 更改了 SkRuntimeEffect::Uniform，使成员名称为小写且不带 'f' 前缀。
    https://review.skia.org/365696

  * 弃用（并忽略）SkAndroidCodec::ExifOrientation
    https://review.skia.org/344763

  * 修复了光照图像滤镜中的几个小问题：
    - 聚光灯衰减指数不再被限制在 [1, 128] 范围内。SVG 1.1 要求镜面反射
      光照效果的指数（光泽度）被限制；而不是聚光灯的衰减。任何此类参数限制都是客户端的职责，
      这使得 Skia 的光照效果可以轻松适配 SVG 1.1（限制指数）或 SVG 2（不限制）。
    - 修复聚光灯在锥角内错误缩放光照的问题。
    - 将 RGBA 饱和度处理移至光照强度与光照颜色相乘之后，这改善了漫反射和镜面反射常数大于 1 时的渲染效果。
    https://review.skia.org/355496

  * SkDeferredDisplayListRecorder::makePromiseTexture 已移至 SkImage::MakePromiseTexture。
    新代码应使用新的入口点——迁移 CL 即将到来。
    https://review.skia.org/373716

* * *

里程碑 89
------------

  * 移除了 SkYUVAIndex 和 SkYUVASizeInfo。这些已不再在任何公开 API 中使用。
    https://review.skia.org/352497

  * 对 SkRuntimeEffect 进行了大量更改，使其能力和限制与 The OpenGL ES Shading Language 1.00
    （即 OpenGL ES2 和 WebGL 1.0 的着色语言）保持一致。
    第 8.1 至 8.6 节的所有内置函数已在所有后端实现并测试。
    移除了需要更新版本 GLSL 的类型和功能：
      https://review.skia.org/346657  [非方阵矩阵]
      https://review.skia.org/347046  [uint、short、ushort、byte、ubyte]
      https://review.skia.org/349056  [while 和 do-while 循环]
      https://review.skia.org/350030  [位运算符和整数取余]

  * 新增 SkShadowUtils::GetLocalBounds。生成相对于路径的阴影包围盒。
    https://review.skia.org/351922

  * 移除了 SkPerlinNoiseShader::MakeImprovedNoise。
    https://review.skia.org/352057

  * 移除了已弃用版本的 MakeFromYUVATextures。请改用接受 GrYUVABackendTextures 的版本。
    https://review.skia.org/345174

  * SkAnimatedImage：始终遵循 EXIF 方向信息。
    将 SkPixmapPriv::ShouldSwapWidthHeight 替换为 SkEncodedOriginSwapsWidthHeight。
    https://review.skia.org/344762

  * 新增 kDirectionalLight_ShadowFlag 支持。启用后，光源位置表示一个指向光源的方向向量，
    光源半径为高度 1 处的模糊半径。
    https://review.skia.org/321792

  * 支持 GL_LUMINANCE8_ALPHA8 纹理。这些纹理可与 GrDirectContext 上的 GrBackendTexture API
    一起使用，也可通过 GrYUVABackendTextures 作为 YUVA 图像的平面使用。
    https://review.skia.org/344761

  * 移除了先前已弃用的 SkImage::MakeFromYUVATexturesCopyToExternal。
    https://review.skia.org/342077

  * 新增接受 GrSurfaceOrigin 参数的 GrDirectContext::createBackendTexture 和
    updateBackendTexture 版本。先前的版本已弃用。
    https://review.skia.org/341005

  * 移除 SkCanvas::SaveLayerRec 中对已弃用的 kDontClipToLayer_SaveLayerFlag 的支持。
    https://review.skia.org/339988

  * 在 SkCodec::FrameInfo 中暴露更多信息。
    https://review.skia.org/339857

  * 为 SkImageFilters::Shader 工厂添加了抖动控制。
    https://review.skia.org/338156

  * 为 GrMtlBackendContext 添加 MTLBinaryArchive 参数。这允许 Skia 将 PipelineState
    缓存到给定的归档中，以便在未来运行时实现更快的着色器编译。客户端必须自行处理归档的加载和保存。
    https://review.skia.org/333758

  * 已弃用的枚举 SkYUVAInfo::PlanarConfig 已被移除。
    https://review.skia.org/334161

  * 已弃用的 SkImage 工厂已从 SkDeferredDisplayListRecorder 中移除。

  * 以下 YUV 图像工厂已被移除：
    SkImage::MakeFromYUVTexturesCopyWithExternalBackend
    SkImage::MakeFromNV12TexturesCopyWithExternalBackend
    替代方案如下所述。
        1) 使用 MakeFromYUVATextures 创建图像
        2) 使用 SkSurface::MakeFromBackendTexture 围绕结果纹理创建 SkSurface
        3) surface->getCanvas()->drawImage(image, 0, 0);
        4) surface->flushAndSubmit()
        5) 可选：使用 SkImage::MakeFromBackendTexture() 作为 SkImage 使用。
    https://review.skia.org/334596

  * 新增了一个使用新结构体 GrMtlBackendContext 在 Metal 中创建 GrDirectContext 的新接口。
    先前接受 MTLDevice 和 MTLCommandQueue 的接口已弃用。
    https://review.skia.org/334426

  * SkCanvas::flush 已弃用。

* * *

里程碑 88
------------

  * SkYUVAInfo 现在为通道在平面间的划分和子采样分别使用单独的枚举。
    先前的组合枚举 PlanarConfig 已弃用。
    https://review.skia.org/334102

  * 简化了 SkDeferredDisplayListRecorder 的 Promise 图像 API。移除了"release"回调并将"done"
    回调重命名为"release"。新的"release"过程可以为 null。新增了一个基于 SkYUVAInfo 的 YUVA
    Promise 纹理图像工厂，并弃用了旧的基于 SkYUVAIndex 的工厂。
    https://review.skia.org/331836
    https://review.skia.org/333519

  * 将 SkRuntimeEffect 中支持的类型和内置函数限制为 GLSL ES 1.00。
    https://review.skia.org/332597

  * 为 SkHeifCodec 添加 AVIF 支持。

  * 新增直接创建 SkSurfaceCharacterization 的支持，以供 GrVkSecondaryCBDrawContext 使用。
    https://review.skia.org/331877

  * 移除了 SkSurfaceProps::kLegacyFontHost_InitType、SkFontLCDConfig 及相关代码。
    SkSurfaceProps 的默认像素几何现在为 kUnknown 而非 kRGB_H。
    该移除由 SK_LEGACY_SURFACE_PROPS 构建标志保护，该标志后来也被移除。
    https://review.skia.org/322490
    https://review.skia.org/329364

  * 从 SkImageGenerator 移除了旧版 8 位 YUV 接口。请改用更灵活的基于 SkYUVAPixmaps 的接口。
    https://review.skia.org/327917

  * SkImage::MakeFromYUVATextures 的新变体。接受新类型 GrYUVATextures，该类型封装了
    SkYUVAInfo 和一组兼容的 GrBackendTextures。这提供了更完整和结构化的平面配置规范。
    先前的版本已弃用。
    已添加已弃用的 MakeFromYUVATexturesCopyToExternal 以替换其他已弃用的 API。
    不建议客户端使用此方法，而应使用 API 注释中描述的模式。
    https://review.skia.org/317762
    https://review.skia.org/329956

  * 在 GrContextOptions 中添加字段以禁用 mipmap 支持，即使后端支持也是如此。

  * SkTPin() 已从公开 API 中移除。

  * 新增 SkImageFilters::Blend 工厂函数，以替代现已弃用的 SkImageFilters::Xfermode 工厂函数。
    行为相同，但名称更符合 SkShader 和 SkColorFilter 中的命名约定。
    https://review.skia.org/324623

  * SkImageFilters::Foo() 工厂函数现在接受 SkIRect、SkRect 以及可选的 SkIRect* 或 SkRect*，
    而不是先前仅接受可选的 SkIRect*。在内部，裁剪矩形以浮点数存储，
    以允许在局部坐标系中（在画布矩阵变换之前）定义分数裁剪。
    https://review.skia.org/324622

  * 新增 SkImageFilters::Shader 工厂并弃用 SkImageFilters::Paint 工厂。
    所有受支持/有效的 Paint() 滤镜都可以更简洁地表示为 Shader 图像滤镜。
    https://review.skia.org/323680

  * GrContext 已被两个独立的类替代：GrDirectContext 是传统意义上的 GrContext，
    而 GrRecordingContext 是用于录制 SkDeferredDisplayList 的上下文，因此功能有所减少。
    除非您使用 SkDeferredDisplayList，否则在所有情况下直接迁移到 GrDirectContext。

  * 为 SkSurface::flushAndSubmit() 和 GrContext::flushAndSubmit() 添加了 CPU 同步布尔值。

  * 移除了 SkImage::MakeFromYUVAPixmaps 的旧版变体。请改用接受 SkYUVAPixmaps 的版本。
    它对平面配置有更结构化的描述。
    https://review.skia.org/322480

  * 一些 SkImage YUV 图像工厂已被移除。替代方案如下所述。
    SkImage::MakeFromYUVATexturesCopy
        1) 使用 SkImage::MakeFromYUVATextures 从 YUVA 平面创建 SkImage
        2) 使用 Skia 通过 SkSurface::MakeRenderTarget 分配 Surface
        3) surface->getCanvas()->drawImage(image, 0, 0);
        4) surface->makeImageSnapShot() 生成 RGBA 图像。
    SkImage::MakeFromYUVATexturesCopyWithExternalBackend
        1) 使用 MakeFromYUVATextures 创建图像
        2) 使用 SkSurface::MakeFromBackendTexture 围绕结果纹理创建 SkSurface
        3) surface->getCanvas()->drawImage(image, 0, 0);
        4) surface->flushAndSubmit()
        5) 可选：使用 SkImage::MakeFromBackendTexture() 作为 SkImage 使用。
    SkImage::MakeFromNV12TexturesCopy
        同 SkImage::MakeFromYUVATexturesCopy
    https://review.skia.org/321537

  * 使用 stencilBits 参数创建的 GrBackendRenderTargets 现在要求 stencilBits 为 0、8 或 16。
    https://review.skia.org/321545

* * *

里程碑 87
------------

  * GrVkImageInfo 现在有一个采样数字段。同时接受 GrVkImageInfo 和单独采样数的
    GrBackendRenderTarget 构造函数已弃用。请改用不带采样数的版本。类似地，
    GrD3DTextureResourceInfo 现在也有一个采样数字段，GrBackendRenderTarget 不再为 Direct3D
    接受单独的采样数。GrBackendRenderTarget 的采样数现在直接从 MtlTexture 查询，而不是单独传递。
    接受单独采样数的版本已弃用，该参数将被忽略。
    https://review.skia.org/320262
    https://review.skia.org/320757
    https://review.skia.org/320956

  * 为 MacOS 10.13、iOS 8.3 及更早版本上的 Metal 支持添加了弃用警告。
    https://review.skia.org/320260

  * GrVkImageInfo 现在有一个采样数字段。同时接受 GrVkImageInfo 和单独采样数的
    GrBackendRenderTarget 构造函数已弃用。请改用不带采样数的版本。

  * 更新 SkClipOp::kMax_EnumValue，在未定义 SK_SUPPORT_DEPRECATED_CLIPOPS 时仅包含
    intersect 和 difference。
    https://review.skia.org/320064

  * 为 Direct3D 12 后端添加外部分配器支持。
    定义了与后端纹理关联的分配的基类和创建此类分配的内存分配器。
    将内存分配器添加到后端上下文中。
    https://review.skia.org/317243

  * 为 GrContext::setBackend[Texture/RenderTarget]State 添加了新的可选参数，可用于返回
    请求更改之前的 GrBackendSurfaceMutableState。
    https://review.skia.org/318698

  * 为 GPU 后端新增优化的裁剪栈。默认启用，但可以在构建时定义 SK_DISABLE_NEW_GR_CLIP_STACK
    来恢复基于 SkClipStack 的旧行为。它与 SK_SUPPORT_DEPRECATED_CLIPOPS 不兼容，
    我们的目标是移除对已弃用的扩展裁剪操作的支持。
    https://review.skia.org/317209

  * GPU 后端现在在调用 drawAtlas 时正确遵循 SkFilterQuality。
    https://review.skia.org/313081

  * 与 SkRuntimeEffect SkSL 一起使用的 'main' 签名已更改。不再有 'inout half4 color' 参数，
    效果必须改为返回其颜色值。
    现在有效的签名为 'half4 main()' 或 'half4 main(float2 coord)'。
    https://review.skia.org/310756

  * SkCodec、SkImageGenerator、SkImage::MakeFromYUVAPixmaps 的新 YUVA 平面规范。
    色度子采样以更结构化的方式指定。SkCodec 和 SkImageGenerator 不再假设 3 个平面和
    8 位平面值。旧 API 已弃用。
    https://review.skia.org/309658
    https://review.skia.org/312886
    https://review.skia.org/314276
    https://review.skia.org/316837
    https://review.skia.org/317097

  * 为 GrVkImageInfo 结构体添加了 VkImageUsageFlags。

* * *

里程碑 86
------------

  * 从 SkRuntimeEffect 移除了对 'in' 变量的支持。API 现在专门将输入称为 'uniforms'。
    https://review.skia.org/309050

  * 添加了 SkImageGeneratorNDK 和 SkEncodeImageWithNDK，用于使用 Android 的 NDK API
    进行解码和编码。
    https://review.skia.org/308185
    https://review.skia.org/308800

  * SkImage：移除了 DecodeToRaster、DecodeToTexture。
    https://review.skia.org/306331

  * 添加 GrContext API 以更新压缩后端纹理。
    https://review.skia.org/302265

  * 将 GrMipMapped 重命名为 GrMipmapped 以与新 API 保持一致。
    同时将 GrBackendTexture::hasMipMaps() 重命名为 GrBackendTexture::hasMipmaps()。
    https://review.skia.org/304576
    https://review.skia.org/304598

  * 添加选项，允许客户端在等待调用后拥有信号量的所有权。
    https://review.skia.org/301216

  * 移除过时的 GrFlushFlags。
    https://review.skia.org/298818

  * 为 SkSurface、SkImage 和 GrContext 添加默认 flush() 调用。这些调用执行基本的刷新而不提交。
    如果您已有几个版本未更新 Skia，且代码中仍有期望执行刷新并提交的 flush() 调用，
    您应将所有这些调用更新为先前添加的 flushAndSubmit() 调用。
    https://review.skia.org/299141

  * 为 Direct3D 后端启用 BackendSemaphores。
    https://review.skia.org/298752

  * 添加了 SkImage:asyncRescaleAndReadPixels 和 SkImage::asyncRescaleAndReadPixelsYUV420。
    https://review.skia.org/299281

  * Ganesh 正在从用 GrDirectContext/GrRecordingContext 对来替代 GrContext。
    GrDirectContext 可以_直接_访问 GPU，与旧的 GrContext 非常相似。GrRecordingContext
    是功能较弱的上下文，缺乏 GPU 访问权限，但在 DDL 录制期间提供类似上下文的工具。
    SkSurfaces 和 SkCanvas 现在只返回 GrRecordingContexts。需要 GPU 访问的上下文功能的客户端
    可以通过 GrRecordingContext::asDirectContext 检查可用的录制上下文是否实际上是直接上下文。

  * 将 SkString 中的 #define 值替换为等价的 constexpr。
    http://review.skia.org/306160

* * *

里程碑 85
------------

  * 添加了 GrContext::oomed()，用于报告 Skia 是否遇到了 Open GL [ES] 的 GL_OUT_OF_MEMORY
    错误或 Vulkan 的 VK_ERROR_OUT_OF_*_MEMORY 错误。
    https://review.skia.org/298216

  * 在 SkSurface::flush 上添加选项，可传入 GrBackendSurfaceMutableState，
    我们将在刷新结束时将 GPU 后端 Surface 设置为该状态。
    https://review.skia.org/295567

  * 添加 GrContext 函数以在后端 Surface 上设置可变状态。目前仅用于设置 Vulkan VkImage
    布局和队列族。
    https://review.skia.org/293844

  * 接受 GrBackendTexture 或 GrBackendRenderTarget 的 SkSurface 工厂现在在失败时始终调用
    释放过程（如果提供了的话）。SkSurface::replaceBackendTexture 也在失败时调用释放过程。
    https://review.skia.org/293762

  * SkSurface::asyncRescaleAndReadPixels 和 SkSurface::asyncRescaleAndReadPixelsYUV420
    现在需要显式调用 GrContext submit 以确保回调在有限时间内被调用。
    https://review.skia.org/292840

  * 为 GrVkImageInfo 添加 VkSharingMode 字段。
    https://review.skia.org/293559

  * 将 SkBitmapRegionDecoder 移至 client_utils/android。

  * SkCanvas.clear 和 SkCanvas.drawColor 现在除了接受 SkColor 外还接受 SkColor4f。

  * 移除 SkSurface::MakeFromBackendTextureAsRenderTarget。
    此工厂的存在是为了解决 Chrome 命令缓冲区中 GL_TEXTURE_RECTANGLE 的相关问题。
    这些问题已被解决。请改用 SkSurface::MakeFromBackendTexture 或
    SkSurface::MakeFromBackendRenderTarget。
    https://review.skia.org/292719

  * 为 GrFlushInfo 添加 submittedProc 回调，当刷新调用中的工作提交到 GPU 时将被调用。
    这对于了解随刷新发送的信号量何时已提交并可以等待特别有用。
    https://review.skia.org/291078

  * 现在需要调用 GrContext submit 才能将 GPU 工作发送到实际的 GPU。刷新调用只是生成准备好
    提交的 3D API 特定对象（例如命令缓冲区）。对于 GL 后端，刷新仍会将命令发送到驱动程序。
    但是，客户端仍应假设必须调用 submit，这是调用同步对象所需的任何 glFlush 的地方。
    GrContext、SkSurface 和 SkImage 上有 flushAndSubmit() 函数，其行为与先前的 flush() 函数相同。
    这将刷新工作并立即调用 submit。
    https://review.skia.org/289033

  * 移除 GrContext 和 SkSurface 上已弃用版本的 flush 调用。
    https://review.skia.org/2290540

  * SkCanvas::drawVertices 和 drawPatch 现在支持在没有显式纹理坐标的情况下映射 SkShader。
    如果未提供纹理坐标，将直接使用局部位置（顶点位置或 Patch 三次贝塞尔位置）来采样 SkShader。
    https://review.skia.org/290130

* * *

里程碑 84
------------

  * 在 GrContext 上添加 updateBackendTexture API，用于将新数据上传到 GrBackendTexture。
    https://review.skia.org/288909

  * 为 SkSurface 添加 GrContext 获取器。
    https://review.skia.org/289479

  * 弃用 GrContext 和 SkSurface 的 flush() 调用，并用 flushAndSubmit() 替代。
    这仅影响不带参数的默认 flush 调用。
    https://review.skia.org/289478

  * GrContext::createBackendTexture 中初始化纹理的函数不再保证所有数据已上传且 GPU 已完成
    对纹理的处理。相反，客户端可以假设上传工作已提交到 GPU，并且必须等待该工作完成后才能
    删除纹理。这可以通过客户端自己的同步机制来完成，或者通过在创建调用中传入一个完成过程
    来实现，该过程将在安全删除纹理时被调用（至少就创建期间完成的工作而言）。
    https://review.skia.org/286517

  * 移除未使用的 SkMaskFilter 辅助方法：combine、compose。
    注意：shadermaskfilter 可能在下一步被移除（clipShader 应能替代）。

  * 恢复 SkCanvas::kPreserveLCDText_SaveLayerFlag 以指示 saveLayer() 将保留 LCD 文本。
    图层中的所有文本必须绘制在不透明背景上以确保正确渲染。

  * 添加新目录 client_utils/，用于存放仅针对单个客户端的代码，应视为与 Skia 主体分离。
    将 SkFrontBufferedStream 移至子目录 android/。

  * SkBitmap 和 SkPixmap 的 erase() 方法现在对其颜色参数的处理与 Skia 的其余部分保持一致，
    所有 SkColors 和任何未标记的 SkColor4fs 被解释为 sRGB，而不是位图颜色空间中的颜色。
    SkPixmap::erase(SkColor4f) 现在接受一个 SkColorSpace，因此如果您想要旧的行为，
    可以传递 pixmap.colorSpace()。

  * SkCamera.h 和 SkMatrix44.h 已弃用。
    如果您需要 3D 变换，请使用 SkM44。

  * 将 Dilate 和 Erode 图像滤镜的半径参数从 int 改为 SkScalar。虽然图像滤镜本身是按离散像素
    定义的，但用户提供的半径会经过 CTM 映射，因此使用 int 会强制过早离散化。
    经过 CTM 映射后，半径现在会四舍五入为像素值。
    https://review.skia.org/281731
    https://review.skia.org/282636

  * 更新了 GrContext 和 SkSurface flush 调用关于信号量的约定。明确了调用者有责任在 flush 调用后
    删除所有已初始化的信号量，无论我们是否能够提交它们。此外，如果部分信号量创建失败，
    允许 Skia 仅提交请求的信号量的子集。
    https://review.skia.org/282265


  * SkCanvas::drawVertices 现在将始终填充顶点指定的三角形。此前，没有颜色且没有
    （纹理坐标或着色器）的顶点会以线框模式绘制。
    https://review.skia.org/282043

* * *

里程碑 83
------------

  * 从 SkShaders::[Blend, Lerp] 中移除 localmatrix 选项。

  * 填充 Direct3D 后端纹理和后端渲染目标的参数。

  * SkImage::makeTextureImage() 接受一个可选的 SkBudgeted 参数。

  * 使非 GL 的 GPU 后端构建更加健壮。
    https://review.skia.org/277456

  * MoltenVK 支持已移除。请改用 Metal 后端。
    https://review.skia.org/277612

* * *

里程碑 82
------------

  * 从 SkDevice 中移除了 drawBitmap 及相关函数；SkCanvas 上所有公开的 drawBitmap 函数会自动
    将位图封装为 SkImage 并调用等效的 drawImage 函数。
    绘制可变的 SkBitmaps 现在将产生强制复制。请切换为直接使用 SkImage，
    或在绘制前将位图标记为不可变。

  * 从 SkVertices 中移除了"volatile"标志。所有 SkVertices 对象都被假定为
    volatile（先前的默认行为）。

  * 从 SkCanvas 中移除了特殊的旧版位图函数（drawBitmapLattice、drawBitmapNine）；
    特殊的 SkImage 函数仍然存在。

  * 使得可以选择性地打开/关闭各个编码器/解码器，
    使用 skia_use_(libpng/libjpeg_turbo/libwebp)(decode/encode)。

  * 从公开 API 中移除了 GrGpuResource、GrSurface 和 GrTexture。这些本不应是公开的，
    我们现在可以将它们移至 src 目录。同时从 SkImage.h 中移除了 getTexture 函数。

  * 从 SkVertices 中移除了 Bones。

  * 在 GrContextOptions 中添加了一个字段，用于控制在分配纹理等的 GL 调用之后是否检查 GL 错误。
    它还控制着色器编译成功和程序链接成功的检查。

  * 将 SkDeferredDisplayList.h 正式纳入公开 API（即移至 include/core）。
    还为 SkDeferredDisplayList 添加了 ProgramIterator，允许客户端预编译 DDL 所需的部分着色器。

  * 为 SkSurfaceCharacterization 添加了两个新的辅助方法：createBackendFormat 和 createFBO0。
    这使得客户端更容易创建与现有 Surface 特征仅有少许差异的新 Surface 特征。

  * 移除了 SkTMax 和 SkTMin。
  * 移除了 SkTClamp 和 SkClampMax。
  * 移除了 SkScalarClampMax 和 SkScalarPin。
  * 移除了 SkMax32 和 SkMin32。
  * 移除了 SkMaxScalar 和 SkMinScalar。

  * SkColorSetA 现在会在结果未使用时发出警告。

  * 将 SkColorSpace 为 null 的 SkImageInfo 传递给 SkCodec::getPixels() 及相关调用时，
    被视为请求在解码时不进行颜色校正。

  * 添加新 API，用于在创建带标签的 PDF 时向文档结构节点添加属性。

  * 从 SkCreateTypefaceFromCTFont 中移除 CGFontRef 参数。
    使用 CTFontManagerCreateFontDescriptorFromData 代替 CGFontCreateWithDataProvider
    来创建 CTFonts，以避免内存使用问题。

  * 添加了 SkCodec:: 和 SkAndroidCodec::getICCProfile，用于报告编码图像的原生 ICC 配置文件，
    即使它无法映射到 SkColorSpace。

  * SkSurface::ReplaceBackendTexture 接受 ContentChangeMode 作为参数，
    允许调用者指定是否保留当前内容的副本。

  * 强制执行 SkCanvas::saveLayer 中的现有文档，即它会忽略恢复 SkPaint 上的任何遮罩滤镜。
    图层的"覆盖范围"定义不明确，遮罩应通过预裁剪或使用 SaveLayerRec 的辅助裁剪遮罩图像来处理。

* * *

里程碑 81
------------

  * 添加了对 GL_NV_fence 扩展的支持。

  * 使 SkImageInfo::validRowBytes 要求 rowBytes 按像素对齐。这使 SkBitmap 在拒绝未对齐的
    rowBytes 时与光栅 SkSurfaces 的行为一致。

  * 添加了 SkImage::MakeRasterFromCompressed 入口点。同时更新了
    SkImage::MakeFromCompressed，当 GPU 不支持指定的压缩类型时会解压缩压缩图像数据
    （即 macOS Metal 不支持 BC1_RGB8_UNORM，因此此类压缩图像在该平台上始终会被解压缩）。

  * 添加了对 BC1 RGBA 压缩纹理的支持。

  * 为 SkImage::makeRasterImage 添加了 CachingHint。

  * 添加了 SkAnimatedImage::getCurrentFrame()。

  * 添加了从 MTKView 创建 SkSurface 的支持，支持延迟获取 MTLDrawable。
    入口点：SkSurface::MakeFromMTKView

  * 移除了 SkIRect::EmptyIRect()。请改用 SkIRect::MakeEmpty()。
    https://review.skia.org/262382/

  * 将 SkRuntimeEffect 移至公开 API。这是自定义 SkSL 着色器和颜色滤镜的新（实验性）接口。

  * 添加了 BC1 压缩格式支持。Metal 和 Vulkan 似乎仅在桌面设备上支持 BC 格式。

  * 添加了后端纹理创建 API 的压缩格式支持。
    新增以下入口点：
    GrContext::compressedBackendFormat
    GrContext::createCompressedBackendTexture
    后者有多个变体，支持颜色初始化和压缩纹理数据初始化。

  * 添加了 SkMatrix::MakeTrans(SkIVector)。
    https://review.skia.org/259804

* * *

里程碑 80
------------

  * 对于 Vulkan 后端，我们现在要求 VkDevice、Queue 和 Instance 的生命周期超过 GrContext
    的销毁或放弃。此外，所有通过 GrContext::createBackendTexture 调用创建的 GrBackendTextures
    必须在销毁或放弃 GrContext 之前删除。
    https://review.skia.org/257921

  * 移除了 SkSize& SkSize::operator=(const SkISize&)。
    https://review.skia.org/257880

  * SkISize 的 width() 和 height() 现在为 constexpr。
    https://review.skia.org/257680

  * 添加了 SkMatrix::MakeTrans(SkVector) 和 SkRect::makeOffset(SkVector)。
    https://review.skia.org/255782

  * 添加了 SkImageInfo::MakeA8(SkISize) 并为 SkImageInfo::MakeN32Premul(SkISize)
    添加了可选的颜色空间参数。

  * 为 SkAnimatedImage 添加了 dimensions() 和 getFrameCount()。
    https://review.skia.org/253542

  * 从 SkColorSpace 中移除了 toXYZD50 的 SkMatrix44 版本。将 transferFn、invTransferFn
    和 gamutTransformTo 函数切换为使用 skcms 类型。
    https://review.skia.org/252596

  * 从 SkColorMatrix 中移除了旋转和 YUV 支持。
    https://review.skia.org/252188

  * 添加了 kBT2020_SkYUVColorSpace。这是 BT.2020 的 YCbCr 转换（非恒定亮度）。
    https://review.skia.org/252160

  * 移除旧的异步读取像素 API。
    https://review.skia.org/251198

  * 暴露 SkBlendModeCoeff 和 SkBlendMode_AsCoeff，用于 Porter-Duff 混合模式。
    https://review.skia.org/252600

* * *

里程碑 79
------------

  * SkTextBlob::Iter 用于发现每个 Run 中的字形索引和字体。
    https://skia-review.googlesource.com/246296

  * 为 SkColorSpace 添加了对 PQ 和 HLG 传输函数的支持。
    https://skia-review.googlesource.com/c/skia/+/249000

  * 在 GrContext 上添加了新 API ComputeImageSize。这替代了旧的静态辅助方法
    ComputeTextureSize。
    https://skia-review.googlesource.com/c/skia/+/247337

  * SkSurface 异步缩放并读取 API 的新版本，允许客户端延长结果数据的生命周期。旧版本已弃用。
    https://review.skia.org/245457

  * 添加 SkColorInfo。它是无尺寸的 SkImageInfo。
    https://review.skia.org/245261

  * 为 GrContext 添加了基于 SkPixmap 的 createBackendTexture 方法。这允许客户端创建
    Skia/Ganesh 不知道/不追踪的后端资源（使用纹理数据初始化）。
    https://review.skia.org/244676

  * 为 SkColorFilter::filterColor4f() 添加显式的源和目标颜色空间参数。
    https://review.skia.org/244882

  * 移除 Vulkan/Metal float32 RGBA 纹理支持。
    https://review.skia.org/244881

  * 添加 SkSurface::MakeFromCAMetalLayer。
    https://review.skia.org/242563

  * 添加了 kAlpha_F16_SkColorType、kRG_F16_SkColorType 和 kRGBA_16161616_SkColorType。
    这旨在帮助支持 HDR YUV 用例（例如 P010 和 P016）。因此，
    添加的重点是允许创建 SkPixmaps 和 SkImages 而不是 SkSurfaces
    （即谁会想渲染到这些格式？）
    https://review.skia.org/241357

  * 开始将嵌套的 SkPath 类型（例如 Direction、Verb）上移到 SkPathTypes.h 的根级别。
    https://review.skia.org/241079

  * 从公开 API 中移除 isRectContour 和 isNestedFillRects。
    https://review.skia.org/241078

  * 添加了 kRG_88_SkColorType。这旨在帮助支持 YUV 用例（例如 NV12）。
    因此，添加的重点是允许创建 SkPixmaps 和 SkImages 而不是 SkSurfaces
    （即谁会想渲染到 RG？）
    https://review.skia.org/239930
    https://review.skia.org/235797

  * 通过 GrContextOptions::fRuntimeProgramCacheSize 使程序/管线缓存的大小可配置。
    https://review.skia.org/239756

  * 添加了 kAlpha_16_SkColorType 和 kRG_1616_SkColorType。这旨在帮助支持 HDR YUV
    用例（例如 P010 和 P016）。因此，添加的重点是允许创建 SkPixmaps 和 SkImages 而不是
    SkSurfaces（即谁会想渲染到这些格式？）
    https://review.skia.org/239930

  * 添加 GrContext::precompileShader 以允许预先编译先前缓存的着色器。
    https://review.skia.org/239438

* * *

里程碑 78
------------

  * SkDrawLooper 不再在 SkPaint 或 SkCanvas 中受支持。
    https://review.skia.org/230579
    https://review.skia.org/231736

  * SkPath::Iter::next() 现在忽略其 consumDegenerates 布尔值。这些参数将很快被完全移除。
    https://review.skia.org/235104

  * SkImage：新工厂方法：DecodeToRaster、DecodeToTexture。
    https://review.skia.org/234476

  * SkImageFilter API 重构开始：
    - 在 include/effects/SkImageFilters 中提供新的工厂 API
    - 统一枚举类型以使用 SkTileMode 和 SkColorChannel
    - 隐藏滤镜实现类
    - 隐藏 SkImageFilter 上先前公开但仅供内部使用的函数
    https://review.skia.org/230198
    https://review.skia.org/230876
    https://review.skia.org/231256

  * SkColorFilters::HSLAMatrix - 在 HSLA 空间中操作的新矩阵颜色滤镜。
    https://review.skia.org/231736

  * 修改 GrBackendFormat 的 getter 以不返回内部指针。为 GL 格式使用枚举类。
    https://review.skia.org/233160

  * 在定义了 SK_ENABLE_DUMP_GPU 时暴露 GrContext::dump()。
    https://review.skia.org/233557

  * Vulkan 后端现在支持 I420 Vulkan 图像的 YCbCr 采样器（不由外部图像支持的情况下）。
    https://review.skia.org/233776

  * 添加 SkCodec::SelectionPolicy，用于区分解码容器格式（如 HEIF）中的静态图像或图像序列。
    https://review.skia.org/232839

  * SkImage::makeTextureImage 和 SkImage::MakeCrossContextFromPixmap 不再接受
    SkColorSpace 参数。该参数未被使用。
    https://review.skia.org/234579
    https://review.skia.org/234912

  * SkImage::reinterpretColorSpace - 在新的颜色空间中重新解释图像内容。
    https://review.skia.org/234328

  * 移除了 SkImage::MakeCrossContextFromEncoded。
    https://review.skia.org/234912

  * 为 Metal 添加 GrFence、GrSemaphore 和 GrBackendSemaphore 支持。
    https://review.skia.org/233416

  * SkMallocPixelRef：从 API 中移除 MakeDirect 和 MakeWithProc。
    https://review.skia.org/234660

  * 移除 SkRect::join() 和 intersect() 的 4 参数变体，以及 intersect() 的 noemptycheck 变体。
    https://review.skia.org/235832
    https://review.skia.org/237142

  * 移除未使用的 sk_sp 比较运算符。
    https://review.skia.org/236942

  * 为 SkiaRenderer 的 experimental_DrawEdgeAAQuad 添加 SkColor4f 变体。
    https://review.skia.org/237492

  * 弃用 Ganesh 的 maxCount 资源缓存限制。
    这已经很长时间不再相关。

  * 将 GrContextOptions 的 fDisallowGLSLBinaryCaching 更改为 fShaderCacheStrategy，
    并允许缓存 SkSL。
    https://review.skia.org/238856

  * 使用 GL_QCOM_TILED_RENDERING 显式丢弃模板缓冲区。

  * 添加了 RELEASE_NOTES.txt 文件。
    https://review.skia.org/229760

  * 实现了 OpenGL 曲面细分的内部支持。
