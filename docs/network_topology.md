# Network Topology

```text
+---------------------+        RS485        +------------------------+
|  DV10 Ventilation   |<------------------->|  ESP32-POE (Olimex)    |
|  (Modbus slave id=1)|                    |  Modbus RTU master     |
+----------+----------+                    +-----------+------------+
           |                                           |
           |                                           | Ethernet (PoE)
           |                                           |
           |                                   +-------v--------+
           |                                   |   Switch /    |
           +----------------------------------->  Router/LAN   |
                                               +-------+------+
                                                       |
                                                       | LAN
                                                       |
                                              +--------v--------+
                                              |   Debian host   |
                                              |  (Docker + API) |
                                              +--------+--------+
                                                       |
             +------------------ Docker bridge network iot-net ------------------+
             |                                                                    |
     +-------v--------+   MQTT   +--------v--------+   SQL/PG  +-------v--------+
     |   mosquitto    |<-------->| mqtt_ingestor   |--------->|    QuestDB     |
     | (MQTT broker)  |          | + SparkplugB    |          | (time-series DB)|
     +----------------+          +-----------------+          +-------+--------+
                                                                               |
                                                                               | HTTP (PostgreSQL)
                                                                       +-------v--------+
                                                                       |   FastAPI      |
                                                                       |   main.py      |
                                                                       +-------+--------+
                                                                               |
                                                                               | HTTP
                                                   +---------------------------+------------------------+
                                                   |                                                        |
                                           +-------v--------+                                      +-------v--------+
                                           |  Web Dashboard |                                      |   Grafana     |
                                           | index.html     |                                      | Dashboards    |
                                           +----------------+                                      +----------------+

