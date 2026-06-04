### Отчистка текущего содержания тома

```bash
sudo rm -rf /var/lib/docker/volumes/dio-website-cms_wagtail_media/_data/*
```

### Распаковка архивированного бекапа обратно в том

```bash
sudo tar -xzf /root/backups/wagtail_media_backup_20260101_120000.tar.gz -C /var/lib/docker/volumes/dio-website-cms_wagtail_media/_data
```

### Восстановление прав, чтобы контейнер мог читать/писать (обычно владелец — пользователь внутри контейнера, например 1000 или wagtail)

```bash
sudo chown -R 1000:1000 /var/lib/docker/volumes/dio-website-cms_wagtail_media/_data
```
