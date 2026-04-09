# 📊 Resumen de Refactorización: action_3dengine.py

## 🎯 Cambios Realizados

### Fase 1: Funciones Auxiliares Centralizadas ✅

Se añadieron funciones reutilizables para **estandarizar** todas las acciones:

```python
# 1. RingContext - Contenedor para contexto del anillo
class RingContext:
    ring_id: Optional[str]
    profile_id: Optional[str]
    variant_id: Optional[str]
    
    def is_valid() -> bool
    def has_all_ids() -> bool

# 2. extract_ring_context(tracker)
# Obtiene contexto con prioridad: metadata > slots
# Siempre retorna data más reciente

# 3. safe_api_call(session, endpoint, action_name, expected_key)
# Llamada API SEGURA con validación HTTP + estructura
# Retorna (success: bool, data: Optional[Dict])

# 4. validate_ring_context(dispatcher, context, required_ids, action_name)
# Valida que existan los IDs necesarios
# Envía mensaje de error automático si faltan

# 5. log_action_start(action_name, **context)
# Log estructurado al INICIO de acción
# Muestra qué slots/IDs se recibieron

# 6. log_action_end(action_name, events)
# Log estructurado al FINAL de acción
# Muestra qué slots se van a actualizar

# 7. handle_api_error(dispatcher, action_name, error_type)
# Manejo consistente de errores
# Mensajes de error claros y útiles
```

---

### Fase 2: Refactorización de Acciones de "Cambio" ✅

Se refactorizaron **8 acciones clave** para usar las funciones auxiliares:

#### 1️⃣ `ActionChangeBase` 
```python
ANTES:
- Prints inconsistentes
- No reseteaba variante_id
- Retornaba ring_id innecesariamente

DESPUÉS:
- Usa log_action_start/end
- Resetea ring_id → profile_id → variante_id (cascada)
- Limpia slot temporal base_id
- Mensaje de error claro
```

#### 2️⃣ `ActionChangeProfile`
```python
ANTES:
- No limpiaba profile_id
- Comentario "NO limpiar aquí"

DESPUÉS:
- Resetea variante_id (depende de profile)
- Limpia profile_id después de usarlo
- Logs estructurados
```

#### 3️⃣ `ActionChangeVariante`
```python
ANTES:
- No limpiaba variante_id
- Comentario "NO limpiar aquí"

DESPUÉS:
- Limpia variante_id siempre
- Logs estructurados
- Validación clara
```

#### 4️⃣ `ActionChangeMaterial`
```python
ANTES:
- Lógica con eventos inline

DESPUÉS:
- Usa helper functions
- Logs claros
- Validación con log_action_start/end
```

#### 5️⃣ `ActionChangePurezaMaterial`
```python
ANTES:
- Error silencioso si material_id faltante
- Logs inconsistentes

DESPUÉS:
- Valida current_material_id
- Mensaje de error útil si falta
- Limpia ambos slots al finalizar
```

#### 6️⃣ `ActionChangeGema`
```python
ANTES:
- Conversión de gem_position inline
- No validaba input

DESPUÉS:
- Usa log_action_start/end
- Validación clara de gema_id
- Default gem_position = 0 explícito
```

#### 7️⃣ `ActionChangeFormaGema`
```python
ANTES:
- Conversión try/except anidada
- Error silencioso con WARNING

DESPUÉS:
- Usa log_action_start/end
- Conversión segura documentada
- Validación clara
```

#### 8️⃣ `ActionChangeEngaste` → `ActionChangeBoxShape` → `ActionChangeBoxOuterColor` → `ActionChangeBoxInnerColor`
```python
ANTES:
- Inconsistentes entre sí
- Algunos validaban, otros no
- Logs diferentes

DESPUÉS:
- Siguen mismo patrón
- Validación uniforme
- Logs estructurados
- Mensajes de error claros
```

---

## 🔄 Patrón de Slot Limpieza

### **Cascada de Dependencias**

Cuando cambias un slot, **DEBES resetear sus dependientes:**

```
ring_id (base)
    ↓ actualiza
profile_id (depende de ring_id)
    ↓ resetea
variante_id (depende de profile_id)

material_id (base)
    ↓ actualiza
current_material_id (depende de material_id)
    ↓ resetea
pureza_id (depende de material_id)
```

### Implementación:

```python
# ActionChangeBase
return [
    SlotSet("ring_id", base_id),      # ✅ Nuevo valor
    SlotSet("profile_id", None),       # ✅ Resetear hijo
    SlotSet("variante_id", None),      # ✅ Resetear nieto
    SlotSet("base_id", None)           # ✅ Limpiar temporal
]

# ActionChangeProfile
return [
    SlotSet("variante_id", None),      # ✅ Resetear dependiente
    SlotSet("profile_id", None)        # ✅ Limpiar temporal
]

# ActionChangeMaterial
return [
    SlotSet("current_material_id", material_id),  # 💾 Guardar para pureza
    SlotSet("material_id", None)                   # 🧹 Limpiar temporal
]

# ActionChangePurezaMaterial
return [
    SlotSet("pureza_id", None),               # 🧹 Limpiar
    SlotSet("current_material_id", None)      # 🧹 Limpiar padre
]
```

---

## 🎁 Nuevos Archivos

### `ACTION_GUIDELINES.md`
- Guía completa de mejores prácticas
- Plantilla para nuevas acciones
- Checklist de validación
- Guía de debugging

---

## 📈 Beneficios de los Cambios

| Aspecto | Antes | Después |
|--------|--------|---------|
| **Consistencia** | 🔴 Cada acción diferente | 🟢 Mismo patrón en todas |
| **Debugging** | 🔴 Logs confusos | 🟢 Logs estructurados |
| **Errores API** | 🔴 Silenciosos | 🟢 Validación clara |
| **Limpieza slots** | 🔴 Inconsistente | 🟢 Cascada automática |
| **Mantenibilidad** | 🔴 Difícil | 🟢 Fácil (plantilla clara) |
| **Bugs** | 🔴 Frecuentes | 🟢 Menos probabilidad |

---

## 🚀 Próximos Pasos

1. **Refactorizar acciones de "pedir" (ActionAskXxx)**
   - Actualmente tienen API calls inline
   - Deberían usar `safe_api_call()` y `extract_ring_context()`

2. **Estandarizar slots en domain.yml**
   - Documentar cuáles slots dependen de cuáles
   - Usar convención de nombres clara

3. **Agregar tests unitarios**
   - Validar que slots se resetean correctamente
   - Validar que APIs se llaman con parámetros correctos

4. **Monitorear logs en producción**
   - Las nuevas estructuras facilitarán análisis

---

## 📝 Notas Técnicas

### Metadata vs Slots
- **Metadata** = datos en la REQUEST actual del usuario
- **Slots** = estado persistente entre mensajes
- **Prioridad:** metadata > slots (metadata siempre más reciente)

### API Errors
- Ahora validamos **HTTP status** AND **estructura JSON**
- Antes solo checkeábamos status, y si JSON estaba corrupto, no lo sábamos

### Logging
- Formato: `[ACCIÓN] mensaje` o `[ERROR] mensaje`
- Facilita buscar en logs específicamente problemas de una acción

---

## ⚠️ Consideraciones Especiales

### `gem_position` y variantes
- `gem_position`: Posición para cambiar gema específica
- `gem_position_for_cut`: Posición para cambiar forma de gema
- `gem_position_for_setting`: Posición para cambiar engaste
- **Estos SON DIFERENTES** - No mezclar slots

### Materiales
- `material_id`: Slot temporal del formulario
- `current_material_id`: Almacenamiento para pureza
- Esta distinción evita conflicts entre requests

---

## 🔍 Testing Manual

Para verificar que los cambios funcionan:

```yaml
# Test 1: Cambiar base sin resetear profile
- Usuario selecciona base A
- ✅ ring_id = base_A
- ✅ profile_id = None (reseteado)
- ✅ variante_id = None (reseteado)

# Test 2: Cambiar profile sin ofrecer variantes antiguas
- Usuario tenía variante X de perfil A
- Usuario cambia a perfil B
- ✅ profile_id = profile_B
- ✅ variante_id = None (no muestra X)

# Test 3: Error API
- API devuelve 500
- ✅ Acción retorna [] (error)
- ✅ Usuario ve mensaje: "Error de conexión con el servidor"
- ✅ Logs muestran: [ACCIÓN] ERROR HTTP 500

# Test 4: Material y pureza
- Usuario selecciona Material A (oro)
- ✅ current_material_id = Material_A
- Usuario selecciona Pureza X (18k)
- ✅ Ambos slots se limpian
- ✅ Frontend recibe: {type: "change_pureza", material_id: Material_A, pureza_id: Pureza_X}
```
