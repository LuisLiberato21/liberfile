from fastapi import FastAPI, Request, Form, Depends, HTTPException, Cookie, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_mail import ConnectionConfig
from motor.motor_asyncio import AsyncIOMotorClient
from routes.auth import router as auth_router
from pymongo import MongoClient
from pydantic import BaseModel
from typing import List
from bson import ObjectId
from core.config import MONGO_DETAILS
import bcrypt
import gridfs
import mimetypes
import os

app = FastAPI()

# Configuración de archivos estáticos y plantillas
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(auth_router)

@app.get("/")
async def read_root():
    return {"message": "¡Hola, FastAPI en Render!"}

# Configuración de MongoDB
MONGO_DETAILS = "mongodb+srv://admin:foralltid54237286@liberfile.fhwy6.mongodb.net/liberfile_db"
client = AsyncIOMotorClient(MONGO_DETAILS)
db = client.liberfile_db
usuarios_collection = db.get_collection("usuarios")

# Configurar conexión a MongoDB
client = MongoClient(MONGO_DETAILS)
db = client.liberfile_db
fs = gridfs.GridFS(db)

# Configuración para envío de correos
conf = ConnectionConfig(
    MAIL_USERNAME="liberfile@gmail.com",
    MAIL_PASSWORD="gqnq mhvl sjwg swpr",
    MAIL_FROM="liberfile@gmail.com",
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)

# Modelo para actualizar usuario
class UsuarioUpdate(BaseModel):
    nombres: str
    apellidos: str
    correo_electronico: str
    rol: str

# Ruta para mostrar el formulario de login
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Ruta para manejar el inicio de sesión
@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "password":  
        return RedirectResponse(url="/file-manager")
    else:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Credenciales incorrectas."})

# Ruta para cerrar sesión
@app.get("/logout")
async def logout():
    # Aquí puedes manejar la lógica de cierre de sesión (por ejemplo, borrar el token o la sesión)
    return RedirectResponse(url="/")  # Redirigir al formulario de inicio de sesión

# Ruta para mostrar el formulario de registro
@app.get("/register")
def register_form():
    return {"message": "Formulario de registro"}

# Ruta para mostrar verify_code.html
@app.get("/verify_code", response_class=HTMLResponse)
async def verify_code_page(request: Request):
    return templates.TemplateResponse("verify_code.html", {"request": request})

# Ruta para mostrar la página de gestión de archivos
@app.get("/file-manager", response_class=HTMLResponse)
async def file_manager(request: Request):
    return templates.TemplateResponse("file_manager.html", {"request": request})

# Ruta para mostrar la página de usuarios
@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request):
    return templates.TemplateResponse("users.html", {"request": request})

# Ruta para mostrar la página de compartir archivos
@app.get("/share-files", response_class=HTMLResponse)
async def share_files_page(request: Request):
    return templates.TemplateResponse("share_files.html", {"request": request})

# Ruta para mostrar la página de administración de usuario
@app.get("/admin-user", response_class=HTMLResponse)
async def admin_user_page(request: Request):
    return templates.TemplateResponse("admin_user.html", {"request": request})

@app.post("/upload-file/")
async def upload_file(file: UploadFile = File(...)):
    valid_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.docx']
    ext = os.path.splitext(file.filename)[1].lower()

    if ext not in valid_extensions:
        return JSONResponse(status_code=400, content={"message": "Tipo de archivo no válido."})

    # Guardar archivo en GridFS
    file_id = fs.put(file.file, filename=file.filename, content_type=mimetypes.guess_type(file.filename)[0])
    return {"file_id": str(file_id), "filename": file.filename}

@app.get("/download-file/{file_id}")
async def download_file(file_id: str):
    try:
        file_data = fs.get(file_id)
        return JSONResponse(content={"filename": file_data.filename, "content_type": file_data.content_type})
    except Exception as e:
        return JSONResponse(status_code=404, content={"message": "Archivo no encontrado."})

# Ruta para mostrar el listado de usuarios    
@app.get("/api/usuarios")
async def obtener_usuarios():
    usuarios = []
    async for usuario in usuarios_collection.find({}, {"_id": 1, "nombres": 1, "apellidos": 1, "correo_electronico": 1, "rol": 1}):
        usuario["_id"] = str(usuario["_id"])  # Convertimos ObjectId a string
        usuarios.append(usuario)
    
    return JSONResponse(content=usuarios)

# Ruta para eliminar usuario
@app.delete("/api/usuarios/{usuario_id}")
async def eliminar_usuario(usuario_id: str):
    resultado = await usuarios_collection.delete_one({"_id": usuario_id})
    
    if resultado.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return {"mensaje": "Usuario eliminado correctamente"}

# Ruta para modificar usuario
@app.put("/api/usuarios/{usuario_id}")
async def modificar_usuario(usuario_id: str, usuario: UsuarioUpdate):
    resultado = await usuarios_collection.update_one(
        {"_id": usuario_id},
        {"$set": usuario.dict()}
    )
    
    if resultado.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return {"mensaje": "Usuario actualizado correctamente"}
