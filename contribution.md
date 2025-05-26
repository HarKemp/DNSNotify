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


## Māris:
ML modeļa izstrāde un apmācība
### Risinājuma apraksts
Projekta ietvaros tika izstrādāts ML modelis, kas balstīts uz Gadījuma meža (Random Forest) klasifikatoru. Modeļa izstrādē izpētīti esošie pētījumi, kuru idejas izmantotas
arī šī darba izstrādē:
Kolla, T. (2023). A Machine Learning Approach to Identifying Malicious DNS Requests through Server Log Analysis (Doctoral dissertation, Dublin Business School).
Marques, C., Malta, S., & Magalhães, J. P. (2021). DNS dataset for malicious domains detection. Data in brief, 38, 107342.
Singh, S. K., & Roy, P. K. (2022). Malicious traffic detection of DNS over https using ensemble machine learning. International Journal of Computing and Digital Systems, 11(1), 189-197.
ML modelis ir izvietots uz Docker konteinera un veic DNS pieprasījumu apstrādi reāllaikā, bet neveic kādas citas darbības. Klasifikācijas rezultāts tiek nosūtīts uz datubāzi tālākai analīzei.
### Realizācijas gaita
1. Izpētītas esošās pieejas DNS pieprasījumu klasificēšanai.
2. Izpētīta DNS log struktūra un sagatavots kods īpašību izgūšanai.
3. Apkopota pašu datu kopa no dažādiem avotiem, kas satur gan ļaunprātīgus, gan neļaunprātīgus pieprasījumus.
4. Veikta RandomForest klasifikātora izveide un apmācība uz esošās datu kopas
5. RandomForest klasifikātors tiek izvietots uz Docker konteinera un savienots ar citiem servisiem, lai veiktu pieprasījumu apstrādi. 
### Rezultāti
Iegūts ML modelis, kas spēj klasificēt ienākošos DNS pieprasījumus. Sākotnējais modelis trenēts uz publiskām datu kopām darbojās slikti, tāpēc tika izveidota pašu apkopota datu kopa, kura uzlaboja klasifikācijas precizitāti. Turpmākajai lietošanai var apskatīt sarežģītākus modeļus, kas spētu saskatīt sakarības laikā (LSTM, Transformers), kā arī mainīt izmantotās īpašības no loga, atkarībā no pielietošanas mērķa un nepieciešamās precizitātes, jo šobrīd modelis nespēj pilnīgi korekti klasificēt katru ierakstu.
