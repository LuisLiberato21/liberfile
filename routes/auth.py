from fastapi import APIRouter, Form, HTTPException, Body, Request, Depends
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from motor.motor_asyncio import AsyncIOMotorClient
from email.mime.text import MIMEText
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from core.config import MONGO_DETAILS
import bcrypt
import random
import time
import string
import smtplib


router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Configuración de MongoDB
client = AsyncIOMotorClient(MONGO_DETAILS)
db = client['liberfile_db']
usuarios_collection = db['usuarios']

# Modelos de datos
class Usuario(BaseModel):
    cedula: str
    usuario: str
    nombres: str
    apellidos: str
    correo: EmailStr
    direccion: str
    telefono: str
    contraseña: str
    rol: str

# Ruta para mostrar el formulario de registro
@router.get("/register-user", response_class=HTMLResponse)
async def mostrar_registro_usuario(request: Request):
    return templates.TemplateResponse("register_user.html", {"request": request})

# Registrar usuario
@router.post("/register")
async def registrar_usuario(
    cedula: str = Form(...),
    usuario: str = Form(...),
    nombres: str = Form(...),
    apellidos: str = Form(...),
    correo_electronico: str = Form(...),
    direccion: str = Form(None),
    telefono: str = Form(None),
    contraseña: str = Form(...),
    rol: str = Form(...),
):
    # Verificar si el usuario ya existe
    usuario_existente = await usuarios_collection.find_one({"_id": cedula})
    if usuario_existente:
        return JSONResponse(content={"detail": "La cédula ya está registrada"}, status_code=400)

    usuario_existente = await usuarios_collection.find_one({"usuario": usuario})
    if usuario_existente:
        return JSONResponse(content={"detail": "El nombre de usuario ya existe"}, status_code=400)
    
    correo_existente = await usuarios_collection.find_one({"correo_electronico": correo_electronico})
    if correo_existente:
        return JSONResponse(content={"detail": "El correo electrónico ya está en uso"}, status_code=400)

    # Si el usuario no existe, continúa con el registro
    hashed_password = bcrypt.hashpw(contraseña.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    nuevo_usuario = {
        "_id": cedula,
        "usuario": usuario,
        "nombres": nombres,
        "apellidos": apellidos,
        "correo_electronico": correo_electronico,
        "direccion": direccion,
        "telefono": telefono,
        "contraseña": hashed_password,
        "rol": rol,
    }
    await usuarios_collection.insert_one(nuevo_usuario)

    # Devolver respuesta JSON indicando éxito
    return JSONResponse(content={"mensaje": "Usuario registrado exitosamente."}, status_code=200)

# Iniciar sesión
@router.post("/login")
async def login(usuario: str = Form(...), contraseña: str = Form(...)):
    usuario_db = await usuarios_collection.find_one({"usuario": usuario}) 
    if not usuario_db:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if bcrypt.checkpw(contraseña.encode('utf-8'), usuario_db['contraseña'].encode('utf-8')):
        return {
            "mensaje": "Inicio de sesión exitoso, bienvenido",
            "nombres": usuario_db['nombres'],
            "apellidos": usuario_db['apellidos']
        }
    raise HTTPException(status_code=401, detail="Contraseña incorrecta")

# Eliminar usuario
@router.delete("/delete-user")
async def eliminar_usuario(cedula: str = Body(...)):
    result = await usuarios_collection.delete_one({"_id": cedula})
    if result.deleted_count == 1:
        return {"message": "Usuario eliminado exitosamente."}
    raise HTTPException(status_code=404, detail="Usuario no encontrado")

# Página de modificar contraseña
@router.get("/modify-password")
async def modify_password_page(request: Request):
    return templates.TemplateResponse("modify_password.html", {"request": request})

# Modificar contraseña
@router.post("/modify-password")
async def modify_password(
    request: Request,
    usuario: str = Form(...),
    contraseña_actual: str = Form(...),
    nueva_contraseña: str = Form(...),
):
    usuario_db = await usuarios_collection.find_one({"usuario": usuario})
    
    if not usuario_db or not bcrypt.checkpw(contraseña_actual.encode('utf-8'), usuario_db['contraseña'].encode('utf-8')):
        return JSONResponse(content={"detail": "Usuario o contraseña actual incorrectos"}, status_code=400)
    
    nueva_contraseña_hash = bcrypt.hashpw(nueva_contraseña.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    await usuarios_collection.update_one({"usuario": usuario}, {"$set": {"contraseña": nueva_contraseña_hash}})
    
    return JSONResponse(content={"mensaje": "Contraseña modificada con éxito"}, status_code=200)

# Restablecer contraseña
@router.post("/reset-password")
async def send_reset_email(usuario: str = Form(...), email: str = Form(...)):
    usuario_db = await usuarios_collection.find_one({"usuario": usuario, "correo_electronico": email})
    if not usuario_db:
        raise HTTPException(status_code=404, detail="Usuario o correo no encontrados")

    # Generar un código de verificación o un token
    codigo_verificacion = generar_codigo_verificacion()
    tiempo_expiracion = time.time() + 600  # Expira en 10 minutos
    # Almacena el código o token en la base de datos asociado al usuario para verificarlo más tarde
    await usuarios_collection.update_one({"usuario": usuario}, {"$set": {"codigo_verificacion": codigo_verificacion, "codigo_expiracion": tiempo_expiracion}})

    enviar_email(email, "Recuperación de contraseña", f"Tu código de verificación es: {codigo_verificacion}")
    
    return {"mensaje": "Correo de restablecimiento enviado"}

# Página de restablecimiento de contraseña
@router.get("/reset-password")
async def reset_password_page(request: Request):
    return templates.TemplateResponse("reset_password.html", {"request": request})

# Función para generar código de verificación
def generar_codigo_verificacion(length=6):
    caracteres = string.ascii_letters + string.digits
    codigo = ''.join(random.choice(caracteres) for _ in range(length))
    return codigo

# Función para enviar correo
def enviar_email(destinatario: str, asunto: str, cuerpo: str):
    remitente = "liberfile@gmail.com"
    contraseña = "gqnq mhvl sjwg swpr"  # Mejor usar variables de entorno

    msg = MIMEText(cuerpo)
    msg['Subject'] = asunto
    msg['From'] = remitente
    msg['To'] = destinatario

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(remitente, contraseña)
            server.sendmail(remitente, destinatario, msg.as_string())
            print("Correo enviado exitosamente")
    except Exception as e:
        print(f"Error enviando correo: {e}")

@router.post("/verify-code")  # La ruta sea la misma que la del formulario
async def verificar_codigo(usuario: str = Form(...), codigo: str = Form(...), nueva_contraseña: str = Form(...)):
    usuario_db = await usuarios_collection.find_one({"usuario": usuario})
    
    if not usuario_db:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Verificar si el código coincide
    if usuario_db.get("codigo_verificacion") != codigo:
        raise HTTPException(status_code=400, detail="Código incorrecto")

    # Verificar si el código ha expirado
    if time.time() > usuario_db.get("codigo_expiracion", 0):
        raise HTTPException(status_code=400, detail="El código ha expirado")

    # Actualizar la contraseña del usuario en la base de datos
    hashed_password = bcrypt.hashpw(nueva_contraseña.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    await usuarios_collection.update_one(
        {"usuario": usuario},
        {
            "$set": {"contraseña": hashed_password},
            "$unset": {"codigo_verificacion": "", "codigo_expiracion": ""}
        }
    )
    
    return JSONResponse(content={"mensaje": "Contraseña actualizada exitosamente"}, status_code=200)