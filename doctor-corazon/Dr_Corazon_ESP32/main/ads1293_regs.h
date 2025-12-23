#ifndef ADS1293_REGS_H
#define ADS1293_REGS_H

// Operation Mode Registers
#define CONFIG_REG                  0x00    // Main Configuration

// Input Channel Selection Registers
#define FLEX_CH1_CN_REG            0x01    // Flex Routing Switch Control for Channel 1
#define FLEX_CH2_CN_REG            0x02    // Flex Routing Switch Control for Channel 2
#define FLEX_CH3_CN_REG            0x03    // Flex Routing Switch Control for Channel 3
#define FLEX_PACE_CN_REG           0x04    // Flex Routing Switch Control for Pace Channel
#define FLEX_VBAT_CN_REG           0x05    // Flex Routing Switch for Battery Monitoring

// Lead-off Detect Control Registers
#define LOD_CN_REG                 0x06    // Lead-Off Detect Control
#define LOD_EN_REG                 0x07    // Lead-Off Detect Enable
#define LOD_CURRENT_REG            0x08    // Lead-Off Detect Current
#define LOD_AC_CN_REG              0x09    // AC Lead-Off Detect Control

// Common-Mode Detection and Right-Leg Drive Feedback Control Registers
#define CMDET_EN_REG               0x0A    // Common-Mode Detect Enable
#define CMDET_CN_REG               0x0B    // Common-Mode Detect Control
#define RLD_CN_REG                 0x0C    // Right-Leg Drive Control

// Wilson Control Registers
#define WILSON_EN1_REG             0x0D    // Wilson Reference Input one Selection
#define WILSON_EN2_REG             0x0E    // Wilson Reference Input two Selection
#define WILSON_EN3_REG             0x0F    // Wilson Reference Input three Selection
#define WILSON_CN_REG              0x10    // Wilson Reference Control

// Reference Registers
#define REF_CN_REG                 0x11    // Internal Reference Voltage Control

// OSC Control Registers
#define OSC_CN_REG                 0x12    // Clock Source and Output Clock Control

// AFE Control Registers
#define AFE_RES_REG                0x13    // Analog Front End Frequency and Resolution
#define AFE_SHDN_CN_REG            0x14    // Analog Front End Shutdown Control
#define AFE_FAULT_CN_REG           0x15    // Analog Front End Fault Detection Control
// Reservado 0x16
#define AFE_PACE_CN_REG            0x17    // Analog Pace Channel Output Routing Control

// Error Status Registers (Read Only)
#define ERROR_LOD_REG              0x18    // Lead-Off Detect Error Status
#define ERROR_STATUS_REG           0x19    // Other Error Status
#define ERROR_RANGE1_REG           0x1A    // Channel 1 AFE Out-of-Range Status
#define ERROR_RANGE2_REG           0x1B    // Channel 2 AFE Out-of-Range Status
#define ERROR_RANGE3_REG           0x1C    // Channel 3 AFE Out-of-Range Status
#define ERROR_SYNC_REG             0x1D    // Synchronization Error
#define ERROR_MISC_REG             0x1E    // Miscellaneous Errors

// Digital Registers
#define DIGO_STRENGTH_REG          0x1F    // Digital Output Drive Strength
#define R2_RATE_REG                0x21    // R2 Decimation Rate
#define R3_RATE_CH1_REG            0x22    // R3 Decimation Rate for Channel 1
#define R3_RATE_CH2_REG            0x23    // R3 Decimation Rate for Channel 2
#define R3_RATE_CH3_REG            0x24    // R3 Decimation Rate for Channel 3
#define R1_RATE_REG                0x25    // R1 Decimation Rate
#define DIS_EFILTER_REG            0x26    // ECG Filter Disable
#define DRDYB_SRC_REG              0x27    // Data Ready Pin Source
#define SYNCB_CN_REG               0x28    // SYNCB In/Out Pin Control
#define MASK_DRDYB_REG             0x29    // Optional Mask Control for DRDYB Output
#define MASK_ERR_REG               0x2A    // Mask Error on ALARMB Pin
// Reservados 0x2B, 0x2C, 0x2D
#define ALARM_FILTER_REG           0x2E    // Digital Filter for Analog Alarm Signals
#define CH_CNFG_REG                0x2F    // Configure Channel for Loop Read Back Mode

// Pace and ECG Data Read Back Registers (Read Only)
#define DATA_STATUS_REG            0x30    // ECG and Pace Data Ready Status
#define DATA_CH1_PACE_H_REG        0x31    // Channel 1 Pace Data High Byte
#define DATA_CH1_PACE_L_REG        0x32    // Channel 1 Pace Data Low Byte
#define DATA_CH2_PACE_H_REG        0x33    // Channel 2 Pace Data High Byte
#define DATA_CH2_PACE_L_REG        0x34    // Channel 2 Pace Data Low Byte
#define DATA_CH3_PACE_H_REG        0x35    // Channel 3 Pace Data High Byte
#define DATA_CH3_PACE_L_REG        0x36    // Channel 3 Pace Data Low Byte
#define DATA_CH1_ECG_H_REG         0x37    // Channel 1 ECG Data High Byte
#define DATA_CH1_ECG_M_REG         0x38    // Channel 1 ECG Data Middle Byte
#define DATA_CH1_ECG_L_REG         0x39    // Channel 1 ECG Data Low Byte
#define DATA_CH2_ECG_H_REG         0x3A    // Channel 2 ECG Data High Byte
#define DATA_CH2_ECG_M_REG         0x3B    // Channel 2 ECG Data Middle Byte
#define DATA_CH2_ECG_L_REG         0x3C    // Channel 2 ECG Data Low Byte
#define DATA_CH3_ECG_H_REG         0x3D    // Channel 3 ECG Data High Byte
#define DATA_CH3_ECG_M_REG         0x3E    // Channel 3 ECG Data Middle Byte
#define DATA_CH3_ECG_L_REG         0x3F    // Channel 3 ECG Data Low Byte

#define REVID_REG                  0x40    // Revision ID
#define DATA_LOOP_REG              0x50    // Loop Read-Back Address

// Bits importantes del registro CONFIG (0x00)
#define START_CON_BIT              0x01    // Start conversion
#define STANDBY_BIT                0x02    // Standby mode
#define PWR_DOWN_BIT               0x04    // Power-down mode

// Bits para el registro OSC_CN (0x12)
#define EN_CLKOUT_BIT              0x01    // Enable CLK pin output driver
#define SHDN_OSC_BIT               0x02    // Select clock source
#define STRTCLK_BIT                0x04    // Start the clock


// MQTT Root CA Certificate
const char mqtt_root_ca[] =
"-----BEGIN CERTIFICATE-----\n"
"MIIFazCCA1OgAwIBAgIRAIIQz7DSQONZRGPgu2OCiwAwDQYJKoZIhvcNAQELBQAw\n"
"TzELMAkGA1UEBhMCVVMxKTAnBgNVBAoTIEludGVybmV0IFNlY3VyaXR5IFJlc2Vh\n"
"cmNoIEdyb3VwMRUwEwYDVQQDEwxJU1JHIFJvb3QgWDEwHhcNMTUwNjA0MTEwNDM4\n"
"WhcNMzUwNjA0MTEwNDM4WjBPMQswCQYDVQQGEwJVUzEpMCcGA1UEChMgSW50ZXJu\n"
"ZXQgU2VjdXJpdHkgUmVzZWFyY2ggR3JvdXAxFTATBgNVBAMTDElTUkcgUm9vdCBY\n"
"MTCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBAK3oJHP0FDfzm54rVygc\n"
"h77ct984kIxuPOZXoHj3dcKi/vVqbvYATyjb3miGbESTtrFj/RQSa78f0uoxmyF+\n"
"0TM8ukj13Xnfs7j/EvEhmkvBioZxaUpmZmyPfjxwv60pIgbz5MDmgK7iS4+3mX6U\n"
"A5/TR5d8mUgjU+g4rk8Kb4Mu0UlXjIB0ttov0DiNewNwIRt18jA8+o+u3dpjq+sW\n"
"T8KOEUt+zwvo/7V3LvSye0rgTBIlDHCNAymg4VMk7BPZ7hm/ELNKjD+Jo2FR3qyH\n"
"B5T0Y3HsLuJvW5iB4YlcNHlsdu87kGJ55tukmi8mxdAQ4Q7e2RCOFvu396j3x+UC\n"
"B5iPNgiV5+I3lg02dZ77DnKxHZu8A/lJBdiB3QW0KtZB6awBdpUKD9jf1b0SHzUv\n"
"KBds0pjBqAlkd25HN7rOrFleaJ1/ctaJxQZBKT5ZPt0m9STJEadao0xAH0ahmbWn\n"
"OlFuhjuefXKnEgV4We0+UXgVCwOPjdAvBbI+e0ocS3MFEvzG6uBQE3xDk3SzynTn\n"
"jh8BCNAw1FtxNrQHusEwMFxIt4I7mKZ9YIqioymCzLq9gwQbooMDQaHWBfEbwrbw\n"
"qHyGO0aoSCqI3Haadr8faqU9GY/rOPNk3sgrDQoo//fb4hVC1CLQJ13hef4Y53CI\n"
"rU7m2Ys6xt0nUW7/vGT1M0NPAgMBAAGjQjBAMA4GA1UdDwEB/wQEAwIBBjAPBgNV\n"
"HRMBAf8EBTADAQH/MB0GA1UdDgQWBBR5tFnme7bl5AFzgAiIyBpY9umbbjANBgkq\n"
"hkiG9w0BAQsFAAOCAgEAVR9YqbyyqFDQDLHYGmkgJykIrGF1XIpu+ILlaS/V9lZL\n"
"ubhzEFnTIZd+50xx+7LSYK05qAvqFyFWhfFQDlnrzuBZ6brJFe+GnY+EgPbk6ZGQ\n"
"3BebYhtF8GaV0nxvwuo77x/Py9auJ/GpsMiu/X1+mvoiBOv/2X/qkSsisRcOj/KK\n"
"NFtY2PwByVS5uCbMiogziUwthDyC3+6WVwW6LLv3xLfHTjuCvjHIInNzktHCgKQ5\n"
"ORAzI4JMPJ+GslWYHb4phowim57iaztXOoJwTdwJx4nLCgdNbOhdjsnvzqvHu7Ur\n"
"TkXWStAmzOVyyghqpZXjFaH3pO3JLF+l+/+sKAIuvtd7u+Nxe5AW0wdeRlN8NwdC\n"
"jNPElpzVmbUq4JUagEiuTDkHzsxHpFKVK7q4+63SM1N95R1NbdWhscdCb+ZAJzVc\n"
"oyi3B43njTOQ5yOf+1CceWxG1bQVs5ZufpsMljq4Ui0/1lvh+wjChP4kqKOJ2qxq\n"
"4RgqsahDYVvTH9w7jXbyLeiNdd8XM2w9U/t7y0Ff/9yi0GE44Za4rF2LN9d11TPA\n"
"mRGunUHBcnWEvgJBQl9nJEiU0Zsnvgc/ubhPgXRR4Xq37Z0j4r7g1SgEEzwxA57d\n"
"emyPxgcYxn/eR44/KJ4EBs+lVDR3veyJm+kXQ99b21/+jh5Xos1AnX5iItreGCc=\n"
"-----END CERTIFICATE-----\n";

#endif // ADS1293_REGS_H