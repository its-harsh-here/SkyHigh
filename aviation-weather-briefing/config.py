"""
Configuration settings for Aviation Weather Briefing System
"""
import os

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'aviation-weather-briefing-dev-key-2024'
    
    # Weather API settings
    AVIATIONWEATHER_BASE_URL = 'https://aviationweather.gov/api/data'
    USE_SAMPLE_DATA = False  # Always use live data
    
    # Request timeout settings
    REQUEST_TIMEOUT = 30
    
    # Cache settings (for future implementation)
    CACHE_TIMEOUT = 300  # 5 minutes
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # Rate limiting (for future implementation)
    RATE_LIMIT_PER_MINUTE = 60

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    USE_SAMPLE_DATA = False  # Use live data in development too

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    USE_SAMPLE_DATA = False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    USE_SAMPLE_DATA = False  # Use live data for testing too

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
