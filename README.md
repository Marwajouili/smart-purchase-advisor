# Smart Purchase Advisor

Assistant IA qui aide à déterminer où acheter un produit en minimisant le
coût réel : prix du produit **+** coût et temps du déplacement nécessaire
pour l'obtenir. Périmètre initial : Houilles, Carrières-sur-Seine,
Sartrouville, Île-de-France.

Projet portfolio démontrant : intégration LLM/agents, architecture logicielle
propre, testing, CI/CD, cloud, et bases MLOps/LLMOps.

## Principe architectural

> Le LLM orchestre, le code déterministe calcule.

Aucun calcul financier ou temporel n'est jamais délégué au modèle de
langage. Le moteur de coût (`src/domain/cost_engine.py`) est du code
Python classique, 100% testé, sans dépendance au LLM ni appel réseau.

## État d'avancement — Phase 1 : cœur du domaine

- [x] Modèles de domaine (`src/domain/models.py`) : `Product`, `Store`,
      `PriceInfo`, `Route`, `PurchaseOption`, `CostBreakdown`
- [x] Moteur de coût déterministe (`src/domain/cost_engine.py`) :
      calcul du coût total (voiture / transit / marche), classement des
      options
- [x] Suite de tests unitaires (`tests/test_cost_engine.py`)
- [ ] Providers (routing réel, prix) — Phase 4/5
- [ ] Agent LLM (extraction d'intention, tool calling) — Phase 6
- [ ] API FastAPI — Phase 2
- [ ] Persistance PostgreSQL — Phase 3

## Structure

```text
src/
  domain/      cœur métier : modèles + moteur de coût (aucune dépendance externe)
  providers/   implémentations concrètes (routing, prix, LLM) — à venir
  api/         API FastAPI — à venir
tests/         tests unitaires / intégration
docs/          decisions d'architecture (ADR), diagrammes
```

## Lancer les tests

```bash
pip install -e ".[dev]"
pytest tests/ -v --cov=src
```

## Notes sur les données

Les prix utilisés en Phase 1/MVP sont des **relevés réels ponctuels**
(pas une simulation aléatoire), documentés avec `is_simulated=True` et une
date `last_updated`. Ce n'est pas du temps réel — c'est un instantané
assumé et affiché comme tel à l'utilisateur. Le routing/transit visera des
données réelles via les APIs officielles gratuites d'Île-de-France
Mobilités et SNCF Open Data (Phase 4/5).
