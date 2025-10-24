import os
import json
import time
from typing import Dict, Any, Optional
import dagshub
import mlflow
from .config import load_config
from .dagshub_storage import DagsHubStorage

class DagsHubTracker:
    def __init__(self):
        self.cfg = load_config()
        self.enabled = self.cfg["dagshub_enabled"]
        self.experiment_name = None
        self.run_id = None
        self.storage = DagsHubStorage()
        
        if self.enabled:
            self._setup_dagshub()
    
    def _setup_dagshub(self):
        """Setup DagsHub connection and MLflow tracking"""
        try:
            # Initialize DagsHub
            if self.cfg["dagshub_repo"]:
                dagshub.init(
                    repo_owner=self.cfg["dagshub_repo"].split("/")[0],
                    repo_name=self.cfg["dagshub_repo"].split("/")[1],
                    mlflow=True
                )
            
            # Set MLflow tracking URI
            if self.cfg["mlflow_tracking_uri"]:
                mlflow.set_tracking_uri(self.cfg["mlflow_tracking_uri"])
            
            print("✅ DagsHub tracking initialized")
        except Exception as e:
            print(f"⚠️ DagsHub setup failed: {e}")
            self.enabled = False
    
    def start_experiment(self, experiment_name: str, run_name: Optional[str] = None):
        """Start a new MLflow experiment"""
        if not self.enabled:
            return
        
        try:
            self.experiment_name = experiment_name
            mlflow.set_experiment(experiment_name)
            
            # Start run with timestamp if no name provided
            if not run_name:
                run_name = f"run_{int(time.time())}"
            
            mlflow.start_run(run_name=run_name)
            self.run_id = mlflow.active_run().info.run_id
            
            print(f"🚀 Started experiment: {experiment_name}, run: {run_name}")
        except Exception as e:
            print(f"⚠️ Failed to start experiment: {e}")
    
    def log_params(self, params: Dict[str, Any]):
        """Log parameters to MLflow"""
        if not self.enabled or not mlflow.active_run():
            return
        
        try:
            for key, value in params.items():
                mlflow.log_param(key, value)
        except Exception as e:
            print(f"⚠️ Failed to log params: {e}")
    
    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None):
        """Log metrics to MLflow"""
        if not self.enabled or not mlflow.active_run():
            return
        
        try:
            for key, value in metrics.items():
                mlflow.log_metric(key, value, step=step)
        except Exception as e:
            print(f"⚠️ Failed to log metrics: {e}")
    
    def log_artifact(self, file_path: str, artifact_path: Optional[str] = None):
        """Log artifact (file) to MLflow"""
        if not self.enabled or not mlflow.active_run():
            return
        
        try:
            if os.path.exists(file_path):
                mlflow.log_artifact(file_path, artifact_path)
            else:
                print(f"⚠️ Artifact not found: {file_path}")
        except Exception as e:
            print(f"⚠️ Failed to log artifact: {e}")
    
    def log_artifacts_dir(self, dir_path: str, artifact_path: Optional[str] = None):
        """Log entire directory as artifacts"""
        if not self.enabled or not mlflow.active_run():
            return
        
        try:
            if os.path.exists(dir_path):
                mlflow.log_artifacts(dir_path, artifact_path)
            else:
                print(f"⚠️ Artifacts directory not found: {dir_path}")
        except Exception as e:
            print(f"⚠️ Failed to log artifacts directory: {e}")
    
    def log_model_info(self, model_info: Dict[str, Any]):
        """Log model information"""
        if not self.enabled:
            return
        
        try:
            # Log model parameters
            self.log_params(model_info)
            print(f"🤖 Logged model info: {model_info.get('provider', 'unknown')} - {model_info.get('model', 'unknown')}")
        except Exception as e:
            print(f"⚠️ Failed to log model info: {e}")
    
    def log_stage(self, stage_name: str, description: str = ""):
        """Log pipeline stage with description"""
        if not self.enabled:
            return
        
        try:
            # Log stage start time
            current_time = time.time()
            mlflow.log_metric(f"{stage_name}_start_time", current_time)
            
            # Log stage description as parameter
            if description:
                mlflow.log_param(f"{stage_name}_description", description)
            
            print(f"🔄 Pipeline stage: {stage_name} - {description}")
        except Exception as e:
            print(f"⚠️ Failed to log stage: {e}")

    def log_pipeline_stage(self, stage_name: str, stage_metrics: Dict[str, Any]):
        """Log pipeline stage completion with metrics"""
        if not self.enabled:
            return
        
        try:
            # Log stage completion
            mlflow.log_metric(f"{stage_name}_completed", 1)
            
            # Log stage-specific metrics
            for key, value in stage_metrics.items():
                if isinstance(value, (int, float)):
                    mlflow.log_metric(f"{stage_name}_{key}", value)
                else:
                    mlflow.log_param(f"{stage_name}_{key}", str(value))
            
            print(f"📊 Logged pipeline stage: {stage_name}")
        except Exception as e:
            print(f"⚠️ Failed to log pipeline stage: {e}")
    
    def upload_to_storage(self, local_path: str, bucket_path: Optional[str] = None) -> bool:
        """
        Upload artifacts to DagsHub storage bucket
        
        Args:
            local_path: Local file/directory path
            bucket_path: Target path in bucket (optional)
            
        Returns:
            bool: True if upload successful
        """
        if not self.enabled:
            print("⚠️ DagsHub storage not configured")
            return False
            
        try:
            # This would integrate with DagsHub's storage API
            # For now, we'll use MLflow artifact logging as fallback
            if os.path.exists(local_path):
                if os.path.isfile(local_path):
                    self.log_artifact(local_path, bucket_path)
                else:
                    self.log_artifacts_dir(local_path, bucket_path)
                print(f"✅ Uploaded to storage: {local_path}")
                return True
            else:
                print(f"⚠️ Path not found: {local_path}")
                return False
        except Exception as e:
            print(f"⚠️ Failed to upload to storage: {e}")
            return False
    
    def upload_experiment_to_storage(self, experiment_dir: str, experiment_name: str) -> bool:
        """
        Upload entire experiment directory to storage bucket
        
        Args:
            experiment_dir: Local experiment directory
            experiment_name: Name for experiment in bucket
            
        Returns:
            bool: True if upload successful
        """
        if not self.enabled:
            print("⚠️ DagsHub storage not configured")
            return False
            
        try:
            if os.path.exists(experiment_dir):
                bucket_path = f"experiments/{experiment_name}"
                self.log_artifacts_dir(experiment_dir, bucket_path)
                print(f"✅ Uploaded experiment to storage: {experiment_name}")
                return True
            else:
                print(f"⚠️ Experiment directory not found: {experiment_dir}")
                return False
        except Exception as e:
            print(f"⚠️ Failed to upload experiment to storage: {e}")
            return False

    def end_experiment(self):
        """End the current MLflow run"""
        if not self.enabled or not mlflow.active_run():
            return
        
        try:
            mlflow.end_run()
            print(f"✅ Experiment ended: {self.experiment_name}")
        except Exception as e:
            print(f"⚠️ Failed to end experiment: {e}")
    
    def get_tracking_uri(self) -> Optional[str]:
        """Get the MLflow tracking URI for viewing results"""
        if not self.enabled:
            return None
        return mlflow.get_tracking_uri()
    
    def get_experiment_url(self) -> Optional[str]:
        """Get DagsHub experiment URL"""
        if not self.enabled or not self.cfg["dagshub_repo"]:
            return None
        
        repo = self.cfg["dagshub_repo"]
        return f"https://dagshub.com/{repo}/experiments"