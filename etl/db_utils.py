"""
Database utilities for GTI-OS Data Platform
Provides connection pooling, bulk operations, and query helpers
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from urllib.parse import quote_plus
import psycopg2
from psycopg2 import pool, extras
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sqlalchemy as sa
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration loader"""
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load database configuration from YAML"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        return config['database']
    
    def get_connection_string(self) -> str:
        """Build PostgreSQL connection string"""
        user = quote_plus(self.config['user'])
        password = quote_plus(self.config['password'])
        host = self.config['host']
        port = self.config['port']
        database = self.config['database']
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    def get_psycopg2_params(self) -> Dict[str, Any]:
        """Get parameters for psycopg2 connection"""
        return {
            'host': self.config['host'],
            'port': self.config['port'],
            'database': self.config['database'],
            'user': self.config['user'],
            'password': self.config['password']
        }


class DatabaseManager:
    """
    Manages database connections and operations
    Supports both SQLAlchemy (for ORM/migrations) and psycopg2 (for bulk ops)
    """
    
    def __init__(self, config_path: str):
        self.config = DatabaseConfig(config_path)
        self._engine: Optional[Engine] = None
        self._connection_pool: Optional[pool.SimpleConnectionPool] = None
    
    def get_engine(self) -> Engine:
        """Get SQLAlchemy engine (lazy initialization)"""
        if self._engine is None:
            connection_string = self.config.get_connection_string()
            self._engine = create_engine(
                connection_string,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
                echo=False
            )
            logger.info("SQLAlchemy engine initialized")
        return self._engine
    
    def get_connection_pool(self) -> pool.SimpleConnectionPool:
        """Get psycopg2 connection pool for bulk operations"""
        if self._connection_pool is None:
            params = self.config.get_psycopg2_params()
            self._connection_pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                **params
            )
            logger.info("psycopg2 connection pool initialized")
        return self._connection_pool
    
    @contextmanager
    def get_connection(self):
        """Context manager for psycopg2 connection from pool"""
        conn_pool = self.get_connection_pool()
        conn = conn_pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn_pool.putconn(conn)
    
    @contextmanager
    def get_cursor(self, cursor_factory=None):
        """Context manager for database cursor"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
            finally:
                cursor.close()
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[tuple]:
        """Execute SELECT query and return results"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_insert(self, query: str, params: Optional[tuple] = None) -> None:
        """Execute INSERT/UPDATE/DELETE query"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
    
    def bulk_insert_copy(self, table_name: str, columns: List[str], data_buffer) -> int:
        """
        Bulk insert using PostgreSQL COPY command
        
        Args:
            table_name: Target table name
            columns: List of column names
            data_buffer: StringIO or file-like object with CSV data
        
        Returns:
            Number of rows inserted
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Reset buffer position
                data_buffer.seek(0)
                
                # Use COPY for bulk insert
                copy_sql = f"COPY {table_name} ({','.join(columns)}) FROM STDIN WITH (FORMAT CSV, NULL '')"
                cursor.copy_expert(copy_sql, data_buffer)
                
                rows_inserted = cursor.rowcount
                logger.info(f"Bulk inserted {rows_inserted} rows into {table_name}")
                return rows_inserted
    
    def bulk_insert_execute_batch(
        self, 
        query: str, 
        data: List[tuple], 
        page_size: int = 1000
    ) -> int:
        """
        Bulk insert using execute_batch (efficient alternative to COPY)
        
        Args:
            query: INSERT query with placeholders
            data: List of tuples with values
            page_size: Batch size
        
        Returns:
            Number of rows inserted
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                extras.execute_batch(cursor, query, data, page_size=page_size)
                rows_inserted = len(data)
                logger.info(f"Batch inserted {rows_inserted} rows")
                return rows_inserted
    
    def table_exists(self, table_name: str) -> bool:
        """Check if table exists"""
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = %s
            );
        """
        result = self.execute_query(query, (table_name,))
        return result[0][0] if result else False
    
    def get_table_row_count(self, table_name: str) -> int:
        """Get row count for table"""
        query = f"SELECT COUNT(*) FROM {table_name};"
        result = self.execute_query(query)
        return result[0][0] if result else 0
    
    def close(self):
        """Close all connections"""
        if self._connection_pool:
            self._connection_pool.closeall()
            logger.info("Connection pool closed")
        if self._engine:
            self._engine.dispose()
            logger.info("SQLAlchemy engine disposed")


def create_database_if_not_exists(config_path: str, db_name: str = "aaziko_trade") -> None:
    """
    Create database if it doesn't exist
    Connects to 'postgres' database to create target database
    """
    config = DatabaseConfig(config_path)
    params = config.get_psycopg2_params()
    
    # Connect to default 'postgres' database
    params['database'] = 'postgres'
    
    try:
        conn = psycopg2.connect(**params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s;",
            (db_name,)
        )
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(f"CREATE DATABASE {db_name};")
            logger.info(f"Database '{db_name}' created successfully")
        else:
            logger.info(f"Database '{db_name}' already exists")
        
        cursor.close()
        conn.close()
    
    except Exception as e:
        logger.error(f"Error creating database: {e}")
        raise


def apply_schema(config_path: str, schema_file: str) -> None:
    """
    Apply database schema from SQL file
    
    Args:
        config_path: Path to database config YAML
        schema_file: Path to SQL schema file
    """
    db_manager = DatabaseManager(config_path)
    schema_path = Path(schema_file)
    
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_file}")
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    # Use psycopg2 directly for better PostgreSQL compatibility
    config = DatabaseConfig(config_path)
    params = config.get_psycopg2_params()
    
    conn = psycopg2.connect(**params)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    
    try:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        logger.info(f"Schema applied from {schema_file}")
    except psycopg2.errors.DuplicateTable as e:
        # Schema objects already exist - this is OK for re-runs
        logger.warning(f"Schema objects already exist (this is normal): {e}")
        logger.info(f"Schema validation complete - database is ready")
    except psycopg2.errors.DuplicateObject as e:
        # Indexes or other objects already exist - this is OK
        logger.warning(f"Some schema objects already exist (this is normal): {e}")
        logger.info(f"Schema validation complete - database is ready")
    except Exception as e:
        logger.error(f"Error applying schema: {e}")
        raise
    finally:
        conn.close()
        db_manager.close()
