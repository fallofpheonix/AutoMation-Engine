import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import asdict


class Database:
    """SQLite database for task management"""
    
    def __init__(self, db_path: str = "tasks.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
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
                FOREIGN KEY(task_id) REFERENCES tasks(id),
                FOREIGN KEY(step_id) REFERENCES steps(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def create_task(self, task_id: str, name: str) -> bool:
        """Create a new task"""
        conn = sqlite3.connect(self.db_path)
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
            conn.close()
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """Get task details"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()
        
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
        conn = sqlite3.connect(self.db_path)
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
            conn.close()
    
    def create_step(
        self,
        step_id: str,
        task_id: str,
        step_number: int,
        action: str,
        action_params: Dict[str, Any]
    ) -> bool:
        """Create a step for a task"""
        conn = sqlite3.connect(self.db_path)
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
            conn.close()
    
    def update_step_result(
        self,
        step_id: str,
        status: str,
        duration_ms: float,
        error_message: Optional[str] = None,
        retry_count: int = 0
    ) -> bool:
        """Update step execution result"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE steps 
                SET status = ?, started_at = ?, duration_ms = ?, error_message = ?, retry_count = ?
                WHERE id = ?
            """, (
                status,
                datetime.now().isoformat(),
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
            conn.close()
    
    def log(
        self,
        task_id: str,
        message: str,
        severity: str = "info",
        step_id: Optional[str] = None,
        log_id: Optional[str] = None
    ) -> bool:
        """Add log entry"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO logs (id, task_id, step_id, message, timestamp, severity)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                log_id or f"log_{task_id}_{datetime.now().timestamp()}",
                task_id,
                step_id,
                message,
                datetime.now().isoformat(),
                severity
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error logging: {e}")
            return False
        finally:
            conn.close()
    
    def get_task_logs(self, task_id: str) -> List[Dict]:
        """Get all logs for a task"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, task_id, step_id, message, timestamp, severity
            FROM logs
            WHERE task_id = ?
            ORDER BY timestamp ASC
        """, (task_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'id': row[0],
                'task_id': row[1],
                'step_id': row[2],
                'message': row[3],
                'timestamp': row[4],
                'severity': row[5]
            }
            for row in rows
        ]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get system metrics"""
        conn = sqlite3.connect(self.db_path)
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
        
        conn.close()
        
        return {
            'total_tasks': total_tasks,
            'successful_tasks': successful,
            'success_rate': (successful / total_tasks * 100) if total_tasks > 0 else 0,
            'avg_execution_time_ms': avg_duration
        }
