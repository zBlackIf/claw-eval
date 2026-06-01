/*
 * glamor_egl.c - EGL/DMA-BUF texture import for Glamor (X.org DDX)
 *
 * This file handles importing DMA-BUF file descriptors as OpenGL textures
 * for zero-copy YUV video display. Multiple import strategies are supported:
 *   - OES (GL_OES_EGL_image_external): hardware YUV->RGB in GPU
 *   - ZC_R8: manual plane import as R8/GR88 textures + shader conversion
 *   - CPU upload: fallback memcpy path
 */

#include "glamor_priv.h"
#include "glamor_egl.h"
#include <epoxy/gl.h>
#include <epoxy/egl.h>

#define GLAMOR_DMABUF_IMPORT_CPU_UPLOAD   0
#define GLAMOR_DMABUF_IMPORT_OES          1
#define GLAMOR_DMABUF_IMPORT_ZC_R8        2
#define GLAMOR_DMABUF_IMPORT_AFBC_DROP    3

#define SUNXI_YUV_AFBC_MOD_16x16  0x100
#define SUNXI_YUV_AFBC_MOD_32x8   0x200
#define DRM_FORMAT_MOD_INVALID     0xFFFFFFFF
#define PANFROST_STRIDE_ALIGN      64

#define DRM_FORMAT_NV12   0x3231564E
#define DRM_FORMAT_P010   0x30313050
#define DRM_FORMAT_R8     0x20203852
#define DRM_FORMAT_GR88   0x38385247
#define DRM_FORMAT_R16    0x20363152
#define DRM_FORMAT_GR1616 0x32335247

typedef int Bool;
#define TRUE 1
#define FALSE 0

/* Forward declarations of helper functions */
static Bool compute_yuv_plane_layout(int width, int height, int stride,
                                     uint32_t fourcc, off_t buf_size,
                                     int afbc, int is_10bit,
                                     int *n_planes, uint32_t *drm_fourcc,
                                     int pitches[3], int offsets[3]);

static Bool glamor_dmabuf_import_oes(void *display, int dma_fd,
                                     int width, int height, uint32_t drm_fourcc,
                                     int n_planes, int pitches[3], int offsets[3],
                                     uint64_t modifier, uint32_t *out_tex);

static Bool glamor_dmabuf_import_2plane(void *display, int dma_fd,
                                        int width, int height,
                                        int pitches[3], int offsets[3],
                                        uint32_t fmt_y, uint32_t fmt_uv,
                                        uint32_t *out_tex_y, uint32_t *out_tex_u);

static Bool glamor_dmabuf_import_3plane_r8(void *display, int dma_fd,
                                           int width, int height,
                                           int pitches[3], int offsets[3],
                                           uint32_t *out_tex_y, uint32_t *out_tex_u,
                                           uint32_t *out_tex_v);

/* Simulated epoxy extension check */
extern Bool epoxy_has_gl_extension(const char *ext);

/* Simulated GL functions */
extern const char *glGetString(unsigned int name);
#define GL_RENDERER 0x1F01
#define GL_VENDOR   0x1F00

/* Error reporting */
extern void ErrorF(const char *fmt, ...);
extern unsigned int eglGetError(void);

/* Screen private data accessors (simulated) */
typedef struct {
    void *display;
} glamor_egl_screen_private;

typedef struct {
    int dummy;
} glamor_screen_private;

static glamor_egl_screen_private *glamor_egl_get_screen_private(void *scrn) {
    static glamor_egl_screen_private priv = { .display = (void*)0x1 };
    return &priv;
}

static glamor_screen_private *glamor_get_screen_private(void *screen) {
    static glamor_screen_private priv = { 0 };
    return &priv;
}

static void glamor_make_current(glamor_screen_private *priv) {
    (void)priv;
}

static void *xf86ScreenToScrn(void *screen) {
    return screen;
}

/*
 * glamor_import_dmabuf_textures - Main entry point for DMA-BUF texture import
 *
 * Attempts multiple strategies in order:
 * 1. AFBC OES (for AFBC-compressed buffers)
 * 2. Non-AFBC OES (hardware YUV->RGB conversion)
 * 3. ZC_R8 (manual R8/GR88 plane import with shader conversion)
 * 4. CPU upload fallback
 *
 * Returns: GLAMOR_DMABUF_IMPORT_* status code
 */
int
glamor_import_dmabuf_textures(void *screen, int dma_fd,
                              int width, int height, int stride,
                              uint32_t fourcc, off_t buf_size,
                              int afbc, int is_10bit,
                              uint32_t *out_tex_y, uint32_t *out_tex_u, uint32_t *out_tex_v)
{
    void *scrn = xf86ScreenToScrn(screen);
    glamor_egl_screen_private *glamor_egl = glamor_egl_get_screen_private(scrn);
    glamor_screen_private *glamor_priv = glamor_get_screen_private(screen);
    int n_planes;
    uint32_t drm_fourcc;
    int pitches[3], offsets[3];

    *out_tex_y = 0;
    *out_tex_u = 0;
    *out_tex_v = 0;

    if (buf_size <= 0)
        return GLAMOR_DMABUF_IMPORT_CPU_UPLOAD;

    glamor_make_current(glamor_priv);

    /* Compute plane layout */
    if (!compute_yuv_plane_layout(width, height, stride, fourcc, buf_size,
                                  afbc, is_10bit,
                                  &n_planes, &drm_fourcc, pitches, offsets)) {
        return GLAMOR_DMABUF_IMPORT_CPU_UPLOAD;
    }

    if (afbc) {
        Bool has_oes = epoxy_has_gl_extension("GL_OES_EGL_image_external") ||
                       epoxy_has_gl_extension("GL_OES_EGL_image_external_essl3");

        if (has_oes) {
            if (glamor_dmabuf_import_oes(glamor_egl->display, dma_fd,
                               width, height, drm_fourcc,
                               n_planes, pitches, offsets,
                               SUNXI_YUV_AFBC_MOD_16x16, out_tex_y)) {
                static Bool logged = FALSE;
                if (!logged) {
                    ErrorF("glamor: AFBC 16x16 OES import OK %dx%d "
                           "fourcc=0x%x\n", width, height, drm_fourcc);
                    logged = TRUE;
                }
                return GLAMOR_DMABUF_IMPORT_OES;
            }
            if (glamor_dmabuf_import_oes(glamor_egl->display, dma_fd,
                               width, height, drm_fourcc,
                               n_planes, pitches, offsets,
                               SUNXI_YUV_AFBC_MOD_32x8, out_tex_y)) {
                static Bool logged = FALSE;
                if (!logged) {
                    ErrorF("glamor: AFBC 32x8 OES import OK %dx%d "
                           "fourcc=0x%x\n", width, height, drm_fourcc);
                    logged = TRUE;
                }
                return GLAMOR_DMABUF_IMPORT_OES;
            }
        }
        return GLAMOR_DMABUF_IMPORT_AFBC_DROP;
    }

    /* Non-AFBC OES import: let hardware do YUV->RGB conversion */
    if (epoxy_has_gl_extension("GL_OES_EGL_image_external") ||
        epoxy_has_gl_extension("GL_OES_EGL_image_external_essl3")) {

        if (glamor_dmabuf_import_oes(glamor_egl->display, dma_fd,
                           width, height, drm_fourcc,
                           n_planes, pitches, offsets,
                           DRM_FORMAT_MOD_INVALID, out_tex_y)) {
            return GLAMOR_DMABUF_IMPORT_OES;
        }

        ErrorF("glamor_import_dmabuf_textures: OES import failed "
               "(fourcc=0x%x) -- falling back to R8\n", drm_fourcc);
    }

    /* ZC_R8 path: manual plane import with shader-based YUV->RGB */
    if (n_planes == 2 && drm_fourcc == DRM_FORMAT_NV12) {
        if ((pitches[0] % PANFROST_STRIDE_ALIGN) != 0 ||
            (pitches[1] % PANFROST_STRIDE_ALIGN) != 0)
            return GLAMOR_DMABUF_IMPORT_CPU_UPLOAD;

        if (!glamor_dmabuf_import_2plane(glamor_egl->display, dma_fd,
                               width, height, pitches, offsets,
                               DRM_FORMAT_R8, DRM_FORMAT_GR88,
                               out_tex_y, out_tex_u)) {
            ErrorF("glamor_import_dmabuf_textures: NV12 R8+GR88 import failed\n");
            return GLAMOR_DMABUF_IMPORT_CPU_UPLOAD;
        }
        return GLAMOR_DMABUF_IMPORT_ZC_R8;

    } else if (n_planes == 2 && drm_fourcc == DRM_FORMAT_P010) {
        if ((pitches[0] % PANFROST_STRIDE_ALIGN) != 0 ||
            (pitches[1] % PANFROST_STRIDE_ALIGN) != 0)
            return GLAMOR_DMABUF_IMPORT_CPU_UPLOAD;

        if (!glamor_dmabuf_import_2plane(glamor_egl->display, dma_fd,
                               width, height, pitches, offsets,
                               DRM_FORMAT_R16, DRM_FORMAT_GR1616,
                               out_tex_y, out_tex_u)) {
            static Bool p010_logged = FALSE;
            if (!p010_logged) {
                ErrorF("glamor_import_dmabuf_textures: P010 R16+GR1616 import "
                       "failed (egl_err=0x%x)\n", eglGetError());
                p010_logged = TRUE;
            }
            return GLAMOR_DMABUF_IMPORT_CPU_UPLOAD;
        }
        return GLAMOR_DMABUF_IMPORT_ZC_R8;

    } else if (n_planes == 3) {
        if (!glamor_dmabuf_import_3plane_r8(glamor_egl->display, dma_fd,
                                  width, height, pitches, offsets,
                                  out_tex_y, out_tex_u, out_tex_v)) {
            ErrorF("glamor_import_dmabuf_textures: 3-plane R8 import failed\n");
            return GLAMOR_DMABUF_IMPORT_CPU_UPLOAD;
        }
        return GLAMOR_DMABUF_IMPORT_ZC_R8;
    }

    return GLAMOR_DMABUF_IMPORT_CPU_UPLOAD;
}
