# HACS Setup Guide for Chatterbox Integration

**Last Updated:** 2026-03-25
**Version:** 0.1.0

---

## What is HACS?

**HACS** (Home Assistant Community Store) is the package manager for Home Assistant custom components and integrations. It simplifies installation and keeps integrations up-to-date.

**Advantages:**
- One-click installation and updates
- Automatic version management
- Easy removal/uninstallation
- Community ratings and reviews

---

## Prerequisites

1. **Home Assistant** installed and running (version 2025.x or later)
2. **Network access** to GitHub (to download the integration)
3. **Administrator access** to Home Assistant settings

---

## Step 1: Install HACS (if not already installed)

If HACS is already installed, skip to [Step 2](#step-2-add-chatterbox-as-custom-repository).

### Option A: Manual Installation (Recommended)

1. **Download HACS:**
   - Visit https://github.com/hacs/integration/releases
   - Download the latest `hacs.zip`

2. **Extract to Home Assistant:**
   ```bash
   unzip hacs.zip -d ~/.homeassistant/custom_components/hacs/
   # or
   unzip hacs.zip -d ~/config/custom_components/hacs/
   ```

3. **Restart Home Assistant:**
   - Settings → System → Restart

4. **Set Up HACS:**
   - Settings → Devices & Services
   - Click "Create Integration"
   - Search for "HACS"
   - Follow the setup wizard

### Option B: Using Terminal/SSH

```bash
cd ~/.homeassistant/custom_components/  # or ~/config/custom_components/
wget https://github.com/hacs/integration/releases/download/1.32.1/hacs.zip
unzip hacs.zip
rm hacs.zip
```

Then restart Home Assistant from the UI.

---

## Step 2: Add Chatterbox as Custom Repository

HACS allows adding custom repositories beyond the official store. Chatterbox is hosted as a custom repository.

### Steps

1. **Open HACS:**
   - Go to Home Assistant
   - Click HACS in the sidebar (or go to Settings → Devices & Services → HACS)

2. **Access Custom Repositories:**
   - Click the three-dot menu (⋮) in the top right
   - Select "Custom repositories"

3. **Add Repository:**
   - **Repository URL:** `https://github.com/phaedrus/hentown`
   - **Category:** Integration
   - Click **Create**

   You should see a confirmation message.

4. **Verify It's Added:**
   - Go back to HACS → Integrations
   - The Chatterbox repository should appear in the list
   - May take a moment to sync

---

## Step 3: Install Chatterbox

Once the repository is added, install the integration.

1. **Find Chatterbox in HACS:**
   - Go to HACS → Integrations
   - Search for "Chatterbox"
   - Click on the result

2. **View Integration Details:**
   - Version number
   - Author: phaedrus
   - Description
   - Link to documentation

3. **Install:**
   - Click "Install"
   - Wait for download to complete
   - You should see a success message

4. **Restart Home Assistant:**
   - Settings → System → Restart
   - Wait for restart (this may take a minute)

---

## Step 4: Configure Chatterbox in Home Assistant

After restart, add the integration to Home Assistant.

1. **Create Integration:**
   - Settings → Devices & Services
   - Click "Create Integration" (bottom right button)
   - Search for "Chatterbox"

2. **Configure:**
   - Follow the configuration flow (see [Home Assistant Integration Guide](ha-integration-guide.md))
   - Enter server URL and API key
   - Test connection
   - Finish setup

3. **Verify:**
   - Settings → Devices & Services
   - You should see "Chatterbox" listed with status "Connected"

---

## Step 5: Set Up Voice Pipeline

Now configure your voice pipeline to use Chatterbox.

1. **Open Voice Assistants:**
   - Settings → Voice Assistants (or Voice & Assist in older versions)

2. **Select Pipeline:**
   - Click "Default" (or your pipeline name)

3. **Configure Conversation Agent:**
   - Under "Conversation Agent", select your Chatterbox agent
   - Example: "Kitchen Assistant" (the name you chose during setup)

4. **Configure STT and TTS:**
   - Choose speech-to-text service (e.g., Whisper)
   - Choose text-to-speech service (e.g., Piper)

5. **Save:**
   - Click "Save" or "Finish"

6. **Test:**
   - Speak a command: "What time is it?"
   - You should hear Chatterbox respond

---

## Managing Chatterbox in HACS

### Checking for Updates

HACS automatically checks for updates weekly. To manually check:

1. **Go to HACS → Integrations**
2. **Find Chatterbox**
3. If an update is available, you'll see an update badge
4. Click the update button and follow the prompt

### Updating Chatterbox

1. **In HACS Integrations list:**
   - Find Chatterbox
   - Click it

2. **Update:**
   - If an update is available, click "Update" or "Upgrade"
   - Wait for download
   - Click "Restart" or restart manually:
     - Settings → System → Restart

3. **Verify:**
   - After restart, configuration should be preserved
   - Voice pipeline should still work

### Viewing Installation Details

1. **In HACS:**
   - Click on Chatterbox
   - You'll see:
     - Current version installed
     - Available version
     - Installation date
     - File size
     - Link to GitHub

### Reinstalling (Troubleshooting)

If something goes wrong:

1. **In HACS:**
   - Click on Chatterbox
   - Click the three dots (⋮)
   - Select "Reinstall"
   - Wait for completion
   - Restart Home Assistant

2. **Or manually:**
   - Remove the integration from Settings → Devices & Services
   - Uninstall from HACS (click three dots → Uninstall)
   - Reinstall from HACS

---

## hacs.json Explanation

The `hacs.json` file at the repository root tells HACS how to find and install the integration.

### Current hacs.json

```json
{
  "name": "Chatterbox",
  "content_in_root": false,
  "filename": "custom_components/chatterbox"
}
```

### Field Meanings

| Field | Value | Meaning |
|-------|-------|---------|
| `name` | "Chatterbox" | Display name in HACS UI |
| `content_in_root` | `false` | Integration is NOT in repo root |
| `filename` | "custom_components/chatterbox" | Path to integration folder |

### Why These Values?

- **name:** Shows up when searching HACS for "Chatterbox"
- **content_in_root: false:** The integration is in `custom_components/chatterbox/`, not at repo root
- **filename:** Tells HACS exactly where to find the integration code

If these values change, HACS will fail to find or install the integration.

---

## Troubleshooting HACS Issues

### "Repository Not Found"

**Symptom:** Adding custom repository gives "Repository not found" error.

**Causes:**
1. URL is incorrect
2. Repository doesn't exist
3. GitHub is unreachable

**Solutions:**

1. **Verify URL:**
   - Should be: `https://github.com/phaedrus/hentown`
   - (without `.git` at the end)

2. **Check GitHub:**
   - Visit the URL in a browser
   - Should see the hentown repository

3. **Check Internet:**
   - Ping GitHub: `ping github.com`
   - Should get a response

4. **Try again:**
   - Custom repositories → Add another copy of the URL
   - HACS may have rate limiting

---

### "Cannot Install - Integration Not Found"

**Symptom:** HACS shows the repository but can't find the integration to install.

**Causes:**
1. `hacs.json` is malformed
2. `hacs.json` has wrong path
3. Integration folder doesn't exist

**Solutions:**

1. **Check hacs.json exists:**
   ```bash
   curl https://raw.githubusercontent.com/phaedrus/hentown/main/hacs.json
   # Should return valid JSON
   ```

2. **Check format:**
   ```bash
   # Validate with Python
   python3 -c "import json; json.load(open('hacs.json'))"
   # Should not error
   ```

3. **Check integration folder:**
   - Path in `hacs.json`: `custom_components/chatterbox`
   - Folder must exist at: `https://github.com/phaedrus/hentown/tree/main/custom_components/chatterbox`

---

### "Installation Failed"

**Symptom:** HACS downloaded the file but installation failed.

**Causes:**
1. Corrupt download
2. Permission issues on Home Assistant
3. Conflicting integration with same name

**Solutions:**

1. **Check Permissions:**
   ```bash
   ls -la ~/.homeassistant/custom_components/
   # Should be readable/writable
   ```

2. **Remove Conflicting Integration:**
   ```bash
   rm -rf ~/.homeassistant/custom_components/chatterbox/
   # Remove any existing installation
   ```

3. **Try HACS Uninstall + Reinstall:**
   - HACS → Click on Chatterbox
   - Three dots (⋮) → Uninstall
   - Restart Home Assistant
   - Re-add repository and install fresh

4. **Manual Installation:**
   - If HACS continues to fail, use [manual installation](ha-integration-guide.md#manual-installation)

---

### Updates Not Showing

**Symptom:** HACS says "Already up-to-date" but you know there's a newer version.

**Causes:**
1. HACS hasn't checked for updates yet
2. Release tag format is wrong on GitHub
3. Local version is newer than GitHub

**Solutions:**

1. **Force Update Check:**
   - HACS → Click three dots (⋮) → "Check for update" (if available)
   - Or restart Home Assistant

2. **Check GitHub Releases:**
   - Visit: https://github.com/phaedrus/hentown/releases
   - See what versions are available

3. **Manual Update:**
   - Delete current integration: `rm -rf ~/.homeassistant/custom_components/chatterbox/`
   - Reinstall from HACS
   - Restart Home Assistant

---

### HACS Sidebar Not Appearing

**Symptom:** HACS is installed but doesn't show in Home Assistant sidebar.

**Solutions:**

1. **Restart Home Assistant:**
   - Settings → System → Restart

2. **Clear Browser Cache:**
   - Ctrl+Shift+Delete (Chrome)
   - Cmd+Shift+Delete (Mac)
   - Refresh the page

3. **Check Installation:**
   ```bash
   ls ~/.homeassistant/custom_components/hacs/
   # Should show files
   ```

4. **Check Logs:**
   - Settings → System → Logs
   - Search for "HACS" errors

---

## Advanced HACS Usage

### Finding Release Notes

When an update is available:

1. **In HACS:**
   - Click on Chatterbox
   - Scroll down to see recent changes
   - Or click the version number for full release notes

2. **On GitHub:**
   - https://github.com/phaedrus/hentown/releases
   - See detailed changelog for each release

### Backing Up Before Update

Before updating to a new version:

```bash
# Backup the current integration
cp -r ~/.homeassistant/custom_components/chatterbox/ \
      ~/.homeassistant/custom_components/chatterbox.backup/

# If update fails, restore:
rm -rf ~/.homeassistant/custom_components/chatterbox/
mv ~/.homeassistant/custom_components/chatterbox.backup/ \
   ~/.homeassistant/custom_components/chatterbox/
```

### Switching Between Versions

HACS doesn't have built-in version switching, but you can:

1. **Using GitHub:**
   - Download a specific release from GitHub
   - Extract to custom_components/
   - Restart Home Assistant

2. **Or reinstall latest:**
   - Uninstall from HACS
   - Reinstall from HACS

---

## HACS and CI/CD

If you're developing Chatterbox or maintaining a fork:

HACS automatically validates new releases using:
- `hacs.json` format
- Integration structure
- Python code quality

If your release fails HACS validation, you'll see errors in GitHub Actions.

---

## Directory Structure After Installation

After successful HACS installation, your Home Assistant custom components directory should look like:

```
~/.homeassistant/custom_components/
├── hacs/
│   ├── __init__.py
│   └── ... (HACS files)
└── chatterbox/
    ├── __init__.py
    ├── manifest.json
    ├── const.py
    ├── config_flow.py
    ├── conversation.py
    ├── strings.json
    ├── translations/
    │   └── en.json
    └── ... (Chatterbox files)
```

---

## Community Support

If you run into issues:

1. **Check Home Assistant Community:**
   - https://community.home-assistant.io/
   - Search for "Chatterbox"
   - Post a question (include logs and configuration)

2. **GitHub Issues:**
   - https://github.com/phaedrus/hentown/issues
   - Include Home Assistant version, Chatterbox version, and full error logs

3. **HACS Documentation:**
   - https://hacs.xyz/docs/

---

## See Also

- [Home Assistant Integration Guide](ha-integration-guide.md)
- [Settings Schema Reference](ha-settings-schema.md)
- [Troubleshooting Guide](ha-integration-guide.md#troubleshooting)

---

**Last Updated:** 2026-03-25
**Version:** 0.1.0
