"""
Скрипт для создания схемы dds и заполнения тестовыми данными.
Запуск: python -m src.db.seed
Требует DATABASE_URL_SYNC в .env или переменной окружения.
Зависимость: psycopg2-binary (pip install psycopg2-binary)
"""
import sys
import os

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.config import settings
from src.logger import log

DDL = """
CREATE SCHEMA IF NOT EXISTS dds;

CREATE TABLE IF NOT EXISTS dds.dim_counteragent (
    dwh_id      BIGSERIAL PRIMARY KEY,
    jira_id     BIGINT,
    counteragent TEXT,
    industry    INT,
    responsible VARCHAR
);

CREATE TABLE IF NOT EXISTS dds.dim_project (
    issueid     BIGINT PRIMARY KEY,
    project_name VARCHAR(255),
    created     TIMESTAMPTZ,
    updated     TIMESTAMPTZ,
    status      INT,
    type        INT,
    description TEXT,
    date_begin  DATE,
    date_end    DATE,
    kam         VARCHAR(255),
    pm          VARCHAR(255),
    front_admin VARCHAR(255),
    dwh_insert_date TIMESTAMP DEFAULT now() NOT NULL,
    dwh_update_date TIMESTAMP DEFAULT now() NOT NULL,
    dwh_delete_date TIMESTAMP,
    labor_cost_accounting_type INT
);

CREATE TABLE IF NOT EXISTS dds.dim_contract (
    jira_issueid BIGINT PRIMARY KEY,
    name        VARCHAR(255),
    type        INT,
    counteragent_id BIGINT REFERENCES dds.dim_counteragent(dwh_id) ON UPDATE CASCADE,
    sum         FLOAT,
    date_sign   DATE,
    date_end    DATE,
    dwh_insert_date TIMESTAMP DEFAULT now() NOT NULL,
    dwh_update_date TIMESTAMP DEFAULT now() NOT NULL,
    dwh_delete_date TIMESTAMP,
    date_created TIMESTAMPTZ,
    company     INT,
    status      INT,
    project_id  INT,
    manager     TEXT,
    curator     TEXT,
    resolution  TEXT,
    revenue_it  FLOAT,
    revenue_non_it FLOAT
);

CREATE TABLE IF NOT EXISTS dds.link_contract_project (
    contract_id BIGINT NOT NULL REFERENCES dds.dim_contract(jira_issueid) ON UPDATE CASCADE,
    project_id  BIGINT NOT NULL REFERENCES dds.dim_project(issueid) ON UPDATE CASCADE,
    dwh_insert_date TIMESTAMP DEFAULT now() NOT NULL,
    dwh_delete_date TIMESTAMP,
    PRIMARY KEY (contract_id, project_id)
);

CREATE TABLE IF NOT EXISTS dds.fact_forecast (
    issueid     BIGINT PRIMARY KEY,
    summary     VARCHAR(255),
    created     TIMESTAMPTZ,
    updated     TIMESTAMPTZ,
    description TEXT,
    date_start  DATE,
    date_end    DATE,
    forecast_sum FLOAT,
    income_subcounteragent INT,
    pr_id       BIGINT REFERENCES dds.dim_project(issueid) ON UPDATE CASCADE,
    dwh_insert_date TIMESTAMP DEFAULT now() NOT NULL,
    dwh_update_date TIMESTAMP DEFAULT now() NOT NULL,
    dwh_delete_date TIMESTAMP,
    plan_date_pay DATE,
    fact_sum    FLOAT,
    plan_cost_k NUMERIC,
    status      INT
);
"""

SEED_DATA = """
-- Контрагенты
INSERT INTO dds.dim_counteragent (jira_id, counteragent, industry, responsible)
VALUES
  (101, 'ООО "ТехноСервис"', 1, 'Иванов А.А.'),
  (102, 'АО "Банк Развития"', 2, 'Петрова М.С.'),
  (103, 'ГУП "Городской транспорт"', 4, 'Сидоров В.В.')
ON CONFLICT DO NOTHING;

-- Проекты
INSERT INTO dds.dim_project (issueid, project_name, status, type, description, date_begin, date_end, kam, pm)
VALUES
  (1001, 'Автоматизация отчётности ТехноСервис', 1, 2, 'Разработка системы автоматической генерации отчётов', '2024-01-15', '2024-12-31', 'Иванов А.А.', 'Козлов П.И.'),
  (1002, 'Банковская аналитика', 1, 2, 'Внедрение BI-платформы для анализа данных банка', '2024-03-01', '2025-03-01', 'Петрова М.С.', 'Новиков Д.С.'),
  (1003, 'Транспортный мониторинг', 2, 1, 'Система мониторинга городского транспорта', '2023-06-01', '2024-06-01', 'Сидоров В.В.', 'Фёдоров А.Н.'),
  (1004, 'CRM для ТехноСервис', 1, 2, 'Разработка CRM-системы для управления клиентами', '2024-07-01', '2025-07-01', 'Иванов А.А.', 'Козлов П.И.'),
  (1005, 'ML-платформа Банк Развития', 1, 3, 'Разработка платформы машинного обучения', '2025-01-01', '2025-12-31', 'Петрова М.С.', 'Миронов С.К.')
ON CONFLICT DO NOTHING;

-- Контракты
INSERT INTO dds.dim_contract (jira_issueid, name, type, counteragent_id, sum, date_sign, date_end, status, manager)
VALUES
  (2001, 'Договор №2024-01 ТехноСервис', 1, 1, 4500000.0, '2024-01-10', '2024-12-31', 1, 'Иванов А.А.'),
  (2002, 'Договор №2024-02 Банк Развития', 1, 2, 8200000.0, '2024-03-01', '2025-03-01', 1, 'Петрова М.С.'),
  (2003, 'Договор №2023-03 Транспорт', 1, 3, 3100000.0, '2023-06-01', '2024-06-01', 2, 'Сидоров В.В.'),
  (2004, 'Договор №2024-04 CRM', 1, 1, 5700000.0, '2024-07-01', '2025-07-01', 1, 'Иванов А.А.')
ON CONFLICT DO NOTHING;

-- Связи контрактов и проектов
INSERT INTO dds.link_contract_project (contract_id, project_id)
VALUES
  (2001, 1001),
  (2002, 1002),
  (2003, 1003),
  (2004, 1004)
ON CONFLICT DO NOTHING;

-- Выработки (fact_forecast)
INSERT INTO dds.fact_forecast (issueid, summary, date_start, date_end, forecast_sum, fact_sum, pr_id, status, plan_date_pay, income_subcounteragent)
VALUES
  (3001, 'Выработка Q1 2024 ТехноСервис', '2024-01-15', '2024-03-31', 1100000.0, 1050000.0, 1001, 3, '2024-04-15', 0),
  (3002, 'Выработка Q2 2024 ТехноСервис', '2024-04-01', '2024-06-30', 1200000.0, 1150000.0, 1001, 3, '2024-07-15', 0),
  (3003, 'Выработка Q3 2024 ТехноСервис', '2024-07-01', '2024-09-30', 1100000.0, 900000.0, 1001, 2, '2024-10-15', 100000),
  (3004, 'Выработка Q4 2024 ТехноСервис', '2024-10-01', '2024-12-31', 1100000.0, NULL, 1001, 4, '2025-01-15', 0),
  (3005, 'Выработка Q1 2024 Банк', '2024-03-01', '2024-06-30', 2000000.0, 1950000.0, 1002, 3, '2024-07-01', 200000),
  (3006, 'Выработка Q2 2024 Банк', '2024-07-01', '2024-12-31', 2200000.0, 2100000.0, 1002, 2, '2025-01-15', 300000),
  (3007, 'Выработка Транспорт 2023-2024', '2023-06-01', '2024-06-01', 3100000.0, 2900000.0, 1003, 3, '2024-07-01', 0),
  (3008, 'Выработка Q3 2024 CRM', '2024-07-01', '2024-09-30', 1400000.0, 1350000.0, 1004, 3, '2024-10-31', 150000)
ON CONFLICT DO NOTHING;
"""


def run_seed():
    try:
        import psycopg2
    except ImportError:
        log.error("psycopg2-binary не установлен. Выполните: pip install psycopg2-binary")
        sys.exit(1)

    url = settings.database_url_sync
    log.info(f"Подключение к БД: {url.split('@')[-1]}")

    conn = psycopg2.connect(url)
    conn.autocommit = True
    cur = conn.cursor()

    log.info("Создание схемы и таблиц dds...")
    cur.execute(DDL)
    log.info("Таблицы созданы")

    log.info("Заполнение тестовыми данными...")
    cur.execute(SEED_DATA)
    log.info("Тестовые данные добавлены")

    cur.close()
    conn.close()
    log.info("Seed завершён успешно")


if __name__ == "__main__":
    run_seed()
