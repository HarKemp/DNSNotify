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

## Haralds:
Sistēmas infrastruktūras izveide un konfigurācija
### Risinājuma apraksts
* Visas turpmākajā tekstā veiktās atsauces uz failiem ir meklējamas relatīvi no projekta direktorijas - DNSNotify/Application/
* Risinājuma izvietošanai tika izmantotas divas virtuālās mašīnas, kas atradās divās mākoņu platformās. Serveris 1 jeb “Centrālais serveris” atrodas uz Oracle Cloud VM (4 vCPU, 24 GB RAM). Serveris 2 jeb “DNS starpniekserveris” atrodas uz Amazon Web Services VM (1 vCPU 1 GB RAM). Abi serveri darbojas nepārtraukti (vismaz šī projekta izveides laika posmā). Projekta Github repozitorijā tika ieviests Github Actions, kas izvietoja “main” atzarojumā (branch) publicētās izmaiņas uz “Centrālā servera”, izmantojot konfigurāciju no prod.yml faila un Docker Swarm, un ml-model repliku skaits noklusējumā ir 3. DNS Starpniekserverī izmaiņas tika izvietotas manuāli, projekta beigu posmā, izmantojot konfigurāciju no dnsserver.yml faila un Docker Compose.
* Testēšanas laikā uz izstrādes vidēm (personīgajiem datoriem) tika izmantots docker-compose.yml fails, kas satur visu konfigurāciju vai local.yml fails, kas satur tikai CoreDNS un Vector servisu.
* Demonstrācijas laikā uz personīgajiem datoriem tika nomainīta DNS konfigurācija, lai DNS vaicājumi tiktu sūtīti uz DNS Starpniekserveri.
### Demonstrācijā lietotā konfigurācija
#### Uz DNS Starpniekservera
* CoreDNS serviss, kas gala implementācijā darbojās uz DNS starpniekservera (DNS Proxy) gaidīja pieprasījumus, kuri pienāca uz servera 53 portu, kur tas šo DNS vaicājumu (DNS Query) pārsūtīja uz Google DNS serveriem (8.8.8.8). Saņemot atbildi, tas veica ierakstu docker log failā un pārsūtīja atbildi arī sākotnējam DNS vaicājuma izveidotājam (Piemēram, klienta datoram). Integrējot sistēmu uzņēmumā vai organizācijā būtu iespējams Google DNS servera adreses vietā iestatīt uzņēmuma privātā DNS servera adresi. 
* Vector serviss, kas gala implementācijā arī darbojās uz DNS starpnieksevera (DNS Proxy) lasīja log failus no docker atlasot tikai tos, kurus izveidoja CoreDNS serviss. Atrodot kādu log ierakstu no CoreDNS, tas pārbauda šis log ieraksts tiešām satur DNS vaicājuma informāciju (lai izvairītos no CoreDNS servisa uzsākšanas posmā izveidoto log ierakstu nevajadzīgas pārsūtīšanas. Pēc tam, tas pārveido katru log ierakstu divās daļās, viena satur laika atzīmi, otra satur visu vaicājumu un abas pārsūta uz NATS servisu JSON formātā.
#### Uz Centrālā servera
* NATS Serviss, kas gala implementācijā darbojās uz “Centrālā servera”, kas uz servera porta 4222. Kad NATS saņem log failus no Vector, tas tos uzglabā docker volume – nats-data, un tie tur gaida līdz brīdim, kad tos paņem kāds no pieejamiem ml-model konteineriem. NATS servisā ir izveidota arī papildus ziņojumu grupa, kas saņem no ml-model un glabā informāciju par pieprasījumiem, kuri izrādījās ļaunprātīgi, lai tos varētu tālāk apstrādāt notification-service.
* ml-model konteinerī darbojas python programma, kas izvelk NATS uzglabātos neapstrādātos ierakstus - tas notiek vai nu katru sekundi, vai kad NATS ir uzkrāti 100 pieprasījumi, atkarībā no tā kurš no nosacījumiem izpildās ātrāk. Šī konfigurācija ir paredzēta, lai samazinātu noslodzi uz Clickhouse datu bāzi un veiktu ierakstu pievienošanu tajā pa blokiem, nevis pa vienam. Konteinerī, tās pašas programmas ietvaros, darbojas arī funkcija, kas nolasa domēna nosaukumus no config/allowlist.txt faila un neveic tajā ierakstīto domēnu apstrādi ar mašīnmācīšanās modeli. Kad ir veikta vaicājumu apstrāde, tie tiek ierakstīti clickhouse datu bāzē.
* Clickhouse datu bāze uzglabā informāciju par visiem DNS vaicājumiem, kas tikuši apstrādāti ml-model konteinerī. Tā tabulas struktūra ir redzama clickhouse/init.sql failā.
* Grafana un Mattermost servisiem tika atvērti 3000 un 8065 porti, kas attiecīgi tika izmantoti, lai pārvirzītu savienojumus, ko saņem nginx tīmekļa serveris (no visual.harak.lat un matmost.harak.lat), uz attiecīgajiem konteineriem.
* notification-service konteinerī darbojās python skripts programma, ar kuru tika veikta no NATS ļaunprātīgo domēnu grupas izņemto pieprasījumu formatēšana un nosūtīšana Mattermost servisam ar webhook.
* Tika izveidots arī test-client konteineris, kurā darbojās alpine linux distribūcija un testa nolūkos sūta DNS  vaicājumus par iepriekš definētām domēna adresēm (test-client/domains.txt) - vienu katras 30 sekundes
### Realizācijas gaita
1.	Sākotnējā sistēmas izkārtojuma izveide.
2.	Docker Compose konfigurācijas izveide ar vienotu .env, tīklu netw.
3.	CoreDNS konfigurācija un žurnālu nolasīšana ar fluent-bit, kas bija izmantots kā pagaidu variants (pagaidām rezultāti redzami tikai konteinera log ierakstos).
4.	ml-model konteinera izveide ar Flask un Fluent-bit konfigurācijas izmaiņa, tiešai log failu pārsūtīšanai uz ml-model konteineri un šo ierakstu izvadi teksta failā.
5.	Clickhouse datu bāzes izveide un ml-model veikto apstrādes rezultātu izvietošana šajā datu bāzē. Pāreja no Flask uz Fastapi, lai samazinātu lietoto resursu apjomu
6.	NATS Servisa izveide un pāriešana ml-model konteinerī no Fastapi uz programmu, kas “abonē” NATS grupu, kura satur DNS vaicājumums ml-model konteinerī. Kā arī pāriešana no Fluent-Bit uz Vector, ērtākas konfigurācijas dēļ.
7.	Grafana un notification-service konteineru izveide. 
8.	visual.harak.lat un matmost.harak.lat domēnu izveide un to konfigurēšana nginx servisā savienojumu novirzīšanai uz attiecīgajiem Grafana un Mattermost servisiem.
9.	Centrālā servera konfigurācija un automātiska servisu izvietošana uz tā izmantojot Github Actions.
10.	Docker swarm servisa izveide uz Centrālā servera un DNS Starpniekservera konfigurācija.
### Rezultāti
Izveidotā sistēma spēj efektīvi apstrādāt apjomīgu DNS vaicājumu daudzumu. Testētais apjoms ir aptuveni 300 vaicājumi minūtē, tie visi tika apstrādāti dažu sekunžu laikā). Reālai sistēmas limitu noteikšanai būtu jāpievieno šī sistēma uzņēmuma vai organizācijas sistēmai, vai veicot lielāku DNS vaicājumu apjoma mākslīgu ģenerēšanu. Sistēma ir mērogojama, viegli segmentējama - tajā esošos servisus var katru izvietot atsevišķā sistēmā, izmainot tikai savienojuma izveidošanai nepieciešamos datus (vienīgais izņēmums ir CoreDNS un Vector, kuriem ar pašreizējo konfigurāciju ir nepieciešams atrasties uz vienas un tās pašas sistēmas). Lai ieviestu risinājumu reālā vidē, būtu nepieciešams veikt .env faila un docker konfigurācijas failu pārstrādāšanu, lai nodrošinātu Grafana, Mattermost un Clickhouse autentifikācijas datu konfidencialitāti. Uzlabotai drošībai nepieciešams arī nodrošināt TLS sertifikātu izmantošanu komunikācijai starp Vector, ml-model, notification-service servisiem un NATS. Papildus, atkarībā no apstrādāto vaicājumu skaita izmaiņām dažādos laika periodos, būtu nepieciešams veikt arī slodzes balansēšanas (load balancing) implementēšanu. Visbeidzot būtu noderīgi izveidot arī administratora paneli, kurā ir iespējams operatīvi veikt konfigurācijas izmaiņas.

