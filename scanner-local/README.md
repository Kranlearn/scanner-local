# Scanner TCP local

Projet pedagogique de cybersécurité : scanner TCP minimal pour **une seule cible explicitement autorisée**.

## Objectifs

- tester la connectivité TCP sur une liste de ports choisie ;
- distinguer les ports ouverts des ports fermés ou filtrés ;
- produire un rapport JSON exploitable ;
- conserver l'historique dans SQLite sans dupliquer le rapport complet ;
- exposer l'historique via une API HTTP locale minimale ;
- pratiquer la validation d'entrées, la concurrence contrôlée et la journalisation de résultats.

Le projet ne fait pas de découverte de réseau, ne scanne pas une plage d'adresses et ne tente aucune exploitation.
Utilise-le uniquement sur `127.0.0.1`, une machine que tu possèdes ou une cible pour laquelle tu as une autorisation explicite.

## Pré-requis

- Python 3.10 ou supérieur
- aucune dépendance externe

## Lancer les tests

Depuis ce dossier :

```powershell
python -m unittest -v
```

## Exemples autorisés

Tester quelques ports sur sa propre machine :

```powershell
python .\scanner.py 127.0.0.1 --ports 22,80,443
```

Par défaut, le résultat est enregistré dans `scanner.db`. Pour un essai sans écriture :

```powershell
python .\scanner.py 127.0.0.1 --ports 22,80,443 --no-save
```

Ecrire le rapport dans un fichier JSON :

```powershell
python .\scanner.py 127.0.0.1 --ports 1-1024 --timeout 0.2 --output .\reports\localhost.json
```

Le dossier de sortie doit exister avant l'exécution :

```powershell
New-Item -ItemType Directory -Force .\reports
```

## API locale

Lancer l'API, toujours liée à la boucle locale :

```powershell
python .\api.py --port 8000 --database .\scanner.db
```
cd "/c/Users/HP OMEN/Documents/scanner-locale"
#lancer API: python api.py --port 8000 --database scanner.db
Routes disponibles :

- `GET /` : tableau de bord web local ;
- `GET /dashboard.css` et `GET /dashboard.js` : ressources de l'interface ;
- `GET /health` : vérification rapide du service ;
- `GET /scans` : liste compacte des derniers scans ;
- `GET /scans/{id}` : détail d'un scan ;
- `POST /scans` : lancer et enregistrer un scan autorisé.

Exemple Git Bash :

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/scans
curl -X POST http://127.0.0.1:8000/scans \
	-H 'Content-Type: application/json' \
	-d '{"target":"127.0.0.1","ports":"8000","timeout":0.2}'
```

Après le lancement, ouvre également `http://127.0.0.1:8000/` dans ton navigateur pour utiliser le tableau de bord.

Les réponses API sont sérialisées sans espaces inutiles. SQLite conserve les métadonnées et les résultats de ports dans
des tables séparées, ce qui évite de répéter un gros JSON et accélère les recherches courantes grâce aux index.

## Format du rapport

Chaque résultat contient :

- `port` : numéro du port ;
- `state` : `open`, `closed_or_filtered` ou `error` ;
- `service` : nom TCP connu localement, quand disponible ;
- `latency_ms` : durée approximative du test ;
- `error` : détail présent uniquement en cas d'erreur.

## Prochaines évolutions

1. ajouter un module de détection limitée des services ;
2. ajouter une interface web et des tests d'intégration ;
3. préparer une version conteneurisée pour un environnement cloud de laboratoire.
