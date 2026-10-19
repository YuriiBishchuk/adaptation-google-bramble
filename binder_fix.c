typedef unsigned int uint32_t;
typedef unsigned long size_t;
typedef int int32_t;

__attribute__((visibility("default")))
int ABinderProcess_setThreadPoolMaxThreadCount(uint32_t numThreads) {
    return 1;
}

__attribute__((visibility("default")))
int32_t _ZN7android12ProcessState27setThreadPoolMaxThreadCountEm(void* self, size_t maxThreads) {
    return 0;
}
