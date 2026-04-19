# SETUP RAILWAY — Comandos para Windows
# Copia y pega estos comandos en orden en tu terminal (PowerShell)

## ─────────────────────────────────────────
## PASO 1: Instalar Scoop (gestor de paquetes para Windows)
## Abre PowerShell como administrador y corre estos 2 comandos:
## ─────────────────────────────────────────

Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

irm get.scoop.sh | iex


## ─────────────────────────────────────────
## PASO 2: Instalar Railway CLI
## ─────────────────────────────────────────

scoop bucket add railway https://github.com/railwayapp/scoop-railway

scoop install railway/railway


## ─────────────────────────────────────────
## PASO 3: Login en Railway con token (sin browser)
## ─────────────────────────────────────────

railway login --token 8284dee0-d8de-4b68-b7ff-a9633cbd14cc


## ─────────────────────────────────────────
## PASO 4: Ir a la carpeta del proyecto
## ─────────────────────────────────────────

cd "C:\Users\aleja\OneDrive\Escritorio\Alejandro\Agente Lote Autos\AGENTE LOTE AUTOS\whatsapp-agent"


## ─────────────────────────────────────────
## PASO 5: Vincular con el proyecto ya creado en Railway
## (proyecto: valiant-essence, ID: b50e6eb3-4215-41f9-a88f-15ef2db3f4ea)
## ─────────────────────────────────────────

railway link --project b50e6eb3-4215-41f9-a88f-15ef2db3f4ea


## ─────────────────────────────────────────
## PASO 6: Subir el código a Railway
## ─────────────────────────────────────────

railway up --detach


## ─────────────────────────────────────────
## PASO 7: Generar URL pública del servidor
## ─────────────────────────────────────────

railway domain


## ─────────────────────────────────────────
## VARIABLES DE ENTORNO — agregar en Railway después del deploy
## Dashboard → tu proyecto → Variables → Add Variable
## ─────────────────────────────────────────

# ANTHROPIC_API_KEY    = sk-ant-XXXXXXXX  (tu API key de Claude)
# NOMBRE_AGENTE        = Carlos            (nombre del asesor)
# META_VERIFY_TOKEN    = automax_token_123 (lo inventas tú, lo usarás en Meta)
# META_ACCESS_TOKEN    = (se obtiene después en Meta for Developers)
# META_PHONE_NUMBER_ID = (se obtiene después en Meta for Developers)
