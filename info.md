# Home Assistant Tuya IR Air Conditioner Integration

Tested with the following devices:

![image](https://github.com/EnzoD86/tuya-smart-ir-ac/assets/61162811/d887c8a1-9e66-4552-835e-bbe333482a85)

## Configuration

|Name|Type|Description|Required|
| ------------- | -------- | ------------------------------------ |---- |
| access_id     | `string` | Tuya access ID.                      | Yes |
| access_secret | `string` | Tuya access secret.                  | Yes |
| climate_id    | `string` | Air conditioner ID.                  | Yes |
| infrared_id   | `string` | Infrared ID.                         | Yes |
| name          | `string` | The name of the climate device.      | Yes |
| unique_id     | `string` | The unique id of the climate entity. | No  |
| temp_sensor   | `string` | Name of the temperature sensor.      | No  |
| min_temp      | `float`  | Minimum set point available.         | No  |
| max_temp      | `float`  | Maximum set point available.         | No  |
| temp_step     | `float`  | Step size for temperature set point. | No  |

### Example
```yaml
climate:
   - platform: tuya_smart_ir_ac
     access_id: ""
     access_secret: ""
     climate_id: ""
     infrared_id: ""
     name: "conditioner name"
     unique_id: conditioner_id
     temp_sensor: "sensor.temperature_name"
     min_temp: 18
     max_temp: 30
     temp_step: 1
```
