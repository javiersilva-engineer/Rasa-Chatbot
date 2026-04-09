# 🔍 Guía Rápida de Debugging

## Estructura de Logs (Nueva)

Todos los logs ahora siguen este patrón:

```
======================================================================
[ACCIÓN] Iniciando: action_change_base
  - base_id: 5f7c2b1e...
  - ring_id: 5f7baf4e...
======================================================================

... [código ejecutándose] ...

======================================================================
[ACCIÓN] Finalizando: action_change_base
  - SlotSet: ring_id = 5f7c2b1e
  - SlotSet: profile_id = None
  - SlotSet: variante_id = None
  - SlotSet: base_id = None
======================================================================
```

---

## 🐛 Debugging: Paso a Paso

### Problema: "El cambio no se guarda"

```
1. Buscar en logs: [ACCIÓN] Iniciando
   └─ ¿Se recibió el slot?
   
2. Buscar en logs: [ACCIÓN] Finalizando
   └─ ¿Se retornó SlotSet()?
   
3. Si no hay logs, la acción NI SIQUiera se ejecutó
   └─ Problema en rules/domain.yml, no en la acción
```

### Problema: "El API devuelve error"

```
Buscar: [action_change_base] ERROR HTTP [STATUS]

Si ves:
- [action_change_base] GET http://louv.ovh/api/...
- [action_change_base] ERROR HTTP 404

Significa:
- El endpoint está MAL en el código
- Verificar URL en el .env o en el código
```

### Problema: "Dice que cambió, pero el frontend no actualiza"

```
1. Buscar: [ACCIÓN] Finalizando
   └─ ¿Hay SlotSets? Si no, la acción retorna []
   
2. Buscar en dispatcher.utter_message()
   └─ ¿Tiene custom payload? Necesario para frontend
   
3. Verificar custom payload:
   ├─ "type": ¿es el que espera el frontend?
   ├─ "gemma_id": ¿tiene el ID correcto?
   └─ ¿Todos los datos necesarios?
```

---

## 📋 Checklist: ¿Por Qué Falla?

### La acción NO se ejecuta
- [ ] ¿Está en domain.yml?
- [ ] ¿El nombre es exacto?
- [ ] ¿El rule la triggeragent correctamente?
- [ ] ¿Hay conflicto con otro rule?

### Se ejecuta pero NO hace nada
- [ ] Ver logs: ¿Hay error de validación?
- [ ] ¿El slot de entrada está NULL?
- [ ] ¿El API devuelve error?

### Dice que funcionó pero frontend no actualiza
- [ ] Verificar `custom` payload
- [ ] ¿El "type" coincide con lo que espera el frontend?
- [ ] ¿Van todos los IDs necesarios?

### Los cambios se pierden cuando selecciono otra opción
- [ ] Ver logs: ¿Se limpian slots dependientes?
- [ ] Ej: Cambias base → ¿profile_id se resetea a None?
- [ ] Si no → Este es el problema (necesita más SlotSet(None))

---

## 🔧 Herramientas para Debugging

### Ver logs en tiempo real
```bash
# Terminal 1: Rasa en modo debug
rasa shell --debug

# Terminal 2: Tail del archivo de logs (si estás en producción)
tail -f /ruta/logs/rasa.log | grep "\[ACCIÓN\]"
```

### Buscar en logs
```bash
# Todas las acciones que fallaron
grep "ERROR" rasa.log | grep "\[action_"

# Una acción específica
grep "action_change_base" rasa.log

# Todas las acciones iniciadas
grep "\[ACCIÓN\] Iniciando" rasa.log
```

### Ver estado de slots en Shell
```
En Rasa shell después de cada respuesta:
>> /set_slot(slot_name, value)  # Establece manual
>> Listo, ahora puedes continuar

# O ver en conversación con /debug
```

---

## 📊 Ejemplos de Logs y Qué Significan

### ✅ TODO OK
```
======================================================================
[ACCIÓN] Iniciando: action_change_base
  - base_id: 5f7c2b1e90a9b4c8d2e3f5a1
======================================================================
[action_change_base] Actualizando slots
======================================================================
[ACCIÓN] Finalizando: action_change_base
  - SlotSet: ring_id = 5f7c2b1e90a9b4c8d2e3f5a1
  - SlotSet: profile_id = None
  - SlotSet: variante_id = None
  - SlotSet: base_id = None
======================================================================
```

### ❌ Falta base_id
```
======================================================================
[ACCIÓN] Iniciando: action_change_base
  - base_id: None  ← ⚠️ PROBLEMA
======================================================================
[action_change_base] ERROR: base_id no recibido
======================================================================
[ACCIÓN] Finalizando: action_change_base
  - (sin SlotSets)
======================================================================
```

### ❌ Error de API
```
======================================================================
[ACCIÓN] Iniciando: action_ask_material_id
  - ring_id: 5f7c2b1e90a9b4c8d2e3f5a1
======================================================================
[action_ask_material_id] GET http://louv.ovh/api/baseStructures
[action_ask_material_id] Response status: 500  ← ⚠️ ERROR
[action_ask_material_id] ERROR HTTP 500
======================================================================
[ACCIÓN] Finalizando: action_ask_material_id
  - (sin SlotSets)
======================================================================
```

### ❌ Metadata stale
```
======================================================================
[ACCIÓN] Iniciando: action_ask_variante_id
  - Ring ID (metadata): 5f7c2b1e  ← Viejo
  - Ring ID (slot): None         ← No existe
  - Ring ID (final): 5f7c2b1e    ← Usa metadatavieja
======================================================================
[action_ask_variante_id] GET http://louv.ovh/api/.../5f7c2b1e
[action_ask_variante_id] Response status: 404  ← El ID no existe
======================================================================
```

---

## 💡 Trucos para Avanzados

### Logs con JSON formateado
```python
import json
print(f"[ACTION] Data: {json.dumps(data, indent=2)}")
```

### Logs condicionales
```python
if DEBUG_MODE:
    log_action_start(...)
```

### Rastrear un request específico
```python
# En el principio de la acción
conversation_id = tracker.sender_id
print(f"[{action_name}] Conv: {conversation_id}")

# Luego buscar:
# grep "Conv: <id>" logs.txt
```

### Medir tiempo de ejecución
```python
import time
start = time.time()
# ... código ...
elapsed = time.time() - start
print(f"[{action_name}] Took {elapsed:.2f}s")
```

---

## 🎯 Resumen Rápido

| Síntoma | Buscar en Logs |
|--------|-----------------|
| No se ejecuta | `[ACCIÓN] Iniciando` - si no aparece, problema en domain.yml |
| Error validación | `ERROR: ` seguido del nombre del slot faltante |
| Error API | `ERROR HTTP [codigo]` - verificar endpoint y URL |
| Cambio no persiste | `SlotSet` en `Finalizando` - si no hay, acción retorna [] |
| Frontend no actualiza | `custom` en utter_message - verificar "type" y datos |
| Datos viejos | `metadata` vs `slot` en logs - si metadata vieja, es bug de flow |
