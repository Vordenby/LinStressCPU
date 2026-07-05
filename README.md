# LinStressCPU

LinStressCPU is a Python CPU stress testing utility. It is designed as an analog of CPUStress for Linux and provides
both a command-line interface and a simple graphical interface for configuring per-thread load.

LinStressCPU — Python утилита для нагрузочного тестирования CPU. Она имитирует поведение CPUStress для Linux и предоставляет
как CLI интерфейс, так и простую графическую оболочку для настройки нагрузки по каждому потоку.

## Features / Возможности
- CLI с опциями для количества потоков, длительности, приоритета и уровня загрузки.
- Поддержка задания индивидуального уровня активности и приоритета для каждого потока.
- Простая GUI на Tkinter: `LinStressGUI.py` — настраивает каждый поток отдельно и управляет запуском/остановкой.
- Не требует дополнительных библиотек для базовой работы; `psutil` рекомендуется для корректной установки приоритетов.

## CLI Usage / Использование (CLI)

English:

Run with defaults — one worker per CPU, maximum load (infinite duration):

```bash
python LinStress.py
```

Options:

- `-t, --threads N` — number of workers (integer or `all`, default: CPU count)
- `-l, --level LEVEL` — load level: `Low`, `Medium`, `Busy`, `Maximum` (default `Maximum`)
- `--levels` — per-thread comma-separated levels or float values between 0.0 and 1.0, e.g.: `Low,0.5,Maximum`
- `-d, --duration SEC` — duration in seconds (0 = infinite)
- `-p, --priority PRIO` — priority: `Normal`, `High`, `Realtime` (default `Normal`)
- `--priorities` — per-thread comma-separated priorities or numeric nice values, e.g.: `Normal,High,-10`

Examples:

- Run 4 threads with individual levels and priorities for 60 seconds:
  ```bash
  python LinStress.py -t 4 --levels Low,Medium,0.9,Maximum --priorities Normal,High,-10,Realtime -d 60
  ```

- Quick test with two threads:
  ```bash
  python LinStress.py -t 2 --levels 0.5,0.2 --priorities 0,0 -d 5
  ```

Русский:

Запуск по умолчанию — по количеству CPU, максимальная загрузка (бесконечно):

```bash
python LinStress.py
```

Опции:

- `-t, --threads N` — количество воркеров (число или `all`, по умолчанию: число CPU)
- `-l, --level LEVEL` — уровень загрузки: `Low`, `Medium`, `Busy`, `Maximum` (по умолчанию `Maximum`)
- `--levels` — уровни по потокам через запятую или численные значения 0.0–1.0, например: `Low,0.5,Maximum`
- `-d, --duration SEC` — длительность в секундах (0 = бесконечно)
- `-p, --priority PRIO` — приоритет: `Normal`, `High`, `Realtime` (по умолчанию `Normal`)
- `--priorities` — приоритеты по потокам через запятую или числовые nice-значения, например: `Normal,High,-10`

Примеры:

- Запустить 4 потока с индивидуальными уровнями и приоритетами на 60 секунд:
  ```bash
  python LinStress.py -t 4 --levels Low,Medium,0.9,Maximum --priorities Normal,High,-10,Realtime -d 60
  ```

- Быстрый тест с двумя потоками:
  ```bash
  python LinStress.py -t 2 --levels 0.5,0.2 --priorities 0,0 -d 5
  ```

## GUI Usage / Использование (GUI)

English:

Run:

```bash
python LinStressGUI.py
```

The GUI provides controls for selecting the number of threads, duration, and for each thread — load level and priority dropdowns.

Русский:

Запустите:

```bash
python LinStressGUI.py
```

GUI предоставляет виджет для выбора числа потоков, длительности и для каждого потока — выпадающие списки уровня загрузки и приоритета.

## Notes / Замечания
- Если не установлен `psutil`, программа пытается использовать `os.setpriority` (ограниченная поддержка на Windows).
- Значения в `--levels` могут быть либо имена (`Low`, `Medium`, `Busy`, `Maximum`), либо числа от `0.0` до `1.0`.
- Значения в `--priorities` могут быть либо имена (`Normal`, `High`, `Realtime`), либо целые nice-значения.
