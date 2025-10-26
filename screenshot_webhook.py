import os
import time
import random
import requests
import logging
import json
import argparse
import io
import gc
import psutil
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from PIL import ImageGrab, Image
from logging.handlers import RotatingFileHandler
from pathlib import Path
import signal
import sys

# Configuration with validation
class Config:
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.webhook_url: Optional[str] = None
        self.min_interval: int = 30
        self.max_interval: int = 60
        self.delete_after_send: bool = True
        self.max_file_size_mb: int = 8  # Discord file size limit
        self.image_quality: int = 85
        self.log_level: str = "INFO"
        self.screenshot_dir: str = "screenshots"
        # Resource optimization settings
        self.max_memory_mb: int = 200  # Maximum memory usage in MB
        self.max_cpu_percent: int = 30  # Maximum CPU usage percentage
        self.enable_memory_monitoring: bool = True
        self.low_power_mode: bool = False
        self.max_resolution: Tuple[int, int] = (1920, 1080)  # Max screenshot resolution
        self.load_config()
    
    def load_config(self):
        """Load configuration from file or environment variables"""
        # Try to load from config file first
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                    self.webhook_url = config_data.get('webhook_url')
                    self.min_interval = config_data.get('min_interval', self.min_interval)
                    self.max_interval = config_data.get('max_interval', self.max_interval)
                    self.delete_after_send = config_data.get('delete_after_send', self.delete_after_send)
                    self.max_file_size_mb = config_data.get('max_file_size_mb', self.max_file_size_mb)
                    self.image_quality = config_data.get('image_quality', self.image_quality)
                    self.log_level = config_data.get('log_level', self.log_level)
                    self.screenshot_dir = config_data.get('screenshot_dir', self.screenshot_dir)
                    # Resource optimization settings
                    self.max_memory_mb = config_data.get('max_memory_mb', self.max_memory_mb)
                    self.max_cpu_percent = config_data.get('max_cpu_percent', self.max_cpu_percent)
                    self.enable_memory_monitoring = config_data.get('enable_memory_monitoring', self.enable_memory_monitoring)
                    self.low_power_mode = config_data.get('low_power_mode', self.low_power_mode)
                    max_res = config_data.get('max_resolution', self.max_resolution)
                    self.max_resolution = tuple(max_res) if isinstance(max_res, list) else self.max_resolution
            except (json.JSONDecodeError, IOError) as e:
                logging.warning(f"Failed to load config file: {e}")
        
        # Override with environment variables if available
        self.webhook_url = os.getenv('DISCORD_WEBHOOK_URL', self.webhook_url)
        self.min_interval = int(os.getenv('MIN_INTERVAL', self.min_interval))
        self.max_interval = int(os.getenv('MAX_INTERVAL', self.max_interval))
        self.delete_after_send = os.getenv('DELETE_AFTER_SEND', str(self.delete_after_send)).lower() == 'true'
        self.max_file_size_mb = int(os.getenv('MAX_FILE_SIZE_MB', self.max_file_size_mb))
        self.image_quality = int(os.getenv('IMAGE_QUALITY', self.image_quality))
        self.log_level = os.getenv('LOG_LEVEL', self.log_level)
        self.screenshot_dir = os.getenv('SCREENSHOT_DIR', self.screenshot_dir)
        # Resource optimization environment variables
        self.max_memory_mb = int(os.getenv('MAX_MEMORY_MB', self.max_memory_mb))
        self.max_cpu_percent = int(os.getenv('MAX_CPU_PERCENT', self.max_cpu_percent))
        self.enable_memory_monitoring = os.getenv('ENABLE_MEMORY_MONITORING', str(self.enable_memory_monitoring)).lower() == 'true'
        self.low_power_mode = os.getenv('LOW_POWER_MODE', str(self.low_power_mode)).lower() == 'true'
        
        self.validate_config()
    
    def validate_config(self):
        """Validate configuration values"""
        if not self.webhook_url or self.webhook_url == 'your_discord_webhook_url' or self.webhook_url == '':
            raise ValueError("Discord webhook URL must be provided")
        
        if not self.webhook_url.startswith('https://discord.com/api/webhooks/'):
            raise ValueError("Invalid Discord webhook URL format")
        
        if self.min_interval < 10:
            raise ValueError("Minimum interval must be at least 10 seconds")
        
        if self.max_interval < self.min_interval:
            raise ValueError("Maximum interval must be greater than minimum interval")
        
        if self.max_file_size_mb > 8:
            raise ValueError("File size cannot exceed 8MB (Discord limit)")
        
        if not (1 <= self.image_quality <= 100):
            raise ValueError("Image quality must be between 1 and 100")
        
        # Create screenshot directory if it doesn't exist
        Path(self.screenshot_dir).mkdir(exist_ok=True)

# Resource monitoring class
class ResourceMonitor:
    def __init__(self, config):
        self.config = config
        self.process = psutil.Process()
        self.last_memory_check = 0
        self.memory_check_interval = 30  # Check every 30 seconds
        
    def get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB"""
        try:
            return self.process.memory_info().rss / 1024 / 1024
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return 0.0
    
    def get_cpu_percent(self) -> float:
        """Get current CPU usage percentage"""
        try:
            return self.process.cpu_percent()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return 0.0
    
    def should_throttle(self) -> bool:
        """Check if we should throttle operations due to high resource usage"""
        if not self.config.enable_memory_monitoring:
            return False
        
        current_time = time.time()
        if current_time - self.last_memory_check < self.memory_check_interval:
            return False
        
        self.last_memory_check = current_time
        
        memory_mb = self.get_memory_usage_mb()
        cpu_percent = self.get_cpu_percent()
        
        if memory_mb > self.config.max_memory_mb:
            logging.warning(f"High memory usage: {memory_mb:.1f}MB (limit: {self.config.max_memory_mb}MB)")
            return True
        
        if cpu_percent > self.config.max_cpu_percent:
            logging.warning(f"High CPU usage: {cpu_percent:.1f}% (limit: {self.config.max_cpu_percent}%)")
            return True
        
        return False
    
    def force_garbage_collection(self):
        """Force garbage collection to free memory"""
        gc.collect()
        logging.debug("Forced garbage collection")

# Global config instance
config = Config()

# Configure logging with rotation
def setup_logging():
    """Setup logging configuration"""
    log_handler = RotatingFileHandler('screenshot_tool.log', maxBytes=5e6, backupCount=5)
    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    log_handler.setFormatter(log_formatter)
    
    # Clear existing handlers
    logger = logging.getLogger()
    logger.handlers.clear()
    logger.addHandler(log_handler)
    logger.setLevel(getattr(logging, config.log_level.upper(), logging.INFO))
    
    # Also add console handler for immediate feedback
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    logger.addHandler(console_handler)

# Screenshot manager class
class ScreenshotManager:
    def __init__(self):
        self.running = True
        self.consecutive_failures = 0
        self.max_consecutive_failures = 5
        self.resource_monitor = ResourceMonitor(config)
        self.last_screenshot_time = 0
        self.min_screenshot_interval = 5  # Minimum 5 seconds between screenshots
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logging.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def take_screenshot(self) -> Optional[str]:
        """Take a screenshot and return the filename"""
        try:
            # Check if we should throttle due to resource usage
            if self.resource_monitor.should_throttle():
                logging.info("Throttling screenshot due to high resource usage")
                return None
            
            # Check minimum interval between screenshots
            current_time = time.time()
            if current_time - self.last_screenshot_time < self.min_screenshot_interval:
                logging.debug("Skipping screenshot due to minimum interval")
                return None
            
            # Take screenshot with optimized settings
            screenshot = ImageGrab.grab()
            
            # Immediately limit resolution if needed
            screenshot = self._limit_resolution(screenshot)
            
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            filepath = os.path.join(config.screenshot_dir, filename)
            
            # Use memory-efficient compression
            screenshot = self._compress_image_efficient(screenshot)
            
            # Save with optimized settings
            screenshot.save(filepath, optimize=True, quality=config.image_quality)
            
            # Check file size and compress further if needed
            file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
            if file_size_mb > config.max_file_size_mb:
                logging.warning(f"Screenshot {filename} is {file_size_mb:.2f}MB, exceeding limit")
                # Try to compress further
                screenshot = self._compress_image_efficient(screenshot, max_size_mb=config.max_file_size_mb)
                screenshot.save(filepath, optimize=True, quality=50)
                file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
                logging.info(f"Compressed screenshot to {file_size_mb:.2f}MB")
            
            self.last_screenshot_time = current_time
            logging.info(f"Screenshot taken and saved as {filepath} ({file_size_mb:.2f}MB)")
            
            # Force garbage collection to free memory
            del screenshot
            self.resource_monitor.force_garbage_collection()
            
            return filepath
            
        except Exception as e:
            logging.error(f"Failed to take screenshot: {e}")
            return None
    
    def _limit_resolution(self, image: Image.Image) -> Image.Image:
        """Limit image resolution to reduce memory usage"""
        if config.low_power_mode:
            max_width, max_height = config.max_resolution
            current_width, current_height = image.size
            
            if current_width > max_width or current_height > max_height:
                # Calculate scale factor to fit within max resolution
                scale_w = max_width / current_width
                scale_h = max_height / current_height
                scale_factor = min(scale_w, scale_h)
                
                new_width = int(current_width * scale_factor)
                new_height = int(current_height * scale_factor)
                
                # Use faster resampling for low power mode
                resampling = Image.Resampling.NEAREST if config.low_power_mode else Image.Resampling.LANCZOS
                image = image.resize((new_width, new_height), resampling)
                logging.debug(f"Limited resolution from {current_width}x{current_height} to {new_width}x{new_height}")
        
        return image
    
    def _compress_image_efficient(self, image: Image.Image, max_size_mb: Optional[float] = None) -> Image.Image:
        """Memory-efficient image compression"""
        if max_size_mb is None:
            max_size_mb = config.max_file_size_mb
        
        # Convert to RGB if necessary (more memory efficient than RGBA)
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        
        # Calculate target dimensions based on file size
        original_size = image.size
        max_pixels = max_size_mb * 1024 * 1024 * 8  # Rough estimate
        
        if original_size[0] * original_size[1] > max_pixels:
            scale_factor = (max_pixels / (original_size[0] * original_size[1])) ** 0.5
            new_size = (int(original_size[0] * scale_factor), int(original_size[1] * scale_factor))
            
            # Use appropriate resampling based on power mode
            resampling = Image.Resampling.NEAREST if config.low_power_mode else Image.Resampling.LANCZOS
            image = image.resize(new_size, resampling)
            logging.info(f"Resized image from {original_size} to {new_size}")
        
        return image
    
    def send_to_discord(self, filepath: str) -> bool:
        """Send screenshot to Discord webhook with memory optimization"""
        try:
            # Use streaming upload to reduce memory usage
            with open(filepath, 'rb') as file:
                files = {'file': (os.path.basename(filepath), file, 'image/png')}
                
                # Use shorter timeout and smaller chunk size for low power mode
                timeout = 15 if config.low_power_mode else 30
                
                response = requests.post(
                    config.webhook_url, 
                    files=files,
                    timeout=timeout,
                    stream=True  # Enable streaming for memory efficiency
                )
            
            if response.status_code == 200:
                logging.info(f"Successfully sent {os.path.basename(filepath)} to Discord")
                self.consecutive_failures = 0
                return True
            else:
                logging.error(f"Failed to send {os.path.basename(filepath)} to Discord: {response.status_code} - {response.text}")
                self.consecutive_failures += 1
                return False
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Network error sending to Discord: {e}")
            self.consecutive_failures += 1
            return False
        except Exception as e:
            logging.error(f"Unexpected error sending to Discord: {e}")
            self.consecutive_failures += 1
            return False
        finally:
            # Force garbage collection after network operations
            self.resource_monitor.force_garbage_collection()
    
    def cleanup_file(self, filepath: str):
        """Clean up screenshot file"""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logging.info(f"Deleted screenshot file {os.path.basename(filepath)}")
        except Exception as e:
            logging.error(f"Failed to delete file {filepath}: {e}")
    
    def get_dynamic_interval(self) -> int:
        """Get dynamic interval based on failure rate and resource usage"""
        base_interval = random.randint(config.min_interval, config.max_interval)
        
        # Increase interval if we have consecutive failures
        if self.consecutive_failures > 0:
            multiplier = min(2 ** self.consecutive_failures, 8)  # Cap at 8x
            base_interval = int(base_interval * multiplier)
            logging.info(f"Increased interval due to {self.consecutive_failures} consecutive failures")
        
        # Increase interval if resources are high
        if self.resource_monitor.should_throttle():
            base_interval = int(base_interval * 2)  # Double the interval
            logging.info("Increased interval due to high resource usage")
        
        # Use longer intervals in low power mode
        if config.low_power_mode:
            base_interval = int(base_interval * 1.5)
            logging.debug("Using longer interval for low power mode")
        
        return base_interval
    
    def should_continue(self) -> bool:
        """Check if we should continue running"""
        if not self.running:
            return False
        
        if self.consecutive_failures >= self.max_consecutive_failures:
            logging.error(f"Too many consecutive failures ({self.consecutive_failures}), stopping")
            return False
        
        return True

def create_sample_config():
    """Create a sample configuration file"""
    sample_config = {
        "webhook_url": "YOUR_DISCORD_WEBHOOK_URL_HERE",
        "min_interval": 30,
        "max_interval": 60,
        "delete_after_send": True,
        "max_file_size_mb": 8,
        "image_quality": 85,
        "log_level": "INFO",
        "screenshot_dir": "screenshots",
        # Resource optimization settings
        "max_memory_mb": 200,
        "max_cpu_percent": 30,
        "enable_memory_monitoring": True,
        "low_power_mode": False,
        "max_resolution": [1920, 1080]
    }
    
    with open("config.json", "w") as f:
        json.dump(sample_config, f, indent=2)
    
    print("Sample config.json created. Please edit it with your Discord webhook URL.")

def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(description="Screenshot webhook tool for Discord")
    parser.add_argument("--config", default="config.json", help="Configuration file path")
    parser.add_argument("--create-config", action="store_true", help="Create sample configuration file")
    parser.add_argument("--test-webhook", action="store_true", help="Test webhook connection")
    
    args = parser.parse_args()
    
    if args.create_config:
        create_sample_config()
        return
    
    try:
        # Initialize configuration
        global config
        config = Config(args.config)
        
        # Setup logging
        setup_logging()
        
        logging.info("Starting screenshot webhook tool")
        logging.info(f"Configuration loaded from {args.config}")
        logging.info(f"Webhook URL: {config.webhook_url[:50]}...")
        logging.info(f"Interval range: {config.min_interval}-{config.max_interval} seconds")
        logging.info(f"Screenshot directory: {config.screenshot_dir}")
        
        if args.test_webhook:
            # Test webhook connection
            manager = ScreenshotManager()
            test_file = os.path.join(config.screenshot_dir, "test_screenshot.png")
            try:
                # Create a small test image
                test_image = Image.new('RGB', (100, 100), color='red')
                test_image.save(test_file)
                
                if manager.send_to_discord(test_file):
                    print("✓ Webhook test successful!")
                else:
                    print("✗ Webhook test failed!")
                
                manager.cleanup_file(test_file)
            except Exception as e:
                print(f"✗ Webhook test error: {e}")
            return
        
        # Setup signal handlers for graceful shutdown
        manager = ScreenshotManager()
        signal.signal(signal.SIGINT, manager.signal_handler)
        signal.signal(signal.SIGTERM, manager.signal_handler)
        
        # Main loop
        while manager.should_continue():
            try:
                filepath = manager.take_screenshot()
                if filepath:
                    success = manager.send_to_discord(filepath)
                    if success and config.delete_after_send:
                        manager.cleanup_file(filepath)
                else:
                    manager.consecutive_failures += 1
                
            except KeyboardInterrupt:
                logging.info("Received keyboard interrupt, shutting down...")
                break
            except Exception as e:
                logging.error(f"Unexpected error in main loop: {e}")
                manager.consecutive_failures += 1
            
            if manager.should_continue():
                sleep_time = manager.get_dynamic_interval()
                logging.info(f"Sleeping for {sleep_time} seconds")
                time.sleep(sleep_time)
        
        logging.info("Screenshot webhook tool stopped")
        
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Run with --create-config to create a sample configuration file")
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()