#!/bin/bash
set -e

echo "Seeding test data for Palmi..."

psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER:-palmi}" --dbname "${POSTGRES_DB:-palmi}" <<-EOSQL
    -- Insert test elder
    INSERT INTO elders (id, wechat_user_id, nickname, phone, status)
    VALUES (
        'a0000000-0000-0000-0000-000000000001',
        'test_external_userid_001',
        '美兰阿姨',
        '13800138001',
        'active'
    ) ON CONFLICT (wechat_user_id) DO NOTHING;

    -- Insert test configurator
    INSERT INTO configurators (id, wechat_openid, nickname, phone)
    VALUES (
        'b0000000-0000-0000-0000-000000000001',
        'test_openid_001',
        '小明',
        '13900139001'
    ) ON CONFLICT (wechat_openid) DO NOTHING;

    RAISE NOTICE 'Seed data inserted successfully!';
EOSQL

echo "Seeding complete."
