#!/usr/bin/env python3
"""
Script para crear un endpoint de debug que muestre exactamente
qué mensajes está recibiendo el bot desde Node-RED
"""

from flask import Flask, request, jsonify
import json
from datetime import datetime

app = Flask(__name__)

@app.route('/debug/webhook', methods=['POST'])
def debug_webhook():
    """Endpoint de debug para capturar mensajes de Node-RED"""
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Capturar todos los datos
    headers = dict(request.headers)
    json_data = request.get_json() if request.is_json else None
    form_data = dict(request.form) if request.form else None
    raw_data = request.get_data(as_text=True)
    
    debug_info = {
        "timestamp": timestamp,
        "method": request.method,
        "url": request.url,
        "headers": headers,
        "json_data": json_data,
        "form_data": form_data,
        "raw_data": raw_data
    }
    
    # Imprimir en consola
    print(f"\n{'='*60}")
    print(f"DEBUG WEBHOOK - {timestamp}")
    print(f"{'='*60}")
    
    if json_data:
        print(f"📨 JSON DATA:")
        print(json.dumps(json_data, indent=2, ensure_ascii=False))
    
    if form_data:
        print(f"📝 FORM DATA:")
        print(json.dumps(form_data, indent=2, ensure_ascii=False))
        
    if raw_data:
        print(f"📄 RAW DATA:")
        print(raw_data)
    
    # Extraer mensaje si existe
    message_text = None
    if json_data:
        message_text = json_data.get('message', json_data.get('text', None))
        if isinstance(message_text, dict):
            message_text = message_text.get('text', None)
    
    if message_text:
        print(f"🎯 MENSAJE DETECTADO: '{message_text}'")
        
        # Verificar si el formato es correcto
        formats_ok = [
            "COMPANIA_DETECTADA" in message_text.upper(),
            "OPERATOR" in message_text.upper(),
            message_text.strip() in ['Telcel', 'Movistar', 'AT&T', 'Unefon', 'Virgin Mobile', 'Altan Redes', 'Spot Uno']
        ]
        
        if any(formats_ok):
            print(f"✅ FORMATO CORRECTO - Bot debería detectar compañía")
        else:
            print(f"❌ FORMATO INCORRECTO - Bot enviará mensaje genérico")
            print(f"💡 Formatos esperados:")
            print(f"   - COMPANIA_DETECTADA NombreOperador")
            print(f"   - OPERATOR NombreOperador NUMERO 1234567890")
            print(f"   - NombreOperador (directo)")
    else:
        print(f"❌ NO SE ENCONTRÓ MENSAJE DE TEXTO")
    
    print(f"{'='*60}\n")
    
    # Responder como lo haría Rasa
    return jsonify([{
        "text": f"Debug: Recibí mensaje '{message_text}' a las {timestamp}"
    }])

@app.route('/status', methods=['GET'])
def status():
    """Endpoint de status"""
    return jsonify({"status": "Debug webhook activo"})

if __name__ == '__main__':
    print("🚀 INICIANDO DEBUG WEBHOOK")
    print("="*50)
    print("URL: http://localhost:5006/debug/webhook")
    print("Status: http://localhost:5006/status") 
    print("Configura Node-RED para enviar mensajes aquí")
    print("="*50)
    
    app.run(host='0.0.0.0', port=5006, debug=True)
