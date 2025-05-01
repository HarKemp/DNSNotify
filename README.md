# DNSNotify

# Uzstādīšana un izmēģinājums ar datu bāzi
## Uzstādīšana
* Instalē Docker desktop
* Noklonē DNSNotify repozitoriju
* No DNSNotify\Application mapes izpilda komandu:
```docker compose up -d --build --remove-orphans```

## Izmēģinājums
* Šobrīd tiek veikta automātiska dns pieprasījumu veikšana no test-client konteinera (katras 30 sekundes)
* Zemāk redzama iespēja to izdarīt manuāli, ja nepieciešams
### Manuāla DNS pieprasījumu veikšana
* Vispirms jāizveido savienojums ar konteineru, kas veiks DNS pieprasījumus:
```docker compose exec test-client /bin/sh```
* Izpilda dig komandu 
```dig @coredns rtu.lv``` - rtu.lv aizvieto ar jebkuru citu domēnu
* Tagad izveidojas papildu ieraksts clickhouse datubāzē
### Datu bāzes aplūkošana
* Atver clickhouse datubāzi
```docker compose exec clickhouse clickhouse-client --user default --password default```
* Izpilda komandu, lai apskatītu tabulu, kurā tagad vajadzētu būt vismaz vienam ierakstam
```SELECT * FROM dns_logs;```
* Svarīgākos datus var izvilkt ar komandu
```SELECT log_time,client_ip,query_type,domain,response_code,prediction,malicious_probability FROM dns_logs;```


## Piezīmes
* Fluent-Bit log failu pārsūtīšanai tagad ir aizvietots ar Vector
* Log failu saņemšanai no CoreDNS+Vector tagad izmanto NATS - tas log failus ieliek rindā un tos paņem ml-model, kad process nav aizņemts
* Ar NATS implementāciju FastAPI vai Flask vairs nav vajadzīgs
* Servisu/konteineru konfigurācija tagad ir pieejama .env failā
* Coredns šobrīd domēna IP adresi neatgriež
* Funkcijas, kas atbild par datu/log apstrādi tagad ir pieejamas ![ml_processing.py](Application/ml-model/ml_processing.py) failā
* ![main.py](Application/ml-model/main.py) failā ir pieejamas funkcijas, kas izveido savienojumus ar NATS un Clickhouse
* Ja tiek mainīta clickhouse saglabātās dns_logs tabulas struktūra (![init.sql](Application/clickhouse/init.sql) failā), tad jāmaina arī konfigurācija ![ml-model/main.py](Application/ml-model/ml_processing.py) failā
* Ja tiek mainīta tabulas struktūra, tad ir jāizdzēš clickhouse konteinera volumes
```docker compose down -v``` vai ```docker compose down clickhouse -v```
* Tika izveidots pagaidu konteiners, kas "sūta" (Vēl ir jāveic MatterMost implementācija) brīdinājumus uz MatterMost
