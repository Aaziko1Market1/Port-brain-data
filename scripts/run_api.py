#!/usr/bin/env python
"""
EPIC 7B - API Server Entrypoint
================================
Starts the GTI-OS Control Tower API using Uvicorn.

Usage:
    python scripts/run_api.py
    python scripts/run_api.py --port 8080
    python scripts/run_api.py --host 127.0.0.1 --port 8000 --reload

Environment Variables:
    DB_CONFIG_PATH: Path to database config (default: config/db_config.yml)

Part of GTI-OS Data Platform Architecture v1.0
"""

import os
import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def print_banner():
    """Print the application banner."""
    print()
    print("=" * 70)
    print("  GTI-OS Data Platform - Control Tower API")
    print("  EPIC 7B: Read-Only API Layer")
    print("=" * 70)
    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='GTI-OS Control Tower API Server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Start on 0.0.0.0:8000
  %(prog)s --port 8080               # Start on port 8080
  %(prog)s --host 127.0.0.1          # Localhost only
  %(prog)s --reload                  # Auto-reload on code changes
  %(prog)s --workers 4               # Use 4 worker processes

API Documentation:
  Swagger UI: http://localhost:8000/docs
  ReDoc:      http://localhost:8000/redoc

Key Endpoints:
  GET /api/v1/health              - Health check
  GET /api/v1/meta/stats          - Global statistics
  GET /api/v1/buyers              - List buyers
  GET /api/v1/buyers/{uuid}/360   - Buyer 360 view
  GET /api/v1/hs-dashboard        - HS code dashboard
  GET /api/v1/risk/top-shipments  - Top risky shipments
  GET /api/v1/risk/top-buyers     - Top risky buyers
        """
    )
    
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='Port to bind to (default: 8000)'
    )
    
    parser.add_argument(
        '--reload',
        action='store_true',
        help='Enable auto-reload for development'
    )
    
    parser.add_argument(
        '--workers',
        type=int,
        default=1,
        help='Number of worker processes (default: 1, use >1 for production)'
    )
    
    parser.add_argument(
        '--config',
        default='config/db_config.yml',
        help='Path to database config file (default: config/db_config.yml)'
    )
    
    parser.add_argument(
        '--log-level',
        default='info',
        choices=['debug', 'info', 'warning', 'error'],
        help='Logging level (default: info)'
    )
    
    args = parser.parse_args()
    
    # Set environment variable for DB config
    os.environ['DB_CONFIG_PATH'] = args.config
    
    # Verify config exists
    if not Path(args.config).exists():
        print(f"ERROR: Database config not found: {args.config}")
        sys.exit(1)
    
    print_banner()
    print(f"  Host:       {args.host}")
    print(f"  Port:       {args.port}")
    print(f"  Reload:     {args.reload}")
    print(f"  Workers:    {args.workers}")
    print(f"  DB Config:  {args.config}")
    print(f"  Log Level:  {args.log_level}")
    print()
    print(f"  API Docs:   http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}/docs")
    print()
    print("=" * 70)
    print()
    
    # Import uvicorn here to avoid import errors if not installed
    try:
        import uvicorn
    except ImportError:
        print("ERROR: uvicorn not installed. Run: pip install uvicorn")
        sys.exit(1)
    
    # Run the server
    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,  # Workers doesn't work with reload
        log_level=args.log_level
    )


if __name__ == '__main__':
    main()
