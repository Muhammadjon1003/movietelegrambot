"""
Bot handlers for the Telegram Video Indexer Bot.
Handles commands, channel post processing, and dynamic menu system.
"""
import logging
from datetime import datetime
from typing import List, Dict
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from database import VideoDatabase
from config import Config

logger = logging.getLogger(__name__)

class BotHandlers:
    """Handles all bot commands, message processing, and menu navigation."""
    
    def __init__(self, database: VideoDatabase):
        """Initialize handlers with database connection."""
        self.db = database
        self.pending_movies = {}  # Store pending movie data while waiting for file
        self.user_states = {}  # Store user navigation state (genre, page, etc.)
    
    def is_admin(self, user_id: int) -> bool:
        """Check if the user is an admin - always return True to allow everyone."""
        return True
    
    def get_reply_keyboard(self, user_id: int) -> ReplyKeyboardMarkup:
        """Get the appropriate reply keyboard for the user."""
        reply_keyboard = [
            [KeyboardButton("📁 Kategoriya bo'yicha ko'rish"), KeyboardButton("🔍 Kod bo'yicha qidirish")],
            [KeyboardButton("📚 Yordam"), KeyboardButton("ℹ️ Ma'lumot")],
            [KeyboardButton("🏠 Asosiy menyu")]
        ]
        return ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, is_persistent=True)
    
    async def addmovie_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /addmovie command - show pending movies from channel."""
        # Get pending movies from channel
        pending_movies = self.db.get_pending_movies()
        
        if not pending_movies:
            await update.message.reply_text(
                "📭 Kutilayotgan filmlar topilmadi.\n\n"
                "Filmlar qo'shish uchun:\n"
                "1. Videolarni kanalingizga xeshteglar bilan joylang (masalan, #M001)\n"
                "2. Bu buyruqdan foydalanib sarlavha va kategoriyalarni qo'shing\n"
                "3. Filmlar /categories va /search da ko'rinadi"
            )
            return
        
        # Create inline keyboard with pending movies
        keyboard = []
        for movie in pending_movies[:10]:  # Show max 10 pending movies
            code = movie['code']
            caption = movie.get('caption', 'Sarlavha yo\'q')
            if len(caption) > 30:
                caption = caption[:30] + '...'
            
            # Check if code already exists in movies table
            existing_movie = self.db.get_movie_by_code(code)
            if existing_movie:
                button_text = f"⚠️ {code} - {caption} (MAVJUD)"
            else:
                button_text = f"🎬 {code} - {caption}"
            
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"add_movie_{code}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "🎬 *Kanaldan kutilayotgan filmlar*\n\n"
        text += "Quyidagi filmlar sarlavha va kategoriya kutmoqda. Birini tanlang:"
        
        await update.message.reply_text(
            text=text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command - send welcome message and show main menu."""
        welcome_text = """
🎬 *Film Kutubxonasi Botiga xush kelibsiz!*

Men sizga kolleksiyamizdan filmlarni topish va ko'rishda yordam bera olaman.

Boshlash uchun quyidagi variantlardan birini tanlang:
        """
        
        reply_markup = self.get_reply_keyboard(update.effective_user.id)
        
        await update.message.reply_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command - look up movie by code and send video/file."""
        if not context.args:
            await update.message.reply_text(
                "🔍 *Kod bo'yicha qidirish*\n\n"
                "Qidirmoqchi bo'lgan film kodingizni yuboring.\n\n"
                "Faqat kodni yozing va yuboring!",
                parse_mode='Markdown'
            )
            return
        
        code = context.args[0]
        logger.info(f"Search code: {code}")
        
        # Show typing indicator
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action='typing'
        )
        
        # Search for the code and send results
        await self._search_and_send_results(update, context, code)
    
    async def _search_and_send_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE, code: str):
        """Search for a code and send the results."""
        results = []
        found_codes = set()  # Track codes we've already found to avoid duplicates
        
        # Search both database movies AND channel videos
        # First, try database movies
        movie = self.db.get_movie_by_code(code)
        if movie:
            # Validate that the code still exists and hasn't changed
            if await self._validate_movie_code(movie, code):
                movie['type'] = 'movie'
                results.append(movie)
                found_codes.add(code)
                logger.info(f"Found movie in database: {movie['title']} ({code})")
            else:
                logger.warning(f"Movie code {code} validation failed - code may have changed")
        
        # Only search for channel videos if no database movie was found
        if not results:
            channel_results = self.db.search_channel_by_hashtag(f"#{code}")
            logger.info(f"Channel search for #{code} returned {len(channel_results)} results")
            for channel_result in channel_results:
                logger.info(f"Channel result: {channel_result.get('codes', 'no codes')}")
                if channel_result.get('codes') and f"#{code}" in channel_result.get('codes', ''):
                    # Validate channel video code
                    if await self._validate_channel_code(channel_result, code):
                        channel_result['type'] = 'video'
                        results.append(channel_result)
                        found_codes.add(f"#{code}")
                        logger.info(f"Added channel video #{code} to results")
                        break  # Only take the first channel video found
                    else:
                        logger.warning(f"Channel video code {code} validation failed")
        
        # If we found any results, send them immediately
        if results:
            await self._send_search_results(update, context, results, code)
            return
        
        # Only try prefixes if:
        # 1. No exact match found
        # 2. Code is 1-3 digits (not 4+ digits like 1001, 0001)
        # 3. Code doesn't start with 0 (to avoid confusion with 001 vs M001)
        if code.isdigit() and len(code) <= 3 and not code.startswith('0'):
            prefixes = ['M', 'A', 'C', 'D', 'H', 'S', 'F', 'T']
            for prefix in prefixes:
                full_code = f"{prefix}{code}"
                movie = self.db.get_movie_by_code(full_code)
                if movie:
                    movie['type'] = 'movie'
                    results.append(movie)
                    found_codes.add(full_code)
                    break
            
            # If not found in movies, try channel videos
            if not results:
                for prefix in prefixes:
                    full_code = f"{prefix}{code}"
                    channel_results = self.db.search_channel_by_hashtag(f"#{full_code}")
                    for channel_result in channel_results:
                        if channel_result.get('codes') and f"#{full_code}" in channel_result.get('codes', ''):
                            channel_result['type'] = 'video'
                            results.append(channel_result)
                            break
                    if results:
                        break
        
        if results:
            await self._send_search_results(update, context, results, code)
        else:
            reply_markup = self.get_reply_keyboard(update.effective_user.id)
            await update.message.reply_text("❌ Film topilmadi.", reply_markup=reply_markup)
    
    async def _validate_movie_code(self, movie: Dict, code: str) -> bool:
        """Validate that a movie code still exists and hasn't changed."""
        try:
            # Re-check the movie in database to ensure it still exists
            current_movie = self.db.get_movie_by_code(code)
            if not current_movie:
                logger.warning(f"Movie {code} no longer exists in database")
                return False
            
            # Check if the movie data matches (title, category, etc.)
            if (current_movie['title'] != movie['title'] or 
                current_movie['category'] != movie['category'] or
                current_movie['code'] != movie['code']):
                logger.warning(f"Movie {code} data has changed")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error validating movie code {code}: {e}")
            return False
    
    async def _validate_channel_code(self, channel_result: Dict, code: str) -> bool:
        """Validate that a channel video code still exists and hasn't changed."""
        try:
            # Re-check the channel video to ensure it still exists
            current_channel_results = self.db.search_channel_by_hashtag(f"#{code}")
            if not current_channel_results:
                logger.warning(f"Channel video {code} no longer exists")
                return False
            
            # Check if the channel video data matches
            for current_result in current_channel_results:
                if (current_result.get('chat_id') == channel_result.get('chat_id') and
                    current_result.get('message_id') == channel_result.get('message_id')):
                    return True
                    
            logger.warning(f"Channel video {code} data has changed")
            return False
        except Exception as e:
            logger.error(f"Error validating channel code {code}: {e}")
            return False

    async def _send_search_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE, results: List[Dict], code: str):
        """Send search results to the user."""
        reply_markup = self.get_reply_keyboard(update.effective_user.id)
        
        for result in results:
            try:
                if result['type'] == 'movie':
                    await context.bot.send_video(
                        chat_id=update.effective_chat.id,
                        video=result['file_id'],
                        caption=f"🎬 *{result['title']}*\n📁 Kategoriya: {result['category']}\n🔢 Kod: {result['code']}",
                        parse_mode='Markdown',
                        reply_markup=reply_markup
                    )
                elif result['type'] == 'video':
                    try:
                        await context.bot.forward_message(
                            chat_id=update.effective_chat.id,
                            from_chat_id=result['chat_id'],
                            message_id=result['message_id']
                        )
                        # Send keyboard after forwarding
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=f"📤 Video yuborildi! Davom etish uchun quyidagi tugmalardan foydalaning.",
                            reply_markup=reply_markup
                        )
                    except Exception:
                        # If forwarding fails, send the file directly
                        await context.bot.send_video(
                            chat_id=update.effective_chat.id,
                            video=result['file_id'],
                            caption=f"📹 #{code} kodi bilan video\n{result.get('caption', '')}",
                            reply_markup=reply_markup
                        )
            except Exception as e:
                logger.error(f"Error sending {result.get('type', 'unknown')} {result.get('code', 'unknown')}: {e}")
                await update.message.reply_text(
                    f"❌ {result.get('title', 'Content')} yuborishda xatolik.",
                    reply_markup=reply_markup
                )
    
    async def categories_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /categories command - show genres first, then movies."""
        categories = self.db.get_categories()
        
        if not categories:
            await update.message.reply_text("❌ Kategoriyalar topilmadi.")
            return
        
        text = "📁 *Mavjud janrlar*\n\n"
        text += "Filmlarni ko'rish uchun janrni tanlang:\n\n"
        
        # Create reply keyboard with genre buttons
        keyboard = []
        for category in categories:
            # Get movie count for this category (database movies only for count)
            movies, total_count = self.db.get_movies_by_category(category, page=1, per_page=1)
            keyboard.append([KeyboardButton(f"📁 {category} ({total_count} film)")])
        
        # Add navigation buttons
        keyboard.append([KeyboardButton("🏠 Asosiy menyu")])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)
        
        await update.message.reply_text(
            text=text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def show_movies_in_genre(self, update: Update, context: ContextTypes.DEFAULT_TYPE, genre: str, page: int = 1):
        """Show movies in a specific genre with pagination."""
        try:
            movies_per_page = 8
            # Get database movies for this genre
            db_movies, db_total_count = self.db.get_movies_by_category(genre, page=page, per_page=movies_per_page)
            
            if not db_movies:
                reply_markup = self.get_reply_keyboard(update.effective_user.id)
                await update.message.reply_text(
                    f"❌ '{genre}' janrida filmlar topilmadi.",
                    reply_markup=reply_markup
                )
                return
            
            # Calculate pagination info
            total_pages = (db_total_count + movies_per_page - 1) // movies_per_page
            start_movie = (page - 1) * movies_per_page + 1
            end_movie = min(page * movies_per_page, db_total_count)
            
            text = f"🎬 *{genre} janridagi filmlar*\n\n"
            text += f"📊 {db_total_count} filmdan {start_movie}-{end_movie} ko'rsatilmoqda\n"
            if total_pages > 1:
                text += f"📄 {total_pages} sahifadan {page}-sahifa\n"
            text += "\nQuyidagi tugmalardan filmni tanlang:\n\n"
            
            # Create reply keyboard with movie buttons
            keyboard = []
            for movie in db_movies:
                keyboard.append([KeyboardButton(f"🎬 {movie['title']} ({movie['code']})")])
            
            # Add pagination buttons if needed
            if total_pages > 1:
                pagination_row = []
                if page > 1:
                    pagination_row.append(KeyboardButton("⬅️ Oldingi sahifa"))
                if page < total_pages:
                    pagination_row.append(KeyboardButton("➡️ Keyingi sahifa"))
                if pagination_row:
                    keyboard.append(pagination_row)
            
            # Add navigation buttons
            keyboard.append([KeyboardButton("⬅️ Janrlarga qaytish"), KeyboardButton("🏠 Asosiy menyu")])
            
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)
            
            await update.message.reply_text(
                text=text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in show_movies_in_genre: {e}")
            reply_markup = self.get_reply_keyboard(update.effective_user.id)
            await update.message.reply_text(
                "❌ Filmlarni yuklashda xatolik. Qaytadan urinib ko'ring.",
                reply_markup=reply_markup
            )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command - explain how to use the bot."""
        help_text = """
📚 <b>Film Kutubxonasi Botidan foydalanish</b>

<b>Mavjud buyruqlar:</b>
• /start - Xush kelish xabari va asosiy menyu
• /search &lt;kod&gt; - Filmni kodi bo'yicha qidirish
• /categories - Filmlarni kategoriya bo'yicha ko'rish
• /help - Bu yordam xabarini ko'rsatish
• /about - Bot haqida ma'lumot

<b>Qanday qidirish:</b>
• Filmni kodi bo'yicha topish uchun /search 001 ishlating
• Misol: /search 001 "Chennay Express" ni topadi
• Faqat raqamli kodlarni ishlating

<b>Qanday ko'rish:</b>
• Barcha mavjud kategoriyalarni ko'rish uchun /categories ishlating
• Kategoriyaga bosib, o'sha kategoriyadagi filmlarni ko'ring
• Ko'p filmlar orasida harakatlanish uchun sahifa tugmalaridan foydalaning

<b>Maslahatlar:</b>
• Barcha filmlar noyob raqamli kodlarga ega (001, 002, 003 va boshqalar)
• Yangi filmlar qo'shilganda kategoriyalar avtomatik yangilanadi
• Sahifada 5 tagacha filmni ko'rishingiz mumkin
• Qo'llab-quvvatlash uchun: @muhammadjon_yangiboyev
        """
        
        await update.message.reply_text(
            help_text,
            parse_mode='HTML'
        )
    
    async def about_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /about command - give info about the bot."""
        about_text = """
🤖 <b>Film Kutubxonasi Boti</b>

<b>Haqida:</b>
Bu bot kategoriyalar bo'yicha tashkil etilgan tanlangan film kolleksiyasiga kirish imkonini beradi.

<b>Imkoniyatlar:</b>
• 🎬 Filmlarni kategoriya bo'yicha ko'rish
• 🔍 Filmlarni noyob kodlar bo'yicha qidirish
• 📄 Oson navigatsiya uchun sahifalash
• 🆕 Yangi filmlar qo'shilganda avtomatik yangilanish

<b>Aloqa:</b>
Qo'llab-quvvatlash yoki takliflar uchun: @muhammadjon_yangiboyev
        """
        
        await update.message.reply_text(
            about_text,
            parse_mode='HTML'
        )
    
    async def channel_post_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle channel posts to index videos."""
        message = update.channel_post
        
        # Check if the post has a video or video-document
        video = message.video or message.video_note
        if not video:
            logger.debug(f"Message {message.message_id} doesn't contain video, skipping")
            return
        
        # Save video to database
        success = self.db.save_video(
            chat_id=message.chat.id,
            message_id=message.message_id,
            file_id=video.file_id,
            caption=message.caption or '',
            date=datetime.now()
        )
        
        if success:
            # Extract hashtags and save as pending movies
            codes = self.db.extract_hashtags_as_codes(message.caption or '')
            if codes:
                # Split codes and save each as pending movie
                code_list = codes.split()
                for code in code_list:
                    # Remove # prefix for storage
                    clean_code = code.replace('#', '')
                    
                    # Check if code already exists in movies table
                    existing_movie = self.db.get_movie_by_code(clean_code)
                    if existing_movie:
                        print(f"⚠️  WARNING: Code '{clean_code}' already exists!")
                        print(f"   Existing movie: {existing_movie['title']} ({existing_movie['category']})")
                        print(f"   New video will overwrite pending movie for this code")
                        print()
                    
                    self.db.add_pending_movie(
                        code=clean_code,
                        channel_message_id=message.message_id,
                        channel_id=message.chat.id,
                        file_id=video.file_id,
                        caption=message.caption or ''
                    )
            
            print(f"📹 Video indexed from channel {message.chat.username}")
            print(f"   Message ID: {message.message_id}")
            print(f"   Codes indexed: {codes if codes else 'None'}")
            if message.caption:
                print(f"   Caption: {message.caption[:100]}{'...' if len(message.caption) > 100 else ''}")
            print()
        else:
            print(f"❌ Failed to index video from channel {message.chat.username}")
            print(f"   Message ID: {message.message_id}")
            print()
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard button presses."""
        query = update.callback_query
        await query.answer()
        
        logger.info(f"Callback received: {query.data}")
        
        if query.data.startswith("add_movie_"):
            code = query.data.replace("add_movie_", "")
            user_id = query.from_user.id
            
            # Get pending movie data
            pending_movie = self.db.get_pending_movie_by_code(code)
            if not pending_movie:
                await query.edit_message_text("❌ Bu film kutilayotgan filmlar ro'yxatida topilmadi.")
                return
            
            # Start step-by-step movie addition process
            self.pending_movies[user_id] = {
                'code': code,
                'channel_message_id': pending_movie['channel_message_id'],
                'channel_id': pending_movie['channel_id'],
                'file_id': pending_movie['file_id'],
                'pending_movie': True,
                'step': 'title'
            }
            
            await query.edit_message_text(
                f"🎬 *Film qo'shilmoqda: {code}*\n\n"
                f"Original sarlavha: `{pending_movie['caption']}`\n\n"
                f"**1/2-qadam: Film sarlavhasini yuboring**\n\n"
                f"Faqat film sarlavhasini yozing va yuboring.\n"
                f"Misol: `Avengers: Endgame`",
                parse_mode='Markdown'
            )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages (non-commands) and file uploads."""
        user_id = update.effective_user.id
        
        # Handle reply keyboard button presses
        if update.message.text:
            text = update.message.text.strip()
            
            # Handle direct code search (only numbers)
            if len(text) <= 10 and text.isdigit() and not text.startswith(("📁", "🔍", "📚", "ℹ️", "🏠", "⬅️", "🎬")):
                # Use the same search logic as the search command
                await self._search_and_send_results(update, context, text)
                return
            
            if text == "📁 Kategoriya bo'yicha ko'rish":
                await self.categories_command(update, context)
                return
            elif text == "🔍 Kod bo'yicha qidirish":
                await self.search_command(update, context)
                return
            elif text == "📚 Yordam":
                await self.help_command(update, context)
                return
            elif text == "ℹ️ Ma'lumot":
                await self.about_command(update, context)
                return
            elif text == "🏠 Asosiy menyu":
                await self.start(update, context)
                return
            elif text.startswith("📁 ") and user_id in self.pending_movies:
                # Handle genre selection for movie addition
                try:
                    if self.pending_movies[user_id].get('step') == 'category':
                        genre = text.replace("📁 ", "")
                        movie_data = self.pending_movies[user_id]
                        
                        # Get all data and add movie
                        title = movie_data['title']
                        code = movie_data['code']
                        
                        # Get pending movie data from database
                        pending_movie = self.db.get_pending_movie_by_code(code)
                        if not pending_movie:
                            await update.message.reply_text("❌ Kutilayotgan film ma'lumotlari topilmadi.")
                            return
                        
                        # Add movie to database
                        success = self.db.add_movie(
                            code=code,
                            title=title,
                            category=genre,
                            channel_message_id=pending_movie['channel_message_id'],
                            channel_id=pending_movie['channel_id'],
                            file_id=pending_movie['file_id']
                        )
                        
                        if success:
                            # Remove from pending movies
                            self.db.remove_pending_movie(code)
                            del self.pending_movies[user_id]
                            
                            # Reset keyboard to main menu
                            reply_markup = self.get_reply_keyboard(user_id)
                            
                            await update.message.reply_text(
                                f"🎉 **Film muvaffaqiyatli qo'shildi!**\n\n"
                                f"🎬 **Sarlavha:** {title}\n"
                                f"📁 **Kategoriya:** {genre}\n"
                                f"🔢 **Kod:** {code}\n\n"
                                f"✅ Film endi `/categories` va `/search` da mavjud!",
                                parse_mode='Markdown',
                                reply_markup=reply_markup
                            )
                            logger.info(f"User {user_id} added movie: {title} ({code}) in category {genre}")
                        else:
                            await update.message.reply_text(
                                f"❌ *{title}* (`{code}`) filmini qo'shishda xatolik. "
                                "Bu kod bilan film allaqachon mavjud bo'lishi mumkin."
                            )
                        return
                except Exception as e:
                    logger.error(f"Error processing genre selection: {e}")
                    await update.message.reply_text("❌ Kategoriya tanlashda xatolik yuz berdi.")
                    return
            elif text == "➕ Yangi kategoriya qo'shish" and user_id in self.pending_movies:
                # Handle adding new category
                try:
                    if self.pending_movies[user_id].get('step') == 'category':
                        await update.message.reply_text(
                            "📝 Yangi kategoriya nomini yuboring:\n\n"
                            "Misol: `Fantasy`, `Documentary`, `Musical` va boshqalar.",
                            parse_mode='Markdown'
                        )
                        # Change step to 'new_category' to handle text input
                        self.pending_movies[user_id]['step'] = 'new_category'
                        return
                except Exception as e:
                    logger.error(f"Error handling new category: {e}")
                    await update.message.reply_text("❌ Yangi kategoriya qo'shishda xatolik.")
                    return
            elif text == "⬅️ Janrlarga qaytish":
                # Clear user state when going back to genres
                if user_id in self.user_states:
                    del self.user_states[user_id]
                await self.categories_command(update, context)
                return
            elif text.startswith("📁 "):
                # Handle genre button press - extract genre name
                try:
                    # Extract genre from button text like "📁 Action (5 movies)"
                    # Remove the 📁 prefix and split by " (" to get the genre name
                    genre = text.replace("📁 ", "").split(" (")[0]
                    # Store user state for pagination
                    self.user_states[user_id] = {'genre': genre, 'page': 1}
                    await self.show_movies_in_genre(update, context, genre, page=1)
                    return
                except Exception as e:
                    logger.error(f"Error handling genre button: {e}")
                    await update.message.reply_text("❌ Error processing genre selection.")
                    return
            elif text.startswith("🎬 "):
                # Handle movie button press - extract code from button text
                try:
                    # Extract code from button text like "🎬 Movie Title (A001)"
                    if "(" in text and ")" in text:
                        code = text.split("(")[-1].split(")")[0]
                        await self.send_movie_by_code(update, context, code)
                        return
                except Exception as e:
                    logger.error(f"Error handling movie button: {e}")
                    await update.message.reply_text("❌ Error processing movie selection.")
                    return
            elif text == "⬅️ Oldingi sahifa":
                # Handle previous page button
                try:
                    if user_id in self.user_states:
                        state = self.user_states[user_id]
                        current_page = state.get('page', 1)
                        if current_page > 1:
                            new_page = current_page - 1
                            state['page'] = new_page
                            await self.show_movies_in_genre(update, context, state['genre'], new_page)
                            return
                        else:
                            await update.message.reply_text("❌ Siz allaqachon birinchi sahifadasiz.")
                            return
                    else:
                        await update.message.reply_text("❌ Navigatsiya holati topilmadi. Avval kategoriyani tanlang.")
                        return
                except Exception as e:
                    logger.error(f"Error handling previous page: {e}")
                    await update.message.reply_text("❌ Oldingi sahifaga o'tishda xatolik. Qaytadan urinib ko'ring.")
                    return
            elif text == "➡️ Keyingi sahifa":
                # Handle next page button
                try:
                    if user_id in self.user_states:
                        state = self.user_states[user_id]
                        current_page = state.get('page', 1)
                        genre = state.get('genre', '')
                        
                        if not genre:
                            await update.message.reply_text("❌ Janr tanlanmagan. Avval kategoriyani tanlang.")
                            return
                        
                        # Get total count to check if there's a next page
                        _, total_count = self.db.get_movies_by_category(genre, page=1, per_page=8)
                        total_pages = (total_count + 8 - 1) // 8
                        
                        if current_page < total_pages:
                            new_page = current_page + 1
                            state['page'] = new_page
                            await self.show_movies_in_genre(update, context, genre, new_page)
                            return
                        else:
                            await update.message.reply_text("❌ Siz allaqachon oxirgi sahifadasiz.")
                            return
                    else:
                        await update.message.reply_text("❌ Navigatsiya holati topilmadi. Avval kategoriyani tanlang.")
                        return
                except Exception as e:
                    logger.error(f"Error handling next page: {e}")
                    await update.message.reply_text("❌ Keyingi sahifaga o'tishda xatolik. Qaytadan urinib ko'ring.")
                    return
        
        # Check if user has a pending movie upload
        if user_id in self.pending_movies:
            movie_data = self.pending_movies[user_id]
            
            # Check if this is a pending movie from channel (has pending_movie key)
            if 'pending_movie' in movie_data:
                # Step-by-step movie addition process
                try:
                    message_text = update.message.text.strip()
                    
                    # Step 1: Get title
                    if movie_data.get('step') == 'title':
                        if not message_text:
                            await update.message.reply_text("❌ To'g'ri film sarlavhasini kiriting.")
                            return
                        
                        # Store title and show genre selection buttons
                        movie_data['title'] = message_text
                        movie_data['step'] = 'category'
                        
                        # Create genre selection keyboard
                        keyboard = [
                            [KeyboardButton("📁 Hind kinolar")],
                            [KeyboardButton("➕ Yangi kategoriya qo'shish")]
                        ]
                        
                        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)
                        
                        await update.message.reply_text(
                            f"✅ Sarlavha saqlandi: *{message_text}*\n\n"
                            f"**2/2-qadam: Film kategoriyasini tanlang**\n\n"
                            f"Quyidagi tugmalardan birini tanlang yoki yangi kategoriya qo'shing:",
                            parse_mode='Markdown',
                            reply_markup=reply_markup
                        )
                        return
                    
                    # Step 2: Get category (now handled by button selection)
                    elif movie_data.get('step') == 'category':
                        # This should not happen as we now use buttons for category selection
                        await update.message.reply_text("❌ Kategoriyani tugma orqali tanlang.")
                        return
                    
                    # Handle new category input
                    elif movie_data.get('step') == 'new_category':
                        if not message_text:
                            await update.message.reply_text("❌ To'g'ri kategoriya nomini kiriting.")
                            return
                        
                        # Get all data and add movie with new category
                        title = movie_data['title']
                        category = message_text
                        code = movie_data['code']
                        
                        # Get pending movie data from database
                        pending_movie = self.db.get_pending_movie_by_code(code)
                        if not pending_movie:
                            await update.message.reply_text("❌ Kutilayotgan film ma'lumotlari topilmadi.")
                            return
                        
                        # Add movie to database
                        success = self.db.add_movie(
                            code=code,
                            title=title,
                            category=category,
                            channel_message_id=pending_movie['channel_message_id'],
                            channel_id=pending_movie['channel_id'],
                            file_id=pending_movie['file_id']
                        )
                        
                        if success:
                            # Remove from pending movies
                            self.db.remove_pending_movie(code)
                            del self.pending_movies[user_id]
                            
                            # Reset keyboard to main menu
                            reply_markup = self.get_reply_keyboard(user_id)
                            
                            await update.message.reply_text(
                                f"🎉 **Film muvaffaqiyatli qo'shildi!**\n\n"
                                f"🎬 **Sarlavha:** {title}\n"
                                f"📁 **Kategoriya:** {category}\n"
                                f"🔢 **Kod:** {code}\n\n"
                                f"✅ Film endi `/categories` va `/search` da mavjud!",
                                parse_mode='Markdown',
                                reply_markup=reply_markup
                            )
                            logger.info(f"User {user_id} added movie: {title} ({code}) in new category {category}")
                        else:
                            await update.message.reply_text(
                                f"❌ *{title}* (`{code}`) filmini qo'shishda xatolik. "
                                "Bu kod bilan film allaqachon mavjud bo'lishi mumkin."
                            )
                        return
                        
                except Exception as e:
                    logger.error(f"Error processing movie addition: {e}")
                    await update.message.reply_text(
                        "❌ So'rovingizni qayta ishlashda xatolik yuz berdi. Qaytadan urinib ko'ring."
                    )
        else:
            # Regular message handling
            await update.message.reply_text(
                "🤖 Mavjud buyruqlarni ko'rish uchun /help ishlating!",
                parse_mode='Markdown'
            )
    
    async def send_movie_by_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE, code: str):
        """Send a movie by its code."""
        # Use the same search logic for consistency
        await self._search_and_send_results(update, context, code)
    
    def get_handlers(self) -> List:
        """Return list of all handlers for the bot."""
        return [
            CommandHandler('start', self.start),
            CommandHandler('search', self.search_command),
            CommandHandler('categories', self.categories_command),
            CommandHandler('addmovie', self.addmovie_command),
            CommandHandler('help', self.help_command),
            CommandHandler('about', self.about_command),
            CallbackQueryHandler(self.handle_callback_query),
            MessageHandler(filters.ChatType.CHANNEL, self.channel_post_handler),
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message),
        ]