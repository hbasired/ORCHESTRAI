"""Test if backend can start"""
import sys
print("Python version:", sys.version)

try:
    print("Testing imports...")
    from config import settings
    print("✓ Config loaded")
    
    from api.routes import router
    print("✓ API routes loaded")
    
    from services.state_manager import StateManager
    print("✓ State manager loaded")
    
    from services.decision_engine import DecisionEngine
    print("✓ Decision engine loaded")
    
    print("\n✅ All imports successful!")
    print(f"Simulation mode: {settings.simulation_mode}")
    print(f"Port: {settings.port}")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
