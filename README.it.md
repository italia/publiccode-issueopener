# publiccode-issueopener

[![License](https://img.shields.io/github/license/italia/publiccode-issueopener.svg)]
(https://github.com/italia/publiccode-issueopener/blob/main/LICENSE)
[![Join the #publiccode channel](https://img.shields.io/badge/Slack%20channel-%23publiccode-blue.svg)]
(https://app.slack.com/client/T6C27AXE0/CAM3F785T)
[![Get invited](https://slack.developers.italia.it/badge.svg)]
(https://slack.developers.italia.it/)

<p align="center">
  <a href="README.md">Inglese</a> | 
  <a href="README.it.md">Italiano</a>
</p>

publiccode-issueopener è un bot di automazione in Python progettato per
garantire la correttezza dei file `publiccode.yml` nei repository GitHub.

Questo bot ottiene l'elenco dei repository nel [catalogo del software italiano]
(https://developers.italia.it/it/search) tramite 
[developers-italia-api](https://github.com/italia/developers-italia-api), controlla 
la validità di file `publiccode.yml` per errori, li stampa e apre issue sui relativi
repo GitHub.

Ciò contribuisce a mantenere alta la qualità dei metadati del catalogo del 
software, per garantire una condivisione e un riutilizzo fluidi del codice pubblico
tra diversi enti.

## 🚀 Funzionalità

- **Generazione automatica di problemi:** Qualsiasi errore rilevato nel file 
`publiccode.yml` attiva automaticamente la creazione di issue GitHub.
- **Conformità publiccode.yml:** Garantisce che i file publiccode.yml aderiscano
allo [Standard definito dallo schema di publiccode.yml](https://yml.publiccode.tools).

## 💻 Per iniziare

### Prerequisiti

- Python 3.6 o superiore

Installa le librerie Python richieste con pip:

```bash
pip install -r requirements.txt
```

### Installazione

Clona il repository:

```bash
git clone https://github.com/italia/publiccode-issueopener
cd publiccode-issueopener
```

## 🎮 Utilizzo

Puoi eseguire lo script con:

```bash
./publiccode-issueopener.py [--since NUMERO_DI_GIORNI]
```

L'opzione `--since` definisce il numero di giorni passati da analizzare nei log. 
Di default, lo script controlla i log del giorno precedente per eventuali errori
nel publiccode.yml.

### Variabili d'ambiente

Per utilizzare il bot, dovrai impostare alcune variabili d'ambiente nel tuo sistema:

- `BOT_GITHUB_TOKEN`: (**obbligatorio**) Il token GitHub per il bot, usato 
per autenticarsi quando apre issue nei repository
- `GITHUB_USERNAME`: Il nome utente del bot GitHub che aprirà i problemi. Default `publiccode-validator-bot`
- `API_BASEURL`: L'URL di base per l'API utilizzata per recuperare gli errori nei 
file publiccode.yml. Default `https://api.developers.italia.it/v1`

## 🤝 Contribuire

I contributi sono sempre benvenuti! Apri issue, fai fork del repository o invia una Pull Request.

## 🔗 Progetti correlati

* [publiccode-crawler](https://github.com/italia/publiccode-crawler)
* [developers-italia-api](https://github.com/italia/developers-italia-api)

## 👥 Manutentori

Questo software è mantenuto dal team di [Developers Italia](https://developers.italia.it).

## 📄 Licenza

Copyright© 2022-presente - Presidenza del Consiglio dei Ministri

Questo software è rilasciato con licenza EUPL-1.2. Per ulteriori dettagli, consulta il file `LICENSE`.
