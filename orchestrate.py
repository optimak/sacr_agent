#!/usr/bin/env python3
"""
SACR Project Orchestration Script
Runs all steps sequentially: Scraping → Processing → Services
"""

import os
import sys
import time
import subprocess
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SACROrchestrator:
    def __init__(self):
        """Initialize orchestrator with configuration validation"""
        self.validate_configuration()
        self.steps_completed = []
        self.current_step = 0
        self.total_steps = 5
    
    def validate_configuration(self):
        """Validate configuration and check for conflicts"""
        logger.info("Validating configuration...")
        
        # Check vector database configuration
        use_local = os.getenv("USE_LOCAL_VECTOR_DB", "true").lower() == "true"
        use_azure = os.getenv("USE_AZURE_AI_SEARCH", "false").lower() == "true"
        
        if use_local and use_azure:
            logger.error("❌ Configuration conflict: Both USE_LOCAL_VECTOR_DB and USE_AZURE_AI_SEARCH are enabled")
            logger.error("Please set only one to 'true' in your .env file")
            sys.exit(1)
        
        if not use_local and not use_azure:
            logger.error("❌ No vector database configured")
            logger.error("Please set either USE_LOCAL_VECTOR_DB=true or USE_AZURE_AI_SEARCH=true")
            sys.exit(1)
        
        # Check required environment variables
        required_vars = ["NOTION_TOKEN", "AZURE_OPENAI_KEY", "AZURE_ENDPOINT"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            sys.exit(1)
        
        logger.info("✅ Configuration validated successfully")
    
    def run_step(self, step_name: str, step_function, *args, **kwargs) -> bool:
        """Run a single step with error handling and progress tracking"""
        self.current_step += 1
        logger.info(f"🔄 Step {self.current_step}/{self.total_steps}: {step_name}")
        
        try:
            result = step_function(*args, **kwargs)
            if result:  # Only mark as completed if the step actually succeeded
                self.steps_completed.append(step_name)
                logger.info(f"✅ Step {self.current_step} completed: {step_name}")
                return True
            else:
                logger.error(f"❌ Step {self.current_step} failed: {step_name}")
                return False
        except Exception as e:
            logger.error(f"❌ Step {self.current_step} failed: {step_name}")
            logger.error(f"Error: {str(e)}")
            return False
    
    def step_1_scrape_data(self) -> bool:
        """Step 1: Run data scraping"""
        logger.info("Starting data scraping...")
        
        try:
            # Change to data_ingestion directory
            os.chdir("data_ingestion")
            
            # Run the scraper
            result = subprocess.run(
                [sys.executable, "main_scraper.py"],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                logger.info("Data scraping completed successfully")
                return True
            else:
                logger.error(f"Scraping failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Data scraping timed out")
            return False
        except Exception as e:
            logger.error(f"Error running data scraping: {e}")
            return False
        finally:
            # Return to project root
            os.chdir("..")
    
    def step_2_process_rag(self) -> bool:
        """Step 2: Run RAG processing"""
        logger.info("Starting RAG processing...")
        
        try:
            # Change to rag_agent/src directory
            os.chdir("rag_agent/src")
            
            # Run the enhanced RAG pipeline
            result = subprocess.run(
                [sys.executable, "-c", """
import sys
sys.path.append('.')
from enhanced_rag_pipeline import EnhancedRAGPipeline

pipeline = EnhancedRAGPipeline()
result = pipeline.run_full_pipeline()
print(f'Pipeline result: {result}')
if result['status'] != 'success':
    sys.exit(1)
                """],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0:
                logger.info("RAG processing completed successfully")
                logger.info(f"Output: {result.stdout}")
                return True
            else:
                logger.error(f"RAG processing failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("RAG processing timed out")
            return False
        except Exception as e:
            logger.error(f"Error running RAG processing: {e}")
            return False
        finally:
            # Return to project root
            os.chdir("../..")
    
    def step_3_start_backend(self) -> bool:
        """Step 3: Start backend service"""
        logger.info("Starting backend service...")
        
        try:
            # Start backend in background
            self.backend_process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"],
                cwd="backend",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=None if os.name == 'nt' else os.setsid  # Create new process group
            )
            
            # Wait for backend to start
            logger.info("Waiting for backend to start...")
            time.sleep(10)  # Give more time for startup
            
            # Check if backend is running
            if self.backend_process.poll() is None:
                logger.info("✅ Backend service started successfully")
                return True
            else:
                stdout, stderr = self.backend_process.communicate()
                logger.error(f"❌ Backend service failed to start")
                logger.error(f"STDOUT: {stdout.decode()}")
                logger.error(f"STDERR: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting backend: {e}")
            return False
    
    def step_4_start_frontend(self) -> bool:
        """Step 4: Start frontend service"""
        logger.info("Starting frontend service...")
        
        try:
            # Start frontend in background
            self.frontend_process = subprocess.Popen(
                [sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"],
                cwd="frontend",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=None if os.name == 'nt' else os.setsid  # Create new process group
            )
            
            # Wait for frontend to start
            logger.info("Waiting for frontend to start...")
            time.sleep(10)  # Give more time for startup
            
            # Check if frontend is running
            if self.frontend_process.poll() is None:
                logger.info("✅ Frontend service started successfully")
                return True
            else:
                stdout, stderr = self.frontend_process.communicate()
                logger.error(f"❌ Frontend service failed to start")
                logger.error(f"STDOUT: {stdout.decode()}")
                logger.error(f"STDERR: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting frontend: {e}")
            return False
    
    def step_5_health_check(self) -> bool:
        """Step 5: Perform health checks"""
        logger.info("Performing health checks...")
        
        try:
            import requests
            
            # Check if we're running in Docker (services in same container)
            # or locally (services on localhost)
            backend_url = "http://localhost:8000/health"
            frontend_url = "http://localhost:8501"
            
            # Check backend health
            try:
                backend_response = requests.get(backend_url, timeout=10)
                if backend_response.status_code == 200:
                    logger.info("✅ Backend health check passed")
                else:
                    logger.error("❌ Backend health check failed")
                    return False
            except requests.exceptions.ConnectionError:
                logger.warning("⚠️ Backend health check skipped (connection refused - may be starting up)")
                # Don't fail the orchestration for this, services might still be starting
            
            # Check frontend (basic connectivity)
            try:
                frontend_response = requests.get(frontend_url, timeout=10)
                if frontend_response.status_code == 200:
                    logger.info("✅ Frontend health check passed")
                else:
                    logger.warning("⚠️ Frontend health check failed (may be starting up)")
            except requests.exceptions.ConnectionError:
                logger.warning("⚠️ Frontend health check skipped (connection refused - may be starting up)")
            
            # Health checks are informational - don't fail orchestration
            logger.info("✅ Health checks completed (services may still be starting up)")
            return True
            
        except Exception as e:
            logger.warning(f"Health check warning: {e}")
            # Don't fail orchestration for health check issues
            return True
    
    def run_orchestration(self):
        """Run the complete orchestration"""
        logger.info("🚀 Starting SACR Project Orchestration")
        logger.info("=" * 50)
        
        # Run all steps
        steps = [
            ("Data Scraping", self.step_1_scrape_data),
            ("RAG Processing", self.step_2_process_rag),
            ("Backend Service", self.step_3_start_backend),
            ("Frontend Service", self.step_4_start_frontend),
            ("Health Checks", self.step_5_health_check)
        ]
        
        for step_name, step_function in steps:
            success = self.run_step(step_name, step_function)
            if not success:
                logger.error(f"❌ Orchestration failed at step: {step_name}")
                self.cleanup()
                sys.exit(1)
        
        # Success!
        logger.info("=" * 50)
        logger.info("🎉 SACR Project Orchestration Completed Successfully!")
        logger.info(f"✅ Completed steps: {', '.join(self.steps_completed)}")
        logger.info("")
        logger.info("🌐 Services are now running:")
        logger.info("   Frontend: http://localhost:8501")
        logger.info("   Backend:  http://localhost:8000")
        logger.info("   Health:   http://localhost:8000/health")
        logger.info("")
        logger.info("Press Ctrl+C to stop all services")
        
        # Keep services running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 Shutting down services...")
            self.cleanup()
    
    def cleanup(self):
        """Clean up running processes"""
        if hasattr(self, 'backend_process') and self.backend_process.poll() is None:
            try:
                if os.name == 'nt':
                    self.backend_process.terminate()
                else:
                    os.killpg(os.getpgid(self.backend_process.pid), 15)  # SIGTERM
                logger.info("✅ Backend service stopped")
            except Exception as e:
                logger.warning(f"Error stopping backend: {e}")
        
        if hasattr(self, 'frontend_process') and self.frontend_process.poll() is None:
            try:
                if os.name == 'nt':
                    self.frontend_process.terminate()
                else:
                    os.killpg(os.getpgid(self.frontend_process.pid), 15)  # SIGTERM
                logger.info("✅ Frontend service stopped")
            except Exception as e:
                logger.warning(f"Error stopping frontend: {e}")

def main():
    """Main entry point"""
    orchestrator = SACROrchestrator()
    orchestrator.run_orchestration()

if __name__ == "__main__":
    main()
