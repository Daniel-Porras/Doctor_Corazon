// ============================================================================
//      ADS1293 SPI + WIFI UDP – COLA ENTRE DRDY Y WIFI (PAQUETES GRANDES)
//        (Anti-double-read on DRDYB + ALAB state sent via WiFi UDP)
// ============================================================================

#include <stdio.h>
#include <string.h>
#include <errno.h>

#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include "driver/uart.h"
#include "esp_timer.h"
#include "ads1293_regs.h"

// WiFi / TCP-IP
#include "nvs_flash.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "lwip/sockets.h"
#include "lwip/netdb.h"
#include "lwip/inet.h"

// ============================================================================
//                             DEFINICIONES
// ============================================================================

#define OFFSTET_CHANELS   6075000  // para centrar en 0 las señales

// --------------------- PINES ESP32 → ADS1293 -------------------------
#define MOSI_GPIO      23
#define MISO_GPIO      19
#define SCLK_GPIO      18
#define CS_GPIO         5
#define DRDYB_GPIO     27
#define ALAB_GPIO      26

// --------------------- WIFI / UDP CONFIG -----------------------------

#define WIFI_SSID      "DrCorazon"
#define WIFI_PASS      "123456789"

// IP de tu PC en la misma red
#define UDP_DEST_IP    "10.243.226.10"
#define UDP_DEST_PORT  5005

// Bits para el event group de WiFi
#define WIFI_CONNECTED_BIT BIT0

// Parámetros de empaquetado UDP (conservadores)
#define UDP_PACKET_MAX_LEN       1200   // máx bytes por datagrama
#define MAX_SAMPLES_PER_PACKET   20     // nº de muestras por paquete

static const char *TAG = "ADS1293";

// Handle global para SPI
static spi_device_handle_t spi_device_handle = NULL;

// Task para procesar DRDYB
static TaskHandle_t drdy_task_handle = NULL;

// Contador de muestras
static uint32_t sample_count = 0;

// Flag atómico para evitar doble notificación/lectura
static volatile unsigned char drdy_busy = 0;

// Event group para WiFi
static EventGroupHandle_t s_wifi_event_group;

// Socket UDP y dirección de destino
static int udp_sock = -1;
static struct sockaddr_in dest_addr;

// ============================================================================
//               ESTRUCTURA DE MUESTRA + COLA ENTRE DRDY Y WIFI
// ============================================================================

typedef struct {
    int32_t ch1;
    int32_t ch2;
    int32_t ch3;
    int     alab;
} ecg_sample_t;

// Cola grande para dar “pulmón” al sistema
static QueueHandle_t ecg_queue = NULL;

// ============================================================================
//                           WIFI + UDP FUNCTIONS
// ============================================================================

static void udp_init(void)
{
    if (udp_sock != -1) {
        close(udp_sock);
    }

    udp_sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_IP);
    if (udp_sock < 0) {
        ESP_LOGE(TAG, "Unable to create UDP socket: errno %d", errno);
        udp_sock = -1;
        return;
    }

    dest_addr.sin_addr.s_addr = inet_addr(UDP_DEST_IP);
    dest_addr.sin_family = AF_INET;
    dest_addr.sin_port = htons(UDP_DEST_PORT);

    ESP_LOGI(TAG, "UDP socket ready to %s:%d", UDP_DEST_IP, UDP_DEST_PORT);
}

static void wifi_event_handler(void *arg,
                               esp_event_base_t event_base,
                               int32_t event_id,
                               void *event_data)
{
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } 
    else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        ESP_LOGW(TAG, "WiFi disconnected, retrying...");
        esp_wifi_connect();
        xEventGroupClearBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
    } 
    else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
        ESP_LOGI(TAG, "Got IP:" IPSTR, IP2STR(&event->ip_info.ip));
        xEventGroupSetBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
        // Una vez conectado, preparamos el socket UDP
        udp_init();
    }
}

static void wifi_init_sta(void)
{
    s_wifi_event_group = xEventGroupCreate();

    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    ESP_ERROR_CHECK(esp_event_handler_register(
        WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(
        IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL));

    wifi_config_t wifi_config = {
        .sta = {
            .ssid = WIFI_SSID,
            .password = WIFI_PASS,
            .threshold.authmode = WIFI_AUTH_WPA2_PSK,
        },
    };

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_LOGI(TAG, "WiFi init STA finished.");

    // Esperar hasta estar conectado antes de seguir
    EventBits_t bits = xEventGroupWaitBits(s_wifi_event_group,
                                           WIFI_CONNECTED_BIT,
                                           pdFALSE,
                                           pdFALSE,
                                           portMAX_DELAY);
    if (bits & WIFI_CONNECTED_BIT) {
        ESP_LOGI(TAG, "WiFi connected, ready to send UDP");
    } else {
        ESP_LOGE(TAG, "WiFi connection failed");
    }
}

// ============================================================================
//                                 UTILIDADES
// ============================================================================

// Convierte tres bytes (MSB, mid, LSB) en un entero SIGNADO de 24 bits
static int32_t reconstructSigned24bit(uint8_t h, uint8_t m, uint8_t l)
{
    int32_t v = ((int32_t)h << 16) | ((int32_t)m << 8) | l;

    if (v & 0x800000)
        v |= 0xFF000000;

    return v;
}

static void init_alab_pin(void)
{
    gpio_config_t io = {
        .pin_bit_mask = (1ULL << ALAB_GPIO),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE
    };

    gpio_config(&io);
    ESP_LOGI(TAG, "ALAB pin configured (GPIO %d)", ALAB_GPIO);
}

// ============================================================================
//                               SPI FUNCTIONS
// ============================================================================

static esp_err_t init_spi(void)
{
    ESP_LOGI(TAG, "Initializing SPI bus...");

    spi_bus_config_t buscfg = {
        .mosi_io_num = MOSI_GPIO,
        .miso_io_num = MISO_GPIO,
        .sclk_io_num = SCLK_GPIO,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 64
    };

    spi_device_interface_config_t devcfg = {
        .mode = 0,                       // ADS1293 usa SPI MODE 0
        .clock_speed_hz = 2000000,       // 2 MHz (conservador)
        .spics_io_num = CS_GPIO,
        .queue_size = 4,
        .flags = 0,
        .pre_cb = NULL,
        .post_cb = NULL
    };

    ESP_ERROR_CHECK(spi_bus_initialize(SPI2_HOST, &buscfg, SPI_DMA_CH_AUTO));
    ESP_ERROR_CHECK(spi_bus_add_device(SPI2_HOST, &devcfg, &spi_device_handle));

    ESP_LOGI(TAG, "SPI initialized OK (SPI2_HOST, 2 MHz, Mode 0)");
    return ESP_OK;
}

// Escritura simple de registro (2 bytes)
static void spi_write(uint8_t reg, uint8_t value)
{
    uint8_t tx[2] = {
        reg & 0x7F,    // bit7 = 0 → escritura
        value
    };

    spi_transaction_t t = {
        .length = 16,           // 16 bits = 2 bytes
        .tx_buffer = tx,
        .rx_buffer = NULL
    };

    esp_err_t ret = spi_device_polling_transmit(spi_device_handle, &t);
    if (ret != ESP_OK)
        ESP_LOGE(TAG, "WRITE REG 0x%02X FAILED (%s)", reg, esp_err_to_name(ret));

    vTaskDelay(pdMS_TO_TICKS(1)); // Pequeño delay para estabilidad
}

// Lectura de 1 byte (register read)
static uint8_t spi_read_byte(uint8_t reg)
{
    uint8_t tx[2] = { (uint8_t)(0x80 | reg), 0x00 };
    uint8_t rx[2] = {0};

    spi_transaction_t t = {
        .length = 16,
        .tx_buffer = tx,
        .rx_buffer = rx
    };

    esp_err_t ret = spi_device_polling_transmit(spi_device_handle, &t);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "SPI read byte failed reg=0x%02X (%s)", reg, esp_err_to_name(ret));
        return 0xFF;
    }
    return rx[1];
}

// Lectura streaming
static esp_err_t spi_read_stream(uint8_t reg, uint8_t *rx, size_t len)
{
    uint8_t tx[16] = {0};
    size_t tx_len = len + 1;
    if (tx_len > sizeof(tx)) tx_len = sizeof(tx);
    tx[0] = (uint8_t)(0x80 | reg);  // comando de lectura (bit 7 = 1)

    spi_transaction_t t;
    memset(&t, 0, sizeof(t));
    t.length = (int)((tx_len) * 8);
    t.tx_buffer = tx;
    t.rx_buffer = rx;

    esp_err_t ret = spi_device_polling_transmit(spi_device_handle, &t);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Stream read failed: %s", esp_err_to_name(ret));
    }
    return ret;
}

// ============================================================================
//                          TAREA ENVÍO WIFI (COLA → UDP)
// ============================================================================

static void wifi_tx_task(void *arg)
{
    ecg_sample_t s;

    // Buffer para acumular varias muestras en un solo paquete UDP
    char   packet_buf[UDP_PACKET_MAX_LEN];
    size_t packet_len = 0;
    int    samples_in_packet = 0;

    ESP_LOGI(TAG, "wifi_tx_task started, waiting for samples...");

    while (1) {
        // Esperar hasta 10 ms por una muestra
        if (xQueueReceive(ecg_queue, &s, pdMS_TO_TICKS(10)) == pdTRUE) {

            // Construir la línea de texto de UNA muestra
            char line[64];
            int line_len = snprintf(line, sizeof(line),
                                    "%ld %ld %ld %d\n",
                                    (long)s.ch1, (long)s.ch2, (long)s.ch3, s.alab);
            if (line_len <= 0) {
                continue;
            }

            // Si no cabe esta línea en el paquete actual, enviar el paquete previo
            if (packet_len + (size_t)line_len > sizeof(packet_buf)) {
                if (samples_in_packet > 0 && udp_sock >= 0) {
                    int err = sendto(udp_sock, packet_buf, packet_len, 0,
                                     (struct sockaddr *)&dest_addr,
                                     sizeof(dest_addr));
                    if (err < 0) {
                        int e = errno;
                        if (e == ENOMEM) {
                            ESP_LOGW(TAG, "Error sending UDP: ENOMEM (errno 12) on full packet");
                        } else {
                            ESP_LOGW(TAG, "Error sending UDP: errno %d on full packet", e);
                        }
                    }
                }
                // Reiniciar paquete
                packet_len = 0;
                samples_in_packet = 0;
            }

            // Añadir la línea al paquete
            memcpy(packet_buf + packet_len, line, line_len);
            packet_len       += (size_t)line_len;
            samples_in_packet += 1;

            // Si ya tenemos suficientes muestras en el paquete, lo enviamos
            if (samples_in_packet >= MAX_SAMPLES_PER_PACKET) {
                if (udp_sock >= 0) {
                    int err = sendto(udp_sock, packet_buf, packet_len, 0,
                                     (struct sockaddr *)&dest_addr,
                                     sizeof(dest_addr));
                    if (err < 0) {
                        int e = errno;
                        if (e == ENOMEM) {
                            ESP_LOGW(TAG, "Error sending UDP: ENOMEM (errno 12) on max-samples packet");
                            vTaskDelay(pdMS_TO_TICKS(1));  // pequeña pausa
                        } else {
                            ESP_LOGW(TAG, "Error sending UDP: errno %d on max-samples packet", e);
                        }
                    }
                }
                // Reiniciar paquete
                packet_len = 0;
                samples_in_packet = 0;
            }
        } else {
            // Timeout de 10 ms sin muestras nuevas:
            // si hay datos pendientes en el paquete, enviamos un paquete parcial
            if (samples_in_packet > 0 && udp_sock >= 0) {
                int err = sendto(udp_sock, packet_buf, packet_len, 0,
                                 (struct sockaddr *)&dest_addr,
                                 sizeof(dest_addr));
                if (err < 0) {
                    int e = errno;
                    if (e == ENOMEM) {
                        ESP_LOGW(TAG, "Error sending UDP: ENOMEM (errno 12) on flush packet");
                        vTaskDelay(pdMS_TO_TICKS(1));
                    } else {
                        ESP_LOGW(TAG, "Error sending UDP: errno %d on flush packet", e);
                    }
                }
                // Reiniciar paquete
                packet_len = 0;
                samples_in_packet = 0;
            }
        }
    }
}

// ============================================================================
//                                 DRDYB TASK
// ============================================================================

// Esta tarea espera notificaciones desde la ISR y manda muestras a la cola
static void drdy_task(void *arg)
{
    uint8_t raw[16] = {0};    // rx buffer: [0] = echo del comando, [1..] = datos
    int32_t ch1, ch2, ch3;

    ESP_LOGI(TAG, "DRDY task started, waiting for interrupts...");

    while (1)
    {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);

        esp_err_t ret = spi_read_stream(DATA_LOOP_REG, raw, 9);
        if (ret != ESP_OK) {
            ESP_LOGW(TAG, "Failed to read data stream");
            __atomic_clear(&drdy_busy, __ATOMIC_RELEASE);
            continue;
        }
        
        uint8_t err_status = spi_read_byte(ERROR_STATUS_REG);
        (void)err_status; // por ahora no lo usamos

        ch1 = reconstructSigned24bit(raw[1], raw[2], raw[3]) - OFFSTET_CHANELS;
        ch2 = reconstructSigned24bit(raw[4], raw[5], raw[6]) - OFFSTET_CHANELS;
        ch3 = reconstructSigned24bit(raw[7], raw[8], raw[9]) - OFFSTET_CHANELS;

        int alab_state = gpio_get_level(ALAB_GPIO);

        sample_count++;

        // Enviar la muestra a la cola (no bloquea si está llena)
        if (ecg_queue != NULL) {
            ecg_sample_t s = {
                .ch1  = ch1,
                .ch2  = ch2,
                .ch3  = ch3,
                .alab = alab_state
            };

            BaseType_t ok = xQueueSend(ecg_queue, &s, 0);
            if (ok != pdTRUE) {
                // Si quieres monitorizar drops:
                // ESP_LOGW(TAG, "ECG queue full, dropping sample");
            }
        }

        __atomic_clear(&drdy_busy, __ATOMIC_RELEASE);
    }
}

// ============================================================================
//                                 INTERRUPCIÓN DRDYB
// ============================================================================

static void IRAM_ATTR drdy_isr(void *arg)
{
    BaseType_t high = pdFALSE;
    if (!__atomic_test_and_set(&drdy_busy, __ATOMIC_ACQUIRE)) {
        vTaskNotifyGiveFromISR(drdy_task_handle, &high);
        if (high == pdTRUE) {
            portYIELD_FROM_ISR();
        }
    }
}

static void init_drdy_interrupt(void)
{
    ESP_LOGI(TAG, "Configuring DRDYB interrupt on GPIO%d...", DRDYB_GPIO);

    gpio_config_t io = {
        .pin_bit_mask = (1ULL << DRDYB_GPIO),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_NEGEDGE
    };

    gpio_config(&io);

    gpio_install_isr_service(ESP_INTR_FLAG_IRAM);
    gpio_isr_handler_add((gpio_num_t)DRDYB_GPIO, drdy_isr, NULL);

    ESP_LOGI(TAG, "DRDYB interrupt enabled (NEGEDGE trigger)");
}

// ============================================================================
//                               CONFIG ADS1293
// ============================================================================

static esp_err_t ads1293_init(void)
{
    ESP_LOGI(TAG, "Configuring ADS1293 for 3-lead ECG...");

    spi_write(CONFIG_REG, 0x00);
    vTaskDelay(pdMS_TO_TICKS(10));

    // Configuración estándar TI (tu configuración)
    spi_write(FLEX_CH1_CN_REG, 0x11);
    spi_write(FLEX_CH2_CN_REG, 0x19);
    spi_write(FLEX_CH3_CN_REG, 0x1C);
    spi_write(CMDET_EN_REG,     0x0F);
    spi_write(RLD_CN_REG,       0x05);
    spi_write(OSC_CN_REG,       0x04);

    spi_write(R2_RATE_REG,       0x02);
    spi_write(R3_RATE_CH1_REG,   0x02);
    spi_write(R3_RATE_CH2_REG,   0x02);
    spi_write(R3_RATE_CH3_REG,   0x02);

    spi_write(DRDYB_SRC_REG, 0x10);
    spi_write(CH_CNFG_REG,   0x70);

    vTaskDelay(pdMS_TO_TICKS(50));

    ESP_LOGI(TAG, "✓ ADS1293 configured (streaming mode enabled)");
    return ESP_OK;
}

static esp_err_t ads1293_check_errors(void)
{
    ESP_LOGI(TAG, "Checking ADS1293 error registers...");

    uint8_t err_lod     = spi_read_byte(ERROR_LOD_REG);
    uint8_t err_status  = spi_read_byte(ERROR_STATUS_REG);
    uint8_t err_range1  = spi_read_byte(ERROR_RANGE1_REG);
    uint8_t err_range2  = spi_read_byte(ERROR_RANGE2_REG);
    uint8_t err_range3  = spi_read_byte(ERROR_RANGE3_REG);
    uint8_t err_sync    = spi_read_byte(ERROR_SYNC_REG);
    uint8_t err_misc    = spi_read_byte(ERROR_MISC_REG);

    ESP_LOGI(TAG, "ERROR_LOD (0x18)     = 0x%02X", err_lod);
    ESP_LOGI(TAG, "ERROR_STATUS (0x19)  = 0x%02X", err_status);
    ESP_LOGI(TAG, "ERROR_RANGE1 (0x1A)  = 0x%02X", err_range1);
    ESP_LOGI(TAG, "ERROR_RANGE2 (0x1B)  = 0x%02X", err_range2);
    ESP_LOGI(TAG, "ERROR_RANGE3 (0x1C)  = 0x%02X", err_range3);
    ESP_LOGI(TAG, "ERROR_SYNC (0x1D)    = 0x%02X", err_sync);
    ESP_LOGI(TAG, "ERROR_MISC (0x1E)    = 0x%02X", err_misc);

    bool has_errors = false;

    if (err_lod != 0) {
        ESP_LOGW(TAG, "⚠ Lead-Off detected (check electrode connections)");
        has_errors = true;
    }

    if (err_range1 | err_range2 | err_range3) {
        ESP_LOGW(TAG, "⚠ Out-of-range detected");
        has_errors = true;
    }

    if (err_sync != 0) {
        ESP_LOGW(TAG, "⚠ Sync error (possible noise or clock issue)");
        has_errors = true;
    }

    if (err_status != 0) {
        ESP_LOGE(TAG, "⛔ General error: ERROR_STATUS = 0x%02X", err_status);
        return ESP_FAIL;
    }

    if (!has_errors) {
        ESP_LOGI(TAG, "✓ No critical errors detected");
    }

    return ESP_OK;
}

// ============================================================================
//                                   MAIN
// ============================================================================

void app_main(void)
{
    // Opcional: subir baud de la consola UART0 (solo para logs)
    ESP_ERROR_CHECK(uart_set_baudrate(UART_NUM_0, 921600));

    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "  ADS1293 SPI + WiFi UDP (with ALAB)");
    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "");

    // 0. Inicializar NVS (requerido por WiFi)
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    // 1. WiFi STA + UDP
    wifi_init_sta();   // bloquea hasta estar conectado y prepara el socket UDP

    // 2. Inicializar SPI
    if (init_spi() != ESP_OK) {
        ESP_LOGE(TAG, "SPI init failed!");
        return;
    }

    // 3. Inicializar ALAB GPIO
    init_alab_pin();

    vTaskDelay(pdMS_TO_TICKS(100));

    // 4. Configurar ADS1293
    if (ads1293_init() != ESP_OK) {
        ESP_LOGE(TAG, "Configuration failed!");
        return;
    }

    // 5. Verificar errores (opcional)
    ads1293_check_errors();

    // 6. Crear cola para muestras (capacidad grande: 1024)
    ecg_queue = xQueueCreate(1024, sizeof(ecg_sample_t));
    if (ecg_queue == NULL) {
        ESP_LOGE(TAG, "Failed to create ECG queue");
        return;
    }

    // 7. Crear tarea de envío WiFi
    xTaskCreate(wifi_tx_task, "wifi_tx_task", 4096, NULL, 8, NULL);

    // 8. Crear task para procesar DRDY (prioridad un poco mayor)
    xTaskCreate(drdy_task, "drdy_task", 4096, NULL, 10, &drdy_task_handle);

    // 9. Configurar interrupción DRDYB
    init_drdy_interrupt();

    // 10. Esperar un momento antes de iniciar
    ESP_LOGI(TAG, "");
    ESP_LOGI(TAG, "Starting acquisition in 2 seconds...");
    ESP_LOGI(TAG, "UDP format (multiple lines per packet): CH1 CH2 CH3 ALAB");
    vTaskDelay(pdMS_TO_TICKS(2000));

    // 11. Iniciar conversiones
    spi_write(CONFIG_REG, 0x01);

    ESP_LOGI(TAG, "✓ System running - sending UDP packets via wifi_tx_task!");
    ESP_LOGI(TAG, "");
}
