# Plateforme Éducative Alpha One Labs

Une plateforme éducative moderne et riche en fonctionnalités, construite avec Django et Tailwind CSS, qui offre une expérience d'apprentissage fluide grâce à la création de cours, aux connexions entre pairs, aux groupes d'étude et aux forums interactifs.

## Aperçu du Projet

Alpha One Labs est une plateforme éducative conçue pour faciliter à la fois l'apprentissage et l'enseignement. Elle offre un environnement complet où les éducateurs peuvent créer et gérer des cours, tandis que les étudiants peuvent apprendre, collaborer et interagir avec leurs pairs. Grâce à des fonctionnalités telles que les groupes d'étude, les connexions entre pairs et les forums de discussion, notre objectif est de créer un environnement d'apprentissage collaboratif qui va au-delà de l'éducation en ligne traditionnelle.

## Fonctionnalités

### Pour les Étudiants

- 📚 Inscription et gestion des cours
- 👥 Connexions et messagerie entre pairs
- 📝 Création et participation à des groupes d'étude
- 💬 Forums de discussion interactifs
- 📊 Suivi des progrès et analyses
- 🌟 Soumission de liens et réception de notes avec retour
- 🌙 Prise en charge du mode sombre
- 📱 Design réactif pour tous les appareils

### Pour les Enseignants

- 📝 Création et gestion de cours
- 📊 Suivi des progrès des étudiants
- 📈 Tableau de bord analytique
- 📣 Outils marketing pour la promotion de cours
- 💯 Notation des liens soumis et retour personnalisé
- 💰 Intégration des paiements avec Stripe
- 📧 Capacités de marketing par e-mail
- 🔔 Notifications automatisées

### Fonctionnalités Techniques

- 🔒 Système d'authentification sécurisé
- 🌐 Prise en charge de l'internationalisation
- 🚀 Performances optimisées
- 📦 Architecture modulaire
- ⚡ Mises à jour en temps réel
- 🔍 Fonction de recherche
- 🎨 Interface personnalisable
- 🏆 Système de notation académique "Get a Grade"

## Pile Technologique

### Backend

- Python 3.10+
- Django 4.x
- Celery pour les tâches asynchrones
- Redis pour le cache
- PostgreSQL (production) / SQLite (développement)

### Frontend

- Tailwind CSS
- Alpine.js
- Icônes Font Awesome
- JavaScript (Vanilla)

### Infrastructure

- Support Docker
- Nginx
- Gunicorn
- SendGrid pour les e-mails
- Stripe pour les paiements

## Instructions d'Installation

### Prérequis

- Python 3.10 ou supérieur
- pip ou poetry pour la gestion des packages
- Git

### Installation Locale pour le Développement

1. Cloner le dépôt :

   ```bash
   git clone https://github.com/yourusername/alphaonelabs-education-website.git
   cd alphaonelabs-education-website
   ```

2. Créer un environnement virtuel :

   ```bash
   python -m venv venv
   source venv/bin/activate  # Sous Windows : venv\Scripts\activate
   ```

3. Installer les dépendances :

   ```bash
   # Avec pip
   pip install -r requirements.txt

   # Avec poetry
   poetry install

   En cas de problèmes sous Windows, essayez :
   poetry lock
   poetry install
   poetry self add poetry-plugin shell
   poetry shell
   poetry run pre-commit run --all-files
   ```

4. Configurer les variables d'environnement :

   ```bash
   cp .env.sample .env
   # Modifier .env avec vos configurations
   ```

5. Appliquer les migrations :

   ```bash
   python manage.py migrate
   ```

6. Créer un superutilisateur :

   ```bash
   python manage.py createsuperuser
   ```

7. Créer des données de test :

   ```bash
   python manage.py create_test_data
   ```

8. Lancer le serveur de développement :

   ```bash
   python manage.py runserver
   ```

9. Visiter [http://localhost:8000](http://localhost:8000) dans votre navigateur.

### Installation avec Docker

1. Construire l'image Docker :

   ```bash
   docker build -t education-website .
   ```

2. Lancer le conteneur Docker :

   ```bash
   docker run -d -p 8000:8000 education-website
   ```

3. Visiter [http://localhost:8000](http://localhost:8000) dans votre navigateur.

### Identifiants d'Administration :

- **Email :** `admin@example.com`
- **Mot de passe :** `adminpassword`

## Configuration des Variables d'Environnement

Copier `.env.sample` vers `.env` et configurer les variables nécessaires.

## Directives de Développement

### Style de Code

- Suivre les directives PEP 8 pour le code Python.
- Utiliser **Black** pour le formatage du code.
- Utiliser **isort** pour le tri des imports.
- Suivre le guide de style Django.
- Utiliser **ESLint** pour le code JavaScript.

### Workflow Git

1. Créer une nouvelle branche pour chaque fonctionnalité ou correctif.
2. Utiliser des **commits conventionnels** pour les messages de commit.
3. Soumettre des **pull requests** pour les révisions.
4. Vérifier que tous les **tests passent** avant de fusionner.

### Tests

- Écrire des tests unitaires pour les nouvelles fonctionnalités.
- Lancer les tests avant chaque commit :

  ```bash
  python manage.py test
  ```

### Hooks Pre-commit (Important)

Nous utilisons des hooks pre-commit pour garantir la qualité du code et appliquer le formatage automatiquement :

```bash
# Installer pre-commit
pip install pre-commit

# Installer les hooks git
pre-commit install

# Corriger automatiquement les erreurs de formatage
poetry run pre-commit run --hook-stage commit

# Exécuter tous les contrôles sur tous les fichiers
poetry run pre-commit run --all-files
```

Voir [PRE-COMMIT-README.md](PRE-COMMIT-README.md) pour plus de détails sur notre configuration des hooks.

### Documentation

- Documenter toutes les nouvelles fonctionnalités et points d'entrée de l'API
- Mettre à jour README.md lors de l'ajout de nouvelles fonctionnalités majeures
- Utiliser des docstrings pour les fonctions et classes Python
- Commenter la logique complexe

## Contribution

Les contributions sont les bienvenues ! Veuillez consulter notre [Guide de Contribution](CONTRIBUTING.md) pour savoir comment soumettre des pull requests, signaler des problèmes et contribuer au projet.

## Support

Si vous rencontrez des problèmes ou avez besoin d'aide, veuillez :

1. Consulter les [Issues existants](https://github.com/alphaonelabs/education-website/issues)
2. Créer une nouvelle issue si votre problème persiste

## Remerciements

- Merci à tous les contributeurs qui ont participé à ce projet
- Développé avec ❤️ par l'équipe Alpha One Labs