<p align="center"><img src="custom_components/linked_entities/brand/icon@2x.png" width="128" alt="Linked Entities"></p>

# Linked Entities

🇬🇧 **English** · 🇪🇸 [Español](README.es.md)

**Make several switches, lights or buttons work as if they were one.**

Turn any of them on and they all turn on. Turn any of them off and they all turn off.
And they always show the same state.

---

## What is it for?

### 💡 One light, two switches
You have a smart switch that controls your patio lights and another smart switch
in the living room that isn't wired to anything.
Link them, and now you can turn the patio lights on or off from either one.
If you turn them on at the patio, the living-room switch shows as on too.

### 🪜 Stairs or a long hallway
One switch downstairs and one upstairs, like a classic two-way switch,
without running a single new wire.

### 🛏️ A button on the nightstand
You have a wireless button next to your bed.
Each press turns the bedroom light on or off (and the wall switch stays in step).

### 🌀 Fan and light together
Link the ceiling fan with its light so they turn on and off together.

---

## How to use it

1. Go to **Settings → Devices & services → Add integration** and search for **Linked Entities**.
2. Give it a name (for example, *Patio lights*).
3. Pick the switches or lights you want to link.
4. If you have wireless buttons, add them in the push buttons field (optional).
5. Choose the **main** switch: the one actually wired to the light.
6. Done. They now work together.

You can create as many links as you like, one per group of switches.
To change one, open the integration and tap **Configure**.

### What you'll see

Each link shows up as a new device with:

- **A switch named after the link** (e.g. *Patio lights*). It turns everything on or off together. Great for your dashboard or your voice assistant.
- **Sync enabled**. Turn it off and the switches stop copying each other until you turn it back on.
- **Last source**. Shows which switch was used last.

---

## FAQ

**Does it work with any brand?**
Yes. If Home Assistant sees it as something that turns on and off, you can link it. You can mix brands and types (Wi-Fi, Zigbee, etc.).

**What if a switch goes offline?**
The others keep working normally. When it comes back, it sets itself to the right state.

**What about a power cut or a Home Assistant restart?**
When everything is back, all switches line up with the main switch.

**Can I put the same switch in two links?**
No. That prevents switches from turning each other on and off in a loop.

**Does it work while Home Assistant is off?**
No: the link is handled by Home Assistant. The switch wired to the light always works, but the others won't control it while Home Assistant is down.

**Do I need this for just two switches?**
It's not required. You could also do it with an automation, but this integration does it in a minute, without mistakes and for as many cases as you want.

---

## Installation

### With HACS (recommended)
1. In HACS, open the menu **⋮ → Custom repositories**.
2. Paste `https://github.com/pabloantonelli/ha-linked-entities` and choose **Integration**.
3. Search for **Linked Entities**, install it and restart Home Assistant.

### Manual
Copy the `custom_components/linked_entities` folder into your Home Assistant `config/custom_components/` folder and restart.

---

Found a problem or have an idea? [Open an issue](https://github.com/pabloantonelli/ha-linked-entities/issues).
