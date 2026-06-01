# Makefile - Simplified build for verification
# This mimics what SCons would do based on the .scons files
#
# The SCons build system is the source of truth.
# This Makefile is generated from the SCons configuration for CI/test purposes.

CC = gcc
CFLAGS = -Wall -Werror -Wimplicit-function-declaration -std=c99
BUILD_DIR = build/libs

# Paths derived from SConscript files
CORE_COMMON_INC = -Icore/api/common -Icore/api/common/storage
EFS_INC = -Icore/storage/efs/inc
QMI_INC = -Icore/mproc/qmi/inc
OEM_INC = -Ioem/fibo_qmi/inc

.PHONY: all clean

all: build/oem_pd_img

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

# EFS module - sources determined by efs.scons
$(BUILD_DIR)/efs_core.o: core/storage/efs/src/efs_core.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) $(CORE_COMMON_INC) $(EFS_INC) -c $< -o $@

# QMI framework
$(BUILD_DIR)/qmi_csi_common.o: core/mproc/qmi/src/qmi_csi_common.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) $(CORE_COMMON_INC) $(QMI_INC) -c $< -o $@

# OEM module - include paths from fibo_qmi.scons
$(BUILD_DIR)/qmi_fibo_svc.o: oem/fibo_qmi/src/qmi_fibo_svc.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) $(CORE_COMMON_INC) $(QMI_INC) $(OEM_INC) -c $< -o $@

# Static libraries
$(BUILD_DIR)/libefs.a: $(BUILD_DIR)/efs_core.o
	ar rcs $@ $^

$(BUILD_DIR)/libqmi_framework.a: $(BUILD_DIR)/qmi_csi_common.o
	ar rcs $@ $^

$(BUILD_DIR)/libfibo_qmi_svc.a: $(BUILD_DIR)/qmi_fibo_svc.o
	ar rcs $@ $^

# Final link
build/oem_pd_img: $(BUILD_DIR)/libfibo_qmi_svc.a $(BUILD_DIR)/libqmi_framework.a $(BUILD_DIR)/libefs.a
	$(CC) -o $@ $(BUILD_DIR)/qmi_fibo_svc.o -L$(BUILD_DIR) -lqmi_framework -lefs

clean:
	rm -rf build/
