# SETUP META WhatsApp Cloud API — Número de prueba gratuito
# Sigue estos pasos después de tener Railway funcionando

## ─────────────────────────────────────────
## PASO 1: Crear cuenta de Meta for Developers
## ─────────────────────────────────────────
# Ve a: https://developers.facebook.com
# Inicia sesión con tu cuenta de Facebook
# Acepta los términos de desarrollador si te los pide

## ─────────────────────────────────────────
## PASO 2: Crear una nueva App
## ─────────────────────────────────────────
# 1. Clic en "My Apps" → "Create App"
# 2. Tipo de app: selecciona "Other" → "Next"
# 3. Tipo: selecciona "Business" → "Next"
# 4. Nombre: "AutoMax Agente" (o el nombre que quieras)
# 5. Email de contacto: el tuyo
# 6. Clic en "Create App"

## ─────────────────────────────────────────
## PASO 3: Agregar WhatsApp a la app
## ─────────────────────────────────────────
# En el dashboard de tu app:
# 1. Busca el producto "WhatsApp" y clic en "Set up"
# 2. Te pedirá una cuenta de Meta Business → clic en "Create new" si no tienes
# 3. Pon el nombre del negocio (ej: "AutoMax Demo")
# 4. Acepta los términos

## ─────────────────────────────────────────
## PASO 4: Obtener el número de prueba y credenciales
## ─────────────────────────────────────────
# En el menú izquierdo: WhatsApp → API Setup
# Ahí encontrarás:
#
#   "From" number → es tu NÚMERO DE PRUEBA GRATUITO (algo como +1 555 xxx xxxx)
#   Phone Number ID → cópialo (va en META_PHONE_NUMBER_ID en Railway)
#   Access Token temporal → cópialo (va en META_ACCESS_TOKEN en Railway)
#
# ⚠️  El Access Token temporal expira en ~24 horas.
#     Para producción se genera uno permanente, pero para la demo sirve.

## ─────────────────────────────────────────
## PASO 5: Agregar números de testers
## ─────────────────────────────────────────
# En: WhatsApp → API Setup → "To" number → "Manage phone number list"
# Agrega:
#   - Tu número de cel
#   - El número del cliente que verá la demo
# (Máximo 5 números en el plan gratuito)
# Cada número recibirá un código de verificación por WhatsApp para confirmarse

## ─────────────────────────────────────────
## PASO 6: Configurar el Webhook
## ─────────────────────────────────────────
# En el menú izquierdo: WhatsApp → Configuration → Webhooks
# Clic en "Edit"
#
#   Callback URL:  https://TU-URL-DE-RAILWAY.railway.app/webhook/meta
#   Verify Token:  automax_token_123  (el mismo que pusiste en Railway)
#
# Clic en "Verify and Save"
# Si Railway está corriendo bien, Meta lo verificará automáticamente ✅
#
# Después en "Webhook fields" → suscribir a: messages ✅

## ─────────────────────────────────────────
## PASO 7: Actualizar variables en Railway
## ─────────────────────────────────────────
# Ahora que tienes los datos de Meta, ve a Railway:
# Dashboard → tu proyecto → Variables
# Actualiza:
#   META_ACCESS_TOKEN    = (el token que copiaste en Paso 4)
#   META_PHONE_NUMBER_ID = (el ID que copiaste en Paso 4)
# Railway reinicia el servidor automáticamente

## ─────────────────────────────────────────
## PASO 8: ¡Probar!
## ─────────────────────────────────────────
# Desde tu cel (registrado como tester):
# Manda un WhatsApp al número de prueba que te dio Meta
# Ejemplo: "Hola, ¿cuánto cuesta el cambio de aceite?"
# El agente debería responder en segundos 🚗🔧
