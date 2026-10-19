#define _GNU_SOURCE
#include <dlfcn.h>
#include <xf86drm.h>
#include <xf86drmMode.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <time.h>
#include <errno.h>
#include <sys/stat.h>
#include <stdlib.h>

#ifndef STATX_MNT_ID
#define STATX_MNT_ID 0x00001000U
#endif
#ifndef STATX_MNT_ID_UNIQUE
#define STATX_MNT_ID_UNIQUE 0x00004000U
#endif

#define DRM_MODE_OBJECT_PLANE 0xeeeeeeee

struct udev_device;

static drmModePlanePtr (*orig_drmModeGetPlane)(int fd, uint32_t plane_id) = NULL;
static ssize_t (*orig_read)(int fd, void *buf, size_t count) = NULL;
static int (*orig_drmGetCap)(int fd, uint64_t capability, uint64_t *value) = NULL;
static drmModeObjectPropertiesPtr (*orig_drmModeObjectGetProperties)(int fd, uint32_t object_id, uint32_t object_type) = NULL;
static const char *(*orig_udev_device_get_property_value)(struct udev_device *udev_device, const char *property) = NULL;
static int (*orig_faccessat)(int dirfd, const char *pathname, int mode, int flags) = NULL;
static int (*orig_statx)(int dirfd, const char *pathname, int flags, unsigned int mask, struct statx *statxbuf) = NULL;

int statx(int dirfd, const char *pathname, int flags, unsigned int mask, struct statx *statxbuf) {
    if (!orig_statx) {
        orig_statx = dlsym(RTLD_NEXT, "statx");
    }
    int ret = orig_statx(dirfd, pathname, flags, mask, statxbuf);
    if (ret == 0 && statxbuf) {
        if (mask & (STATX_MNT_ID | STATX_MNT_ID_UNIQUE)) {
            statxbuf->stx_mask |= (mask & (STATX_MNT_ID | STATX_MNT_ID_UNIQUE));
            statxbuf->stx_mnt_id = 1;
        }
    }
    return ret;
}

static void ensure_display_active(int fd) {
    int bfd = open("/sys/class/backlight/panel0-backlight/brightness", O_WRONLY);
    if (bfd >= 0) {
        write(bfd, "1023\n", 5);
        close(bfd);
    }
    // Connector 29: DSI-1
    // Property 2: DPMS -> 0 (On)
    // Property 37: autorefresh -> 1 (Auto-push frames in command mode)
    drmModeObjectSetProperty(fd, 29, DRM_MODE_OBJECT_CONNECTOR, 2, 0);
    drmModeObjectSetProperty(fd, 29, DRM_MODE_OBJECT_CONNECTOR, 37, 1);
}

int faccessat(int dirfd, const char *pathname, int mode, int flags) {
    if (!orig_faccessat) {
        orig_faccessat = dlsym(RTLD_NEXT, "faccessat");
    }

    if (flags != 0) {
        int ret = orig_faccessat(dirfd, pathname, mode, flags);
        if (ret == -1 && errno == EINVAL) {
            if (flags & AT_SYMLINK_NOFOLLOW) {
                struct stat st;
                return fstatat(dirfd, pathname, &st, AT_SYMLINK_NOFOLLOW);
            }
            return orig_faccessat(dirfd, pathname, mode, 0);
        }
        return ret;
    }
    return orig_faccessat(dirfd, pathname, mode, 0);
}

static const char *(*orig_udev_device_get_devnode)(struct udev_device *udev_device) = NULL;
static const char *(*orig_udev_device_get_sysname)(struct udev_device *udev_device) = NULL;

static void init_udev_ptrs(void) {
    if (!orig_udev_device_get_property_value)
        orig_udev_device_get_property_value = dlsym(RTLD_NEXT, "udev_device_get_property_value");
    if (!orig_udev_device_get_devnode)
        orig_udev_device_get_devnode = dlsym(RTLD_NEXT, "udev_device_get_devnode");
    if (!orig_udev_device_get_sysname)
        orig_udev_device_get_sysname = dlsym(RTLD_NEXT, "udev_device_get_sysname");

    if (!orig_udev_device_get_property_value || !orig_udev_device_get_devnode) {
        void *h = dlopen("libudev.so.1", RTLD_LAZY | RTLD_GLOBAL);
        if (h) {
            if (!orig_udev_device_get_property_value)
                orig_udev_device_get_property_value = dlsym(h, "udev_device_get_property_value");
            if (!orig_udev_device_get_devnode)
                orig_udev_device_get_devnode = dlsym(h, "udev_device_get_devnode");
            if (!orig_udev_device_get_sysname)
                orig_udev_device_get_sysname = dlsym(h, "udev_device_get_sysname");
        }
    }
}

const char *udev_device_get_property_value(struct udev_device *udev_device, const char *property) {
    init_udev_ptrs();
    if (!udev_device || !property)
        return NULL;

    if (strcmp(property, "ID_INPUT_TOUCHSCREEN") == 0 ||
        strcmp(property, "ID_INPUT") == 0 ||
        strcmp(property, "ID_INPUT_KEYBOARD") == 0 ||
        strcmp(property, "ID_SEAT") == 0 ||
        strcmp(property, "WL_OUTPUT") == 0) {

        const char *node = orig_udev_device_get_devnode ? orig_udev_device_get_devnode(udev_device) : NULL;
        const char *sys = orig_udev_device_get_sysname ? orig_udev_device_get_sysname(udev_device) : NULL;

        if ((node && strstr(node, "event2")) || (sys && strstr(sys, "event2"))) {
            if (strcmp(property, "ID_INPUT_TOUCHSCREEN") == 0) return "1";
            if (strcmp(property, "ID_INPUT") == 0) return "1";
            if (strcmp(property, "ID_INPUT_KEYBOARD") == 0) return "0";
            if (strcmp(property, "ID_SEAT") == 0) return "seat0";
            if (strcmp(property, "WL_OUTPUT") == 0) return "DSI-1";
        }
    }

    if (orig_udev_device_get_property_value)
        return orig_udev_device_get_property_value(udev_device, property);
    return NULL;
}

drmModeObjectPropertiesPtr drmModeObjectGetProperties(int fd, uint32_t object_id, uint32_t object_type) {
    if (!orig_drmModeObjectGetProperties)
        orig_drmModeObjectGetProperties = dlsym(RTLD_NEXT, "drmModeObjectGetProperties");
    drmModeObjectPropertiesPtr props = orig_drmModeObjectGetProperties(fd, object_id, object_type);
    if (props && object_type == DRM_MODE_OBJECT_PLANE) {
        // Promote Plane 77 to PRIMARY plane so Weston / Phoc has a primary plane to attach its desktop to
        if (object_id == 77) {
            for (uint32_t i = 0; i < props->count_props; i++) {
                if (props->props[i] == 7) { // prop_id 7 is "type"
                    props->prop_values[i] = 1; // DRM_PLANE_TYPE_PRIMARY
                    break;
                }
            }
        }
    }
    return props;
}

int drmGetCap(int fd, uint64_t capability, uint64_t *value) {
    if (capability == DRM_CAP_TIMESTAMP_MONOTONIC) {
        if (value) *value = 1;
        return 0;
    }
    if (!orig_drmGetCap) orig_drmGetCap = dlsym(RTLD_NEXT, "drmGetCap");
    return orig_drmGetCap(fd, capability, value);
}

ssize_t read(int fd, void *buf, size_t count) {
    if (!orig_read) orig_read = dlsym(RTLD_NEXT, "read");
    ssize_t ret = orig_read(fd, buf, count);
    if (count == 9 && ret == 8) {
        ((char *)buf)[8] = 0;
        return 9;
    }
    if (count >= sizeof(struct drm_event_vblank) && ret >= (ssize_t)sizeof(struct drm_event_vblank)) {
        struct drm_event *e = (struct drm_event *)buf;
        if (e->type == DRM_EVENT_VBLANK || e->type == DRM_EVENT_FLIP_COMPLETE) {
            struct drm_event_vblank *vbl = (struct drm_event_vblank *)buf;
            struct timespec now;
            clock_gettime(CLOCK_MONOTONIC, &now);
            vbl->tv_sec = (uint32_t)now.tv_sec;
            vbl->tv_usec = (uint32_t)(now.tv_nsec / 1000);
        }
    }
    return ret;
}

drmModePlanePtr drmModeGetPlane(int fd, uint32_t plane_id) {
    ensure_display_active(fd);

    if (!orig_drmModeGetPlane) {
        orig_drmModeGetPlane = dlsym(RTLD_NEXT, "drmModeGetPlane");
    }
    drmModePlanePtr p = orig_drmModeGetPlane(fd, plane_id);
    if (!p || !p->formats || p->count_formats <= 1) {
        return p;
    }

    uint32_t unique_count = 0;
    for (uint32_t i = 0; i < p->count_formats; i++) {
        uint32_t fmt = p->formats[i];
        int duplicate = 0;
        for (uint32_t j = 0; j < unique_count; j++) {
            if (p->formats[j] == fmt) {
                duplicate = 1;
                break;
            }
        }
        if (!duplicate) {
            p->formats[unique_count++] = fmt;
        }
    }
    p->count_formats = unique_count;
    return p;
}

#define EGL_EXTENSIONS 0x3055
static const char *(*orig_eglQueryString)(void *dpy, int name) = NULL;

const char *eglQueryString(void *dpy, int name) {
    if (!orig_eglQueryString) {
        orig_eglQueryString = dlsym(RTLD_NEXT, "eglQueryString");
    }
    const char *ret = orig_eglQueryString ? orig_eglQueryString(dpy, name) : NULL;
    if (name == EGL_EXTENSIONS && ret != NULL) {
        if (!strstr(ret, "EGL_EXT_image_dma_buf_import")) {
            static char buf[8192];
            snprintf(buf, sizeof(buf), "%s EGL_EXT_image_dma_buf_import", ret);
            return buf;
        }
    }
    return ret;
}

static void *(*orig_eglGetProcAddress)(const char *procname) = NULL;
void *eglGetProcAddress(const char *procname) {
    if (procname && strcmp(procname, "eglQueryString") == 0) {
        return (void *)eglQueryString;
    }
    if (!orig_eglGetProcAddress) {
        orig_eglGetProcAddress = dlsym(RTLD_NEXT, "eglGetProcAddress");
    }
    return orig_eglGetProcAddress ? orig_eglGetProcAddress(procname) : NULL;
}

static drmModeConnectorPtr (*orig_drmModeGetConnector)(int fd, uint32_t connector_id) = NULL;
static drmModeConnectorPtr (*orig_drmModeGetConnectorCurrent)(int fd, uint32_t connector_id) = NULL;

drmModeConnectorPtr drmModeGetConnector(int fd, uint32_t connector_id) {
    if (!orig_drmModeGetConnector) orig_drmModeGetConnector = dlsym(RTLD_NEXT, "drmModeGetConnector");
    drmModeConnectorPtr c = orig_drmModeGetConnector ? orig_drmModeGetConnector(fd, connector_id) : NULL;
    if (c && c->connector_type == DRM_MODE_CONNECTOR_VIRTUAL) {
        c->connection = DRM_MODE_DISCONNECTED;
    }
    return c;
}

drmModeConnectorPtr drmModeGetConnectorCurrent(int fd, uint32_t connector_id) {
    if (!orig_drmModeGetConnectorCurrent) orig_drmModeGetConnectorCurrent = dlsym(RTLD_NEXT, "drmModeGetConnectorCurrent");
    drmModeConnectorPtr c = orig_drmModeGetConnectorCurrent ? orig_drmModeGetConnectorCurrent(fd, connector_id) : NULL;
    if (c && c->connector_type == DRM_MODE_CONNECTOR_VIRTUAL) {
        c->connection = DRM_MODE_DISCONNECTED;
    }
    return c;
}

void *wlr_allocator_autocreate(void *backend, void *renderer) {
    int fd = open("/dev/dri/card0", O_RDWR | O_CLOEXEC);
    const char *ren = getenv("WLR_RENDERER");
    if (ren && strcmp(ren, "pixman") == 0) {
        void *(*p_dumb)(int) = dlsym(RTLD_DEFAULT, "wlr_drm_dumb_allocator_create");
        if (p_dumb) return p_dumb(fd);
    }
    void *(*p_gbm_alloc)(int) = dlsym(RTLD_DEFAULT, "wlr_gbm_allocator_create");
    if (!p_gbm_alloc) {
        return NULL;
    }
    return p_gbm_alloc(fd);
}

#include <link.h>
#include <sys/mman.h>

static int dl_cb_wlroots(struct dl_phdr_info *info, size_t size, void *data) {
    if (strstr(info->dlpi_name, "libwlroots")) {
        uintptr_t base = info->dlpi_addr;
        uintptr_t target1 = base + 0x792f8;
        uintptr_t target2 = base + 0x79300;
        uintptr_t page = target1 & ~4095;
        if (mprotect((void *)page, 4096, PROT_READ | PROT_WRITE | PROT_EXEC) == 0) {
            *(volatile uint32_t *)target1 = 0xd503201f; // nop
            *(volatile uint32_t *)target2 = 0xd503201f; // nop
            mprotect((void *)page, 4096, PROT_READ | PROT_EXEC);
            __builtin___clear_cache((char *)target1, (char *)target2 + 4);
        }

        uintptr_t target_vk1 = base + 0x53fec;
        uintptr_t page_vk1 = target_vk1 & ~4095;
        if (mprotect((void *)page_vk1, 4096, PROT_READ | PROT_WRITE | PROT_EXEC) == 0) {
            if (*(volatile uint32_t *)target_vk1 == 0x34001254) {
                *(volatile uint32_t *)target_vk1 = 0x140000b3; // b 0x542b8 (match Turnip Vulkan)
                fprintf(stderr, "[patch_wlroots] Successfully patched target_vk1 (0x53fec) to 0x140000b3!\n");
            }
            mprotect((void *)page_vk1, 4096, PROT_READ | PROT_EXEC);
            __builtin___clear_cache((char *)target_vk1, (char *)target_vk1 + 4);
        }

        uintptr_t target_vk = base + 0x54184;
        uintptr_t page_vk = target_vk & ~4095;
        if (mprotect((void *)page_vk, 4096, PROT_READ | PROT_WRITE | PROT_EXEC) == 0) {
            if (*(volatile uint32_t *)target_vk == 0x34000438) {
                *(volatile uint32_t *)target_vk = 0x1400004d; // b 0x542b8 (match Turnip Vulkan)
                fprintf(stderr, "[patch_wlroots] Successfully patched target_vk (0x54184) to 0x1400004d!\n");
            }
            mprotect((void *)page_vk, 4096, PROT_READ | PROT_EXEC);
            __builtin___clear_cache((char *)target_vk, (char *)target_vk + 4);
        }

        // Patch 55df0: DRM_FORMAT_MOD_INVALID support in find_modifier
        // Replaces cbz w3, 55e1c (0x34000163) with tbnz x1, #55, 0x28 (0xb7b80141) -> branches to ret with &modifiers[0]
        uintptr_t target_mod = base + 0x55df0;
        uintptr_t page_mod = target_mod & ~4095;
        if (mprotect((void *)page_mod, 4096, PROT_READ | PROT_WRITE | PROT_EXEC) == 0) {
            if (*(volatile uint32_t *)target_mod == 0x34000163) {
                *(volatile uint32_t *)target_mod = 0xb7b80141; // tbnz x1, #55, 0x28
                fprintf(stderr, "[patch_wlroots] Successfully patched target_mod (0x55df0) for DRM_FORMAT_MOD_INVALID!\n");
            }
            mprotect((void *)page_mod, 4096, PROT_READ | PROT_EXEC);
            __builtin___clear_cache((char *)target_mod, (char *)target_mod + 4);
        }

        // Patch 43c08 & 43bc8: Prevent abort in wlr_renderer_clear / wlr_renderer_end when r->rendering == 0
        uintptr_t target_clr = base + 0x43c08;
        uintptr_t page_clr = target_clr & ~4095;
        if (mprotect((void *)page_clr, 4096, PROT_READ | PROT_WRITE | PROT_EXEC) == 0) {
            *(volatile uint32_t *)target_clr = 0xd65f03c0; // ret
            *(volatile uint32_t *)(base + 0x43bc8) = 0xd65f03c0; // ret
            mprotect((void *)page_clr, 4096, PROT_READ | PROT_EXEC);
            __builtin___clear_cache((char *)target_clr, (char *)target_clr + 4);
            __builtin___clear_cache((char *)(base + 0x43bc8), (char *)(base + 0x43bc8) + 4);
            fprintf(stderr, "[patch_wlroots] Successfully bypassed assertions in wlr_renderer_clear/end!\n");
        }
    }
    return 0;
}

__attribute__((constructor))
static void patch_wlroots_init(void) {
    dl_iterate_phdr(dl_cb_wlroots, NULL);
}

int wlr_renderer_get_drm_fd(void *renderer) {
    int (*orig)(void *) = dlsym(RTLD_NEXT, "wlr_renderer_get_drm_fd");
    int fd = orig ? orig(renderer) : -1;
    if (fd < 0) {
        static int card0_fd = -1;
        if (card0_fd < 0) {
            card0_fd = open("/dev/dri/card0", O_RDWR | O_CLOEXEC);
        }
        return card0_fd;
    }
    return fd;
}

typedef struct VkBaseOutStructure {
    int sType;
    struct VkBaseOutStructure* pNext;
} VkBaseOutStructure;

typedef struct VkPhysicalDeviceProperties2 {
    int sType;
    void* pNext;
} VkPhysicalDeviceProperties2;

typedef struct VkPhysicalDeviceDrmPropertiesEXT {
    int sType;
    void* pNext;
    int hasPrimary;
    int hasRender;
    int64_t primaryMajor;
    int64_t primaryMinor;
    int64_t renderMajor;
    int64_t renderMinor;
} VkPhysicalDeviceDrmPropertiesEXT;

void vkGetPhysicalDeviceProperties2(void* physicalDevice, VkPhysicalDeviceProperties2* pProperties) {
    static void (*orig)(void*, void*) = NULL;
    if (!orig) orig = dlsym(RTLD_NEXT, "vkGetPhysicalDeviceProperties2");
    if (orig) orig(physicalDevice, pProperties);

    if (pProperties) {
        VkBaseOutStructure* cur = (VkBaseOutStructure*)pProperties->pNext;
        while (cur) {
            if (cur->sType == 1000353000) { // VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DRM_PROPERTIES_EXT
                VkPhysicalDeviceDrmPropertiesEXT* drm_props = (VkPhysicalDeviceDrmPropertiesEXT*)cur;
                drm_props->hasPrimary = 1;
                drm_props->hasRender = 0;
                drm_props->primaryMajor = 226;
                drm_props->primaryMinor = 0;
                fprintf(stderr, "[patch_wlroots] Injected card0 (226, 0) DRM properties into Vulkan physical device!\n");
            }
            cur = cur->pNext;
        }
    }
}

void vkGetPhysicalDeviceProperties2KHR(void* physicalDevice, VkPhysicalDeviceProperties2* pProperties) {
    vkGetPhysicalDeviceProperties2(physicalDevice, pProperties);
}

void* (*orig_vkGetInstanceProcAddr)(void* instance, const char* name) = NULL;
void* vkGetInstanceProcAddr(void* instance, const char* name) {
    if (name) {
        if (strcmp(name, "vkGetPhysicalDeviceProperties2") == 0 ||
            strcmp(name, "vkGetPhysicalDeviceProperties2KHR") == 0) {
            return (void*)vkGetPhysicalDeviceProperties2;
        }
    }
    if (!orig_vkGetInstanceProcAddr) orig_vkGetInstanceProcAddr = dlsym(RTLD_NEXT, "vkGetInstanceProcAddr");
    return orig_vkGetInstanceProcAddr ? orig_vkGetInstanceProcAddr(instance, name) : NULL;
}

void *wlr_linux_dmabuf_v1_create(void *display, uint32_t version, void *renderer) {
    if (version > 4) version = 4;
    static void *(*orig)(void *, uint32_t, void *) = NULL;
    if (!orig) orig = dlsym(RTLD_NEXT, "wlr_linux_dmabuf_v1_create");
    return orig ? orig(display, version, renderer) : NULL;
}

void *wlr_linux_dmabuf_v1_create_with_renderer(void *display, uint32_t version, void *renderer) {
    if (version > 4) version = 4;
    static void *(*orig)(void *, uint32_t, void *) = NULL;
    if (!orig) orig = dlsym(RTLD_NEXT, "wlr_linux_dmabuf_v1_create_with_renderer");
    return orig ? orig(display, version, renderer) : NULL;
}
