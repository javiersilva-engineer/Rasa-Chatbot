# 📋 Guía de Mejores Prácticas para Acciones Rasa

## 🎯 Objetivo
Este documento establece estándares para asegurar que todas las acciones funcionen de manera **consistente y confiable**.

---

## ⚠️ Problemas Que Se Solucionaron

### 1. **Inconsistencia en Manejo de Metadata vs Slots**
**Problema:** Algunas acciones usaban `tracker.get_slot()` primero, otras `metadata` primero.
**Solución:** Usar `extract_ring_context()` que **siempre prioriza metadata** (datos más recientes).

```python
# ❌ ANTES (Inconsistente)
ring_id = tracker.get_slot('ring_id')  # Podría ser stale

# ✅ DESPUÉS (Consistente)
context = extract_ring_context(tracker)
ring_id = context.ring_id  # Metadata tiene prioridad
```

---

### 2. **Limpieza Inconsistente de Slots**
**Problema:** Algunos slots se limpiaban, otros no, causando que valores viejos persistieran.
**Solución:** **Regla clara:** Siempre limpiar el slot después de usarlo.

```python
# ❌ ANTES
dispatcher.utter_message(...)
return []  # El slot sigue en memoria

# ✅ DESPUÉS
return [SlotSet("material_id", None)]  # Limpiar siempre
```

---

### 3. **Errores Silenciosos en APIs**
**Problema:** Si el API fallaba, la acción decía "OK" pero no hacía nada.
**Solución:** Usar `safe_api_call()` que valida **estatus HTTP + estructura de datos**.

```python
# ❌ ANTES
try:
    data = await response.json()
    items = data.get('items', [])  # ¿Qué pasa si 'items' no existe?

# ✅ DESPUÉS
success, data = await safe_api_call(session, endpoint, "action_nombre", expected_key='items')
if not success:
    return []
```

---

### 4. **Logs Inconsistentes**
**Problema:** Logs desorganizados hacían difícil el debugging.
**Solución:** Usar `log_action_start()` y `log_action_end()` para logs estructurados.

```python
# ❌ ANTES
print("[DEBUG] INICIO ActionChangeBase")
print(f"[DEBUG] base_id: {base_id}")

# ✅ DESPUÉS
log_action_start("action_change_base", base_id=base_id)
log_action_end("action_change_base", [SlotSet("ring_id", base_id)])
```

---

## 📝 Plantilla para Nuevas Acciones

```python
class ActionMyNewAction(Action):
    """
    Descripción clara de qué hace esta acción.
    Qué slots necesita y qué slots retorna.
    """
    
    def name(self) -> Text:
        return "action_my_new_action"

    async def run(
        self, 
        dispatcher: CollectingDispatcher, 
        tracker: Tracker, 
        domain
    ) -> List[Dict[Text, Any]]:
        
        action_name = self.name()
        
        # ============ OBTENER CONTEXTO ============
        context = extract_ring_context(tracker)
        my_slot = tracker.get_slot('my_slot')
        
        # ============ LOGGING ============
        log_action_start(action_name, slot_name=my_slot, ring_id=context.ring_id)
        
        # ============ VALIDACIÓN ============
        if not my_slot:
            dispatcher.utter_message(text="Mensaje de error claro")
            log_action_end(action_name, [])
            return []
        
        if not validate_ring_context(dispatcher, context, ['ring_id'], action_name):
            log_action_end(action_name, [])
            return []
        
        # ============ LLAMADAS A API (si es necesario) ============
        api_url = os.getenv("API_URL", "https://louv.ovh")
        try:
            async with aiohttp.ClientSession() as session:
                success, data = await safe_api_call(
                    session, 
                    f"{api_url}/api/endpoint",
                    action_name,
                    expected_key='expectedData'
                )
                
                if not success:
                    handle_api_error(dispatcher, action_name, "data")
                    log_action_end(action_name, [])
                    return []
                
                # Procesar datos
                items = data.get('expectedData', [])
                
        except Exception as e:
            print(f"[{action_name}] ERROR no capturado: {e}")
            handle_api_error(dispatcher, action_name, "general")
            log_action_end(action_name, [])
            return []
        
        # ============ RETORNAR CAMBIOS ============
        events = [
            SlotSet("my_slot", None),          # 🧹 Limpiar slot usado
            SlotSet("other_slot", value),      # 💾 Guardar datos si necesario
        ]
        
        dispatcher.utter_message(
            text="Mensaje de éxito",
            custom={
                "type": "custom_event_type",
                "data": "value"
            }
        )
        
        log_action_end(action_name, events)
        return events
```

---

## 🔗 Cadena de Dependencias de Slots

Cuando cambias un slot padre, **SIEMPRE resetea todos sus hijos:**

```
ring_id (base)
├── profile_id (depende de ring_id)
│   ├── variante_id (depende de profile_id)
│   └── otras opciones del perfil
├── material_id
│   └── pureza_id (depende de material_id)
└── otras opciones de la base

gem_position
├── gem_position_for_cut (diferente contexto)
└── gem_position_for_setting (diferente contexto)
```

**Regla:** Si cambias `X`, resetea todos sus dependientes.

```python
def run(...):
    # Cambiar base → resetear todo lo que depende de ella
    return [
        SlotSet("ring_id", base_id),        # ✓ Establecer nuevo
        SlotSet("profile_id", None),        # ✓ Resetear hijo
        SlotSet("variante_id", None),       # ✓ Resetear nieto
        SlotSet("base_id", None),           # ✓ Limpiar temporal
    ]
```

---

## ✅ Checklist Antes de "Commit"

- [ ] La acción usa `extract_ring_context()` si necesita ring_id
- [ ] Todos los slots se validan con `validate_ring_context()` o check manual
- [ ] Las llamadas API usan `safe_api_call()`
- [ ] Los errores usan `handle_api_error()`
- [ ] Usa `log_action_start()` y `log_action_end()`
- [ ] Los slots temporales se limpian: `SlotSet("slot_name", None)`
- [ ] Los slots hijo se resetean cuando el padre cambia
- [ ] Hay conversiones seguras (try/except) para tipos de datos
- [ ] El mensaje de error al usuario es **claro y útil**
- [ ] El custom payload al frontend tiene all los datos necesarios

---

## 🔍 Debugging: Qué Revisar Si Algo Falla

1. **¿El slot tiene un valor?** → Ver logs de `log_action_start()`
2. **¿El API devolvió 200?** → Ver logs de `safe_api_call()`
3. **¿Los datos están en la estructura esperada?** → Ver expected_key
4. **¿Se limpió el slot?** → Ver logs de `log_action_end()`
5. **¿El metadata tiene datos recientes?** → Check en `extract_ring_context()`

---

## 📚 Funciones Auxiliares Disponibles

| Función | Uso |
|---------|-----|
| `extract_ring_context(tracker)` | Obtener ring_id, profile_id, variant_id con prioridad metadata |
| `safe_api_call(session, endpoint, action_name, expected_key)` | Llamada API segura con validación |
| `validate_ring_context(dispatcher, context, required_ids, action_name)` | Validar IDs necesarios |
| `log_action_start(action_name, **context)` | Log estructurado al inicio |
| `log_action_end(action_name, events)` | Log estructurado al final |
| `handle_api_error(dispatcher, action_name, error_type)` | Manejar errores API consistentemente |

---

## 🚀 Resultado: Más Confiable y Mantenible

✅ **Acciones consistentes** - Mismo patrón en todas  
✅ **Menos bugs** - Validación y limpieza centralizada  
✅ **Debugging fácil** - Logs estructurados y claros  
✅ **Mantenimiento simple** - Código predecible  
