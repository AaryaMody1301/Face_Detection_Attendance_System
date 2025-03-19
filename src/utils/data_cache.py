"""
Data Caching Module - Provides caching functionality for analytics data
"""
import os
import json
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Any, Dict, Optional, Union

class DataCache:
    """Class for caching analytics data with expiration"""
    
    def __init__(self, cache_dir: str = "cache"):
        """
        Initialize the cache system
        
        Args:
            cache_dir (str): Directory to store cache files
        """
        self.cache_dir = cache_dir
        self.cache_metadata_file = os.path.join(cache_dir, "cache_metadata.json")
        self.cache_metadata = self._load_cache_metadata()
        os.makedirs(cache_dir, exist_ok=True)
    
    def _load_cache_metadata(self) -> Dict:
        """Load cache metadata from file"""
        if os.path.exists(self.cache_metadata_file):
            try:
                with open(self.cache_metadata_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_cache_metadata(self):
        """Save cache metadata to file"""
        with open(self.cache_metadata_file, 'w') as f:
            json.dump(self.cache_metadata, f)
    
    def _generate_cache_key(self, data_type: str, params: Dict) -> str:
        """
        Generate a unique cache key based on data type and parameters
        
        Args:
            data_type (str): Type of data being cached
            params (Dict): Parameters used to generate the data
            
        Returns:
            str: Unique cache key
        """
        # Sort parameters to ensure consistent keys
        sorted_params = sorted(params.items())
        param_str = "_".join(f"{k}-{v}" for k, v in sorted_params)
        return f"{data_type}_{param_str}"
    
    def get(self, data_type: str, params: Dict, max_age: int = 3600) -> Optional[Any]:
        """
        Retrieve cached data if it exists and is not expired
        
        Args:
            data_type (str): Type of data to retrieve
            params (Dict): Parameters used to generate the data
            max_age (int): Maximum age of cache in seconds
            
        Returns:
            Any: Cached data or None if not found/expired
        """
        cache_key = self._generate_cache_key(data_type, params)
        
        if cache_key not in self.cache_metadata:
            return None
            
        metadata = self.cache_metadata[cache_key]
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.cache")
        
        # Check if cache is expired
        if time.time() - metadata['timestamp'] > max_age:
            self.delete(cache_key)
            return None
            
        try:
            if metadata['type'] == 'dataframe':
                return pd.read_pickle(cache_file)
            elif metadata['type'] == 'numpy':
                return np.load(cache_file)
            else:
                with open(cache_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error reading cache: {e}")
            return None
    
    def set(self, data_type: str, params: Dict, data: Any):
        """
        Cache data with metadata
        
        Args:
            data_type (str): Type of data being cached
            params (Dict): Parameters used to generate the data
            data (Any): Data to cache
        """
        cache_key = self._generate_cache_key(data_type, params)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.cache")
        
        try:
            # Save data based on type
            if isinstance(data, pd.DataFrame):
                data.to_pickle(cache_file)
                data_type = 'dataframe'
            elif isinstance(data, np.ndarray):
                np.save(cache_file, data)
                data_type = 'numpy'
            else:
                with open(cache_file, 'w') as f:
                    json.dump(data, f)
                data_type = 'json'
            
            # Update metadata
            self.cache_metadata[cache_key] = {
                'type': data_type,
                'timestamp': time.time(),
                'params': params
            }
            self._save_cache_metadata()
            
        except Exception as e:
            print(f"Error caching data: {e}")
    
    def delete(self, cache_key: str):
        """
        Delete cached data and its metadata
        
        Args:
            cache_key (str): Key of cache to delete
        """
        if cache_key in self.cache_metadata:
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.cache")
            if os.path.exists(cache_file):
                os.remove(cache_file)
            del self.cache_metadata[cache_key]
            self._save_cache_metadata()
    
    def clear(self, max_age: Optional[int] = None):
        """
        Clear all or expired cache entries
        
        Args:
            max_age (int, optional): Maximum age of cache entries to clear
        """
        current_time = time.time()
        keys_to_delete = []
        
        for cache_key, metadata in self.cache_metadata.items():
            if max_age is None or (current_time - metadata['timestamp'] > max_age):
                keys_to_delete.append(cache_key)
        
        for cache_key in keys_to_delete:
            self.delete(cache_key)
    
    def get_cache_size(self) -> int:
        """
        Get total size of cache in bytes
        
        Returns:
            int: Total size of cache in bytes
        """
        total_size = 0
        for cache_key in self.cache_metadata:
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.cache")
            if os.path.exists(cache_file):
                total_size += os.path.getsize(cache_file)
        return total_size 