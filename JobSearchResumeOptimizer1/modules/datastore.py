# modules/datastore.py

import sqlite3
import logging

class DataStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER,
                job_title TEXT,
                company TEXT,
                location TEXT,
                base_compensation TEXT,
                job_description TEXT,
                resume_path TEXT,
                url TEXT
            )
        ''')
        self.conn.commit()

    def save_job_application(self, job: dict, resume_path: str):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO job_applications (job_id, job_title, company, location, base_compensation, job_description, resume_path, url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            job.get('id'),
            job.get('title', ''),
            job.get('company', ''),
            job.get('location', ''),
            job.get('base_compensation', ''),
            job.get('description', ''),
            resume_path,
            job.get('url', '')
        ))
        self.conn.commit()
