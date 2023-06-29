import asyncio
import os
import time
import re
import shutil
from pyrogram import Client, compose, filters
from pyrogram.errors import FloodWait
from pyrogram.types import (InputMediaAudio, InputMediaDocument, InputMediaPhoto, InputMediaVideo)
from progress import progress_for_pyrogram
from config import *


async def main():
    try:
        shutil.rmtree('./downloads')
    except FileNotFoundError:
        os.mkdir('./downloads')
    apps = [
        Client("bot_session", api_id=api_id, api_hash=api_hash, bot_token=bot_token, sleep_threshold=100000),
        Client("account_session", api_id=api_id, api_hash=api_hash, sleep_threshold=100000, takeout=True)
    ]
    my_bot = apps[0]
    app = apps[1]

    async def get_target_message(msg_link):
        if "?single" in msg_link:
            msg_link = msg_link.split("?single")[0]
        from_chat = int('-100' + msg_link.split('/')[-2]) if msg_link.split('/')[-2].isdigit() else \
            msg_link.split('/')[-2]

        msg_id = int(msg_link.split('/')[-1])
        print(msg_id)
        return await app.get_messages(chat_id=from_chat, message_ids=msg_id)

    def handle_file_list(file_list):
        try:
            if len(file_list) > 0:
                for file_path in file_list:
                    os.remove(file_path)
        except (UnboundLocalError, TypeError):
            pass

    async def handle_caption(target_message, message_group_list=None, want_replace=False):
        # 如果想处理caption的话改成True..
        rex = r'[a-zA-z]+://[^\s]*|t.me[^\s]*|@[a-zA-Z0-9_-]+'
        p = re.compile(rex)
        replace_username = "@username"
        if target_message.media_group_id:
            caption = None
            for new_message in message_group_list:
                if new_message.caption:
                    caption = new_message.caption
        elif not target_message.media_group_id and target_message.media:
            caption = target_message.caption
        else:
            caption = target_message.text
        if want_replace:
            if caption:
                caption = p.sub(replace_username, caption)
        return caption

    filter_keyword = []
    filter_user = []

    def filter_message(caption, target_message):
        Can_be_forwarded = True
        for i in filter_keyword:
            if i in caption:
                Can_be_forwarded = False
                return False
        else:
            Can_be_forwarded = True
        if Can_be_forwarded:
            for i in filter_user:
                if i in target_message.from_user.id:
                    return False
            else:
                return True

    async def check_is_video_photo(target_message, from_chat):
        if target_message.media_group_id:
            message_group_list = await app.get_media_group(from_chat, target_message.id)
            media_type_list = []
            for new_message in message_group_list:
                media_type_list.append(str(new_message.media).split('.')[-1].lower())
            media_type_set = set(media_type_list)
            is_video_photo = True if len(media_type_set) != 1 else False
            return is_video_photo

    async def handle_download(target_message, client, to_edit_message):
        file_save_path = await app.download_media(
            target_message,
            progress=progress_for_pyrogram,
            progress_args=(
                client,
                "**DOWNLOADING:**\n",
                to_edit_message,
                time.time()
            )
        )
        return file_save_path

    async def handle_text(target_message, client, to_edit_message, message, from_chat):
        await client.send_message(message.chat.id, target_message.text)
        await to_edit_message.delete()

    async def handle_video(target_message, client, to_edit_message, message, from_chat):
        file_save_path_list = []
        try:
            if target_message.media_group_id:
                upload_list = []
                message_group_list = await app.get_media_group(from_chat, target_message.id)
                caption = await handle_caption(target_message, message_group_list=message_group_list)
                is_video_photo = await check_is_video_photo(target_message, from_chat)
                if is_video_photo:
                    file_list = await handle_video(target_message, client, to_edit_message, message, from_chat,
                                                   )
                    handle_file_list(file_list)
                else:
                    for new_message in message_group_list:
                        meta_media = getattr(new_message, new_message.media.value)
                        if meta_media.file_size > 2000000000:
                            print('文件超过 2G 无法上传跳过..')
                            continue

                        if meta_media.thumbs:
                            thumbs_path = await app.download_media(
                                meta_media.thumbs[0].file_id)
                            file_save_path_list.append(thumbs_path)
                        else:
                            thumbs_path = None

                        file_save_path = await app.download_media(
                            new_message,
                            progress=progress_for_pyrogram,
                            progress_args=(
                                client,
                                f"**DOWNLOADING:** {meta_media.file_name}\n",
                                to_edit_message,
                                time.time()
                            )
                        )
                        if message_group_list.index(new_message) == len(message_group_list) - 1:
                            upload_list.append(
                                InputMediaVideo(file_save_path,
                                                thumb=thumbs_path,
                                                caption=caption,
                                                duration=meta_media.duration
                                                )
                            )
                        else:
                            upload_list.append(
                                InputMediaVideo(file_save_path,
                                                thumb=thumbs_path,
                                                duration=meta_media.duration
                                                )
                            )
                        file_save_path_list.append(file_save_path)
                    to_edit_message = await client.edit_message_text(message.chat.id, to_edit_message.id,
                                                                     "**Trying to Upload.**")
                    await client.send_media_group(message.chat.id, upload_list)

            else:
                meta_media = getattr(target_message, target_message.media.value)
                if meta_media.file_size > 2000000000:
                    print('文件超过 2G 无法上传跳过..')
                    return
                file_path = await handle_download(target_message, client, to_edit_message)
                thumbs_path = await app.download_media(
                    target_message.video.thumbs[0].file_id) if target_message.video.thumbs else None
                caption = await handle_caption(target_message)
                await client.send_video(message.chat.id, file_path,
                                        caption=caption,
                                        duration=target_message.video.duration,
                                        width=target_message.video.width,
                                        height=target_message.video.height,
                                        thumb=thumbs_path,
                                        progress=progress_for_pyrogram,
                                        progress_args=(
                                            client,
                                            '**UPLOADING:**\n',
                                            to_edit_message,
                                            time.time()
                                        )

                                        )
                os.remove(file_path)
                os.remove(thumbs_path)
            await to_edit_message.delete()
            return file_save_path_list
        except FloodWait as e:
            await asyncio.sleep(e.value)

    async def handle_photo(target_message, client, to_edit_message, message, from_chat):
        file_save_path_list = []
        try:
            if target_message.media_group_id:
                upload_list = []
                message_group_list = await app.get_media_group(from_chat, target_message.id)
                caption = await handle_caption(target_message, message_group_list=message_group_list)
                is_video_photo = await check_is_video_photo(target_message, from_chat)
                if is_video_photo:
                    file_list = await handle_video_photo(target_message, client, to_edit_message, message, from_chat,
                                                         )
                    handle_file_list(file_list)
                else:
                    for new_message in message_group_list:
                        file_save_path = await app.download_media(
                            new_message,
                            progress=progress_for_pyrogram,
                            progress_args=(
                                client,
                                f"**DOWNLOADING:** 正在下载第{message_group_list.index(new_message) + 1}个图片\n",
                                to_edit_message,
                                time.time()
                            )
                        )
                        if message_group_list.index(new_message) == len(message_group_list) - 1:
                            upload_list.append(
                                InputMediaPhoto(file_save_path, caption=caption)
                            )
                        else:
                            upload_list.append(
                                InputMediaPhoto(file_save_path)
                            )

                        file_save_path_list.append(file_save_path)
                    to_edit_message = await client.edit_message_text(message.chat.id, to_edit_message.id,
                                                                     "**Trying to Upload.**")
                    await client.send_media_group(message.chat.id, upload_list)
            else:
                file_path = await handle_download(target_message, client, to_edit_message)
                caption = await handle_caption(target_message)
                await client.send_photo(message.chat.id, file_path,
                                        caption=caption,
                                        progress=progress_for_pyrogram,
                                        progress_args=(
                                            client,
                                            '**UPLOADING:**\n',
                                            to_edit_message,
                                            time.time()
                                        )

                                        )
                os.remove(file_path)
            await to_edit_message.delete()
            return file_save_path_list
        except FloodWait as e:
            await asyncio.sleep(e.value)

    async def handle_video_photo(target_message, client, to_edit_message, message, from_chat):
        message_group_list = await app.get_media_group(from_chat, target_message.id)
        caption = await handle_caption(target_message, message_group_list=message_group_list)
        upload_list = []
        file_save_path_list = []
        for new_message in message_group_list:

            meta_media = getattr(new_message, new_message.media.value)
            if meta_media.file_size > 2000000000:
                print('文件超过 2G 无法上传跳过..')
                continue
            if new_message.video:
                if meta_media.thumbs:
                    thumbs_path = await app.download_media(meta_media.thumbs[0].file_id)
                    file_save_path_list.append(thumbs_path)
                else:
                    thumbs_path = None
                file_save_path = await app.download_media(
                    new_message,
                    progress=progress_for_pyrogram,
                    progress_args=(
                        client,
                        f"**DOWNLOADING:** {meta_media.file_name}\n",
                        to_edit_message,
                        time.time()
                    )
                )
                if message_group_list.index(new_message) == len(message_group_list) - 1:
                    upload_list.append(
                        InputMediaVideo(file_save_path, thumb=thumbs_path, caption=caption,
                                        duration=meta_media.duration)
                    )
                else:
                    upload_list.append(
                        InputMediaVideo(file_save_path, thumb=thumbs_path,
                                        duration=meta_media.duration)
                    )

                file_save_path_list.append(file_save_path)

            elif new_message.photo:
                file_save_path = await app.download_media(
                    new_message,
                    progress=progress_for_pyrogram,
                    progress_args=(
                        client,
                        f"**DOWNLOADING:** 正在下载第{message_group_list.index(new_message) + 1}个图片\n",
                        to_edit_message,
                        time.time()
                    )
                )
                if message_group_list.index(new_message) == len(message_group_list) - 1:
                    upload_list.append(
                        InputMediaPhoto(file_save_path, caption=caption)
                    )
                else:
                    upload_list.append(
                        InputMediaPhoto(file_save_path)
                    )

                file_save_path_list.append(file_save_path)
        to_edit_message = await client.edit_message_text(message.chat.id, to_edit_message.id,
                                                         "**Trying to Upload.**")
        await client.send_media_group(message.chat.id, upload_list)
        await to_edit_message.delete()
        return file_save_path_list

    async def handle_document(target_message, client, to_edit_message, message, from_chat):
        file_save_path_list = []
        try:
            if target_message.media_group_id:
                upload_list = []
                message_group_list = await app.get_media_group(from_chat, target_message.id)
                caption = await handle_caption(target_message, message_group_list=message_group_list)

                for new_message in message_group_list:
                    meta_media = getattr(new_message, new_message.media.value)
                    if meta_media.file_size > 2000000000:
                        print('文件超过 2G 无法上传跳过..')
                        continue
                    file_save_path = await app.download_media(
                        new_message,
                        progress=progress_for_pyrogram,
                        progress_args=(
                            client,
                            f"**DOWNLOADING:** {meta_media.file_name}\n",
                            to_edit_message,
                            time.time()
                        )
                    )
                    if message_group_list.index(new_message) == len(message_group_list) - 1:
                        upload_list.append(
                            InputMediaDocument(file_save_path, caption=caption)
                        )
                    else:
                        upload_list.append(
                            InputMediaDocument(file_save_path)
                        )

                    file_save_path_list.append(file_save_path)
                to_edit_message = await client.edit_message_text(message.chat.id, to_edit_message.id,
                                                                 "**Trying to Upload.**")
                await client.send_media_group(message.chat.id, upload_list)
            else:
                meta_media = getattr(target_message, target_message.media.value)
                if meta_media.file_size > 2000000000:
                    print('文件超过 2G 无法上传跳过..')
                    return
                file_path = await handle_download(target_message, client, to_edit_message)
                caption = await handle_caption(target_message)
                await client.send_document(message.chat.id, file_path,
                                           caption=caption,
                                           progress=progress_for_pyrogram,
                                           progress_args=(
                                               client,
                                               '**UPLOADING:**\n',
                                               to_edit_message,
                                               time.time()
                                           )

                                           )
                os.remove(file_path)
            await to_edit_message.delete()
            return file_save_path_list
        except FloodWait as e:
            await asyncio.sleep(e.value)

    async def handle_audio(target_message, client, to_edit_message, message, from_chat):
        performer = None
        file_save_path_list = []
        try:
            if target_message.media_group_id:
                upload_list = []
                message_group_list = await app.get_media_group(from_chat, target_message.id)
                caption = await handle_caption(target_message, message_group_list=message_group_list)
                for new_message in message_group_list:
                    meta_media = getattr(new_message, new_message.media.value)

                    title = new_message.audio.title if new_message.audio.title else None
                    file_save_path = await app.download_media(
                        new_message,
                        progress=progress_for_pyrogram,
                        progress_args=(
                            client,
                            f"**DOWNLOADING:** {meta_media.file_name}\n",
                            to_edit_message,
                            time.time()
                        )
                    )
                    if message_group_list.index(new_message) == len(message_group_list) - 1:
                        upload_list.append(
                            InputMediaAudio(file_save_path, caption=caption,
                                            duration=new_message.audio.duration, title=title,
                                            performer=performer)
                        )
                    else:
                        upload_list.append(
                            InputMediaAudio(file_save_path,
                                            duration=new_message.audio.duration, title=title,
                                            performer=performer)
                        )

                    file_save_path_list.append(file_save_path)
                to_edit_message = await client.edit_message_text(message.chat.id, to_edit_message.id,
                                                                 "**Trying to Upload.**")
                await client.send_media_group(message.chat.id, upload_list)
            else:
                file_path = await handle_download(target_message, client, to_edit_message)
                title = target_message.audio.title if target_message.audio.title else None
                caption = await handle_caption(target_message, from_chat)
                await client.send_audio(message.chat.id, file_path,
                                        caption=caption,
                                        duration=target_message.audio.duration,
                                        title=title,
                                        file_name=title, performer=performer,
                                        progress=progress_for_pyrogram,
                                        progress_args=(
                                            client,
                                            '**UPLOADING:**\n',
                                            to_edit_message,
                                            time.time()
                                        )

                                        )
                os.remove(file_path)
            await to_edit_message.delete()
            return file_save_path_list
        except FloodWait as e:
            await asyncio.sleep(e.value)

    async def handle_web_page(message, target_message, to_edit_message, client):
        to_edit_message = await client.edit_message_text(message.chat.id,
                                                         to_edit_message.id,
                                                         "Cloning.")
        await client.send_message(message.chat.id, target_message.text.markdown)
        await to_edit_message.delete()

    @my_bot.on_message(filters.text)
    async def handle_command(client, message):
        delay = 4
        func_dic = {
            'audio': handle_audio,
            'document': handle_document,
            'video': handle_video,
            'photo': handle_photo,
        }
        split_space = message.text.split(' ')
        if len(split_space) == 2:
            msg_link, end_id = split_space[0], int(split_space[1])
            if "?single" in msg_link:
                msg_link = msg_link.split("?single")[0]
            start_id = int(msg_link.split('/')[-1])
            from_chat = int('-100' + msg_link.split('/')[-2]) if msg_link.split('/')[-2].isdigit() else \
                msg_link.split('/')[
                    -2]
            print(msg_link, start_id, end_id, from_chat)

            target_message = await get_target_message(msg_link)

            offset = 0
            for message_id in range(start_id, end_id + 1):
                if message_id <= offset:
                    print(f'{message_id} 已经处理过')
                    continue
                target_message = await app.get_messages(chat_id=from_chat, message_ids=message_id)
                if target_message.empty:
                    print(f'跳过空消息 {message_id}')
                    continue
                is_super_user = target_message.sender_chat or target_message.from_user.id == filter_user_id
                if not is_super_user:
                    print('跳过非管理员信息')
                    continue
                to_edit_message = await client.send_message(message.chat.id, f'Processing message id {message_id}!')

                if target_message.media_group_id:
                    message_group_list = await app.get_media_group(from_chat, target_message.id)
                    offset = message_group_list[-1].id
                if target_message.media:
                    meta_media = getattr(target_message, target_message.media.value)

                    try:
                        file_name = meta_media.file_name if meta_media.file_name else '未知文件'
                        to_edit_message = await client.edit_message_text(message.chat.id, to_edit_message.id,
                                                                         f"Trying to Download {file_name}!")
                    except AttributeError:
                        to_edit_message = await client.edit_message_text(message.chat.id, to_edit_message.id,
                                                                         f"Trying to Download Photo!")
                    try:
                        file_list = await func_dic[target_message.media.value](target_message, client, to_edit_message,
                                                                               message,
                                                                               from_chat)
                        handle_file_list(file_list)
                    except KeyError:
                        await to_edit_message.delete()
                        continue
                    if target_message.media_group_id:
                        await asyncio.sleep(delay * len(message_group_list))

                    else:
                        await asyncio.sleep(delay)

                if not target_message.media:
                    if target_message.sender_chat or target_message.from_user.id == filter_user_id:
                        await handle_text(target_message, client, to_edit_message, message, from_chat)
                        await asyncio.sleep(delay)
                    await to_edit_message.delete()

    await compose(apps)


asyncio.run(main())
