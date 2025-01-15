import sys
import importlib
import warnings
from typing import Dict, Optional, Any
from functools import wraps

class PackageCompatibility:
    FALLBACK_VERSIONS = {
        'numpy': {
            'min_version': '1.26.4',
            'fallback_version': '1.24.3',
            'fallback_import': 'numpy_fallback'
        },
        'scipy': {
            'min_version': '1.12.0',
            'fallback_version': '1.11.3',
            'fallback_import': 'scipy_fallback'
        },
        'scikit-learn': {
            'min_version': '1.4.0',
            'fallback_version': '1.3.0',
            'fallback_import': 'sklearn_fallback'
        },
        'pandas': {
            'min_version': '2.2.0',
            'fallback_version': '2.1.0',
            'fallback_import': 'pandas_fallback'
        }
    }

    @staticmethod
    def check_package_version(package_name: str) -> bool:
        """Check if package version is compatible"""
        try:
            pkg = importlib.import_module(package_name)
            version = pkg.__version__
            required_version = PackageCompatibility.FALLBACK_VERSIONS[package_name]['min_version']
            
            return version >= required_version
        except (ImportError, AttributeError):
            return False

    @staticmethod
    def get_compatible_package(package_name: str) -> Any:
        """Get the appropriate package version based on compatibility"""
        try:
            if PackageCompatibility.check_package_version(package_name):
                return importlib.import_module(package_name)
            else:
                fallback = PackageCompatibility.FALLBACK_VERSIONS[package_name]['fallback_import']
                warnings.warn(f"Using fallback version for {package_name}")
                return importlib.import_module(fallback)
        except ImportError as e:
            raise ImportError(f"Neither main nor fallback version of {package_name} could be imported: {e}")

def requires_package(package_name: str):
    """Decorator to handle package compatibility"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                pkg = PackageCompatibility.get_compatible_package(package_name)
                return func(*args, **kwargs, _package=pkg)
            except ImportError as e:
                raise ImportError(f"Required package {package_name} is not available: {e}")
        return wrapper
    return decorator 