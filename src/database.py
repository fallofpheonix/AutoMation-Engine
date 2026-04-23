import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import asdict


class Database:
    """SQLite database for task management"""
    
    def __init__(self, db_path: str = "tasks.db"):
        self.db_path = db_path
        self._is_in_memory = db_path == ":memory:"
        self._persistent_conn = (
            sqlite3.connect(":memory:", check_same_thread=False)
            if self._is_in_memory
            else None
        )
        self.init_db()

    def _get_connection(self):
        if self._persistent_conn is not None:
            return self._persistent_conn
        return sqlite3.connect(self.db_path)

    def _close_connection(self, conn):
        if self._persistent_conn is None:
            conn.close()
    
    def init_db(self):
        """Initialize database schema"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                name TEXT,
                status TEXT,
                created_at TEXT,
                started_at TEXT,
                completed_at TEXT
            )
        """)
        
        # Steps table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS steps (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                step_number INTEGER,
                action TEXT,
                action_params TEXT,
                status TEXT,
                started_at TEXT,
                duration_ms INTEGER,
                error_message TEXT,
                retry_count INTEGER,
                FOREIGN KEY(task_id) REFERENCES tasks(id)
            )
        """)
        
        # Logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                step_id TEXT,
                message TEXT,
                timestamp TEXT,
                severity TEXT,
                action TEXT,
                params TEXT,
                status TEXT,
                duration_ms INTEGER,
                error TEXT,
                FOREIGN KEY(task_id) REFERENCES tasks(id),
                FOREIGN KEY(step_id) REFERENCES steps(id)
            )
        """)

        self._ensure_log_columns(cursor)
        
        conn.commit()
        self._close_connection(conn)

    def _ensure_log_columns(self, cursor):
        """Best-effort schema upgrade for older log tables."""
        cursor.execute("PRAGMA table_info(logs)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        required_columns = {
            "action": "TEXT",
            "params": "TEXT",
            "status": "TEXT",
            "duration_ms": "INTEGER",
            "error": "TEXT",
        }

        for column_name, column_type in required_columns.items():
            if column_name not in existing_columns:
                cursor.execute(f"ALTER TABLE logs ADD COLUMN {column_name} {column_type}")
    
    def create_task(self, task_id: str, name: str) -> bool:
        """Create a new task"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO tasks (id, name, status, created_at)
                VALUES (?, ?, ?, ?)
            """, (task_id, name, "pending", datetime.now().isoformat()))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error creating task: {e}")
            return False
        finally:
            self._close_connection(conn)
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """Get task details"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        self._close_connection(conn)
        
        if row:
            return {
                'id': row[0],
                'name': row[1],
                'status': row[2],
                'created_at': row[3],
                'started_at': row[4],
                'completed_at': row[5]
            }
        return None
    
    def update_task_status(self, task_id: str, status: str) -> bool:
        """Update task status"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            if status == "running":
                cursor.execute(
                    "UPDATE tasks SET status = ?, started_at = ? WHERE id = ?",
                    (status, datetime.now().isoformat(), task_id)
                )
            elif status in ["success", "failed"]:
                cursor.execute(
                    "UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?",
                    (status, datetime.now().isoformat(), task_id)
                )
            else:
                cursor.execute(
                    "UPDATE tasks SET status = ? WHERE id = ?",
                    (status, task_id)
                )
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating task: {e}")
            return False
        finally:
            self._close_connection(conn)
    
    def create_step(
        self,
        step_id: str,
        task_id: str,
        step_number: int,
        action: str,
        action_params: Dict[str, Any]
    ) -> bool:
        """Create a step for a task"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO steps 
                (id, task_id, step_number, action, action_params, status, retry_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                step_id,
                task_id,
                step_number,
                action,
                json.dumps(action_params),
                "pending",
                0
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error creating step: {e}")
            return False
        finally:
            self._close_connection(conn)
    
    def update_step_status(self, step_id: str, status: str) -> bool:
        """Update step status during execution lifecycle"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            if status == "running":
                cursor.execute(
                    "UPDATE steps SET status = ?, started_at = ? WHERE id = ?",
                    (status, datetime.now().isoformat(), step_id)
                )
            else:
                cursor.execute(
                    "UPDATE steps SET status = ? WHERE id = ?",
                    (status, step_id)
                )
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating step status: {e}")
            return False
        finally:
            self._close_connection(conn)

    def update_step_result(
        self,
        step_id: str,
        duration_ms: float,
        error_message: Optional[str] = None,
        retry_count: int = 0
    ) -> bool:
        """Update step execution result"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE steps 
                SET duration_ms = ?, error_message = ?, retry_count = ?
                WHERE id = ?
            """, (
                duration_ms,
                error_message,
                retry_count,
                step_id
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating step: {e}")
            return False
        finally:
            self._close_connection(conn)
    
    def log(
        self,
        task_id: str,
        message: str,
        severity: str = "info",
        step_id: Optional[str] = None,
        log_id: Optional[str] = None,
        action: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        duration_ms: Optional[float] = None,
        error: Optional[str] = None
    ) -> bool:
        """Add log entry"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO logs (
                    id, task_id, step_id, message, timestamp, severity,
                    action, params, status, duration_ms, error
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id or f"log_{task_id}_{datetime.now().timestamp()}",
                task_id,
                step_id,
                message,
                datetime.now().isoformat(),
                severity,
                action,
                json.dumps(params) if params is not None else None,
                status,
                duration_ms,
                error
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error logging: {e}")
            return False
        finally:
            self._close_connection(conn)
    
    def get_task_logs(self, task_id: str) -> List[Dict]:
        """Get all logs for a task"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT
                id, task_id, step_id, message, timestamp, severity,
                action, params, status, duration_ms, error
            FROM logs
            WHERE task_id = ?
            ORDER BY timestamp ASC
        """, (task_id,))
        
        rows = cursor.fetchall()
        self._close_connection(conn)
        
        return [
            {
                'id': row[0],
                'task_id': row[1],
                'step_id': row[2],
                'message': row[3],
                'timestamp': row[4],
                'severity': row[5],
                'action': row[6],
                'params': json.loads(row[7]) if row[7] else None,
                'status': row[8],
                'duration_ms': row[9],
                'error': row[10]
            }
            for row in rows
        ]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get system metrics"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Total tasks
        cursor.execute("SELECT COUNT(*) FROM tasks")
        total_tasks = cursor.fetchone()[0]
        
        # Success count
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'success'")
        successful = cursor.fetchone()[0]
        
        # Average duration
        cursor.execute("SELECT AVG(duration_ms) FROM steps WHERE status = 'success'")
        avg_duration = cursor.fetchone()[0] or 0
        
        self._close_connection(conn)
        
        return {
            'total_tasks': total_tasks,
            'successful_tasks': successful,
            'success_rate': (successful / total_tasks * 100) if total_tasks > 0 else 0,
            'avg_execution_time_ms': avg_duration
        }
