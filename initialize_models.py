#!/usr/bin/env python3
"""
ML Model Initialization Script for ProtLitAI
Downloads and initializes all required ML models for production use
"""

import sys
import time
from pathlib import Path
from typing import Dict, Any

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.config import config
from core.logging import get_logger
from processing.ml_models import get_model_manager


def format_size(bytes_size: int) -> str:
    """Format byte size to human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"


def check_system_requirements() -> Dict[str, Any]:
    """Check system requirements for ML model initialization."""
    logger = get_logger("model_init")
    
    print("🔍 Checking System Requirements")
    print("-" * 50)
    
    requirements = {
        "pytorch_available": False,
        "mps_available": False,
        "disk_space": 0,
        "memory_info": {},
        "status": "unknown"
    }
    
    try:
        # Check PyTorch
        import torch
        requirements["pytorch_available"] = True
        print(f"✅ PyTorch {torch.__version__} installed")
        
        # Check MPS (Metal Performance Shaders)
        if torch.backends.mps.is_available():
            requirements["mps_available"] = True
            print(f"✅ MPS acceleration available")
        else:
            print(f"⚠️  MPS acceleration not available")
        
        # Check disk space
        import shutil
        disk_usage = shutil.disk_usage(Path.cwd())
        requirements["disk_space"] = disk_usage.free
        print(f"✅ Available disk space: {format_size(disk_usage.free)}")
        
        if disk_usage.free < 5 * 1024 * 1024 * 1024:  # 5GB
            print(f"⚠️  Warning: Less than 5GB free space available")
        
        # Check memory
        import psutil
        memory = psutil.virtual_memory()
        requirements["memory_info"] = {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent
        }
        print(f"✅ Available memory: {format_size(memory.available)} ({100-memory.percent:.1f}% free)")
        
        # Overall status
        if requirements["pytorch_available"] and disk_usage.free > 2 * 1024 * 1024 * 1024:
            requirements["status"] = "ready"
        else:
            requirements["status"] = "insufficient"
        
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        requirements["status"] = "missing_deps"
    except Exception as e:
        print(f"❌ System check failed: {e}")
        requirements["status"] = "error"
    
    print(f"\n📊 System Status: {requirements['status'].upper()}")
    return requirements


def initialize_models() -> Dict[str, Any]:
    """Initialize all required ML models."""
    logger = get_logger("model_init")
    
    print("\n🤖 Initializing ML Models")
    print("-" * 50)
    
    results = {
        "sentence_transformer": {"status": "pending", "time": 0, "error": None},
        "spacy_model": {"status": "pending", "time": 0, "error": None},
        "total_time": 0,
        "overall_status": "pending"
    }
    
    start_time = time.time()
    
    try:
        # Get model manager
        print("📦 Creating model manager...")
        manager = get_model_manager()
        print("✅ Model manager created successfully")
        
        # Initialize sentence transformer
        print("\n🔤 Initializing Sentence Transformer model...")
        print("   📥 This may take several minutes on first run...")
        st_start = time.time()
        
        try:
            embedding_model = manager.load_embedding_model()
            st_time = time.time() - st_start
            results["sentence_transformer"] = {
                "status": "success",
                "time": st_time,
                "error": None,
                "model_name": config.settings.embedding_model
            }
            print(f"✅ Sentence Transformer loaded in {st_time:.1f}s")
            
            # Test embedding generation
            print("   🧪 Testing embedding generation...")
            test_embedding = manager.generate_embeddings(["Test protein design paper"])
            print(f"   ✅ Test embedding: {test_embedding.shape} dimensions")
            
        except Exception as e:
            results["sentence_transformer"] = {
                "status": "failed",
                "time": time.time() - st_start,
                "error": str(e)
            }
            print(f"❌ Sentence Transformer failed: {e}")
        
        # Initialize spaCy model
        print("\n🔬 Initializing spaCy biomedical model...")
        print("   📥 This may take time on first run...")
        spacy_start = time.time()
        
        try:
            spacy_model = manager.load_spacy_model()
            spacy_time = time.time() - spacy_start
            results["spacy_model"] = {
                "status": "success",
                "time": spacy_time,
                "error": None,
                "model_name": config.settings.spacy_model
            }
            print(f"✅ spaCy model loaded in {spacy_time:.1f}s")
            
            # Test entity extraction
            print("   🧪 Testing entity extraction...")
            test_entities = manager.extract_entities(["EGFR protein design using machine learning"])
            print(f"   ✅ Test entities extracted: {len(test_entities[0]) if test_entities else 0} entities")
            
        except Exception as e:
            results["spacy_model"] = {
                "status": "failed",
                "time": time.time() - spacy_start,
                "error": str(e)
            }
            print(f"❌ spaCy model failed: {e}")
        
        # Warm up models
        print("\n🔥 Warming up models...")
        warmup_start = time.time()
        try:
            manager.warmup_models()
            warmup_time = time.time() - warmup_start
            print(f"✅ Models warmed up in {warmup_time:.1f}s")
        except Exception as e:
            print(f"⚠️  Model warmup failed: {e}")
        
        # Get performance stats
        try:
            stats = manager.get_performance_stats()
            print(f"\n📊 Performance Statistics:")
            print(f"   Device: {stats.get('device', 'unknown')}")
            print(f"   Memory usage: {stats.get('memory_usage', 'unknown')}")
        except Exception as e:
            print(f"⚠️  Could not get performance stats: {e}")
    
    except Exception as e:
        print(f"❌ Model initialization failed: {e}")
        results["overall_status"] = "failed"
        results["error"] = str(e)
        return results
    
    # Calculate total time and overall status
    total_time = time.time() - start_time
    results["total_time"] = total_time
    
    success_count = sum(1 for r in [results["sentence_transformer"], results["spacy_model"]] 
                       if r["status"] == "success")
    
    if success_count == 2:
        results["overall_status"] = "success"
    elif success_count == 1:
        results["overall_status"] = "partial"
    else:
        results["overall_status"] = "failed"
    
    return results


def main():
    """Main entry point."""
    print("🚀 ProtLitAI ML Model Initialization")
    print("=" * 60)
    
    # Check system requirements
    requirements = check_system_requirements()
    
    if requirements["status"] not in ["ready"]:
        print(f"\n❌ System not ready for model initialization: {requirements['status']}")
        if requirements["status"] == "insufficient":
            print("   Please ensure you have at least 2GB free disk space")
        return 1
    
    # Initialize models
    results = initialize_models()
    
    # Print final summary
    print("\n" + "=" * 60)
    print("🏁 INITIALIZATION SUMMARY")
    print("=" * 60)
    
    print(f"Overall Status: {results['overall_status'].upper()}")
    print(f"Total Time: {results['total_time']:.1f} seconds")
    print()
    
    print("Component Results:")
    for component, result in results.items():
        if isinstance(result, dict) and "status" in result:
            status_icon = "✅" if result["status"] == "success" else "❌"
            print(f"  {status_icon} {component}: {result['status']} ({result['time']:.1f}s)")
            if result.get("error"):
                print(f"      Error: {result['error']}")
    
    if results["overall_status"] == "success":
        print("\n🎉 All models initialized successfully!")
        print("   ProtLitAI is ready for production use.")
    elif results["overall_status"] == "partial":
        print("\n⚠️  Some models failed to initialize.")
        print("   ProtLitAI may have limited functionality.")
    else:
        print("\n❌ Model initialization failed.")
        print("   Please check the errors above and try again.")
        return 1
    
    print(f"\n💡 Next Steps:")
    print(f"   - Run production literature collection: python production_collection.py")
    print(f"   - Launch UI application: python -m src.ui.app")
    print(f"   - Check system status: python test_end_to_end.py")
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInitialization interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nInitialization failed with error: {e}")
        sys.exit(1)