from pyrogram import Client
import builtins
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import logging
import os
import secrets
from dotenv import load_dotenv, set_key, find_dotenv, dotenv_values
from TelegramSessionManager import TelegramSessionManager

load_dotenv()
logging.basicConfig(level=logging.INFO)
# สร้าง custom input function
import uvicorn

# Bearer Token Setup
security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """ตรวจสอบ Bearer Token"""
    token = credentials.credentials
    
    # ดึง token จากไฟล์ .env
    valid_token = os.getenv("API_BEARER_TOKEN")
    
    if not secrets.compare_digest(token, valid_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token
app_api = FastAPI(
    title="Telegram Channel & Group Invitation API",
    version="1.0.0",
    description="""
## บริการจัดการการยืนยันตัวตนและ Session ของ Telegram

API นี้ให้บริการ endpoints สำหรับจัดการ Telegram sessions และเชิญผู้ใช้เข้าช่อง/กลุ่ม

### ฟีเจอร์หลัก:
- **ส่งรหัสยืนยัน** ไปยังบัญชี Telegram
- **สร้าง session strings** สำหรับบัญชีที่ยืนยันตัวตนแล้ว
- **เชิญผู้ใช้** เข้าช่องหรือกลุ่ม Telegram

### ข้อกำหนดเบื้องต้น:
- ข้อมูลบัญชีต้องถูกตั้งค่าไว้ในไฟล์ `.env` ล่วงหน้า
- รูปแบบ: `{account_phone_number}_api_id`, `{account_phone_number}_api_hash`, `{account_phone_number}_phone_number`

### ขั้นตอนการยืนยันตัวตน:
1. เรียกใช้ `/send_verification_code/{account_name}` เพื่อเริ่มการยืนยันตัวตน
2. ใช้ `phone_code_hash` ที่ได้รับพร้อมกับรหัสยืนยันเพื่อสร้าง session ผ่าน `/create_session`
3. เมื่อสร้าง session แล้ว สามารถใช้ `/invite_user_to_channal_or_group` เพื่อเชิญผู้ใช้
""",
    docs_url="/docs",
    redoc_url="/redoc"
)


# Response Models
class VerificationCodeResponse(BaseModel):
    """โมเดล response สำหรับ endpoint ส่งรหัสยืนยัน"""
    api_id: str = Field(..., description="Telegram API ID ของบัญชี")
    api_hash: str = Field(..., description="Telegram API Hash ของบัญชี")
    phone_number: str = Field(..., description="หมายเลขโทรศัพท์ที่เชื่อมโยงกับบัญชี")
    phone_code_hash: str = Field(..., description="รหัส hash ที่จำเป็นสำหรับการสร้าง session (ใช้ค่านี้ใน create_session)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "api_id": "12345678",
                "api_hash": "abcdef1234567890abcdef1234567890",
                "phone_number": "+66917598103",
                "phone_code_hash": "55830a56c762183f80"
            }
        }
    }

class SessionCreatedResponse(BaseModel):
    """โมเดล response สำหรับการสร้าง session สำเร็จ"""
    create_session_string: bool = Field(..., description="บอกว่าสร้าง session string สำเร็จหรือไม่")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "create_session_string": True
            }
        }
    }

class ErrorResponse(BaseModel):
    """โมเดล response มาตรฐานสำหรับข้อผิดพลาด"""
    detail: str = Field(..., description="ข้อความอธิบายว่าเกิดข้อผิดพลาดอะไร")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "detail": "Account name not found"
            }
        }
    }

# Request Models
class CreateSession(BaseModel):
    """Request body สำหรับการสร้าง Telegram session"""
    phone_num: str = Field(..., description="หมายเลขโทรศัพท์เต็มพร้อมรหัสประเทศ (เช่น +66917598103)")
    account_phone_number: str = Field(..., description="ตัวระบุบัญชี (หมายเลขโทรศัพท์ไม่มีรหัสประเทศ เช่น 0917598103)")
    phone_code_hash: str = Field(..., description="Hash ที่ได้รับจาก endpoint /send_verification_code")
    verification_code: str = Field(..., description="รหัสยืนยันที่ได้รับผ่าน Telegram")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "phone_num": "+66917598103",
                    "account_phone_number": "0917598103",
                    "phone_code_hash": "55830a56c762183f80",
                    "verification_code": "50582"
                }
            ]
        }
    }
    

class InviteUser(BaseModel):
    """Request body สำหรับการเชิญผู้ใช้เข้าช่องหรือกลุ่ม"""
    username: str = Field(..., description="ชื่อผู้ใช้ Telegram ของผู้ที่จะเชิญ (ไม่ต้องมี @)")
    channal_or_group: str = Field(..., description="ชื่อผู้ใช้หรือลิงก์ของช่อง/กลุ่มที่จะเชิญผู้ใช้เข้า")
    account_phone_number: str = Field(..., description="หมายเลขโทรศัพท์ของบัญชีที่จะใช้ในการเชิญ (ต้องมี session ที่ใช้งานอยู่)")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username": "MrPz101",
                    "channal_or_group": "siwattestchannal",
                    "account_phone_number": "0912345678"
                }
            ]
        }
    }

class AccountInfo(BaseModel):
    """โมเดลสำหรับแสดงข้อมูลบัญชี"""
    account_name: str = Field(..., description="ชื่อบัญชี (ตัวระบุ)")
    has_api_id: bool = Field(..., description="มี API ID ตั้งค่าไว้หรือไม่")
    has_api_hash: bool = Field(..., description="มี API Hash ตั้งค่าไว้หรือไม่")
    has_phone_number: bool = Field(..., description="มีหมายเลขโทรศัพท์ตั้งค่าไว้หรือไม่")
    has_session_string: bool = Field(..., description="มี session string หรือไม่")
    phone_number: Optional[str] = Field(None, description="หมายเลขโทรศัพท์ (แสดงเฉพาะบางส่วน)")

class AccountListResponse(BaseModel):
    """โมเดล response สำหรับรายการบัญชี"""
    total_accounts: int = Field(..., description="จำนวนบัญชีทั้งหมด")
    accounts: List[AccountInfo] = Field(..., description="รายการบัญชี")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "total_accounts": 2,
                "accounts": [
                    {
                        "account_name": "0917598103",
                        "has_api_id": True,
                        "has_api_hash": True,
                        "has_phone_number": True,
                        "has_session_string": True,
                        "phone_number": "+6691759xxxx"
                    },
                    {
                        "account_name": "0912345678",
                        "has_api_id": True,
                        "has_api_hash": True,
                        "has_phone_number": True,
                        "has_session_string": False,
                        "phone_number": "+6691234xxxx"
                    }
                ]
            }
        }
    }

active_sessions = {}
# Endpoints
@app_api.get(
    "/",
    summary="check_status",
    description="ตรวจสอบว่า Telegram Channel & Group Invitation API กำลังทำงานอยู่หรือไม่",
    tags=["สุขภาพระบบ"],
    response_model=Dict[str, str]
)
async def root():
    """
    Endpoint ตรวจสอบสถานะพื้นฐานเพื่อยืนยันว่า service กำลังทำงาน
    
    Returns:
        dict: สถานะ service พร้อมข้อความ
    """
    return {"message": "Telegram Channel & Group Invitation API", "status": "running"}

@app_api.get(
    "/send_verification_code/{account_name}",
    summary="send_verification_code",
    description="""
    เริ่มการยืนยันตัวตน Telegram โดยส่งรหัสยืนยันไปยังบัญชีที่ระบุ
    
    บัญชีต้องถูกตั้งค่าไว้ในไฟล์ .env ล่วงหน้าในรูปแบบ:
    - `{account_name}_api_id`
    - `{account_name}_api_hash`
    - `{account_name}_phone_number`
    
    Endpoint นี้จะ:
    1. ส่งรหัสยืนยันไปยังบัญชี Telegram
    2. ส่งคืนรายละเอียดบัญชีและ phone_code_hash ที่จำเป็นสำหรับการสร้าง session
    3. เก็บ session manager ไว้ใช้งานสำหรับการสร้าง session ต่อไป
    """,
    tags=["การยืนยันตัวตน"],
    responses={
        200: {
            "description": "ส่งรหัสยืนยันสำเร็จ",
            "model": VerificationCodeResponse
        },
        400: {
            "description": "ไม่พบบัญชีในการตั้งค่า",
            "model": ErrorResponse
        }
    }
)
async def send_verification_code(
    account_name: str 
):
    """
    ส่งรหัสยืนยันไปยังบัญชี Telegram ที่ตั้งค่าไว้
    
    Args:
        account_name: ตัวระบุบัญชีที่ตรงกับคำนำหน้าในไฟล์ .env
        
    Returns:
        ข้อมูลบัญชีรวมถึง phone_code_hash สำหรับการสร้าง session
        
    Raises:
        HTTPException: หากไม่พบบัญชีในการตั้งค่า
    """
    load_dotenv()
    if account_name in list(set([k.split("_")[0] for k in dotenv_values(".env").keys()])):
        logging.info(f"Account name: {account_name}")
        telegram_manager = TelegramSessionManager(account_name=account_name)
        logging.info("Sending verification code...")
        phone_code_hash = await telegram_manager.send_code_and_get_hash(f"{account_name}_session")
        active_sessions[account_name] = telegram_manager
        logging.info(f"info active_sessions : {active_sessions}")
        info = {k.split("_",1)[1]:v for k,v in dotenv_values(".env").items() if k.split("_")[0] == account_name}
        info["phone_code_hash"] = phone_code_hash
        return info
    else:
        raise HTTPException(status_code=400, detail="Account name not found")


@app_api.post(
    "/create_session",
    summary="create_session",
    description="""
    สร้าง Telegram session string โดยใช้รหัสยืนยันที่ได้รับ
    
    **สำคัญ**: ต้องเรียกใช้ `/send_verification_code/{account_name}` ก่อนเพื่อรับ `phone_code_hash`
    
    Endpoint นี้จะ:
    1. ตรวจสอบรหัสที่ให้มากับ Telegram
    2. สร้างและเก็บ session string สำหรับใช้งานในอนาคต
    3. ล้าง session manager ที่ใช้งานอยู่
    
    Session string ที่สร้างจะถูกบันทึกในไฟล์ .env เป็น `{account_phone_number}_session_string`
    """,
    tags=["การยืนยันตัวตน"],
    response_model=SessionCreatedResponse,
    responses={
        200: {
            "description": "สร้าง session สำเร็จ",
            "model": SessionCreatedResponse
        },
        500: {
            "description": "ไม่สามารถสร้าง session ได้",
            "model": ErrorResponse
        }
    }
)
async def create_session(data: CreateSession):
    """
    สร้าง Telegram session string ด้วยรหัสยืนยัน
    
    Args:
        data: รายละเอียดการสร้าง session รวมถึงรหัสยืนยัน
        
    Returns:
        สถานะความสำเร็จของการสร้าง session
        
    Raises:
        HTTPException: หากการสร้าง session ล้มเหลว
    """
    logging.info(f"Account name: {data.phone_num}")
    try :
        # ใช้ manager ที่เชื่อมต่อไว้แล้ว หรือสร้างใหม่หากไม่มี
        if data.account_phone_number in active_sessions:
            telegram_manager = active_sessions[data.account_phone_number]
            logging.info("Using existing connected session")
        else:
            telegram_manager = TelegramSessionManager(account_name=data.account_phone_number)
            logging.info("Created new session manager")
            # ลบ manager ออกจาก active sessions
        logging.info("create session string...")
        await telegram_manager.create_session_string(phone_code_hash=data.phone_code_hash, 
                                                    verification_code=data.verification_code)

        if data.account_phone_number in active_sessions:
            del active_sessions[data.account_phone_number]
        logging.info(f"info active_sessions : {active_sessions}")

        return {"create_session_string": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app_api.post(
    "/invite_user_to_channal_or_group",
    summary="invite_user_to_channal_or_group",
    description="""
    เชิญผู้ใช้เข้าช่องหรือกลุ่ม Telegram โดยใช้บัญชีที่ยืนยันตัวตนแล้ว
    
    **ข้อกำหนดเบื้องต้น**:
    - บัญชีต้องมี session string ที่ใช้งานได้ (สร้างผ่าน `/create_session`)
    - บัญชีต้องมีสิทธิ์เชิญผู้ใช้เข้าช่อง/กลุ่มเป้าหมาย
    - ผู้ใช้เป้าหมายต้องเข้าถึงได้ (ไม่ถูกบล็อก, การตั้งค่าความเป็นส่วนตัวอนุญาตให้เชิญ)
    
    **หมายเหตุ**: ช่อง/กลุ่มสามารถระบุเป็น:
    - ชื่อผู้ใช้ (ไม่มี @): `mychannel`
    - ลิงก์เชิญ: `https://t.me/mychannel`
    """,
    tags=["การจัดการผู้ใช้"],
    responses={
        200: {
            "description": "เชิญผู้ใช้สำเร็จ",
            "content": {
                "application/json": {
                    "example": {
                                "status": "completed",
                                "results": [
                                    {
                                    "user": "MrPz101",
                                    "status": "success"
                                    }
                                ]
                                }
                }
            }
        },
        400: {
            "description": "ไม่พบบัญชีหรือไม่มี session string",
            "model": ErrorResponse
        },
        500: {
            "description": "ไม่สามารถเชิญผู้ใช้ได้",
            "model": ErrorResponse
        }
    }
)
async def invite_user(data: InviteUser):
    """
    เชิญผู้ใช้เข้าช่องหรือกลุ่ม Telegram
    
    Args:
        data: รายละเอียดการเชิญรวมถึงชื่อผู้ใช้และช่อง/กลุ่มเป้าหมาย
        
    Returns:
        ผลลัพธ์ของการพยายามเชิญ
        
    Raises:
        HTTPException: หากไม่พบบัญชีหรือการเชิญล้มเหลว
    """
    load_dotenv()
    dotenv_keys = dotenv_values(".env").keys()
    logging.info(f"Account name: {data.account_phone_number}\naccount_name in dotenv: {data.account_phone_number in list(set([k.split("_")[0] for k in dotenv_keys]))}\nhas session string: {os.getenv(f"{data.account_phone_number}_session_string") is not None}")
    try :
        if data.account_phone_number in list(set([k.split("_")[0] for k in dotenv_keys])) and os.getenv(f"{data.account_phone_number}_session_string") is not None:
            telegram_manager1 = TelegramSessionManager(account_name=data.account_phone_number,session_string=os.getenv(f"{data.account_phone_number}_session_string"))
            result = await telegram_manager1.invite_user_to_channal(group_or_channel=data.channal_or_group, user_name=data.username)
            return result
        else:
            raise HTTPException(status_code=400, detail="ไม่พบชื่อบัญชีหรือไม่มี session string")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # ใช้ manager

@app_api.get(
    "/check_configured_accounts",
    summary="check configured accounts",
    description="""
    แสดงรายการบัญชีทั้งหมดที่ถูกตั้งค่าไว้ในไฟล์ .env
    
    **ต้องการการยืนยันตัวตน**: 
    - ใช้ Bearer Token ในการเข้าถึง
    - Token ถูกเก็บไว้ในไฟล์ .env ในชื่อ `API_BEARER_TOKEN`
    - ส่งใน Header: `Authorization: Bearer {token}`
    - Default token (ถ้าไม่ได้ตั้งค่าใน .env): `Bearer_Admin_Prachakij_01_2024`
    
    Endpoint นี้จะแสดง:
    - จำนวนบัญชีทั้งหมด
    - รายละเอียดแต่ละบัญชี (ชื่อบัญชี, การมีอยู่ของ API credentials, session string)
    - หมายเลขโทรศัพท์ (แสดงเฉพาะบางส่วนเพื่อความปลอดภัย)
    
    **หมายเหตุ**: ข้อมูลที่ละเอียดอ่อนจะไม่ถูกแสดง เช่น API ID, API Hash, Session String
    """,
    tags=["การจัดการบัญชี"],
    response_model=AccountListResponse,
    responses={
        200: {
            "description": "แสดงรายการบัญชีสำเร็จ",
            "model": AccountListResponse
        },
        401: {
            "description": "ไม่ผ่านการยืนยันตัวตน",
            "model": ErrorResponse,
            "headers": {
                "WWW-Authenticate": {
                    "description": "Bearer",
                    "schema": {"type": "string"}
                }
            }
        }
    },
    dependencies=[Depends(verify_token)]
)
async def check_configured_accounts(token: str = Depends(verify_token)):
    """
    ตรวจสอบและแสดงรายการบัญชีที่ตั้งค่าไว้ในไฟล์ .env
    
    Args:
        token: Bearer token ที่ผ่านการยืนยันตัวตน
        
    Returns:
        รายการบัญชีพร้อมรายละเอียดการตั้งค่า
    """
    load_dotenv()
    env_values = dotenv_values(".env")
    
    # รวบรวมชื่อบัญชีทั้งหมด
    account_names = list(set([k.split("_")[0] for k in env_values.keys() if "_" in k]))
    accounts = []
    
    for account_name in account_names:
        # กรองเฉพาะ account ที่เป็น Telegram account จริงๆ (ต้องมีอย่างน้อย 1 ใน 3 field นี้)
        has_api_id = f"{account_name}_api_id" in env_values
        has_api_hash = f"{account_name}_api_hash" in env_values
        has_phone_number = f"{account_name}_phone_number" in env_values
        has_session_string = f"{account_name}_session_string" in env_values
        
        # ข้ามถ้าไม่ใช่ Telegram account (ไม่มี field ที่เกี่ยวข้องเลย)
        if not (has_api_id or has_api_hash or has_phone_number or has_session_string):
            continue
        
        # แสดงเบอร์โทรแบบซ่อนบางส่วน
        phone_number = None
        if has_phone_number:
            full_number = env_values.get(f"{account_name}_phone_number", "")
            if full_number:
                # แสดงเฉพาะ 7 ตัวแรกและ 4 ตัวสุดท้าย
                if len(full_number) > 8:
                    phone_number = f"{full_number[:7]}{'x' * (len(full_number)-8)}{full_number[-4:]}"
                else:
                    phone_number = f"{full_number[:3]}{'x' * (len(full_number)-3)}"
        
        account_info = AccountInfo(
            account_name=account_name,
            has_api_id=has_api_id,
            has_api_hash=has_api_hash,
            has_phone_number=has_phone_number,
            has_session_string=has_session_string,
            phone_number=phone_number
        )
        accounts.append(account_info)
    
    # เรียงตามชื่อบัญชี
    accounts.sort(key=lambda x: x.account_name)
    
    return AccountListResponse(
        total_accounts=len(accounts),
        accounts=accounts
    )

def run_fastapi():
    """
    ฟังก์ชันสำหรับรัน FastAPI ใน thread แยก
    """
    
    config = uvicorn.Config(app_api, host="0.0.0.0", port=8200, log_level="info",reload=True)
    server = uvicorn.Server(config)
    server.run()

if __name__ == "__main__":
    #uvicorn.run("invite_user_tg_service:app_api", host="0.0.0.0", port=8200, reload=True)
    run_fastapi()