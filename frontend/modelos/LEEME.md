# Modelo 3D del cuerpo (`cuerpo.glb`)

**Atribución obligatoria (va en las referencias de la entrega):**

> BodyParts3D, © The Database Center for Life Science licensed under CC Attribution 4.0 International
> https://dbarchive.biosciencedbc.jp/en/bodyparts3d/lic.html

Nota: los archivos OBJ originales todavía traen el texto de licencia antiguo (CC BY-SA 2.1 Japón); la página oficial indica que desde el 27/02/2025 la licencia vigente es **CC BY 4.0**.

## Cómo se construyó

1. Fuente: `partof_BP3D_4.0_obj_99.zip` (65 MB) de https://dbarchive.biosciencedbc.jp/en/bodyparts3d/download.html
2. Piezas elegidas por concepto FMA (`scripts/grupos_bodyparts3d.json`):
   corazón (FMA7088), pulmones (FMA7309, FMA7310), cerebro (FMA50801), ojos (FMA12514, FMA12515),
   esqueleto (FMA23881), sistema cardiovascular (FMA7161, sin hígado ni otros órganos), piel (FMA7163).
3. Blender 5.2 (`scripts/construir_cuerpo_blender.py`): une las piezas de cada órgano, las simplifica
   (~1,2 M → ~132 mil vértices), pasa de mm a metros, apoya los pies en y = 0 y exporta un `.glb` (4,8 MB).

```bash
blender -b --factory-startup --python scripts/construir_cuerpo_blender.py -- <carpeta_obj> scripts/grupos_bodyparts3d.json frontend/modelos/cuerpo.glb
```

## Contrato con el visor

Un objeto por órgano con estos nombres exactos: `corazon`, `cerebro`, `pulmones`, `huesos`, `ojos`, `sangre`, `piel`.
Si alguien cambia el modelo (por ejemplo, uno hecho a mano en Blender), debe mantener esos nombres.
Si el `.glb` no carga, el visor usa automáticamente el cuerpo simple construido por código.
