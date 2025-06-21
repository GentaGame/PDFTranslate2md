"""
PDFTranslate2md - Core Package

PDFファイルを翻訳してMarkdownに変換するコアパッケージ。
Phase 3アーキテクチャによる統合されたモジュール群を提供する。
"""

__version__ = "3.0.0"
__author__ = "PDFTranslate2md Team"

# Core modules
from .app_controller import AppController
from .pdf_extractor import extract_text, extract_images
from .translator_service import TranslatorService
from .markdown_writer import write_markdown

# Utility modules
from .unicode_handler import normalize_unicode_text, validate_text_for_api
from .rate_limiter import RateLimiter, global_rate_limiter
from .retry_manager import RetryManager

# Provider support
from .providers import (
    create_provider,
    get_supported_providers,
    get_default_model,
    validate_provider_name,
    BaseProvider,
    APIError,
    HTTPStatusError,
    RateLimitError,
    ValidationError
)

__all__ = [
    # Core classes
    'AppController',
    'TranslatorService',
    'RateLimiter',
    'RetryManager',
    
    # Core functions
    'extract_text',
    'extract_images', 
    'write_markdown',
    'normalize_unicode_text',
    'validate_text_for_api',
    
    # Provider functions
    'create_provider',
    'get_supported_providers',
    'get_default_model',
    'validate_provider_name',
    
    # Provider classes
    'BaseProvider',
    
    # Exceptions
    'APIError',
    'HTTPStatusError',
    'RateLimitError',
    'ValidationError',
    
    # Global instances
    'global_rate_limiter'
]