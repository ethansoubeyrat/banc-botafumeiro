# Calibration de la latence du système

[![en](https://img.shields.io/badge/English-en-blue.svg?logo=thestorygraph)](README_system_latency-en.md)
[![fr](https://img.shields.io/badge/Français-fr-green.svg?logo=thestorygraph)](README_system_latency-fr.md)

## <span style="color:orange"> Vue d'ensemble </span>

La **latence** du banc de mesure représente le délai entre la détection de θ = 0 (masse au point bas) et l'activation réelle du servomoteur. Cette latence affecte directement la synchronisation de phase et explique le décalage de 5% observé entre les phases optimales théorique et expérimentale.

## <span style="color:orange"> Décomposition de la latence </span>

La latence totale du système est la somme de quatre composantes séquentielles :

1. **Échantillonnage et traitement du capteur IMU** (~20-30 ms)
   - Le BWT901CL échantillonne à 100 Hz (période 10 ms)
   - Calcul de l'angle et assemblage de la trame (protocole 0x55)

2. **Transmission Bluetooth** (~20-40 ms)
   - Conversion UART vers Bluetooth
   - Transmission sur liaison UART Bluetooth (115200 baud)

3. **Réception Raspberry Pi et détection d'angle** (~20-30 ms)
   - Réception de la trame et validation CRC
   - Algorithme de détection du passage à zéro
   - Préparation de la commande GPIO

4. **Actuation du moteur** (~10-20 ms)
   - Propagation du signal PWM vers le servo
   - Temps de réponse électronique du servo

**Latence totale estimée : ~100 ms**

## <span style="color:orange"> Méthodologie de mesure </span>

### <span style="color:#229DD4"> Protocole expérimental </span>

Pour mesurer la latence réelle du système, nous avons utilisé une **approche d'analyse vidéo** :

1. **Configuration d'enregistrement**
   - Caméra smartphone (30 fps = 33 ms par image)
   - Positionnée pour capturer à la fois le fil du pendule et le servomoteur
   - Alignement horizontal pour référence visuelle d'angle
   - Format fichier : vidéo MP4

2. **Extraction des images**
   - Outil `ffmpeg` pour décomposer la vidéo image par image
   - Sortie : séquence PNG (frame_0001.png, frame_0002.png, etc.)
   - Intervalle entre images : 33 ms (1/30 seconde)

3. **Détection des repères visuels**
   - **Image A** : Identifier θ = 0 (fil du pendule vertical)
   - **Image B** : Identifier le premier mouvement visible du moteur
   - **Latence** : (Image B - Image A) × 33 ms

### <span style="color:#229DD4"> Timeline d'exemple </span>

```
Image 0001 : θ = 0 (pendule vertical, pas de mouvement moteur)
Image 0002 : Pas de mouvement moteur (33 ms écoulés)
Image 0003 : Pas de mouvement moteur (66 ms écoulés)
Image 0004 : Premier mouvement visible du moteur (99 ms écoulés)
             → Latence ≈ 100 ms
```

## <span style="color:orange"> Résultats et conclusions </span>

### <span style="color:#229DD4"> Latence mesurée </span>

| Mesure | Valeur | Remarque |
|--------|--------|----------|
| **Latence primaire** | 100 ms | Entre la détection θ = 0 et le premier mouvement moteur |
| **Incertitude de mesure** | ±33 ms | Période d'une image à 30 fps |
| **Intervalle de confiance** | 67-133 ms | ±1 image (1σ) |

### <span style="color:#229DD4"> Interprétation physique </span>

La latence de 100 ms signifie :

1. **Implication sur la phase**
   - Le moteur reçoit les commandes avec un délai de ~100 ms après que le pendule atteigne θ = 0
   - Cela provoque un décalage de la phase d'excitation effective d'environ 5% par rapport à la phase théorique idéale
   - Pour le transfert optimal d'énergie, l'algorithme de contrôle compense en avançant la commande de phase

2. **Impact du mode synchrone**
   - En mode synchrone (pompage synchronisé avec le pendule), la latence doit être compensée
   - Le contrôleur de phase tient compte de cela en prédisant la position du pendule à l'avance de ~100 ms

3. **Implications sur la performance du système**
   - ✅ **Acceptable** : 100 ms << 2200 ms (période du pendule)
   - ✅ **Gérable** : La latence est prévisible et constante
   - ✅ **Compensable** : Peut être calibrée en logiciel

### <span style="color:#229DD4"> Contributeurs dominants (classés par impact) </span>

| Source | Estimé | Potentiel de réduction |
|--------|--------|------------------------|
| Transmission Bluetooth | ~30-40 ms | ⭐⭐ Utiliser UART direct |
| Traitement IMU | ~20-30 ms | ⭐ Limitation matérielle |
| Détection angle Pi | ~20-30 ms | ⭐⭐⭐ Optimisation algorithme |
| Réponse moteur | ~10-20 ms | ⭐ Limitation matérielle |
