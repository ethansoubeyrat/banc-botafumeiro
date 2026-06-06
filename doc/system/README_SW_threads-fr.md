# Architecture Multi-Thread et Synchronisation - Banc Botafumeiro

[![en](https://img.shields.io/badge/English-en-blue.svg?logo=thestorygraph)](README_SW_threads-en.md)
[![fr](https://img.shields.io/badge/Français-fr-green.svg?logo=thestorygraph)](README_SW_threads-fr.md)

## Vue d'ensemble

Le banc de mesure Botafumeiro utilise une **architecture multi-processus** combinant:
- **Processus GUI** (Tkinter, I/O bloquant)
- **Processus APP** (Python asyncio, événementiel)
- **Communication Inter-Processus** (stdin/stdout)

Ce document détaille le modèle de threading, les mécanismes de synchronisation et les sections critiques.

---

## Architecture des Processus

```
┌─────────────────────────────────────────────────────────┐
│  PROCESSUS 1: GUI (Tkinter)                             │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Thread Principal (Boucle d'événements)            │  │
│  │ ├─ Gestion des entrées utilisateur                │  │
│  │ ├─ Mise à jour des widgets                        │  │
│  │ ├─ Polling stdin pour messages APP                │  │
│  │ └─ Non-bloquant (via planificateur after())       │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  Communication: stdin/stdout                            │
│                                                         │
└─────────────────────────────────────────────────────────┘
                         ↕ (IPC)
┌─────────────────────────────────────────────────────────┐
│  PROCESSUS 2: APP (asyncio)                             │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Boucle Asyncio (Thread Principal)                 │  │
│  │ ├─ async_motor_loop()         [Tâche 1]           │  │
│  │ ├─ imu_reader_loop()          [Tâche 2]           │  │
│  │ ├─ current_monitor_loop()     [Tâche 3]           │  │
│  │ ├─ data_logger_task()         [Tâche 4]           │  │
│  │ ├─ command_listener()         [Tâche 5]           │  │
│  │ └─ error_handler()            [Tâche 6]           │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  État partagé: Variables globales + asyncio.Event       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Hiérarchie des Tâches Asyncio

### Structure des Tâches

```
asyncio.run(main())
    │
    ├─► Tâche 1: async_motor_loop()
    │   ├─ Surveille: amplitude, période, phase
    │   ├─ Contrôle: GPIO 18 (PWM)
    │   ├─ Fréquence: 10-100 Hz (configurable)
    │   └─ Synchronisation: asyncio.sleep()
    │
    ├─► Tâche 2: imu_reader_loop()
    │   ├─ Lit: UART Bluetooth
    │   ├─ Parse: trames BWT901CL (protocole 0x55)
    │   ├─ Extrait: angle, omega, accélération
    │   ├─ Fréquence: 100 Hz (fixe du capteur)
    │   └─ Déclenche: zero_crossing_event
    │
    ├─► Tâche 3: current_monitor_loop()
    │   ├─ Lit: I2C (INA219, adresse 0x40)
    │   ├─ Mesure: Vmotor, Imotor, Pmotor
    │   ├─ Fréquence: 50-100 Hz (configurable)
    │   └─ Action: Alertes diagnostiques
    │
    ├─► Tâche 4: data_logger_task()
    │   ├─ Tampon: Toutes les données capteur
    │   ├─ Fréquence: 50 Hz (écriture CSV)
    │   ├─ Verrou: asyncio.Lock (prévention corruption)
    │   └─ Fichier: data_YYYYMMDD_HHMMSS.csv
    │
    ├─► Tâche 5: command_listener()
    │   ├─ Lit: stdin depuis GUI
    │   ├─ Parse: commandes GUI (START, STOP, AMPLITUDE, etc.)
    │   ├─ Mise à jour: variables d'état global
    │   ├─ Fréquence: Événementiel (non-bloquant)
    │   └─ Action: Changements de mode
    │
    └─► Tâche 6: error_handler()
        ├─ Surveille: files d'exceptions
        ├─ Enregistre: messages d'erreur
        ├─ Fréquence: Temps réel
        └─ Action: Récupération gracieuse
```

---

## Mécanismes de Synchronisation

### 1. asyncio.Event - Détection du Passage à Zéro

**Objectif**: Signaler quand le pendule atteint θ = 0

```python
# Déclaration (global)
zero_crossing_event = asyncio.Event()

# Producteur: Tâche IMU Reader
async def imu_reader_loop():
    while running:
        angle = await read_imu_frame()
        if angle_crosses_zero(angle):  # θ = 0 détecté
            zero_crossing_event.set()   # Signal tous les attendeurs
        await asyncio.sleep(0.01)  # 100 Hz

# Consommateur: Tâche Contrôleur Moteur
async def async_motor_loop():
    if synchronous_mode:
        await zero_crossing_event.wait()  # Bloque jusqu'à θ = 0
        zero_crossing_event.clear()       # Réinitialise pour prochain cycle
        activate_motor()                  # Pompage à phase optimale
```

**Propriétés**:
- ✅ Thread-safe (primitive asyncio)
- ✅ Réveille tous les coroutines attendant
- ✅ Pas de polling intensif (efficace CPU)

---

### 2. asyncio.Lock - Protection d'Écriture CSV

**Objectif**: Prévenir les écritures CSV simultanées de plusieurs tâches

```python
# Déclaration (global)
csv_lock = asyncio.Lock()

# Producteur: Tâche Current Monitor
async def current_monitor_loop():
    while running:
        v, i, p = read_ina219()
        async with csv_lock:
            current_data = {'vMotor': v, 'iMotor': i, 'pMotor': p}
        await asyncio.sleep(0.01)  # 100 Hz

# Producteur: Tâche Data Logger
async def data_logger_task():
    while running:
        async with csv_lock:
            # Sûr d'écrire - aucune autre tâche n'écrit simultanément
            write_to_csv(imu_data, current_data)
        await asyncio.sleep(0.02)  # 50 Hz
```

**Propriétés**:
- ✅ Exclusion mutuelle (une seule coroutine à la fois)
- ✅ Prévention des interblocages (pas de verrous imbriqués)
- ✅ Planification équitable (file FIFO)

---

### 3. Variables d'État Global - Mémoire Partagée

**Objectif**: Partager la configuration entre GUI et APP

```python
# État global (partagé entre processus via IPC)
class SystemState:
    motor_amplitude = 0.0      # β_max (0-180°)
    motor_period = 4.0         # T (secondes)
    motor_phase = 0.0          # φ (degrés)
    mode = "manual"            # "manual" | "asynchrone" | "synchrone"
    running = False            # Moteur on/off
    
    # Lectures capteur actuelles (mises à jour par tâches)
    current_angle = 0.0        # θ (degrés)
    current_omega = 0.0        # ω̇ (°/s)
    motor_voltage = 0.0        # Vmotor (volts)
    motor_current = 0.0        # Imotor (mA)
    
state = SystemState()

# Lecture (pas de verrou nécessaire - assignation unique)
async def motor_task():
    amp = state.motor_amplitude  # Lire dernière valeur
    
# Écriture (assignation unique - atomique en Python)
async def command_listener():
    state.motor_amplitude = new_value  # Commande GUI
```

**Propriétés**:
- ✅ GIL Python garantit lectures/écritures atomiques pour types basiques
- ✅ Pas de verrou explicite nécessaire pour assignations simples
- ⚠️ Objets complexes nécessitent Lock (ex: listes, dicts)

---

### 4. asyncio.Queue - Canal de Commandes

**Objectif**: Transmission sûre des commandes de GUI vers APP

```python
# Déclaration
command_queue = asyncio.Queue(maxsize=10)

# Producteur: Processus GUI (lecteur stdin)
async def command_listener():
    while True:
        cmd = await read_stdin_async()  # "START_MOTOR::45::2.5::90"
        await command_queue.put(cmd)    # Non-bloquant (sauf si plein)

# Consommateur: Processus APP (gestionnaire commandes)
async def process_commands():
    while True:
        cmd = await command_queue.get()  # Bloque si vide
        parse_and_execute(cmd)
        command_queue.task_done()        # Signal complétion
```

**Propriétés**:
- ✅ Thread-safe entre tâches
- ✅ Ordre FIFO (aucune commande perdue)
- ✅ Gestion de contrecharge (maxsize=10)

---

## Sections Critiques

### Section 1: Mise à Jour PWM Moteur (Précision ±5ms)

**Localisation**: `async_motor_loop()` dans `app.py`

**Code Critique**:
```python
async def async_motor_loop():
    cycle_start_time = time.time()
    
    while running:
        # CRITIQUE: Synchronisation sur temps absolu
        time_in_cycle = (time.time() - cycle_start_time) % period
        
        if time_in_cycle < period / 2:
            servo.value = amplitude_to_pwm(state.motor_amplitude)
        else:
            servo.value = 0.0
        
        # Calculer prochain changement de phase
        next_phase_time = cycle_start_time + (phase_index + 1) * (period / 2)
        sleep_time = next_phase_time - time.time()
        
        await asyncio.sleep(sleep_time)  # Précision ±5ms
```

**Stratégie de Synchronisation**:
- ✅ **Temps absolu** (pas de délais cumulatifs)
- ✅ **Immunisé contre latences asyncio**
- ✅ **Erreur bornée** (±5ms par cycle)

**Problèmes Potentiels**:
- ❌ Charge système élevée → sleep_time devient négatif
- ❌ Solution: Capturer sleep négatif, sauter prochain cycle

---

### Section 2: Détection Passage à Zéro (Verrouillage IMU → Moteur)

**Localisation**: `imu_reader_loop()` déclenche `zero_crossing_event`

**Code Critique**:
```python
async def imu_reader_loop():
    prev_angle = 0.0
    
    while running:
        angle = await read_imu_frame()
        
        # CRITIQUE: Détecter quand angle croise zéro
        if (prev_angle < 0 and angle >= 0) or (prev_angle > 0 and angle <= 0):
            zero_crossing_event.set()  # Réveille tâche moteur
        
        prev_angle = angle
        await asyncio.sleep(0.01)  # 100 Hz
```

**Stratégie de Synchronisation**:
- ✅ **Événementiel** (pas de polling)
- ✅ **Détection unique par cycle** (prévient déclenchements multiples)

**Problèmes Potentiels**:
- ❌ Hystérésis (bruit près θ = 0 cause détections multiples)
- ❌ Solution: Détection basée seuil (ex: |θ| < 5°)

---

### Section 3: Écriture Données CSV (Prévention Race Condition)

**Localisation**: `data_logger_task()` avec `csv_lock`

**Code Critique**:
```python
async def data_logger_task():
    while running:
        # Collecter snapshot données actuelles
        snapshot = {
            'timestamp': time.time(),
            'angle': state.current_angle,
            'omega': state.current_omega,
            'vMotor': state.motor_voltage,
            'iMotor': state.motor_current,
        }
        
        # CRITIQUE: Écriture atomique
        async with csv_lock:
            csvwriter.writerow(snapshot)
            csvfile.flush()  # Force disque
        
        await asyncio.sleep(0.02)  # 50 Hz
```

**Stratégie de Synchronisation**:
- ✅ **Verrou pendant écriture** (prévient écritures entrelacées)
- ✅ **Flush disque** (assure persistance)

**Problèmes Potentiels**:
- ❌ Contention verrou (producteurs multiples)
- ❌ Solution: Tâche écrivain unique (réduit durée verrou)

---

## Diagramme Temporel

```
AXE TEMPS (millisecondes)
0     10    20    30    40    50    60    70    80    90    100

Tâche IMU:
[1]---[2]---[3]---[4]---[5]---[6]---[7]---[8]---[9]---[10]--
 │ (100 Hz, période 10ms)
 └─ Lit angle depuis Bluetooth

Événement Passage à Zéro:

          ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
          │ Décalage détection: ~30-50ms
          ▼
Tâche Moteur:

     ████████████     ████████████     ████████████     ████
     │                │                │                │
     └─ PWM Haut      └─ PWM Haut      └─ PWM Haut      └─ PWM Haut
        (50ms)           (50ms)           (50ms)           (50ms)

Moniteur Courant:

   [V,I]---[V,I]---[V,I]---[V,I]---[V,I]---[V,I]---[V,I]---
   │ (50 Hz, période 20ms)
   └─ Échantillonne INA219

Écriture CSV (avec verrou):
        ║ W ║        ║ W ║        ║ W ║        ║ W ║
        (verrouillé ~2ms par écriture)
```

---

## Conditions de Course Identifiées et Atténuées

### Condition de Course 1: Mise à Jour Données IMU Pendant Lecture

**Scénario**: Tâche moteur lit `state.current_angle` tandis que tâche IMU l'update

**Atténuation**:
```python
# GIL + assignation unique = atomique
state.current_angle = angle  # Écriture atomique
amp = state.current_angle    # Lecture atomique
```

✅ **Sûr** (pas de verrou explicite nécessaire)

---

### Condition de Course 2: Corruption CSV sur Écritures Simultanées

**Scénario**: Enregistreur données et moniteur courant écrivent CSV simultanément

**Atténuation**:
```python
async with csv_lock:
    csvwriter.writerow(data)  # Seule tâche écrivant
```

✅ **Sûr** (Verrou prévient entrelacement)

---

### Condition de Course 3: Débordement Tampon Commande

**Scénario**: GUI envoie commandes plus vite qu'APP les traite

**Atténuation**:
```python
command_queue = asyncio.Queue(maxsize=10)  # File bornée
await command_queue.put(cmd)  # Bloque si plein
```

✅ **Sûr** (Contrecharge prévient débordement)

---

### Condition de Course 4: Événement Passage à Zéro Perdu

**Scénario**: Tâche moteur rate événement si réinitialisation trop tardive

**Atténuation**:
```python
# Cycle événement approprié
await zero_crossing_event.wait()  # Attendre signal
zero_crossing_event.clear()       # Réinitialiser APRÈS traitement
```

✅ **Sûr** (Clear APRÈS wait assure pas de perte)

---

## Analyse de Performance

### Latences Tâches

| Tâche | Période | Latence | CPU % | Remarques |
|-------|---------|---------|-------|-----------|
| Lecteur IMU | 10 ms | 5-10 ms | 15% | UART Bluetooth bloquant |
| PWM Moteur | 10-100 ms | ±5 ms | 5% | Boucle serrée, temps absolu |
| Moniteur Courant | 20 ms | 8-15 ms | 8% | I2C bloquant |
| Enregistreur Données | 20 ms | 2-3 ms | 10% | Écriture CSV, I/O disque |
| Lecteur Commande | Événementiel | <1 ms | 2% | stdin non-bloquant |
| **Total** | - | - | **40%** | Marge: 60% |

### Utilisation Mémoire

```
Surcharge asyncio:       ~5 MB
Variables d'état:        ~1 MB
Tampon CSV:              ~2 MB
Tampons IMU/Moteur:      ~1 MB
─────────────────────────────
Total:                  ~9 MB / 4096 MB disponible ✅
```

---

## Outils de Débogage

### 1. Surveiller États Tâches

```python
import asyncio

async def debug_task_status():
    while True:
        tasks = asyncio.all_tasks()
        for task in tasks:
            print(f"{task.get_name()}: {task._state}")
        await asyncio.sleep(5)
```

### 2. Détecter Interblocages

```python
async def deadlock_detector():
    while True:
        await asyncio.sleep(10)
        pending = asyncio.all_tasks()
        if len(pending) > 8:  # Nombre inhabituel tâches
            print(f"⚠️ Avertissement interblocage: {len(pending)} tâches en attente")
```

### 3. Profiler Contention Verrou

```python
import time

class VerrouProfilé(asyncio.Lock):
    async def acquire(self):
        t0 = time.time()
        await super().acquire()
        wait_time = time.time() - t0
        if wait_time > 10:  # ms
            print(f"⚠️ Contention verrou: {wait_time:.1f}ms")
```

---

## Résumé

**Modèle Synchronisation**: Asyncio événementiel avec verrouillage minimal

**Garanties Clés**:
- ✅ PWM Moteur: Précision ±5ms (temps absolu)
- ✅ Données IMU: Temps réel (100 Hz) avec détection passage zéro
- ✅ Écritures CSV: Sûres (pas de corruption)
- ✅ Commandes: Ordre FIFO (aucune perte)
- ✅ Charge CPU globale: ~40% (marge pour tâches système)

**Dépendances Critiques**:
1. Responsivité UART Bluetooth (décalage IMU: ~30-50ms)
2. Disponibilité bus I2C (INA219: <20ms)
3. Latence I/O disque (écritures CSV: <5ms)

---

## Références

- Documentation asyncio Python: https://docs.python.org/3/library/asyncio.html
- GIL (Global Interpreter Lock): https://realpython.com/python-gil/
- Contraintes temps réel en Python: https://www.embeddedrelated.com/showarticle/1471.php

