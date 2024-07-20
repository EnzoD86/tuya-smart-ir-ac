# Home Assistant Tuya IR Air Conditioner Integration

## Configuration

| Name                 | Type     | Description                          | Required | Default | Note                       |
| -------------------- | -------- | ------------------------------------ | -------- | ------- | -------------------------- |
| access_id            | `string` | Tuya access ID.                      | Yes      |         |                            |
| access_secret        | `string` | Tuya access secret.                  | Yes      |         |                            |
| climate_id           | `string` | Air conditioner ID.                  | Yes      |         |                            |
| infrared_id          | `string` | Infrared ID.                         | Yes      |         |                            |
| name                 | `string` | The name of the climate device.      | Yes      |         |                            |
| unique_id            | `string` | The unique id of the climate entity. | No       |         |                            |
| temperature_sensor   | `string` | Name of the temperature sensor.      | No       |         |                            |
| humidity_sensor      | `string` | Name of the humidity sensor.         | No       |         |                            |
| min_temp             | `float`  | Minimum set point available.         | No       | 7       | HA default values          |
| max_temp             | `float`  | Maximum set point available.         | No       | 35      | HA default values          |
| temp_step            | `float`  | Step size for temperature set point. | No       | 1       |                            |
| country              | `string` | Tuya country API: EU, US, IN, CN     | No       | EU      | Written in capital letters |


### Country/Data center API

| ID    | Data center |
| ----- | ----------- | 
| EU    | Europe      |
| US    | America     |
| IN    | India       |
| CN    | China       |

***It is important to write the country in all capital letters!!!**

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
     temperature_sensor: sensor.temperature_name
     humidity_sensor: sensor.humidity_name
     min_temp: 18
     max_temp: 30
     temp_step: 1
     country: "EU"
```
