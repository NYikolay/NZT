-- Инициализация расширений с проверкой ошибок
DO $$
DECLARE
    ext_record RECORD;
    required_extensions TEXT[] := ARRAY['timescaledb', 'vector', 'age'];
    ext_name TEXT;
BEGIN
    -- Активация TimescaleDB
    BEGIN
        CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
        RAISE NOTICE 'TimescaleDB успешно активирован';
    EXCEPTION WHEN OTHERS THEN
        RAISE WARNING 'Ошибка активации TimescaleDB: %', SQLERRM;
    END;

    -- Активация pgvector
    BEGIN
        CREATE EXTENSION IF NOT EXISTS vector CASCADE;
        RAISE NOTICE 'pgvector успешно активирован';
    EXCEPTION WHEN OTHERS THEN
        RAISE WARNING 'Ошибка активации pgvector: %', SQLERRM;
    END;

    -- Активация Apache AGE
    BEGIN
        CREATE EXTENSION IF NOT EXISTS age CASCADE;
        -- Загрузка библиотеки AGE
        LOAD 'age';
        -- Установка search_path для AGE
        SET search_path = ag_catalog, "$user", public;
        RAISE NOTICE 'Apache AGE успешно активирован';
    EXCEPTION WHEN OTHERS THEN
        RAISE WARNING 'Ошибка активации AGE: %', SQLERRM;
    END;

    -- Создание тестового графа для AGE
    BEGIN
        PERFORM ag_catalog.create_graph('test_graph');
        RAISE NOTICE 'Тестовый граф создан успешно';
    EXCEPTION WHEN OTHERS THEN
        RAISE WARNING 'Ошибка создания тестового графа: %', SQLERRM;
    END;

    -- Проверка всех расширений
    RAISE NOTICE '=== Проверка установленных расширений ===';
    FOR ext_record IN 
        SELECT extname, extversion 
        FROM pg_extension 
        WHERE extname = ANY(required_extensions)
        ORDER BY extname
    LOOP
        RAISE NOTICE 'Расширение: %, Версия: %', ext_record.extname, ext_record.extversion;
    END LOOP;

    -- Проверка версии PostgreSQL
    RAISE NOTICE 'Версия PostgreSQL: %', current_setting('server_version');
    
    -- Проверка отсутствующих расширений
    FOREACH ext_name IN ARRAY required_extensions
    LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = ext_name) THEN
            RAISE WARNING 'Расширение % не установлено!', ext_name;
        END IF;
    END LOOP;
END $$;