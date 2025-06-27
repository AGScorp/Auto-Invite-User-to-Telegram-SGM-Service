from pyrogram import Client
import os
from dotenv import load_dotenv, set_key, find_dotenv
import logging
import builtins
import requests
import asyncio
from pyrogram.errors import FloodWait, UserPrivacyRestricted, PeerIdInvalid
logging.basicConfig(level=logging.INFO)

class TelegramSessionManager():

    def __init__(self,account_name: str ,session_string: str = None):
        """Initialize Telegram Session Manager"""
        load_dotenv()
        self.account_name = account_name
        self.phone_number = os.getenv(f"{account_name}_phone_number")
        self.api_id = os.getenv(f"{account_name}_api_id")
        self.api_hash = os.getenv(f"{account_name}_api_hash")
        self.original_input = builtins.input
        self.session_string = session_string
        self.app = Client(
            self.account_name,
            api_id=self.api_id,
            api_hash=self.api_hash,
            phone_number=self.phone_number,
            session_string=self.session_string
        )


    
    def custom_input(self, prompt=""):
        print(prompt)
        if "confirmation code" in prompt.lower() or "verification code" in prompt.lower():
            return self.code_callback()

        else:
            # ถ้าไม่ตรงเงื่อนไข ใช้ input ปกติ
            return self.original_input(prompt)
        
    def code_callback(self, *args):
        """verification code จาก user"""
        response = requests.get('https://n8n-pmsg.agilesoftgroup.com/webhook/2caf57bc-44ee-4547-9a83-1b096b7b50ef')
        logging.info(f"Code: {response.json()}")
        A = self.original_input("Enter verification code here aaa: ")
        return A
    
    async def send_code_and_get_hash(self, session_name: str = "my_account"):
        """
        ส่ง code และเก็บ app instance ไว้
        Returns: (app, phone_code_hash)
        """

        await self.app.connect()
        # ส่ง code
        sent_code = await self.app.send_code(self.phone_number)
        logging.info(f"✅ Verification code sent to {self.phone_number}")
        logging.info("⏰ Please enter the code quickly!")
        # ส่งคืน app instance และ phone_code_hash (ไม่ disconnect)

        return sent_code.phone_code_hash
    
    async def create_session_string(self, phone_code_hash: str, verification_code: str) -> None:
        """
        Complete sign in with existing app instance
        """
        try:
          
            # Sign in (แต่ไม่ใช้ result)
            await self.app.sign_in(
                phone_number=self.phone_number,
                phone_code_hash=phone_code_hash,
                phone_code=verification_code
            )
            
            logging.info(f"✅ Successfully signed in!")
            
            # Export session string
            session_string = await self.app.export_session_string()
            self.session_string = session_string
            self.update_env()
            logging.info(f"✅ Session string created and updated .env successfully!")
            return self.session_string
            
        except Exception as e:
            logging.info(f"❌ Error during sign in: {e}")
            raise
        finally:
            # 
            await self.app.disconnect()

    async def invite_user_to_channal(self, group_or_channel: str, user_name: str = "my_account") -> dict:
        """เพิ่มผู้ใช้เข้า group หรือ channel"""
        try:
            # ตรวจสอบการเชื่อมต่อ
            if not self.app.is_connected:
                await self.app.connect()
                logging.info(f"Connected to Telegram")
            
            # ระบุ channel หรือ group (ใช้ username หรือ chat_id)
            chat_id = group_or_channel
            # ระบุ user ที่จะเพิ่ม (ใช้ username หรือ user_id)
            user_ids = [user_name]
            results = []
            
            for user in user_ids:
                try:
                    await self.app.add_chat_members(
                        chat_id=chat_id,
                        user_ids=user
                    )
                    logging.info(f"✅ เพิ่ม {user} เข้า {chat_id} สำเร็จ!")
                    results.append({"user": user, "status": "success"})
                    # หน่วงเวลาเพื่อป้องกัน rate limit
                    await asyncio.sleep(3)
                    
                except UserPrivacyRestricted:
                    logging.warning(f"❌ ไม่สามารถเพิ่ม {user} ได้: ตั้งค่าความเป็นส่วนตัว")
                    results.append({"user": user, "status": "failed", "reason": "privacy_restricted"})
                    
                except PeerIdInvalid:
                    logging.warning(f"❌ ไม่พบ {user} หรือ {chat_id}")
                    results.append({"user": user, "status": "failed", "reason": "not_found"})
                    
                except FloodWait as e:
                    logging.warning(f"⏳ ต้องรอ {e.value} วินาทีเนื่องจาก rate limit")
                    await asyncio.sleep(e.value)
                    results.append({"user": user, "status": "waiting", "wait_seconds": e.value})
                    
                except Exception as e:
                    logging.error(f"❌ เกิดข้อผิดพลาดกับ {user}: {str(e)}")
                    results.append({"user": user, "status": "failed", "reason": str(e)})
            
            return {"status": "completed", "results": results}
            
        except Exception as e:
            # จัดการข้อผิดพลาดในระดับฟังก์ชัน
            logging.error(f"❌ เกิดข้อผิดพลาดในฟังก์ชัน invite_user_to_channal: {str(e)}")
            return {
                "status": "error", 
                "message": str(e),
                "results": []
            }
            
        finally:
            # ตัดการเชื่อมต่ออย่างปลอดภัย
            try:
                if hasattr(self.app, 'is_connected') and self.app.is_connected:
                    logging.info(f"self.app.is_connected: {self.app.is_connected}")
                    await self.app.disconnect()
                    logging.info(f"Disconnected ")
            except Exception as e:
                logging.warning(f"Error during disconnect: {e}")
                
    def update_env(self) -> None:
        dotenv_file = find_dotenv()

        # อ่านไฟล์ทั้งหมด
        with open(dotenv_file, "r") as file:
            content = file.read()

        logging.info("=== ค่าเดิม ===")
        logging.info(content)

        # แทนที่หรือเพิ่มบรรทัดใหม่
        lines = content.split('\n')
        new_lines = []
        found = False

        for line in lines:
            if line.strip().startswith(f'{self.account_name}_session_string='):
                new_lines.append(f"{self.account_name}_session_string={self.session_string}")
                found = True
            else:
                new_lines.append(line)

        # ถ้าไม่เจอ ให้เพิ่มใหม่
        if not found:
            new_lines.append(f"{self.account_name}_session_string={self.session_string}")

        # เขียนกลับ
        new_content = '\n'.join(new_lines)
        with open(dotenv_file, "w") as file:
            file.write(new_content)

        logging.info("=== ค่าใหม่ ===")
        with open(dotenv_file, "r") as file:
            final_content = file.read()
            logging.info(final_content)
            