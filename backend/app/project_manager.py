import logging
import json
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class ProviderType(str, Enum):
    OLLAMA = "ollama"
    LOCAL_LLM = "local_llm"
    OPENAI = "openai"

class ProjectConfig(BaseModel):
    project_id: str
    provider: ProviderType = ProviderType.LOCAL_LLM
    model: str = "microsoft/DialoGPT-medium"
    system_prompt: Optional[str] = None
    settings: Dict[str, Any] = {}

class ProjectManager:
    def __init__(self):
        self.projects_dir = Path("./projects")
        self.projects_dir.mkdir(exist_ok=True)
        self.config_file = self.projects_dir / "projects.json"
        self.load_projects()
    
    def load_projects(self):
        """Load projects from config file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.projects = {pid: ProjectConfig(**config) for pid, config in data.items()}
            else:
                self.projects = {}
        except Exception as e:
            logger.error(f"Error loading projects: {e}")
            self.projects = {}
    
    def save_projects(self):
        """Save projects to config file"""
        try:
            data = {pid: config.dict() for pid, config in self.projects.items()}
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving projects: {e}")
    
    def create_project(self, config: ProjectConfig) -> ProjectConfig:
        """Create a new project"""
        self.projects[config.project_id] = config
        self.save_projects()
        return config
    
    def get_project(self, project_id: str) -> Optional[ProjectConfig]:
        """Get project by ID"""
        return self.projects.get(project_id)
    
    def update_project(self, project_id: str, **kwargs) -> Optional[ProjectConfig]:
        """Update project configuration"""
        if project_id in self.projects:
            project = self.projects[project_id]
            for key, value in kwargs.items():
                if hasattr(project, key):
                    setattr(project, key, value)
            self.save_projects()
            return project
        return None
    
    def list_projects(self) -> List[ProjectConfig]:
        """List all projects"""
        return list(self.projects.values())
    
    def delete_project(self, project_id: str) -> bool:
        """Delete a project"""
        if project_id in self.projects:
            del self.projects[project_id]
            self.save_projects()
            return True
        return False

# Global instance
project_manager = ProjectManager()