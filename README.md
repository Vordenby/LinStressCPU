# LinStressCPU

## English

### LinStressCPU is a Python analogue of CPUStres — a simple CPU stress tester.

## Usage (CLI):

Run with defaults (one worker per CPU, maximum load):
```
python3 ./LinStress.py
```

### Options:

```
-t, --threads N         number of worker processes (default: cpu count)
-l, --level LEVEL       activity level: low|medium|busy|maximum
-d, --duration SEC      duration in seconds (0 = infinite)
-p, --priority PRIO     priority: low|normal|high
--interactive           interactive text menu
```

#### Example: run 4 workers at medium activity for 60 seconds:

```
python3 PythonVer/main.py -t 4 -l medium -d 60
```

## Russian

### LinStressCPU — Python-аналог CPUStres, утилита для нагрузочного тестирования CPU.

## Использование (CLI):

Запуск с настройками по умолчанию (по количеству CPU, максимальная загрузка):

```
python3 PythonVer/main.py
```

### Опции:

```
-t, --threads N         количество процессов-воркеров (по умолчанию: число ядер CPU)
-l, --level LEVEL       уровень активности: low|medium|busy|maximum
-d, --duration SEC      длительность в секундах (0 = бесконечно)
-p, --priority PRIO     приоритет: low|normal|high
--interactive           интерактивное текстовое меню
```

#### Пример: запустить 4 воркера на среднем уровне активности на 60 секунд:

```
python3 PythonVer/main.py -t 4 -l medium -d 60
```