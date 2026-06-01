idf_component_register(
    SRC_DIRS "." "drivers" "services" "core" "ui"
    INCLUDE_DIRS "." "drivers" "services" "core" "ui"
    REQUIRES lvgl esp_lcd freertos driver nvs_flash esp_wifi
)
