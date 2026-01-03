# Roadmap pour finaliser la version 1.0

**Version actuelle :** 1.0.3  
**Objectif :** Finaliser la v1.0.0 stable avant de passer à la v2.0.0

---

## ✅ Fonctionnalités déjà implémentées (v1.0.3)

- [x] Encodage/décodage JSON ↔ JONX
- [x] Auto-détection des types (int16, int32, float16, float32, bool, str, json)
- [x] Compression Zstandard (niveau 7)
- [x] Index automatiques pour colonnes numériques
- [x] Classe `JONXFile` avec accès colonne par colonne
- [x] Support des recherches min/max avec index
- [x] Opérations d'agrégation de base (sum, avg, count)
- [x] Récupération multiple de colonnes (get_columns)

---

## 🎯 Opérations à ajouter pour finaliser la v1.0.0

### 1. Validation et gestion d'erreurs robuste

#### 1.1 Exceptions personnalisées
- [x] Créer des exceptions personnalisées (`JONXError`, `JONXValidationError`, `JONXDecodeError`)
- [x] Remplacer les `ValueError` génériques par des exceptions spécifiques
- [x] Messages d'erreur clairs et informatifs

#### 1.2 Validation des données d'entrée
- [x] Valider que tous les objets JSON ont les mêmes clés
- [x] Valider que les colonnes ont la même longueur
- [x] Valider les types de données avant encodage
- [x] Vérifier l'intégrité du fichier JONX avant décodage

#### 1.3 Validation des paramètres
- [x] Valider que `field_name` existe dans `get_column()`, `find_min()`, etc.
- [x] Valider que les colonnes numériques sont bien numériques pour `sum()`, `avg()`
- [x] Gestion des cas limites (colonnes vides, fichiers corrompus)

**Priorité :** 🔴 **HAUTE** - Essentiel pour la stabilité

---

### 2. Méthodes utilitaires de base

#### 2.1 Informations sur le fichier
- [x] `JONXFile.info()` : Retourne un dictionnaire avec toutes les métadonnées
  ```python
  {
      "path": "data.jonx",
      "version": 1,
      "num_rows": 1000,
      "num_columns": 5,
      "fields": ["id", "name", "price"],
      "types": {"id": "int32", ...},
      "indexes": ["id", "price"],
      "file_size": 12345
  }
  ```

- [x] `JONXFile.has_index(field)` : Vérifie si une colonne a un index
- [x] `JONXFile.is_numeric(field)` : Vérifie si une colonne est numérique

#### 2.2 Validation et vérification
- [x] `JONXFile.validate()` : Valide l'intégrité du fichier JONX
- [x] `JONXFile.check_schema()` : Vérifie la cohérence du schéma

**Priorité :** 🟡 **MOYENNE** - Améliore l'expérience utilisateur

---

### 3. Tests unitaires complets

#### 3.1 Tests d'encodage
- [x] Tests avec différents types de données
- [x] Tests avec données volumineuses
- [x] Tests avec données edge cases (valeurs nulles potentielles, types mixtes)
- [x] Tests de validation des erreurs

#### 3.2 Tests de décodage
- [x] Tests de décodage complet
- [x] Tests de décodage avec fichiers corrompus
- [x] Tests de compatibilité de version

#### 3.3 Tests de JONXFile
- [x] Tests de toutes les méthodes (get_column, find_min, find_max, sum, avg, count)
- [x] Tests avec index et sans index
- [x] Tests de performance basiques

#### 3.4 Tests d'intégration
- [x] Test complet : encode → decode → vérification
- [x] Test avec différents formats de données JSON

**Priorité :** 🔴 **HAUTE** - Essentiel pour la qualité

---

### 4. Documentation technique

#### 4.1 Docstrings complètes
- [ ] Ajouter des docstrings à toutes les fonctions publiques
- [ ] Format Google ou NumPy style
- [ ] Exemples dans les docstrings

#### 4.2 Documentation API
- [ ] Vérifier que toutes les méthodes sont documentées dans le README
- [ ] Ajouter des exemples d'utilisation avancés

**Priorité :** 🟡 **MOYENNE** - Améliore la maintenabilité

---

### 5. Améliorations de robustesse

#### 5.1 Gestion des fichiers
- [ ] Vérifier l'existence des fichiers avant lecture/écriture
- [ ] Gestion des permissions de fichiers
- [ ] Messages d'erreur clairs pour les problèmes de fichiers

#### 5.2 Gestion mémoire
- [ ] Vérifier que le lazy loading fonctionne correctement
- [ ] Documenter les limites de taille de fichiers

**Priorité :** 🟢 **BASSE** - Améliorations optionnelles

---

## 📋 Checklist pour la v1.0.0 finale

Avant de passer à la v2.0.0, s'assurer que :

- [ ] **Toutes les fonctionnalités de base sont implémentées et testées**
- [ ] **Tests unitaires avec couverture > 80%**
- [ ] **Gestion d'erreurs robuste avec exceptions personnalisées**
- [ ] **Validation complète des données d'entrée**
- [ ] **Documentation complète (README + docstrings)**
- [ ] **Pas de bugs critiques connus**
- [ ] **Performance acceptable pour les cas d'usage de base**
- [ ] **Compatibilité Python 3.8+ vérifiée**

---

## 🚀 Ce qui attend dans la v2.0.0

Une fois la v1.0.0 finalisée, la v2.0.0 pourra introduire :

- Support des types additionnels (int8, int64, float64)
- Index personnalisés (multi-colonnes)
- Filtrage et projection de colonnes optimisés
- Support des données nulles (NULL handling)
- Streaming pour fichiers volumineux
- API de requête simple (filtres, groupby, joins)
- Opérations d'agrégation avancées (std, median, quantiles)
- Benchmarks de performance complets

---

## 📊 Estimation des efforts

| Tâche | Priorité | Effort estimé | Bloquant pour v1.0 |
|-------|----------|--------------|-------------------|
| Validation et gestion d'erreurs | 🔴 HAUTE | 2-3 jours | ✅ Oui |
| Tests unitaires | 🔴 HAUTE | 3-4 jours | ✅ Oui |
| Méthodes utilitaires | 🟡 MOYENNE | 1 jour | ❌ Non |
| Documentation | 🟡 MOYENNE | 1 jour | ❌ Non |
| Améliorations robustesse | 🟢 BASSE | 1 jour | ❌ Non |

**Total estimé pour v1.0.0 finale :** 5-7 jours de développement

---

## 🎯 Plan d'action recommandé

1. **Phase 1 (Critique)** : Validation + Gestion d'erreurs
2. **Phase 2 (Critique)** : Tests unitaires complets
3. **Phase 3 (Optionnel)** : Méthodes utilitaires + Documentation
4. **Phase 4 (Release)** : Version 1.0.0 finale
5. **Phase 5 (Future)** : Développement v2.0.0

---

**Note :** Cette roadmap est un guide. Les priorités peuvent être ajustées selon les besoins du projet.

