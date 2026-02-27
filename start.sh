#!/bin/bash
# Create db_config.yml from environment variables if it doesn't exist
if [ ! -f config/db_config.yml ]; then
    echo "Creating config/db_config.yml from environment variables..."
    cat > config/db_config.yml << EOF
database:
  host: ${DB_HOST:-localhost}
  port: ${DB_PORT:-5432}
  database: ${DB_NAME:-aaziko_trade}
  user: ${DB_USER:-portbrain}
  password: ${DB_PASSWORD:-}
EOF
fi

# Start the API server
exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-3000}
