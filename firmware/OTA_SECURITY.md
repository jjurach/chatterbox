# OTA Security & Password Management

This document describes the security configuration for Over-The-Air (OTA) firmware updates on Chatterbox devices.

## Overview

The OTA update mechanism is protected by a password-based authentication system. This prevents unauthorized firmware modifications and ensures only authorized deployments can update devices.

## Configuration

### Enable OTA Password Protection

The OTA endpoint is configured in `voice-assistant.yaml`:

```yaml
ota:
  - platform: esphome
    id: ota_esphome
    password: !secret ota_password
```

The password is loaded from `secrets.yaml` using ESPHome's `!secret` directive.

### Setup Instructions

1. **Create secrets file:**

   ```bash
   cp firmware/secrets.example.yaml firmware/secrets.yaml
   ```

2. **Generate strong password:**

   ```bash
   # Option 1: Using Python
   python -c "import secrets; print(secrets.token_hex(16))"

   # Option 2: Using OpenSSL
   openssl rand -hex 16

   # Option 3: Using /dev/urandom
   head -c 16 /dev/urandom | xxd -p
   ```

3. **Update secrets.yaml:**

   ```yaml
   ota_password: "your_generated_password_here"
   ```

4. **Compile and flash firmware:**

   ```bash
   esphome run firmware/voice-assistant.yaml
   ```

## Password Management Strategies

### Single Fleet Password (Recommended for Small Deployments)

Use one password for all devices in your fleet:

**Pros:**
- Simple management
- Easy batch deployments
- Suitable for development/testing

**Cons:**
- Larger security impact if password is compromised
- No device-level granularity

**Usage:**

```bash
# Deploy with global password
python scripts/ota_deploy.py \
  --binary firmware.bin \
  --batch devices.json \
  --password "fleet_password"
```

### Per-Device Passwords (Recommended for Production)

Use unique passwords for each device:

**Pros:**
- Isolates compromise impact
- Enables device-level auditing
- Better for production deployments

**Cons:**
- More complex management
- Requires device-specific configuration

**Setup:**

1. Generate unique passwords for each device:

   ```bash
   # Create password inventory
   cat > device_passwords.txt << EOF
   device1.local:$(python -c "import secrets; print(secrets.token_hex(16))")
   device2.local:$(python -c "import secrets; print(secrets.token_hex(16))")
   device3.local:$(python -c "import secrets; print(secrets.token_hex(16))")
   EOF
   ```

2. Update device configurations:

   ```bash
   # For device1
   # Edit secrets_device1.yaml:
   ota_password: "device1_specific_password"

   # Edit voice-assistant.yaml to include device-specific secrets:
   substitutions:
     device_name: device1

   # Then compile with device-specific secrets
   esphome run firmware/voice-assistant.yaml -s secrets_file=secrets_device1.yaml
   ```

3. Create batch file with per-device passwords:

   ```json
   [
     {
       "host": "device1.local",
       "password": "device1_specific_password"
     },
     {
       "host": "device2.local",
       "password": "device2_specific_password"
     },
     {
       "host": "device3.local",
       "password": "device3_specific_password"
     }
   ]
   ```

4. Deploy with batch file:

   ```bash
   python scripts/ota_deploy.py --binary firmware.bin --batch devices_with_passwords.json
   ```

### Environment-Based Passwords

Use different passwords for different environments:

**Configuration:**

```yaml
# development environment
ota_password: !secret ota_password_dev

# production environment
ota_password: !secret ota_password_prod
```

**Usage:**

```bash
# Development deployment
esphome run firmware/voice-assistant.yaml -s secrets_file=secrets_dev.yaml

# Production deployment
esphome run firmware/voice-assistant.yaml -s secrets_file=secrets_prod.yaml
```

## Security Best Practices

### Password Generation

✅ **DO:**
- Use cryptographically secure random generation
- Generate passwords with at least 128 bits of entropy (32 hex characters)
- Store generated passwords securely

❌ **DON'T:**
- Use dictionary words or predictable patterns
- Reuse passwords across unrelated systems
- Share passwords via insecure channels

```bash
# Secure generation methods
python -c "import secrets; print(secrets.token_hex(16))"  # 128-bit password
openssl rand -hex 32  # 256-bit password
```

### Storage & Protection

✅ **DO:**
- Store `secrets.yaml` securely with restricted file permissions
- Add `secrets.yaml` to `.gitignore` (NEVER commit to version control)
- Use separate secrets files per environment
- Backup secrets securely (encrypted storage)

❌ **DON'T:**
- Commit `secrets.yaml` to Git or any VCS
- Share password files via email or unencrypted channels
- Use same password across development and production
- Store passwords in plain text without access controls

### File Permissions

```bash
# Restrict secrets file to owner only
chmod 600 firmware/secrets.yaml

# Verify permissions
ls -l firmware/secrets.yaml
# Should show: -rw------- 1 user group ... secrets.yaml
```

### Version Control

```bash
# Add to .gitignore
echo "secrets.yaml" >> .gitignore

# Verify secrets aren't in Git
git status firmware/secrets.yaml
# Should not be tracked
```

## Deployment Workflow

### Development Workflow

```bash
# 1. Generate development password
DEV_PASS=$(python -c "import secrets; print(secrets.token_hex(16))")

# 2. Update secrets.yaml
echo "ota_password: \"$DEV_PASS\"" >> firmware/secrets.yaml

# 3. Compile firmware
esphome compile firmware/voice-assistant.yaml

# 4. Deploy to device
python scripts/ota_deploy.py \
  --device esp32-dev.local \
  --binary .esphome/build/.../firmware.bin \
  --password "$DEV_PASS"
```

### Production Deployment

```bash
# 1. Create batch file with unique passwords
# Edit devices_prod.json with device-specific passwords

# 2. Compile firmware (production environment)
esphome compile firmware/voice-assistant.yaml

# 3. Deploy to all devices
python scripts/ota_deploy.py \
  --binary .esphome/build/.../firmware.bin \
  --batch devices_prod.json
```

### Password Rotation

To rotate OTA passwords securely:

```bash
# 1. Generate new password
NEW_PASS=$(python -c "import secrets; print(secrets.token_hex(16))")

# 2. Update secrets.yaml
sed -i "s/ota_password: .*/ota_password: \"$NEW_PASS\"/" firmware/secrets.yaml

# 3. Compile new firmware with new password
esphome compile firmware/voice-assistant.yaml

# 4. Deploy with old password (devices still have it)
python scripts/ota_deploy.py \
  --binary firmware.bin \
  --batch devices.json \
  --password "$OLD_PASS"

# 5. Next deployments use new password
python scripts/ota_deploy.py \
  --binary firmware.bin \
  --batch devices.json \
  --password "$NEW_PASS"
```

## Troubleshooting

### Authentication Failed

```
❌ Deployment failed: Authentication failed (invalid password)
```

**Solution:**
- Verify password in `secrets.yaml` matches device configuration
- Ensure firmware was compiled with correct password
- Check batch file password matches device configuration

```bash
# Verify password in device
esphome logs firmware/voice-assistant.yaml
# Look for OTA password confirmation in logs
```

### Password Reset

If device password is lost:

1. **Serial reset method:**
   ```bash
   # Connect via USB and reset via serial
   esphome upload firmware/voice-assistant.yaml --device /dev/ttyUSB0
   ```

2. **Factory reset:**
   ```bash
   # Press factory reset button on device (if available)
   # Or trigger via Home Assistant
   ```

### Batch Deployment Issues

```bash
# Verify batch file format
python -m json.tool devices.json

# Test single device first
python scripts/ota_deploy.py \
  --device test_device.local \
  --binary firmware.bin \
  --password test_password
```

## Security Considerations

### OTA Protocol Version

ESPHome supports OTA protocol version 2 (more secure than v1):

```yaml
ota:
  - platform: esphome
    id: ota_esphome
    password: !secret ota_password
    # Protocol version is automatic in recent ESPHome versions
```

### Network Security

- OTA updates happen over unencrypted HTTP (device trusts same LAN)
- Use VPN/secure network for remote deployments
- Consider additional network segmentation for production

### Audit Trail

Keep records of:
- Deployment dates and times
- Firmware versions deployed
- Devices updated
- Update success/failure status

```bash
# Example logging
cat >> deployment_log.txt << EOF
$(date): Deployed firmware v1.2.3 to 5 devices, success rate: 100%
EOF
```

## Related Documentation

- [ESPHome OTA Documentation](https://esphome.io/components/ota.html)
- [OTA Deployment Tool](../scripts/OTA_DEPLOY_README.md)
- [Device Configuration](voice-assistant.yaml)

## Support

For issues or questions:
1. Check the [OTA Deployment Tool documentation](../scripts/OTA_DEPLOY_README.md)
2. Review [ESPHome OTA logs](https://esphome.io/components/logger.html)
3. Consult [ESPHome documentation](https://esphome.io/)
