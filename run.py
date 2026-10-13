"""
Launcher script for Restaurant Order Management Queue Simulator.
Runs FastAPI backend and serves interactive dark-theme frontend.
"""

import sys
import webbrowser
import uvicorn

def main():
    print("=" * 75)
    print("  QUEUE-BASED SIMULATOR FOR RESTAURANT ORDER MANAGEMENT")
    print("  Data Structures Laboratory (DSL) Mini Project")
    print("  Group: DS_GROUP NO-31 | NMIET Pune (Autonomous)")
    print("  Team: NIRAS ADHIRAJ PANDURANG & MITHIL SHANTARAM PAGAR")
    print("=" * 75)
    print("  Server starting at: http://localhost:8000")
    print("  Press Ctrl+C to stop the server.")
    print("=" * 75)

    # Launch server
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()
