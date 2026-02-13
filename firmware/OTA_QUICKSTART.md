# OTA Setup Quick Start

Fast reference for setting up OTA firmware updates with password protection.

## 5-Minute Setup

### 1. Create Secrets File

```bash
cd firmware
cp secrets.example.yaml secrets.yaml
```

### 2. Generate OTA Password

```bash
# Generate random password
python -c "import secrets; print(secrets.token_hex(16))"
```

### 3. Update secrets.yaml

```bash
# Add to secrets.yaml:
ota_password: "your_generated_password_here"
```

### 4. Restrict File Permissions

```bash
chmod 600 firmware/secrets.yaml
```

### 5. Compile Firmware

```bash
esphome compile firmware/voice-assistant.yaml
```

### 6. Flash to Device

```bash
# Initial flash via USB
esphome run firmware/voice-assistant.yaml
```

### 7. Deploy via OTA

```bash
# Next time, deploy over Wi-Fi
python scripts/ota_deploy.py \
  --device esp32.local \
  --binary .esphome/build/esp32-s3-box-3/.pioenvs/esp32-s3-box-3/firmware.bin \
  --password "your_password_here"
```

## Verification

### Check OTA is Running

```bash
# View device logs
esphome logs firmware/voice-assistant.yaml

# Look for: "OTA is running" message
```

### Verify Password Works

```bash
# Successful deployment output:
# ✅ Deployment successful!
```

## Common Issues

| Issue | Fix |
|-------|-----|
| Authentication failed | Check password matches secrets.yaml |
| Connection timeout | Verify device is on same network |
| File not found | Check binary path exists |

## Next Steps

- See [OTA_SECURITY.md](OTA_SECURITY.md) for advanced password management
- See [../scripts/OTA_DEPLOY_README.md](../scripts/OTA_DEPLOY_README.md) for batch deployments
- Check [voice-assistant.yaml](voice-assistant.yaml) for full configuration

## Security Reminders

✅ Always secure secrets.yaml with chmod 600
✅ Never commit secrets.yaml to Git
✅ Use strong, unique passwords
✅ Rotate passwords periodically
