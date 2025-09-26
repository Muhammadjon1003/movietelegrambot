"""
Database operations for the Telegram Video Indexer Bot.
Handles SQLite database operations for storing and searching videos.
"""
import sqlite3
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class VideoDatabase:
    """Handles all database operations for video indexing."""
    
    def __init__(self, db_path: str):
        """Initialize the database connection and create tables if they don't exist."""
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Create the videos and movies tables with the specified schemas."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create videos table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    file_id TEXT NOT NULL,
                    caption TEXT,
                    codes TEXT,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create movies table for the menu system
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS movies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    channel_message_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    file_id TEXT NOT NULL
                )
            """)
            
            # Create pending_movies table for videos with hashtags but no title/category
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pending_movies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL,
                    channel_message_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    file_id TEXT NOT NULL,
                    caption TEXT,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for fast lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_codes ON videos(codes)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_movie_code ON movies(code)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_movie_category ON movies(category)
            """)
            
            conn.commit()
            logger.info("Database initialized successfully with videos and movies tables")
    
    def save_video(self, chat_id: int, message_id: int, file_id: str, caption: str, date: datetime = None) -> bool:
        """Save a video to the database with extracted hashtags as codes."""
        try:
            if date is None:
                date = datetime.now()
            
            # Extract hashtags from caption and format them as codes
            codes = self.extract_hashtags_as_codes(caption)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO videos (
                        chat_id, message_id, file_id, caption, codes, date
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (chat_id, message_id, file_id, caption or '', codes, date))
                
                conn.commit()
                logger.info(f"Video saved: chat_id={chat_id}, message_id={message_id}, codes={codes}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Error saving video to database: {e}")
            return False
    
    def extract_hashtags_as_codes(self, text: str) -> str:
        """Extract hashtags from text and return them as a space-separated string."""
        if not text:
            return ""
        
        hashtag_pattern = r'#\w+'
        hashtags = re.findall(hashtag_pattern, text, re.IGNORECASE)
        return ' '.join(hashtags)
    
    def get_categories(self) -> List[str]:
        """Get all unique categories from the movies table."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT DISTINCT category FROM movies 
                    ORDER BY category ASC
                """)
                
                categories = [row[0] for row in cursor.fetchall()]
                logger.info(f"Retrieved {len(categories)} categories: {categories}")
                return categories
                
        except sqlite3.Error as e:
            logger.error(f"Error getting categories: {e}")
            return []
    
    def get_movies_by_category(self, category: str, page: int = 1, per_page: int = 5) -> Tuple[List[Dict], int]:
        """Get movies from a specific category with pagination."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get total count
                cursor.execute("""
                    SELECT COUNT(*) FROM movies WHERE category = ?
                """, (category,))
                total_count = cursor.fetchone()[0]
                
                # Calculate offset
                offset = (page - 1) * per_page
                
                # Get paginated results
                cursor.execute("""
                    SELECT * FROM movies 
                    WHERE category = ? 
                    ORDER BY code ASC
                    LIMIT ? OFFSET ?
                """, (category, per_page, offset))
                
                movies = []
                for row in cursor.fetchall():
                    movies.append(dict(row))
                
                logger.info(f"Retrieved {len(movies)} movies from category '{category}' (page {page})")
                return movies, total_count
                
        except sqlite3.Error as e:
            logger.error(f"Error getting movies by category: {e}")
            return [], 0
    
    def get_movie_by_code(self, code: str) -> Optional[Dict]:
        """Get a movie by its code."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM movies WHERE code = ?
                """, (code,))
                
                row = cursor.fetchone()
                if row:
                    movie = dict(row)
                    logger.info(f"Found movie: {movie['title']} (code: {code})")
                    return movie
                else:
                    logger.info(f"Movie not found for code: {code}")
                    return None
                    
        except sqlite3.Error as e:
            logger.error(f"Error getting movie by code: {e}")
            return None
    
    def add_movie(self, code: str, title: str, category: str, channel_message_id: int, channel_id: int, file_id: str) -> bool:
        """Add a new movie to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO movies (code, title, category, channel_message_id, channel_id, file_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (code, title, category, channel_message_id, channel_id, file_id))
                
                conn.commit()
                logger.info(f"Movie added: {title} (code: {code}, category: {category}, channel_msg: {channel_message_id})")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Error adding movie: {e}")
            return False
    
    def search_channel_by_hashtag(self, hashtag: str) -> List[Dict]:
        """Search for hashtag codes in channel videos."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Search in videos table for the hashtag
                cursor.execute("""
                    SELECT * FROM videos 
                    WHERE codes LIKE ?
                    ORDER BY date DESC
                """, (f"%{hashtag}%",))
                
                results = []
                for row in cursor.fetchall():
                    video = dict(row)
                    video['type'] = 'video'
                    results.append(video)
                
                logger.info(f"Channel hashtag search '{hashtag}' returned {len(results)} results")
                return results
                
        except sqlite3.Error as e:
            logger.error(f"Error searching channel by hashtag: {e}")
            return []
    
    def add_pending_movie(self, code: str, channel_message_id: int, channel_id: int, file_id: str, caption: str = '') -> bool:
        """Add a pending movie (video with hashtag but no title/category)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO pending_movies (code, channel_message_id, channel_id, file_id, caption)
                    VALUES (?, ?, ?, ?, ?)
                """, (code, channel_message_id, channel_id, file_id, caption))
                
                conn.commit()
                logger.info(f"Pending movie added: {code} (channel_msg: {channel_message_id})")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Error adding pending movie: {e}")
            return False
    
    def get_pending_movies(self) -> List[Dict]:
        """Get all pending movies (videos with hashtags but no title/category)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM pending_movies 
                    ORDER BY date DESC
                """)
                
                results = []
                for row in cursor.fetchall():
                    results.append(dict(row))
                
                logger.info(f"Retrieved {len(results)} pending movies")
                return results
                
        except sqlite3.Error as e:
            logger.error(f"Error getting pending movies: {e}")
            return []
    
    def get_pending_movie_by_code(self, code: str) -> Dict:
        """Get a specific pending movie by code."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM pending_movies 
                    WHERE code = ?
                """, (code,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Error getting pending movie by code {code}: {e}")
            return None
    
    def remove_pending_movie(self, code: str) -> bool:
        """Remove a pending movie after it's been processed."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM pending_movies WHERE code = ?
                """, (code,))
                
                conn.commit()
                logger.info(f"Pending movie removed: {code}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Error removing pending movie: {e}")
            return False