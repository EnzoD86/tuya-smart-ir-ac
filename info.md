# Home Assistant Tuya Smart IR Air Conditioner Integration

## Platform configuration (configuration.yaml)

| Name                 | Type     | Description                      | Required |
| -------------------- | -------- | -------------------------------- | -------- |
| access_id            | `string` | Tuya access ID.                  | Yes      |
| access_secret        | `string` | Tuya access secret.              | Yes      |
| country              | `string` | Tuya country API: EU, US, IN, CN | Yes      |


### Country/Data center API

| ID    | Data center |
| ----- | ----------- | 
| EU    | Europe      |
| US    | America     |
| IN    | India       |
| CN    | China       |

### Example

```yaml
tuya_smart_ir_ac:
  access_id: "tuya_access_id_example"
  access_secret: "tuya_access_secret_example"
  country: "EU"
```

# Debug
It is possible to activate debug mode by adding the following lines in your configuration.yaml file:

```yaml
logger:
  # Begging of lines to add
  logs:
    custom_components.tuya_smart_ir_ac: debug
  # End of lines to add
```
Home Assistant needs to be restarted after this change.
