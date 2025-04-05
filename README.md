# DNSNotify

# Uzstādīšana un izmēģinājums bez datu bāzes
## Uzstādīšana
* Instalē Docker desktop
* Noklonē DNSNotify repozitoriju
* No DNSNotify\Application mapes izpilda komandu:
```docker compose up -d --build```
* Vajadzētu izveidoties jaunai mapei Application/Logs - tajā atrodas ```dns_logs.txt``` fails, kurā tiek saglabāti DNS pieprasījumi - tos izveido ml-model konteinerī esošais flask serveris

## Izmēģinājums
* Vispirms jāizveido savienojums ar konteineru, kas veiks DNS pieprasījumus:
```docker compose exec test-client /bin/sh```
* Izpilda dig komandu 
```dig @coredns rtu.lv``` - rtu.lv aizvieto ar jebkuru citu domēnu
* Tagad izveidojas papildu ieraksts ```dns_logs.txt``` failā
* Iziet no konteinera
```exit```

## Piezīmes
* Nezinu vai lietosim flask, bet, ja lietojam kaut ko citu, tad tam ir jāstrādā ml-model konteinerī uz 5000 porta un pašus log failus jāpieņem /log subdirektorijā vai arī jāmaina konfigurācija ![agent.conf](Application/fluent-bit/agent.conf) failā
* Jāmaina būtu arī ports ml-model/Dockerfile un docker-compose.yml failā.
* coredns šobrīd mājaslapas IP adresi neatgriež
* 