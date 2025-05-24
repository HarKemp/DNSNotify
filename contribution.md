# Dalībnieku ieguldījums
## Miks:
Mattermost apziņošanas integrācija projektā
### Risinājuma apraksts
1. Mattermost konteineris - nodrošina apziņošanas sistēmu, lietotāja interfeisu
2. Postgres konteineris - glabā Mattermost datus
3. Mattermost-setup skripts, izmantojot mmctl:
    * Pirmoreiz palaižot risinājumu, izveido administratora lietotāju, bot (ar kuru tiek izveidots webhook) lietotāju, komandu un kanālu, uz kura tiks aizsūtīti ziņojumi
    * Izveido webhook apziņošanai, ja tāda nav mattermost
    * Padara webhook URL pieejamu notification-service, ievietojot to koplietotā volume ar notification-service
### Projekta realizācijas gaita
1. Lokāli izveidots Mattermost risinājums, webhook darbības analīze, manuāla pārbaude
2. Ieskats mmctl darbības principos, integrācijā ar mattermost
3. Mattermost integrēšana Docker
4. Lietotāju, komandu un kanāla izveides skripta izveide un testēšana
5. Automātiska webhook izveide, manuāla ziņojumu darbības pārbaude
6. Webhook padošanas automatizācija
7. Gala risinājuma pārbaude
### Rezultāti
Apziņošanas sistēma ar webhook uz noteiktu mattermost komandas kanālu, automatizēts skripts webhook un citu vajadzīgo komponenšu izveidei

## Egija:
Vizualizāciju veidošana Grafana
### Risinājuma apraksts
Grafana vidē izstrādāts dashboard, kas satur vizualizācijas DNS pieprasījumu analīzei, izmantojot Clickhouse datubāzi kā datu avotu. Dashboard ietver sevī dažāda tipa vizualizācijas (tabulas, laika rindas grafiki, statistikas paneļi, diagrammas). Risinājums nodrošina iespēju pārskatāmi un ērti novērot un analizēt serverī notiekošos DNS pieprasījumus, trafika tendences u.c.   
### Realizācijas gaita
1. Tiek izveidots savienojums ar Clickhouse datubāzi
2. Balstoties uz datubāzē esošās informācijas, tiek nolemts kāda tipa vizualizācijas veidot un kādus datus tajās attēlot
3. Tiek veidoti un testēti SQL vaicājumi datu iegūšanai un vizualizēšanai
4. Vizualizācijas tiek izveidotas interaktīvas un automātiski pielāgojas dashboard iestatītajam laika periodam 
### Rezultāti
Tika izveidots Grafana dashboard ar interaktīvām vizualizācijām reāllaika DNS pieprasījumu monitoringa un analīzes vajadzībām. 