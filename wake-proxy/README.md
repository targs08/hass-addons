# Home Assistant Add-on: Wake Proxy

Обратный прокси, который будит сервер при первом запросе и держит соединение,
пока сервис не поднимется.

## О add-on'е

Готовые WoL-прокси тут не подходят: машина грузится по PXE в одну из двух ОС.
Разбудить её мало — если следующая загрузка указывает на Windows, Ollama не
появится никогда. Поэтому add-on сначала переключает цель загрузки на Ubuntu,
и только потом шлёт magic packet.

```
запрос → upstream доступен? ──да──► проксируем
              │нет
              ▼
     машина под Windows? ──да──► 503, будить нечего
              │нет
              ▼
   следующая загрузка не Ubuntu? → переключаем
              │
              ▼
        нажимаем кнопку пробуждения
              │
              ▼
     ждём порт upstream (до wake_timeout)
              │
              ▼
          проксируем
```

Запросы, пришедшие во время загрузки, ждут вместе: повторных пробуждений не
будет.

## Установка

1. Подключите репозиторий к Home Assistant (см. [README репозитория][repo]).
2. Установите add-on **Wake Proxy**.
3. Задайте `upstream_host` — IP машины с целевым сервисом.
4. Запустите add-on.

Нужные сущности Home Assistant, полный список настроек и проверка —
в [DOCS.md](DOCS.md).

## Настройки

```yaml
upstream_host: "192.168.178.50"
upstream_port: 11434
wake_entity: button.home_server_wake
boot_ubuntu_entity: shell_command.home_server_boot_ubuntu
next_boot_entity: sensor.home_server_next_boot
windows_entity: binary_sensor.home_server_windows_online
wake_timeout: 240
probe_interval: 3
probe_timeout: 2
boot_settle: 5
```

## Лицензия

MIT — см. [LICENSE](../LICENSE) в корне репозитория.

[repo]: https://github.com/targs08/hass-addons
