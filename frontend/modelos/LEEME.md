**English** | [Español](#español)

# 3D body model (`cuerpo.glb`)

**Required attribution (included in the submission references):**

> BodyParts3D, © The Database Center for Life Science licensed under CC Attribution 4.0 International
> https://dbarchive.biosciencedbc.jp/en/bodyparts3d/lic.html

Note: the original OBJ files still carry the old license text (CC BY-SA 2.1 Japan); the official page states that since 27/02/2025 the current license is **CC BY 4.0**.

## How it was built

1. Source: `partof_BP3D_4.0_obj_99.zip` (65 MB) from https://dbarchive.biosciencedbc.jp/en/bodyparts3d/download.html
2. Parts selected by FMA concept (`scripts/grupos_bodyparts3d.json`):
   heart (FMA7088), lungs (FMA7309, FMA7310), brain (FMA50801), eyes (FMA12514, FMA12515),
   skeleton (FMA23881), cardiovascular system (FMA7161, without the liver or other organs), skin (FMA7163).
3. Blender 5.2 (`scripts/construir_cuerpo_blender.py`): joins each organ's parts, simplifies them
   (~1.2 M → ~132 thousand vertices), converts millimeters to meters, rests the feet on y = 0 and exports a `.glb` (4.8 MB).

```bash
blender -b --factory-startup --python scripts/construir_cuerpo_blender.py -- <obj_folder> scripts/grupos_bodyparts3d.json frontend/modelos/cuerpo.glb
```

## Contract with the viewer

One object per organ with these exact names: `corazon`, `cerebro`, `pulmones`, `huesos`, `ojos`, `sangre`, `piel`.
Anyone who changes the model (for example, one made by hand in Blender) must keep those names.
If the `.glb` does not load, the viewer automatically uses the simple body built in code.

---

## Español

### Modelo 3D del cuerpo (`cuerpo.glb`)

**Atribución obligatoria (va en las referencias de la entrega):**

> BodyParts3D, © The Database Center for Life Science licensed under CC Attribution 4.0 International
> https://dbarchive.biosciencedbc.jp/en/bodyparts3d/lic.html

Nota: los archivos OBJ originales todavía traen el texto de licencia antiguo (CC BY-SA 2.1 Japón); la página oficial indica que desde el 27/02/2025 la licencia vigente es **CC BY 4.0**.

### Cómo se construyó

1. Fuente: `partof_BP3D_4.0_obj_99.zip` (65 MB) de https://dbarchive.biosciencedbc.jp/en/bodyparts3d/download.html
2. Piezas elegidas por concepto FMA (`scripts/grupos_bodyparts3d.json`):
   corazón (FMA7088), pulmones (FMA7309, FMA7310), cerebro (FMA50801), ojos (FMA12514, FMA12515),
   esqueleto (FMA23881), sistema cardiovascular (FMA7161, sin hígado ni otros órganos), piel (FMA7163).
3. Blender 5.2 (`scripts/construir_cuerpo_blender.py`): une las piezas de cada órgano, las simplifica
   (~1,2 M → ~132 mil vértices), pasa de mm a metros, apoya los pies en y = 0 y exporta un `.glb` (4,8 MB).

```bash
blender -b --factory-startup --python scripts/construir_cuerpo_blender.py -- <carpeta_obj> scripts/grupos_bodyparts3d.json frontend/modelos/cuerpo.glb
```

### Contrato con el visor

Un objeto por órgano con estos nombres exactos: `corazon`, `cerebro`, `pulmones`, `huesos`, `ojos`, `sangre`, `piel`.
Si alguien cambia el modelo (por ejemplo, uno hecho a mano en Blender), debe mantener esos nombres.
Si el `.glb` no carga, el visor usa automáticamente el cuerpo simple construido por código.
