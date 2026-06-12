# AJ | Generador de Propuesta de Inversión

App en Streamlit para generar únicamente la página 1 de una propuesta de inversión con formato AJ.

## Archivos

- `app.py`: aplicación principal.
- `requirements.txt`: dependencias para Streamlit Cloud.

## Cómo usar en Streamlit Cloud

1. Crea un repositorio en GitHub.
2. Sube `app.py` y `requirements.txt`.
3. Entra a Streamlit Cloud.
4. Selecciona tu repositorio.
5. Main file path: `app.py`.
6. Deploy.

## Funcionalidad

- Captura datos generales del cliente.
- Edita instrumentos gubernamentales y corporativos.
- Calcula automáticamente:
  - % Gobierno
  - % Corporativos
  - % UDIS
  - Tasa ponderada
  - Duración ponderada
- Genera PDF de una página con diseño AJ.