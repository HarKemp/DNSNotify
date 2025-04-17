# DNSNotify

# Uzstādīšana un izmēģinājums bez datu bāzes
## Uzstādīšana
* Instalē Docker desktop
* Noklonē DNSNotify repozitoriju
* No DNSNotify\Application mapes izpilda komandu:
```docker compose up -d --build --remove-orphans```

## Izmēģinājums
* Vispirms jāizveido savienojums ar konteineru, kas veiks DNS pieprasījumus:
```docker compose exec test-client /bin/sh```
* Izpilda dig komandu 
```dig @coredns rtu.lv``` - rtu.lv aizvieto ar jebkuru citu domēnu
* Tagad ar fastapi starpniecību izveidojas papildu ieraksts clickhouse datubāzē
* Iziet no konteinera
```exit```
* Atver clickhouse datubāzi
```docker compose exec clickhouse clickhouse-client --user default --password default```
* Izpilda komandu, lai apskatītu tabulu, kurā tagad vajadzētu būt vismaz vienam ierakstam
```SELECT * FROM dns_logs;```
* Svarīgākos datus var izvilkt ar komandu
```SELECT log_time,client_ip,query_type,domain,response_code,prediction,malicious_probability FROM dns_logs;```


## Piezīmes
* Šobrīd ir uzstādīts fastapi, ja lietojam kaut ko citu, tad tam ir jāstrādā ml-model konteinerī uz 5000 porta un pašus log failus jāpieņem /log subdirektorijā vai arī jāmaina konfigurācija ![agent.conf](Application/fluent-bit/agent.conf) failā
* Jāmaina būtu arī ports ml-model/Dockerfile un docker-compose.yml failā.
* Coredns šobrīd domēna IP adresi neatgriež
* Ja tiek mainīta clickhouse saglabātās dns_logs tabulas struktūra (![init.sql](Application/clickhouse/init.sql) failā), tad jāmaina arī konfigurācija ![ml-model/main.py](Application/ml-model/main.py) failā
* Ja tiek mainīta tabulas struktūra, tad ir jāizdzēš clickhouse konteinera volumes
```docker compose down -v``` vai ```docker compose down clickhouse -v```
* Pagaidām vēl nav izveidots .env fails, bet to vajadzētu izdarīt
* Iespējams vajadzētu sadalīt fastapi un ml-model funkcionalitāti divos atsevišķos failos, lai viss nebūtu main.py
* Varbūt pārdomāt kā labāk iestatīt clickhouse/users.xml failu, kad būs izveidots .env fails
