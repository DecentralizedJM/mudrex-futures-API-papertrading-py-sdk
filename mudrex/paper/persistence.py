"""
Paper Trading Persistence
=========================

SQLite-based persistence for paper trading state.
Allows state to be saved and restored across restarts.
"""

import json
import logging
import os
import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from mudrex.paper.engine import PaperTradingEngine

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types."""
    
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class PaperDB:
    """
    SQLite-based persistence for paper trading state.
    
    Features:
    - Automatic schema creation
    - Atomic state saves
    - State versioning for migration
    - Multiple named profiles
    
    Example:
        >>> db = PaperDB("~/.mudrex/paper_trading.db")
        >>> 
        >>> # Save state
        >>> db.save_state(engine)
        >>> 
        >>> # Later, restore state
        >>> state = db.load_state()
        >>> if state:
        ...     engine.import_state(state)
    """
    
    SCHEMA_VERSION = 1
    
    def __init__(self, db_path: str = None, profile: str = "default"):
        """
        Initialize the database.
        
        Args:
            db_path: Path to SQLite database file (default: ~/.mudrex/paper_trading.db)
            profile: Named profile for multiple paper trading setups
        """
        if db_path is None:
            db_path = os.path.expanduser("~/.mudrex/paper_trading.db")
        
        self.db_path = os.path.expanduser(db_path)
        self.profile = profile
        
        # Ensure directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            Path(db_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_schema()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_schema(self) -> None:
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Schema version table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY
                )
            """)
            
            # Check current version
            cursor.execute("SELECT version FROM schema_version LIMIT 1")
            row = cursor.fetchone()
            current_version = row["version"] if row else 0
            
            if current_version < self.SCHEMA_VERSION:
                self._migrate_schema(conn, current_version)
            
            # State storage table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paper_state (
                    profile TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Separate tables for efficient queries
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paper_positions (
                    position_id TEXT PRIMARY KEY,
                    profile TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    status TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    opened_at TEXT NOT NULL,
                    closed_at TEXT,
                    FOREIGN KEY (profile) REFERENCES paper_state(profile)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paper_orders (
                    order_id TEXT PRIMARY KEY,
                    profile TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    status TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (profile) REFERENCES paper_state(profile)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paper_trades (
                    trade_id TEXT PRIMARY KEY,
                    profile TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    action TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    executed_at TEXT NOT NULL,
                    FOREIGN KEY (profile) REFERENCES paper_state(profile)
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_profile ON paper_positions(profile)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_symbol ON paper_positions(symbol)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_profile ON paper_orders(profile)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_profile ON paper_trades(profile)")
            
            conn.commit()
            
            logger.debug(f"Database initialized: {self.db_path}")
    
    def _migrate_schema(self, conn: sqlite3.Connection, from_version: int) -> None:
        """Migrate schema to latest version."""
        cursor = conn.cursor()
        
        if from_version < 1:
            # Initial schema - no migration needed
            cursor.execute("INSERT OR REPLACE INTO schema_version (version) VALUES (?)", 
                          (self.SCHEMA_VERSION,))
        
        conn.commit()
        logger.info(f"Schema migrated from v{from_version} to v{self.SCHEMA_VERSION}")
    
    def save_state(self, engine: "PaperTradingEngine") -> None:
        """
        Save engine state to database.
        
        Args:
            engine: PaperTradingEngine instance to save
        """
        state = engine.export_state()
        state_json = json.dumps(state, cls=DecimalEncoder)
        now = datetime.utcnow().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Save main state
            cursor.execute("""
                INSERT OR REPLACE INTO paper_state (profile, state_json, created_at, updated_at)
                VALUES (?, ?, COALESCE((SELECT created_at FROM paper_state WHERE profile = ?), ?), ?)
            """, (self.profile, state_json, self.profile, now, now))
            
            # Clear and repopulate detail tables
            cursor.execute("DELETE FROM paper_positions WHERE profile = ?", (self.profile,))
            cursor.execute("DELETE FROM paper_orders WHERE profile = ?", (self.profile,))
            cursor.execute("DELETE FROM paper_trades WHERE profile = ?", (self.profile,))
            
            # Save positions
            for pos_id, pos_data in state.get("positions", {}).items():
                cursor.execute("""
                    INSERT INTO paper_positions 
                    (position_id, profile, symbol, side, status, data_json, opened_at, closed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pos_id,
                    self.profile,
                    pos_data.get("symbol", ""),
                    pos_data.get("side", ""),
                    pos_data.get("status", ""),
                    json.dumps(pos_data, cls=DecimalEncoder),
                    pos_data.get("opened_at", now),
                    pos_data.get("closed_at"),
                ))
            
            # Save orders
            for order_id, order_data in state.get("orders", {}).items():
                cursor.execute("""
                    INSERT INTO paper_orders 
                    (order_id, profile, symbol, status, data_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    order_id,
                    self.profile,
                    order_data.get("symbol", ""),
                    order_data.get("status", ""),
                    json.dumps(order_data, cls=DecimalEncoder),
                    order_data.get("created_at", now),
                ))
            
            # Save trades
            for trade_data in state.get("trade_history", []):
                cursor.execute("""
                    INSERT INTO paper_trades 
                    (trade_id, profile, symbol, side, action, data_json, executed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade_data.get("trade_id", ""),
                    self.profile,
                    trade_data.get("symbol", ""),
                    trade_data.get("side", ""),
                    trade_data.get("action", ""),
                    json.dumps(trade_data, cls=DecimalEncoder),
                    trade_data.get("executed_at", now),
                ))
            
            conn.commit()
            
        logger.info(f"State saved for profile '{self.profile}'")
    
    def load_state(self) -> Optional[dict]:
        """
        Load engine state from database.
        
        Returns:
            State dictionary or None if no saved state
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT state_json FROM paper_state WHERE profile = ?",
                (self.profile,)
            )
            row = cursor.fetchone()
            
            if row:
                state = json.loads(row["state_json"])
                logger.info(f"State loaded for profile '{self.profile}'")
                return state
            
            logger.info(f"No saved state found for profile '{self.profile}'")
            return None
    
    def delete_state(self) -> bool:
        """
        Delete saved state for current profile.
        
        Returns:
            True if state was deleted
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM paper_state WHERE profile = ?", (self.profile,))
            cursor.execute("DELETE FROM paper_positions WHERE profile = ?", (self.profile,))
            cursor.execute("DELETE FROM paper_orders WHERE profile = ?", (self.profile,))
            cursor.execute("DELETE FROM paper_trades WHERE profile = ?", (self.profile,))
            
            deleted = cursor.rowcount > 0
            conn.commit()
            
            if deleted:
                logger.info(f"State deleted for profile '{self.profile}'")
            
            return deleted
    
    def list_profiles(self) -> list:
        """
        List all saved profiles.
        
        Returns:
            List of profile names
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT profile FROM paper_state ORDER BY updated_at DESC")
            return [row["profile"] for row in cursor.fetchall()]
    
    def get_profile_info(self, profile: str = None) -> Optional[dict]:
        """
        Get information about a profile.
        
        Args:
            profile: Profile name (default: current profile)
            
        Returns:
            Dictionary with profile info or None
        """
        profile = profile or self.profile
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT profile, created_at, updated_at, 
                       LENGTH(state_json) as state_size
                FROM paper_state WHERE profile = ?
            """, (profile,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # Count positions and orders
            cursor.execute(
                "SELECT COUNT(*) as count FROM paper_positions WHERE profile = ?",
                (profile,)
            )
            positions_count = cursor.fetchone()["count"]
            
            cursor.execute(
                "SELECT COUNT(*) as count FROM paper_orders WHERE profile = ?",
                (profile,)
            )
            orders_count = cursor.fetchone()["count"]
            
            cursor.execute(
                "SELECT COUNT(*) as count FROM paper_trades WHERE profile = ?",
                (profile,)
            )
            trades_count = cursor.fetchone()["count"]
            
            return {
                "profile": row["profile"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "state_size_bytes": row["state_size"],
                "positions_count": positions_count,
                "orders_count": orders_count,
                "trades_count": trades_count,
            }
    
    def get_trade_history(
        self,
        limit: int = 100,
        symbol: str = None,
        action: str = None
    ) -> list:
        """
        Query trade history with filters.
        
        Args:
            limit: Maximum records to return
            symbol: Filter by symbol
            action: Filter by action type
            
        Returns:
            List of trade records
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT data_json FROM paper_trades WHERE profile = ?"
            params = [self.profile]
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            if action:
                query += " AND action = ?"
                params.append(action)
            
            query += " ORDER BY executed_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            
            return [json.loads(row["data_json"]) for row in cursor.fetchall()]
    
    def export_to_json(self, filepath: str) -> None:
        """
        Export state to a JSON file.
        
        Args:
            filepath: Path to export file
        """
        state = self.load_state()
        if state:
            with open(filepath, 'w') as f:
                json.dump(state, f, indent=2, cls=DecimalEncoder)
            logger.info(f"State exported to {filepath}")
        else:
            raise ValueError(f"No state found for profile '{self.profile}'")
    
    def import_from_json(self, filepath: str, engine: "PaperTradingEngine") -> None:
        """
        Import state from a JSON file.
        
        Args:
            filepath: Path to import file
            engine: Engine to restore state to
        """
        with open(filepath, 'r') as f:
            state = json.load(f)
        
        engine.import_state(state)
        self.save_state(engine)
        logger.info(f"State imported from {filepath}")


class InMemoryPaperDB:
    """
    In-memory storage for paper trading (no persistence).
    
    Useful for testing or when persistence is not needed.
    """
    
    def __init__(self):
        self._state = None
    
    def save_state(self, engine: "PaperTradingEngine") -> None:
        """Save state to memory."""
        self._state = engine.export_state()
    
    def load_state(self) -> Optional[dict]:
        """Load state from memory."""
        return self._state
    
    def delete_state(self) -> bool:
        """Delete state from memory."""
        had_state = self._state is not None
        self._state = None
        return had_state
