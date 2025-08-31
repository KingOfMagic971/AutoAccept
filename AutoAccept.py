# -*- coding: utf-8 -*-
# meta developer: @Rezoxss
# scope: hikka_only

from .. import loader, utils
import logging
from telethon.tl.types import Message, ChannelParticipantsAdmins
from telethon.tl.functions.messages import HideChatJoinRequestRequest

logger = logging.getLogger(__name__)

@loader.tds
class AutoAcceptMod(loader.Module):
    """Модуль для автоматического принятия заявок в чатах"""
    
    strings = {
        "name": "AutoAccept",
        "no_admin": "<b>🚫 Права администратора недостаточны</b>",
        "enabled": "<b>✅ Автопринятие заявок включено</b>",
        "disabled": "<b>❌ Автопринятие заявок отключено</b>",
        "already_enabled": "<b>⚠️ Автопринятие уже включено</b>",
        "already_disabled": "<b>⚠️ Автопринятие уже отключено</b>",
        "no_rights": "<b>🚫 Недостаточно прав для управления заявками</b>"
    }

    def __init__(self):
        self.active_chats = set()

    async def client_ready(self, client, db):
        self._client = client

    async def can_manage_join_requests(self, chat_id: int) -> bool:
        """Проверяет, может ли бот управлять заявками"""
        try:
            # Получаем информацию о чате
            chat = await self._client.get_entity(chat_id)
            
            # Проверяем, является ли чат супергруппой с заявками
            if hasattr(chat, 'join_request'):
                return True
                
            # Для каналов проверяем права
            if hasattr(chat, 'default_banned_rights'):
                # Право на одобрение заявок
                return not chat.default_banned_rights.invite_users
                
            return False
            
        except Exception as e:
            logger.error(f"Rights check error: {e}")
            return False

    @loader.command()
    async def autoadd(self, message):
        """Включить/выключить автопринятие заявок - .autoadd on/off"""
        chat_id = utils.get_chat_id(message)
        
        args = utils.get_args_raw(message).lower()
        
        # Проверяем права на управление заявками
        if not await self.can_manage_join_requests(chat_id):
            await utils.answer(message, self.strings("no_rights"))
            return
        
        if args == "on":
            if chat_id in self.active_chats:
                await utils.answer(message, self.strings("already_enabled"))
            else:
                self.active_chats.add(chat_id)
                await utils.answer(message, self.strings("enabled"))
                logger.info(f"✅ Автопринятие включено в чате {chat_id}")
                
        elif args == "off":
            if chat_id not in self.active_chats:
                await utils.answer(message, self.strings("already_disabled"))
            else:
                self.active_chats.discard(chat_id)
                await utils.answer(message, self.strings("disabled"))
                logger.info(f"❌ Автопринятие выключено в чате {chat_id}")
                
        else:
            status = "✅ Включено" if chat_id in self.active_chats else "❌ Выключено"
            help_text = (
                f"<b>⚙️ Статус автопринятия в этом чате:</b> {status}\n\n"
                "<b>📋 Команды:</b>\n"
                "<code>.autoadd on</code> - Включить автопринятие\n"
                "<code>.autoadd off</code> - Выключить автопринятие\n\n"
                "<b>💡 Модуль работает только в этом чате!</b>"
            )
            await utils.answer(message, help_text)

    @loader.watcher()
    async def join_request_watcher(self, message):
        """Обработчик заявок на вступление"""
        try:
            chat_id = utils.get_chat_id(message)
            
            # Проверяем, активно ли автопринятие для этого чата
            if chat_id not in self.active_chats:
                return
                
            # Проверяем, что это заявка на вступление
            if hasattr(message, 'action') and message.action:
                action_class = message.action.__class__.__name__
                
                if action_class == 'MessageActionChatJoinRequest':
                    user_id = message.action.user_id
                    
                    try:
                        # Принимаем заявку
                        await self._client(HideChatJoinRequestRequest(
                            peer=chat_id,
                            user_id=user_id,
                            approved=True
                        ))
                        
                        logger.info(f"✅ Принята заявка от пользователя {user_id} в чате {chat_id}")
                        
                        # Отправляем уведомление в чат
                        try:
                            user = await self._client.get_entity(user_id)
                            username = f"@{user.username}" if user.username else user.first_name
                            await message.reply(f"<b>👋 Автоматически принята заявка от {username}</b>")
                        except:
                            await message.reply(f"<b>👋 Автоматически принята заявка от пользователя {user_id}</b>")
                            
                    except Exception as e:
                        logger.error(f"❌ Ошибка принятия заявки: {e}")
                        
        except Exception as e:
            logger.error(f"Ошибка в обработчике заявок: {e}")

    async def on_unload(self):
        """Очистка при выгрузке модуля"""
        self.active_chats.clear()
        logger.info("🧹 Модуль AutoAccept выгружен, все чаты очищены")