# /Users/mruckman1/Desktop/JobSearchResumeOptimizer1/resume-customizer/database.py
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Tuple

@dataclass
class JobApplication:
    id: Optional[int]
    timestamp: datetime
    company: str
    position: str
    input_type: str
    input_content: str
    generated_resume: str
    base_resume_file: str
    context_file: str
    keywords: str
    changes: str

class JobApplicationsDB:
    def __init__(self):
        self.db_path = Path('data/job_applications.db')
        self.setup_database()

    def setup_database(self):
        """Create the database and tables if they don't exist."""
        self.db_path.parent.mkdir(exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS job_applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    company TEXT NOT NULL,
                    position TEXT NOT NULL,
                    input_type TEXT NOT NULL,
                    input_content TEXT NOT NULL,
                    generated_resume TEXT NOT NULL,
                    base_resume_file TEXT NOT NULL,
                    context_file TEXT NOT NULL,
                    keywords TEXT NOT NULL,
                    changes TEXT NOT NULL
                )
            ''')

    def get_counters(self) -> Tuple[int, int, int]:
        """Get total, weekly, and monthly application counts."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Calculate date ranges
            now = datetime.now()
            week_start = now - timedelta(days=now.weekday())
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Get counts
            cursor.execute('SELECT COUNT(*) FROM job_applications')
            total_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM job_applications WHERE timestamp >= ?', 
                         (week_start,))
            weekly_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM job_applications WHERE timestamp >= ?', 
                         (month_start,))
            monthly_count = cursor.fetchone()[0]
            
            return total_count, weekly_count, monthly_count

    def get_tracking_start_date(self) -> datetime:
        """Get the date of the first application."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT MIN(timestamp) FROM job_applications')
            result = cursor.fetchone()[0]
            return datetime.fromisoformat(result) if result else datetime.now()

    def save_application(self, application: JobApplication) -> int:
        """Save a job application to the database and return its ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO job_applications (
                    timestamp, company, position, input_type, input_content,
                    generated_resume, base_resume_file, context_file, keywords, changes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                application.timestamp, application.company, application.position,
                application.input_type, application.input_content, application.generated_resume,
                application.base_resume_file, application.context_file,
                application.keywords, application.changes
            ))
            return cursor.lastrowid

    def get_application(self, application_id: int) -> Optional[JobApplication]:
        """Retrieve a specific job application by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM job_applications WHERE id = ?', (application_id,))
            row = cursor.fetchone()
            
            if row:
                return JobApplication(
                    id=row['id'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    company=row['company'],
                    position=row['position'],
                    input_type=row['input_type'],
                    input_content=row['input_content'],
                    generated_resume=row['generated_resume'],
                    base_resume_file=row['base_resume_file'],
                    context_file=row['context_file'],
                    keywords=row['keywords'],
                    changes=row['changes']
                )
            return None

    def get_recent_applications(self, limit: int = 10) -> List[JobApplication]:
        """Get the most recent job applications."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM job_applications ORDER BY timestamp DESC LIMIT ?',
                (limit,)
            )
            return [JobApplication(
                id=row['id'],
                timestamp=datetime.fromisoformat(row['timestamp']),
                company=row['company'],
                position=row['position'],
                input_type=row['input_type'],
                input_content=row['input_content'],
                generated_resume=row['generated_resume'],
                base_resume_file=row['base_resume_file'],
                context_file=row['context_file'],
                keywords=row['keywords'],
                changes=row['changes']
            ) for row in cursor.fetchall()]

    def search_applications(self, query: str) -> List[JobApplication]:
        """Search job applications by company or position."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM job_applications 
                WHERE company LIKE ? OR position LIKE ?
                ORDER BY timestamp DESC
            ''', (f'%{query}%', f'%{query}%'))
            
            return [JobApplication(
                id=row['id'],
                timestamp=datetime.fromisoformat(row['timestamp']),
                company=row['company'],
                position=row['position'],
                input_type=row['input_type'],
                input_content=row['input_content'],
                generated_resume=row['generated_resume'],
                base_resume_file=row['base_resume_file'],
                context_file=row['context_file'],
                keywords=row['keywords'],
                changes=row['changes']
            ) for row in cursor.fetchall()]

    def get_statistics(self) -> Dict:
        """Get application statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            stats = {}
            
            # Total applications
            cursor.execute('SELECT COUNT(*) FROM job_applications')
            stats['total_applications'] = cursor.fetchone()[0]
            
            # Applications per company
            cursor.execute('''
                SELECT company, COUNT(*) as count 
                FROM job_applications 
                GROUP BY company 
                ORDER BY count DESC
                LIMIT 5
            ''')
            stats['top_companies'] = dict(cursor.fetchall())
            
            # Applications over time
            cursor.execute('''
                SELECT date(timestamp) as date, COUNT(*) as count 
                FROM job_applications 
                GROUP BY date(timestamp) 
                ORDER BY date DESC
                LIMIT 30
            ''')
            stats['daily_applications'] = dict(cursor.fetchall())
            
            return stats