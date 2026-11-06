<p align="center"><img src="custom_components/linked_entities/brand/icon@2x.png" width="128" alt="Linked Entities"></p>

# Linked Entities

🇬🇧 [English](README.md) · 🇪🇸 **Español**

Integración para Home Assistant que **vincula entidades on/off para que se espejen entre sí**.
Si encendés o apagás cualquiera de ellas (desde la tecla física, la app, la voz o una
automatización), se encienden o apagan todas.

> Caso típico: una tecla inteligente conectada a las luces del quincho y otra tecla "libre",
> sin carga, en otra parte de la casa. Con un vínculo, las dos se comportan como una sola tecla de combinación.

## Qué soporta

- **Entidades vinculadas** (se sincronizan en las dos direcciones): `switch`, `light`, `fan`, `input_boolean`, de cualquier protocolo (Wi-Fi, Zigbee, Z-Wave, Matter… se pueden mezclar).
- **Pulsadores** (cada pulsación alterna el vínculo): `event`, `button`, `input_button`. En las entidades `event` podés filtrar los tipos de evento (ej. `press`, `single`).
- **Entidad primaria** (opcional): la que tiene la carga física. Su estado manda al arrancar HA y cuando se reconecta.
- **Anti-bucles**: reconoce sus propios comandos (por `Context`), no envía comandos a entidades que ya están en el estado correcto y absorbe los rebotes de los dispositivos.
- **`unavailable` / `unknown`** no se propagan nunca. Cuando una entidad vuelve a estar disponible, se resincroniza.

Por cada vínculo se crea un dispositivo con:

| Entidad | Para qué sirve |
|---|---|
| `switch.<nombre>` | Un solo interruptor que representa y controla todo el vínculo (útil para dashboards y voz) |
| Switch *Sincronización activa* | Pausar o reanudar la sincronización |
| Sensor *Última fuente* | Diagnóstico: qué entidad originó el último cambio |

La interfaz está en **inglés y español** (`es` y `es-419`, *Español (Latinoamérica)*).

## Instalación (HACS)

1. HACS → ⋮ → *Repositorios personalizados* → `https://github.com/pabloantonelli/ha-linked-entities`, categoría **Integration**.
2. Instalá **Linked Entities** y reiniciá Home Assistant.
3. Andá a *Ajustes → Dispositivos y servicios → Añadir integración → Linked Entities*.

Instalación manual: copiá `custom_components/linked_entities` a tu carpeta `config/custom_components/`.

## Uso

Cada vínculo es una entrada de la integración:

- **Añadir entrada**: nombre, entidades, pulsadores, entidad primaria, debounce y tipos de evento.
- **Configurar**: editar un vínculo existente.
- **⋮ → Eliminar**: borrar el vínculo.

Una entidad solo puede pertenecer a un vínculo, para evitar bucles entre vínculos.

## ¿Cuándo *no* usar esto?

- **Un solo par y nada más**: alcanza con una automatización (disparador: cambio de estado de A o B → aplicar a la otra).
- **Todo Zigbee**: el *binding* directo entre dispositivos (ZHA/Z2M) funciona aunque HA esté caído.
- **Solo querés una entidad que controle varias**, sin que se espejen entre sí: usá un *helper* de grupo.

## Ícono

La integración trae su propio ícono en `custom_components/linked_entities/brand/` (funciona desde Home Assistant 2026.3; en versiones anteriores se ve un ícono genérico).

## Desarrollo

```bash
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -r requirements_test.txt
.venv/bin/python -m pytest -q
```

## Licencia

MIT
