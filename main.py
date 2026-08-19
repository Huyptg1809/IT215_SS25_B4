"""
Nộp hồ sơ đầy đủ CV hợp lệ và Avatar hợp lệ.
=> Kết quả mong đợi: Lưu thành công 2 file, trả về 201 Created.
 
Nộp CV 15MB.
=> Kết quả mong đợi: Lỗi 400 "CV vượt quá dung lượng cho phép". RAM không bị phình to do check dung lượng qua Spool/con trỏ tell().

CV lưu thành công nhưng quá trình lưu Avatar gặp lỗi (ví dụ disk full).
=> Kết quả mong đợi: Lỗi 500 "Lỗi khi lưu Avatar. Đã rollback". File CV vừa lưu sẽ bị hệ thống tự động xóa khỏi ổ đĩa, không để lại file rác.
"""

import os
import uuid
import shutil
from fastapi import FastAPI, APIRouter, UploadFile, Form, File, HTTPException, status
from pydantic import EmailStr
import uvicorn

app = FastAPI(title="Recruitment Portal - B4")
router = APIRouter()

STORAGE_DIR = "storage"
MOCK_DB = []

@router.post("/applications/submit", status_code=status.HTTP_201_CREATED)
async def submit_application(
    full_name: str = Form(...),
    email: EmailStr = Form(...),
    phone: str = Form(...),
    position: str = Form(...),
    cv: UploadFile = File(...),
    avatar: UploadFile = File(...)
):
    for record in MOCK_DB:
        if record["email"] == email and record["position"] == position:
            raise HTTPException(status_code=400, detail="Bạn đã ứng tuyển vị trí này rồi.")
    
    def validate_and_get_ext(file: UploadFile, allowed_types: list, max_size: int, label: str):
        if not file.filename:
            raise HTTPException(status_code=400, detail=f"{label} bị thiếu.")
            
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail=f"{label} sai định dạng.")
            
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
        
        if size == 0:
            raise HTTPException(status_code=400, detail=f"{label} không được rỗng.")
        if size > max_size:
            raise HTTPException(status_code=400, detail=f"{label} vượt quá dung lượng cho phép.")
            
        parts = file.filename.rsplit(".", 1)
        ext = f".{parts[1].lower()}" if len(parts) > 1 else ""
        return ext

    cv_ext = validate_and_get_ext(
        cv, 
        ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
        10 * 1024 * 1024, 
        "CV"
    )
    avatar_ext = validate_and_get_ext(
        avatar, 
        ["image/jpeg", "image/png"], 
        3 * 1024 * 1024, 
        "Avatar"
    )

    os.makedirs(STORAGE_DIR, exist_ok=True)
    
    cv_path = os.path.join(STORAGE_DIR, f"{uuid.uuid4()}_cv{cv_ext}")
    avatar_path = os.path.join(STORAGE_DIR, f"{uuid.uuid4()}_avatar{avatar_ext}")
    
    try:
        with open(cv_path, "wb") as buffer:
            shutil.copyfileobj(cv.file, buffer)
    except Exception:
        raise HTTPException(status_code=500, detail="Lỗi khi lưu CV.")
        
    try:
        with open(avatar_path, "wb") as buffer:
            shutil.copyfileobj(avatar.file, buffer)
    except Exception:
        if os.path.exists(cv_path):
            os.remove(cv_path)
        raise HTTPException(status_code=500, detail="Lỗi khi lưu Avatar. Đã rollback.")

    try:
        MOCK_DB.append({
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "position": position,
            "cv_path": cv_path,
            "avatar_path": avatar_path
        })
    except Exception:
        if os.path.exists(cv_path): os.remove(cv_path)
        if os.path.exists(avatar_path): os.remove(avatar_path)
        raise HTTPException(status_code=500, detail="Lỗi DB. Đã rollback.")

    return {"message": "Nộp hồ sơ thành công!", "candidate": full_name}

app.include_router(router, prefix="/api/v1")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
