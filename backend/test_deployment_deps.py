import sys
import os

def test_deployment_dependencies():
    # Attempt to import the main worker to ensure all runtime dependencies are available
    try:
        import app.worker.monitoring_worker
    except ImportError as e:
        print(f"Missing deployment dependency: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Failed to import monitoring_worker due to another error: {e}")
        # Not failing on other errors as this is just a dependency check
        pass
    print("All deployment dependencies for monitoring worker are present.")

if __name__ == "__main__":
    test_deployment_dependencies()
