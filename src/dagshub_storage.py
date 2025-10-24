"""
DagsHub Storage utilities for uploading and downloading artifacts
"""
import os
import subprocess
import logging
from typing import Optional
from .config import load_config

logger = logging.getLogger(__name__)

class DagsHubStorage:
    """Utility class for interacting with DagsHub storage bucket"""
    
    def __init__(self):
        self.config = load_config()
        self.bucket_name = self.config.get("dagshub_bucket_name", "")
        self.repo = self.config.get("dagshub_repo", "")
        
    def upload_file(self, local_path: str, bucket_path: Optional[str] = None) -> bool:
        """
        Upload a file to DagsHub storage bucket
        
        Args:
            local_path: Path to local file/directory
            bucket_path: Target path in bucket (optional)
            
        Returns:
            bool: True if upload successful, False otherwise
        """
        if not self.bucket_name or not self.repo:
            logger.warning("DagsHub bucket configuration not found")
            return False
            
        try:
            cmd = ["dagshub", "upload", "--bucket", f"{self.repo.split('/')[0]}/{self.bucket_name}", local_path]
            if bucket_path:
                cmd.append(bucket_path)
                
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Successfully uploaded {local_path} to DagsHub bucket")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to upload {local_path}: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Upload error: {str(e)}")
            return False
    
    def download_file(self, bucket_path: str, local_path: Optional[str] = None) -> bool:
        """
        Download a file from DagsHub storage bucket
        
        Args:
            bucket_path: Path in bucket
            local_path: Target local path (optional)
            
        Returns:
            bool: True if download successful, False otherwise
        """
        if not self.bucket_name or not self.repo:
            logger.warning("DagsHub bucket configuration not found")
            return False
            
        try:
            cmd = ["dagshub", "download", "--bucket", f"{self.repo.split('/')[0]}/{self.bucket_name}", bucket_path]
            if local_path:
                cmd.append(local_path)
                
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Successfully downloaded {bucket_path} from DagsHub bucket")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to download {bucket_path}: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Download error: {str(e)}")
            return False
    
    def upload_experiment_artifacts(self, experiment_dir: str, experiment_name: str) -> bool:
        """
        Upload all experiment artifacts to DagsHub bucket
        
        Args:
            experiment_dir: Local experiment directory
            experiment_name: Name for the experiment in bucket
            
        Returns:
            bool: True if upload successful, False otherwise
        """
        if not os.path.exists(experiment_dir):
            logger.error(f"Experiment directory not found: {experiment_dir}")
            return False
            
        bucket_path = f"experiments/{experiment_name}"
        return self.upload_file(experiment_dir, bucket_path)
    
    def is_configured(self) -> bool:
        """Check if DagsHub storage is properly configured"""
        return bool(self.bucket_name and self.repo)