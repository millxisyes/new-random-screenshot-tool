# new-random-screenshot-tool
A tool that screenshots your screen every 30-60 seconds, and sends it to a Discord Webhook. (PERSONAL USE ONLY)

(NOTE: This was entirely made with ChatGPT and Cursor)
# Screenshot Webhook Tool

A robust Python tool that automatically takes screenshots and sends them to a Discord webhook at configurable intervals.

## Features

- **Automatic Screenshots**: Takes screenshots at random intervals within a configurable range
- **Discord Integration**: Sends screenshots directly to Discord via webhook
- **Smart Compression**: Automatically compresses images to stay within Discord's 8MB file size limit
- **Robust Error Handling**: Handles network failures, file system errors, and other exceptions gracefully
- **Configuration Management**: Supports both JSON config files and environment variables
- **Graceful Shutdown**: Handles SIGINT/SIGTERM signals for clean shutdown
- **Comprehensive Logging**: Detailed logging with rotation and console output
- **Failure Recovery**: Exponential backoff on consecutive failures
- **Webhook Testing**: Built-in webhook connection testing

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### Option 1: Configuration File

Create a configuration file by running:
```bash
python screenshot_webhook.py --create-config
```

This creates a `config.json` file with default settings. Edit it with your Discord webhook URL:

```json
{
  "webhook_url": "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL",
  "min_interval": 60,
  "max_interval": 600,
  "delete_after_send": true,
  "max_file_size_mb": 8,
  "image_quality": 85,
  "log_level": "INFO",
  "screenshot_dir": "screenshots"
}
```

### Option 2: Environment Variables

Set environment variables instead of using a config file:

```bash
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR_WEBHOOK_URL"
export MIN_INTERVAL=60
export MAX_INTERVAL=600
export DELETE_AFTER_SEND=true
export MAX_FILE_SIZE_MB=8
export IMAGE_QUALITY=85
export LOG_LEVEL=INFO
export SCREENSHOT_DIR="screenshots"
```

## Usage

### Basic Usage
```bash
python screenshot_webhook.py
```

### Test Webhook Connection
```bash
python screenshot_webhook.py --test-webhook
```

### Use Custom Config File
```bash
python screenshot_webhook.py --config my_config.json
```

### Create Sample Config
```bash
python screenshot_webhook.py --create-config
```

## Configuration Options

| Option | Description | Default | Range |
|--------|-------------|---------|-------|
| `webhook_url` | Discord webhook URL | Required | Valid Discord webhook URL |
| `min_interval` | Minimum seconds between screenshots | 60 | ≥10 |
| `max_interval` | Maximum seconds between screenshots | 600 | ≥min_interval |
| `delete_after_send` | Delete screenshots after sending | true | true/false |
| `max_file_size_mb` | Maximum file size in MB | 8 | ≤8 (Discord limit) |
| `image_quality` | JPEG quality for compression | 85 | 1-100 |
| `log_level` | Logging level | INFO | DEBUG/INFO/WARNING/ERROR |
| `screenshot_dir` | Directory to store screenshots | screenshots | Valid directory path |

## Features Explained

### Smart Compression
- Automatically resizes images if they exceed the size limit
- Converts images to RGB format for better compression
- Uses high-quality Lanczos resampling for resizing
- Adjusts JPEG quality based on file size requirements

### Failure Recovery
- Tracks consecutive failures
- Implements exponential backoff (up to 8x normal interval)
- Stops after 5 consecutive failures to prevent infinite loops
- Resets failure counter on successful operations

### Security
- Validates webhook URL format
- Prevents hardcoded credentials in source code
- Supports environment variable configuration
- Input validation for all configuration parameters

### Logging
- Rotating log files (5MB max, 5 backups)
- Console output for immediate feedback
- Configurable log levels
- Detailed error messages with context

## Discord Webhook Setup

1. Go to your Discord server
2. Navigate to Server Settings → Integrations → Webhooks
3. Click "Create Webhook"
4. Copy the webhook URL
5. Use this URL in your configuration

## Troubleshooting

### Common Issues

**"Discord webhook URL must be provided"**
- Ensure you've set the webhook URL in config.json or as an environment variable

**"Invalid Discord webhook URL format"**
- Make sure the URL starts with `https://discord.com/api/webhooks/`

**"Failed to send screenshot to Discord"**
- Check your internet connection
- Verify the webhook URL is correct and active
- Ensure the webhook hasn't been deleted

**"Screenshot file is too large"**
- The tool will automatically compress images, but very high-resolution screenshots might still exceed limits
- Consider reducing `image_quality` in configuration

### Testing

Use the built-in webhook test:
```bash
python screenshot_webhook.py --test-webhook
```

This creates a small test image and attempts to send it to Discord.

## License

This project is open source. Feel free to modify and distribute as needed.

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.
