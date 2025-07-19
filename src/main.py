"""Main application entry point for ProtLitAI."""

import sys
import asyncio
import signal
from pathlib import Path
from typing import Optional

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

from core.config import config
from core.logging import get_logger
from core.database import db_manager


class ProtLitAIApplication:
    """Main ProtLitAI application."""
    
    def __init__(self):
        self.logger = get_logger("application")
        self.running = False
        self._shutdown_event = asyncio.Event()
    
    async def startup(self) -> None:
        """Initialize application components."""
        self.logger.info("Starting ProtLitAI application", version=config.settings.version)
        
        try:
            # Initialize database
            db_manager.initialize()
            
            # Setup signal handlers
            self._setup_signal_handlers()
            
            self.running = True
            self.logger.info("ProtLitAI application started successfully")
            
        except Exception as e:
            self.logger.critical("Failed to start application", error=str(e))
            raise
    
    async def shutdown(self) -> None:
        """Gracefully shutdown application."""
        self.logger.info("Shutting down ProtLitAI application")
        
        try:
            self.running = False
            
            # Close database connections
            db_manager.close_connections()
            
            self.logger.info("ProtLitAI application shutdown complete")
            
        except Exception as e:
            self.logger.error("Error during shutdown", error=str(e))
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown")
            self._shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run(self) -> None:
        """Main application run loop."""
        await self.startup()
        
        try:
            # Wait for shutdown signal
            await self._shutdown_event.wait()
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        finally:
            await self.shutdown()
    
    def health_check(self) -> dict:
        """Perform application health check."""
        health = {
            "status": "healthy",
            "application": {
                "running": self.running,
                "version": config.settings.version
            }
        }
        
        # Check database health
        try:
            db_health = db_manager.health_check()
            health["database"] = db_health
            
            if db_health["status"] != "healthy":
                health["status"] = "degraded"
                
        except Exception as e:
            health["database"] = {"status": "error", "error": str(e)}
            health["status"] = "degraded"
        
        return health


async def main():
    """Main entry point."""
    app = ProtLitAIApplication()
    await app.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
    except Exception as e:
        print(f"Application failed: {e}")
        sys.exit(1)