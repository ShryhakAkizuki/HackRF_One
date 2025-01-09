#include <stdio.h>
#include <libusb-1.0/libusb.h>

int main() {
    libusb_context *ctx = NULL;
    libusb_device **device_list = NULL;
    ssize_t device_count;
    int result;

    // Initialize libusb
    result = libusb_init(&ctx);
    if (result < 0) {
        fprintf(stderr, "Error initializing libusb: %s\n", libusb_error_name(result));
        return 1;
    }

    // Get a list of USB devices
    device_count = libusb_get_device_list(ctx, &device_list);
    if (device_count < 0) {
        fprintf(stderr, "Error getting device list: %s\n", libusb_error_name((int)device_count));
        libusb_exit(ctx);
        return 1;
    }

    printf("Found %zd USB devices:\n", device_count);

    // Iterate over the list and print device details
    for (ssize_t i = 0; i < device_count; i++) {
        libusb_device *device = device_list[i];
        struct libusb_device_descriptor desc;

        result = libusb_get_device_descriptor(device, &desc);
        if (result < 0) {
            fprintf(stderr, "Error getting device descriptor: %s\n", libusb_error_name(result));
            continue;
        }

        printf("Device %zd:\n", i + 1);
        printf("  Vendor ID: 0x%04x\n", desc.idVendor);
        printf("  Product ID: 0x%04x\n", desc.idProduct);
        printf("  Class: 0x%02x\n", desc.bDeviceClass);
        printf("  Subclass: 0x%02x\n", desc.bDeviceSubClass);
        printf("  Protocol: 0x%02x\n", desc.bDeviceProtocol);
    }

    // Free the device list
    libusb_free_device_list(device_list, 1);

    // Deinitialize libusb
    libusb_exit(ctx);

    return 0;
}