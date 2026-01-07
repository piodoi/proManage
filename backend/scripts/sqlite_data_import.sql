-- ProManage Data Export from MySQL to SQLite
-- Generated: 2026-01-07T18:58:25.153938
-- Import with: sqlite3 promanage.db < sqlite_data_import.sql

BEGIN TRANSACTION;

-- Disable foreign key checks during import
PRAGMA foreign_keys = OFF;

-- Users (2 records)
INSERT INTO users (id, email, name, role, password_hash, oauth_provider, oauth_id, subscription_tier, subscription_expires, ebloc_username, ebloc_password_hash, created_at) VALUES (
  '57ca9597-6a30-4775-bc89-71243d828a98',
  'pio.doi@gmail.com',
  'PioLand',
  'admin',
  '$2b$12$fPhRbMZJ2ypYpVGt/AAGNuyGXdx089aq8P20hGOvnCk5lGDxj3ENC',
  NULL,
  NULL,
  0,
  NULL,
  'piodoi@gmail.com',
  'gAAAAABpVr0rxUeW5pDMLUaQXCIzbLKIVrYHEZ4iy4bPrM9QAoXkJhXr3yk5NgNJaVLw-bK4d_t_VBf5P4AOcOkzDPq29DfKfA==',
  '2025-12-31T11:13:57'
);

INSERT INTO users (id, email, name, role, password_hash, oauth_provider, oauth_id, subscription_tier, subscription_expires, ebloc_username, ebloc_password_hash, created_at) VALUES (
  '748b8c6a-af3b-4328-b087-277a76d1c930',
  'piodoi+ll@gmail.com',
  'PioLandL',
  'landlord',
  '$2b$12$2UVy9RuPG7c0MNNrtgvUTuQXTX6domOccMFkDpDehD4zoELLLsuiC',
  NULL,
  NULL,
  0,
  NULL,
  'piodoi@gmail.com',
  'gAAAAABpWUOkBzUxZg5UDVNYoEAnaG8RElu2bOlXQZ_gpu5HXu6ke0kZniC6lsmu4DrwQIrBiIiwMG-4KHISlcORZTP1cO0i3Q==',
  '2026-01-01T16:38:22'
);

-- Properties (7 records)
INSERT INTO properties (id, landlord_id, address, name, created_at) VALUES (
  '1305a3b8-2509-4cf4-a93a-fe9a868de4c6',
  '57ca9597-6a30-4775-bc89-71243d828a98',
  'Str. Plutonier Radu Gheorghe Sc: A Ap: 25',
  'Str. Plutonier Radu Gheorghe',
  '2025-12-31T11:20:21'
);

INSERT INTO properties (id, landlord_id, address, name, created_at) VALUES (
  'a3b56669-a657-481c-b57f-52fd94f1d7e4',
  '57ca9597-6a30-4775-bc89-71243d828a98',
  'Strada Trapezului nr.2 Bl: M6 Sc: 2 Ap: 53',
  'Strada Trapezului nr.2',
  '2025-12-31T11:20:21'
);

INSERT INTO properties (id, landlord_id, address, name, created_at) VALUES (
  'b2c07414-e2bb-4515-b568-5f3dd596f14d',
  '57ca9597-6a30-4775-bc89-71243d828a98',
  'Spineni nr.1, sector 4,Bucuresti Sc: A Ap: 5',
  'Spineni nr.1, sector 4,Bucuresti',
  '2025-12-31T11:20:21'
);

INSERT INTO properties (id, landlord_id, address, name, created_at) VALUES (
  'e06b83db-1331-4137-a687-3058b969ccae',
  '57ca9597-6a30-4775-bc89-71243d828a98',
  'Str. Mizil nr.57 Sc: C2/1 Ap: 8',
  'Str. Mizil nr.57',
  '2025-12-31T11:20:21'
);

INSERT INTO properties (id, landlord_id, address, name, created_at) VALUES (
  '7b590e84-affd-4310-962d-d889c42ed137',
  '57ca9597-6a30-4775-bc89-71243d828a98',
  'Vlad Tepes 97, Tanganu Ilfov',
  'Vlad Tepes 97',
  '2025-12-31T15:27:03'
);

INSERT INTO properties (id, landlord_id, address, name, created_at) VALUES (
  '67dcfa6a-cbac-429d-a600-c66db6f8b4c5',
  '57ca9597-6a30-4775-bc89-71243d828a98',
  '1 Decembrie 17, Tangau, Ilfov',
  'Loc Joaca',
  '2025-12-31T15:31:01'
);

INSERT INTO properties (id, landlord_id, address, name, created_at) VALUES (
  '3e404c0f-2361-48c7-b2b8-45d7e7cf3964',
  '748b8c6a-af3b-4328-b087-277a76d1c930',
  'Home',
  'First',
  '2026-01-03T16:46:43'
);

-- Renters (7 records)
INSERT INTO renters (id, property_id, name, email, phone, rent_day, start_contract_date, rent_amount_eur, access_token, created_at) VALUES (
  'f938c711-3209-49df-8580-13f9c96b9fbf',
  'a3b56669-a657-481c-b57f-52fd94f1d7e4',
  'Hraniceru',
  NULL,
  NULL,
  25,
  NULL,
  460.0,
  'f725a9cf-cbd6-403a-844a-43a7a1c9d044',
  '2026-01-01T19:23:17'
);

INSERT INTO renters (id, property_id, name, email, phone, rent_day, start_contract_date, rent_amount_eur, access_token, created_at) VALUES (
  'dd205ad6-b2da-413e-957b-af790c7798d8',
  'b2c07414-e2bb-4515-b568-5f3dd596f14d',
  'Andrei Zdrali',
  NULL,
  '+40731733991',
  1,
  NULL,
  360.0,
  'e49c06f9-85fb-44dc-9bb8-63b57aa6ba70',
  '2026-01-01T19:53:33'
);

INSERT INTO renters (id, property_id, name, email, phone, rent_day, start_contract_date, rent_amount_eur, access_token, created_at) VALUES (
  '5090eafa-f0b3-46d3-804e-06bffb59f37a',
  'e06b83db-1331-4137-a687-3058b969ccae',
  'Miruna Pricopie',
  NULL,
  NULL,
  10,
  NULL,
  405.0,
  'aeb52050-a314-467f-a77c-65e91abb3102',
  '2026-01-01T19:57:56'
);

INSERT INTO renters (id, property_id, name, email, phone, rent_day, start_contract_date, rent_amount_eur, access_token, created_at) VALUES (
  '8d9225f3-9d5d-4961-b6e4-2cbb0a4a16ff',
  '1305a3b8-2509-4cf4-a93a-fe9a868de4c6',
  'Zoahib',
  NULL,
  NULL,
  20,
  NULL,
  360.0,
  '74a4a9ad-5b98-4649-8372-c7ff767c5f4f',
  '2026-01-01T20:29:29'
);

INSERT INTO renters (id, property_id, name, email, phone, rent_day, start_contract_date, rent_amount_eur, access_token, created_at) VALUES (
  'bf153da6-17f3-4146-ba80-54fd9ece7621',
  '1305a3b8-2509-4cf4-a93a-fe9a868de4c6',
  'Sojib',
  NULL,
  NULL,
  10,
  NULL,
  170.0,
  '24e267fd-e913-4049-ae10-ecb3b75b3251',
  '2026-01-01T20:30:45'
);

INSERT INTO renters (id, property_id, name, email, phone, rent_day, start_contract_date, rent_amount_eur, access_token, created_at) VALUES (
  'e893c57c-f607-4a7a-a1e4-e345176997af',
  '3e404c0f-2361-48c7-b2b8-45d7e7cf3964',
  'place',
  NULL,
  NULL,
  5,
  NULL,
  100.0,
  'e84a393b-3b2d-48f4-9b97-536dc337b721',
  '2026-01-03T16:47:05'
);

INSERT INTO renters (id, property_id, name, email, phone, rent_day, start_contract_date, rent_amount_eur, access_token, created_at) VALUES (
  '59b04a63-8f2e-44f5-a2ff-b5b80f07ce7f',
  '67dcfa6a-cbac-429d-a600-c66db6f8b4c5',
  'test chi',
  NULL,
  NULL,
  1,
  NULL,
  100.0,
  'ff2aacc4-9d8c-4035-ac2f-287420a98277',
  '2026-01-07T16:25:45'
);

-- Suppliers (10 records)
INSERT INTO suppliers (id, name, has_api, bill_type, extraction_pattern_supplier, created_at) VALUES (
  'b6983cc9-8544-4560-b810-3e348f4bf7ed',
  'Apanova',
  1,
  'utilities',
  NULL,
  '2025-12-31T11:17:45'
);

INSERT INTO suppliers (id, name, has_api, bill_type, extraction_pattern_supplier, created_at) VALUES (
  'ee8a274b-837f-4d72-860e-5aad97487958',
  'Digi',
  0,
  'utilities',
  'Digi',
  '2025-12-31T11:17:45'
);

INSERT INTO suppliers (id, name, has_api, bill_type, extraction_pattern_supplier, created_at) VALUES (
  '1e0537e9-4242-4e5e-82e2-6fad9e08494f',
  'E-bloc',
  0,
  'ebloc',
  'e-bloc',
  '2025-12-31T11:17:45'
);

INSERT INTO suppliers (id, name, has_api, bill_type, extraction_pattern_supplier, created_at) VALUES (
  '07b31939-5944-4f5e-b982-5ee9e1dd1e67',
  'Engie',
  0,
  'utilities',
  'engie',
  '2026-01-05T17:58:31'
);

INSERT INTO suppliers (id, name, has_api, bill_type, extraction_pattern_supplier, created_at) VALUES (
  '5f923979-987f-4bb8-838b-786ee4e275ee',
  'Engie Gaze',
  0,
  'utilities',
  'engie.gaz',
  '2026-01-02T13:26:46'
);

INSERT INTO suppliers (id, name, has_api, bill_type, extraction_pattern_supplier, created_at) VALUES (
  'fd37ddb1-5669-479e-a4ae-bab9a95fac2e',
  'EonRomania',
  1,
  'utilities',
  NULL,
  '2025-12-31T11:17:45'
);

INSERT INTO suppliers (id, name, has_api, bill_type, extraction_pattern_supplier, created_at) VALUES (
  'dc09419b-212a-4e3d-914e-17f083911fc5',
  'Hidroelectrica',
  0,
  'utilities',
  'Hidroelectrica',
  '2025-12-31T11:17:45'
);

INSERT INTO suppliers (id, name, has_api, bill_type, extraction_pattern_supplier, created_at) VALUES (
  '88c40c32-6da4-4b6e-8aea-9e1f2576994c',
  'MyElectrica',
  1,
  'utilities',
  NULL,
  '2025-12-31T11:17:45'
);

INSERT INTO suppliers (id, name, has_api, bill_type, extraction_pattern_supplier, created_at) VALUES (
  'd14bc4a9-0be2-4603-90b4-e256c4204dde',
  'Nova power & gas',
  0,
  'utilities',
  NULL,
  '2025-12-31T11:20:26'
);

INSERT INTO suppliers (id, name, has_api, bill_type, extraction_pattern_supplier, created_at) VALUES (
  '00ca9f3c-93a9-40b0-940d-416739d12d6e',
  'Vodafone',
  0,
  'utilities',
  'Vodafone',
  '2025-12-31T11:17:45'
);

-- Bills (18 records)
INSERT INTO bills (id, property_id, renter_id, supplier_id, bill_type, description, amount, currency, due_date, bill_date, legal_name, iban, bill_number, extraction_pattern_id, contract_id, payment_details, status, source_email_id, created_at) VALUES (
  '9ae952c1-ae7b-444f-ad18-b0f72fd21294',
  '7b590e84-affd-4310-962d-d889c42ed137',
  NULL,
  NULL,
  'utilities',
  'Hidroelectrica',
  769.46,
  'RON',
  '2026-01-26T00:00:00',
  NULL,
  NULL,
  NULL,
  '25110487592',
  '220e67e4-8d81-487c-8d35-639c3ac03a6b',
  '8000324406',
  NULL,
  'paid',
  NULL,
  '2025-12-31T16:01:39'
);

INSERT INTO bills (id, property_id, renter_id, supplier_id, bill_type, description, amount, currency, due_date, bill_date, legal_name, iban, bill_number, extraction_pattern_id, contract_id, payment_details, status, source_email_id, created_at) VALUES (
  'bedd4ced-3a64-474a-981e-67e022085007',
  '67dcfa6a-cbac-429d-a600-c66db6f8b4c5',
  NULL,
  NULL,
  'utilities',
  'Hidroelectrica',
  488.22,
  'RON',
  '2026-01-30T00:00:00',
  NULL,
  NULL,
  NULL,
  '25110916910',
  '220e67e4-8d81-487c-8d35-639c3ac03a6b',
  '8000882523',
  NULL,
  'pending',
  NULL,
  '2025-12-31T16:02:02'
);

INSERT INTO bills (id, property_id, renter_id, supplier_id, bill_type, description, amount, currency, due_date, bill_date, legal_name, iban, bill_number, extraction_pattern_id, contract_id, payment_details, status, source_email_id, created_at) VALUES (
  '3e92a215-0157-4f00-b300-1e13593d5b1c',
  'e06b83db-1331-4137-a687-3058b969ccae',
  NULL,
  NULL,
  'utilities',
  'Hidroelectrica',
  31.27,
  'RON',
  '2026-01-30T00:00:00',
  NULL,
  NULL,
  NULL,
  '25110944560',
  '220e67e4-8d81-487c-8d35-639c3ac03a6b',
  '8000324444',
  NULL,
  'pending',
  NULL,
  '2026-01-01T15:56:46'
);

INSERT INTO bills (id, property_id, renter_id, supplier_id, bill_type, description, amount, currency, due_date, bill_date, legal_name, iban, bill_number, extraction_pattern_id, contract_id, payment_details, status, source_email_id, created_at) VALUES (
  '220a3077-d18a-4556-897c-fc6b822a172a',
  '1305a3b8-2509-4cf4-a93a-fe9a868de4c6',
  NULL,
  NULL,
  'utilities',
  'Hidroelectrica',
  124.68,
  'RON',
  '2026-01-29T00:00:00',
  NULL,
  NULL,
  NULL,
  '25110727979',
  '220e67e4-8d81-487c-8d35-639c3ac03a6b',
  '8000970939',
  NULL,
  'pending',
  NULL,
  '2026-01-01T16:39:32'
);

INSERT INTO bills (id, property_id, renter_id, supplier_id, bill_type, description, amount, currency, due_date, bill_date, legal_name, iban, bill_number, extraction_pattern_id, contract_id, payment_details, status, source_email_id, created_at) VALUES (
  '4da8846b-dc0f-4222-9851-abeaf687dff8',
  'e06b83db-1331-4137-a687-3058b969ccae',
  NULL,
  NULL,
  'utilities',
  'Vodafone',
  44.58,
  'RON',
  '2025-12-22T00:00:00',
  NULL,
  NULL,
  'RO8971726',
  'Data emiterii şi Suma',
  '44bd3890-2d99-49d1-81cb-ec428e99bf9b',
  '271768784',
  NULL,
  'overdue',
  NULL,
  '2026-01-02T09:09:59'
);

INSERT INTO bills (id, property_id, renter_id, supplier_id, bill_type, description, amount, currency, due_date, bill_date, legal_name, iban, bill_number, extraction_pattern_id, contract_id, payment_details, status, source_email_id, created_at) VALUES (
  '07ab4844-c4ec-4c10-a3fb-5d431ba51466',
  'e06b83db-1331-4137-a687-3058b969ccae',
  '5090eafa-f0b3-46d3-804e-06bffb59f37a',
  NULL,
  'rent',
  'Chirie',
  405.0,
  'EUR',
  '2026-01-10T00:00:00',
  NULL,
  NULL,
  NULL,
  '1',
  NULL,
  NULL,
  NULL,
  'pending',
  NULL,
  '2026-01-03T17:44:42'
);

INSERT INTO bills (id, property_id, renter_id, supplier_id, bill_type, description, amount, currency, due_date, bill_date, legal_name, iban, bill_number, extraction_pattern_id, contract_id, payment_details, status, source_email_id, created_at) VALUES (
  '5b47e7a6-8682-4e6e-8ed2-02c489774d12',
  '1305a3b8-2509-4cf4-a93a-fe9a868de4c6',
  'bf153da6-17f3-4146-ba80-54fd9ece7621',
  NULL,
  'rent',
  'Chirie',
  170.0,
  'EUR',
  '2026-01-10T00:00:00',
  NULL,
  NULL,
  NULL,
  '1',
  NULL,
  NULL,
  NULL,
  'pending',
  NULL,
  '2026-01-03T17:44:42'
);

INSERT INTO bills (id, property_id, renter_id, supplier_id, bill_type, description, amount, currency, due_date, bill_date, legal_name, iban, bill_number, extraction_pattern_id, contract_id, payment_details, status, source_email_id, created_at) VALUES (
  'fd083dd1-34b6-47ec-92a6-6a7f61f8f78b',
  '1305a3b8-2509-4cf4-a93a-fe9a868de4c6',
  '8d9225f3-9d5d-4961-b6e4-2cbb0a4a16ff',
  NULL,
  'rent',
  'Chirie',
  360.0,
  'EUR',
  '2026-01-20T00:00:00',
  NULL,
  NULL,
  NULL,
  '1',
  NULL,
  NULL,
  NULL,
  'pending',
  NULL,
  '2026-01-03T17:44:42'
);

INSERT INTO bills (id, property_id, renter_id, supplier_id, bill_type, description, amount, currency, due_date, bill_date, legal_name, iban, bill_number, extraction_pattern_id, contract_id, payment_details, status, source_email_id, created_at) VALUES (
  '07825261-1d0e-47b5-95ee-25d66600807f',
  '1305a3b8-2509-4cf4-a93a-fe9a868de4c6',
  NULL,
  NULL,
  'ebloc',
  'E-bloc',
  0.0,
  'RON',
  '2026-01-03T23:16:34',
  NULL,
  NULL,
  NULL,
  'Octombrie 2025 Ap.25',
  NULL,
  '141936',
  NULL,
  'paid',
  NULL,
  '2026-01-03T23:17:03'
);

INSERT INTO bills (id, property_id, renter_id, supplier_id, bill_type, description, amount, currency, due_date, bill_date, legal_name, iban, bill_number, extraction_pattern_id, contract_id, payment_details, status, source_email_id, created_at) VALUES (
  '486755c0-3645-4354-8ca0-06184fd325fe',
  'e06b83db-1331-4137-a687-3058b969ccae',
  NULL,
  NULL,
  'ebloc',
  'E-bloc',
  0.0,
  'RON',
  '2026-01-03T23:16:16',
  NULL,
  NULL,
  NULL,
  'Octombrie 2025 Ap.8',
  NULL,
  '68210',
  NULL,
  'paid',
  NULL,
  '2026-01-03T23:17:03'
);

INSERT INTO bills (id, property_id, renter_id, supplier_id, bill_type, description, amount, currency, due_date, bill_date, legal_name, iban, bill_number, extraction_pattern_id, contract_id, payment_details, status, source_email_id, created_at) VALUES (
  '728b974d-a8f7-44f6-bad3-82e028e79f88',
  'a3b56669-a657-481c-b57f-52fd94f1d7e4',
  NULL,
  NULL,
  'utilities',
  'Hidroelectrica',
  155.58,
  'RON',
  '2026-01-30T00:00:00',
  NULL,
  NULL,
  NULL,
  '25110944550',
  '220e67e4-8d81-487c-8d35-639c3ac03a6b',
  '8000324423',
  NULL,
  'pending',
  NULL,
  '2026-01-03T23:17:03'
);

INSERT INTO bills (id, property_id, renter_id, supplier_id, bill_type, description, amount, currency, due_date, bill_date, legal_name, iban, bill_number, extraction_pattern_id, contract_id, payment_details, status, source_email_id, created_at) VALUES (
  '02416db0-5d62-451d-9f55-9472556c7b2e',
  'a3b56669-a657-481c-b57f-52fd94f1d7e4',
  NULL,
  NULL,
  'ebloc',
  'E-Bloc',
  0.0,
  'RON',
  '2026-01-04T09:07:47',
  NULL,
  NULL,
  NULL,
  'Noiembrie 2025 Ap.53',
  NULL,
  'A000000',
  NULL,
  'paid',
  NULL,
  '2026-01-04T09:08:20'
);

INSERT INTO bills (id, property_id, renter_id, supplier_id, bill_type, description, amount, currency, due_date, bill_date, legal_name, iban, bill_number, extraction_pattern_id, contract_id, payment_details, status, source_email_id, created_at) VALUES (
  'f2e4585a-fb3c-4c1f-b197-851a489d27c2',
  '7b590e84-affd-4310-962d-d889c42ed137',
  'bf8888dc-be1d-401a-8609-54c944401cab',
  NULL,
  'rent',
  'Chirie',
  250.0,
  'EUR',
  '2026-02-01T00:00:00',
  NULL,
  NULL,
  NULL,
  '2',
  NULL,
  NULL,
  NULL,
  'pending',
  NULL,
  '2026-01-04T19:42:22'
);

INSERT INTO bills (id, property_id, renter_id, supplier_id, bill_type, description, amount, currency, due_date, bill_date, legal_name, iban, bill_number, extraction_pattern_id, contract_id, payment_details, status, source_email_id, created_at) VALUES (
  'b7bcfd92-4b91-4ff2-a259-660a2d071fa2',
  'e06b83db-1331-4137-a687-3058b969ccae',
  NULL,
  NULL,
  'utilities',
  'Engie',
  234.01,
  'RON',
  '2026-01-19T00:00:00',
  NULL,
  NULL,
  'RO40RZBR0000060010660361',
  '11803290532',
  NULL,
  '4001941859',
  NULL,
  'pending',
  NULL,
  '2026-01-05T17:25:04'
);

INSERT INTO bills (id, property_id, renter_id, supplier_id, bill_type, description, amount, currency, due_date, bill_date, legal_name, iban, bill_number, extraction_pattern_id, contract_id, payment_details, status, source_email_id, created_at) VALUES (
  '88b2dde8-3d6f-4cb6-b99e-d496d89f51f7',
  'b2c07414-e2bb-4515-b568-5f3dd596f14d',
  NULL,
  NULL,
  'utilities',
  'e-bloc',
  144.02,
  'RON',
  '2026-01-11T00:00:00',
  NULL,
  NULL,
  'RO41UGBI0000622002421RON',
  'NOIEMBRIE 2025',
  NULL,
  'A1FA387',
  NULL,
  'pending',
  NULL,
  '2026-01-05T21:18:54'
);

INSERT INTO bills (id, property_id, renter_id, supplier_id, bill_type, description, amount, currency, due_date, bill_date, legal_name, iban, bill_number, extraction_pattern_id, contract_id, payment_details, status, source_email_id, created_at) VALUES (
  '0e3ee8af-ac50-4bca-bae7-5106f0f08e4b',
  'a3b56669-a657-481c-b57f-52fd94f1d7e4',
  'f938c711-3209-49df-8580-13f9c96b9fbf',
  NULL,
  'rent',
  'Chirie',
  460.0,
  'EUR',
  '2026-01-25T00:00:00',
  NULL,
  NULL,
  NULL,
  '1',
  NULL,
  NULL,
  NULL,
  'pending',
  NULL,
  '2026-01-06T14:20:19'
);

INSERT INTO bills (id, property_id, renter_id, supplier_id, bill_type, description, amount, currency, due_date, bill_date, legal_name, iban, bill_number, extraction_pattern_id, contract_id, payment_details, status, source_email_id, created_at) VALUES (
  'a9b58180-e7cd-40c7-8f02-57df9011dd2e',
  '1305a3b8-2509-4cf4-a93a-fe9a868de4c6',
  NULL,
  NULL,
  'utilities',
  'e-bloc',
  1125.0,
  'RON',
  '2026-02-05T00:00:00',
  NULL,
  NULL,
  'RO40RNCB0089003747230001',
  'NOIEMBRIE 2025',
  NULL,
  'A4F80C5',
  NULL,
  'pending',
  NULL,
  '2026-01-06T15:04:40'
);

INSERT INTO bills (id, property_id, renter_id, supplier_id, bill_type, description, amount, currency, due_date, bill_date, legal_name, iban, bill_number, extraction_pattern_id, contract_id, payment_details, status, source_email_id, created_at) VALUES (
  '7ac330e4-491a-40a0-93d2-85750ad5acff',
  'b2c07414-e2bb-4515-b568-5f3dd596f14d',
  NULL,
  '07b31939-5944-4f5e-b982-5ee9e1dd1e67',
  'utilities',
  'Engie',
  29.67,
  'RON',
  '2026-01-12T00:00:00',
  NULL,
  NULL,
  'RO23RZBR0000060011419498',
  '70900452673 din',
  'engie',
  '115335242,',
  NULL,
  'pending',
  NULL,
  '2026-01-07T16:32:47'
);

-- Payments (1 records)
INSERT INTO payments (id, bill_id, amount, method, status, commission, created_at) VALUES (
  'd20b5ab3-eda8-434c-9333-66a4c9574926',
  '9ae952c1-ae7b-444f-ad18-b0f72fd21294',
  769.46,
  'payment_service',
  'pending',
  15.3892,
  '2026-01-04T20:05:33'
);

-- User Supplier Credentials (2 records)
INSERT INTO user_supplier_credentials (id, user_id, supplier_id, username, password_hash, created_at, updated_at) VALUES (
  '7b180f8c-b3b1-492e-ac5a-7b0365672037',
  '57ca9597-6a30-4775-bc89-71243d828a98',
  '1e0537e9-4242-4e5e-82e2-6fad9e08494f',
  'gAAAAABpVQb1sTBCQJ7M0G3SfMmUVaHvz2YXwU4GoOm73uW1SKeVY-l2vVwzHGtwHK9A9nqmRsYpxLzyPhAuRZ_zQ8Ofr_4xgic7YmM2QeodpfhJov8SnKY=',
  'gAAAAABpVQb1SHCR0f8csh9oVW7SFllB0zp9uCLsheU-PF6e5g-2LYiv266db7g9d4W8h3AkBZdH0dfHSCqkZulfEiE80v6c_g==',
  '2025-12-31T11:20:21',
  '2025-12-31T11:20:21'
);

INSERT INTO user_supplier_credentials (id, user_id, supplier_id, username, password_hash, created_at, updated_at) VALUES (
  '032de471-3e86-4361-8d83-7525b42cdd7c',
  '57ca9597-6a30-4775-bc89-71243d828a98',
  'dc09419b-212a-4e3d-914e-17f083911fc5',
  'gAAAAABpVTbRWBdSU0lnLYDVcVMewEdGgNe2FMHa6gtPAhX7E8z0LbNQugMrv318urg3Ndi_rbszPYz5Mqfc8z0zpIIocA0TWw==',
  'gAAAAABpVTbRNSnYWSpI5ds2UkoyfTnI4FfEIiZi9V7cLNjRI1Oq5UA19SYVMAEyafNCxUn5OGUiFI_32R0uEhnoyiWfIGy2bQ==',
  '2025-12-31T14:44:34',
  '2025-12-31T14:44:34'
);

-- Property Suppliers (19 records)
INSERT INTO property_suppliers (id, property_id, supplier_id, credential_id, contract_id, direct_debit, created_at, updated_at) VALUES (
  '8ae4fd2e-7827-4652-af89-9b7f2dbd43e0',
  '1305a3b8-2509-4cf4-a93a-fe9a868de4c6',
  '1e0537e9-4242-4e5e-82e2-6fad9e08494f',
  '7b180f8c-b3b1-492e-ac5a-7b0365672037',
  '141936',
  0,
  '2025-12-31T11:20:21',
  '2025-12-31T11:20:21'
);

INSERT INTO property_suppliers (id, property_id, supplier_id, credential_id, contract_id, direct_debit, created_at, updated_at) VALUES (
  'e673d0ed-ba57-4352-8d65-a0a48cc31f3c',
  'a3b56669-a657-481c-b57f-52fd94f1d7e4',
  '00ca9f3c-93a9-40b0-940d-416739d12d6e',
  NULL,
  NULL,
  1,
  '2025-12-31T12:31:19',
  '2026-01-02T09:42:56'
);

INSERT INTO property_suppliers (id, property_id, supplier_id, credential_id, contract_id, direct_debit, created_at, updated_at) VALUES (
  '9e39ce60-a853-4947-8d45-db94aa965042',
  '1305a3b8-2509-4cf4-a93a-fe9a868de4c6',
  'dc09419b-212a-4e3d-914e-17f083911fc5',
  '032de471-3e86-4361-8d83-7525b42cdd7c',
  '8000970939',
  0,
  '2025-12-31T15:29:29',
  '2025-12-31T15:29:29'
);

INSERT INTO property_suppliers (id, property_id, supplier_id, credential_id, contract_id, direct_debit, created_at, updated_at) VALUES (
  '5a66e214-a50c-4d0b-aa5b-ba4cc999b177',
  '67dcfa6a-cbac-429d-a600-c66db6f8b4c5',
  'dc09419b-212a-4e3d-914e-17f083911fc5',
  '032de471-3e86-4361-8d83-7525b42cdd7c',
  '8000882523',
  1,
  '2025-12-31T15:31:11',
  '2026-01-02T09:49:15'
);

INSERT INTO property_suppliers (id, property_id, supplier_id, credential_id, contract_id, direct_debit, created_at, updated_at) VALUES (
  '669c2977-e40d-48ba-b4e4-db35723e311a',
  'a3b56669-a657-481c-b57f-52fd94f1d7e4',
  'dc09419b-212a-4e3d-914e-17f083911fc5',
  '032de471-3e86-4361-8d83-7525b42cdd7c',
  '8000324423',
  1,
  '2025-12-31T15:31:52',
  '2026-01-02T09:36:52'
);

INSERT INTO property_suppliers (id, property_id, supplier_id, credential_id, contract_id, direct_debit, created_at, updated_at) VALUES (
  'd148ae3c-0e59-40d7-b476-36fcdcb8e4ea',
  'e06b83db-1331-4137-a687-3058b969ccae',
  'dc09419b-212a-4e3d-914e-17f083911fc5',
  '032de471-3e86-4361-8d83-7525b42cdd7c',
  '8000324444',
  0,
  '2025-12-31T15:35:58',
  '2025-12-31T15:35:58'
);

INSERT INTO property_suppliers (id, property_id, supplier_id, credential_id, contract_id, direct_debit, created_at, updated_at) VALUES (
  '38fc9ea3-cb4c-4ae8-8dce-239f3fcf8ddb',
  '7b590e84-affd-4310-962d-d889c42ed137',
  'dc09419b-212a-4e3d-914e-17f083911fc5',
  '032de471-3e86-4361-8d83-7525b42cdd7c',
  '8000324406',
  1,
  '2025-12-31T16:01:21',
  '2026-01-02T09:43:52'
);

INSERT INTO property_suppliers (id, property_id, supplier_id, credential_id, contract_id, direct_debit, created_at, updated_at) VALUES (
  '9ee5decf-b072-4c91-8187-c9acced50d6c',
  'e06b83db-1331-4137-a687-3058b969ccae',
  '00ca9f3c-93a9-40b0-940d-416739d12d6e',
  NULL,
  NULL,
  0,
  '2026-01-02T09:09:47',
  '2026-01-02T09:09:47'
);

INSERT INTO property_suppliers (id, property_id, supplier_id, credential_id, contract_id, direct_debit, created_at, updated_at) VALUES (
  '6df0773b-4127-44d9-be4e-2045d6365633',
  'a3b56669-a657-481c-b57f-52fd94f1d7e4',
  'ee8a274b-837f-4d72-860e-5aad97487958',
  NULL,
  NULL,
  1,
  '2026-01-02T09:22:42',
  '2026-01-02T09:22:42'
);

INSERT INTO property_suppliers (id, property_id, supplier_id, credential_id, contract_id, direct_debit, created_at, updated_at) VALUES (
  '78ef93bb-4dad-43fe-9e32-75472b4ec672',
  '7b590e84-affd-4310-962d-d889c42ed137',
  'ee8a274b-837f-4d72-860e-5aad97487958',
  NULL,
  NULL,
  1,
  '2026-01-02T09:43:44',
  '2026-01-02T09:43:44'
);

INSERT INTO property_suppliers (id, property_id, supplier_id, credential_id, contract_id, direct_debit, created_at, updated_at) VALUES (
  'acf0a469-1602-486a-a392-1c0253f15119',
  '7b590e84-affd-4310-962d-d889c42ed137',
  'b6983cc9-8544-4560-b810-3e348f4bf7ed',
  NULL,
  NULL,
  1,
  '2026-01-02T09:48:17',
  '2026-01-02T09:48:17'
);

INSERT INTO property_suppliers (id, property_id, supplier_id, credential_id, contract_id, direct_debit, created_at, updated_at) VALUES (
  '782cb5b2-fb79-4ed2-99e2-6695800cb157',
  '67dcfa6a-cbac-429d-a600-c66db6f8b4c5',
  'ee8a274b-837f-4d72-860e-5aad97487958',
  NULL,
  NULL,
  1,
  '2026-01-02T09:48:56',
  '2026-01-02T09:48:56'
);

INSERT INTO property_suppliers (id, property_id, supplier_id, credential_id, contract_id, direct_debit, created_at, updated_at) VALUES (
  '08cea347-a648-4bd3-8be7-c696410e63ab',
  'e06b83db-1331-4137-a687-3058b969ccae',
  '5f923979-987f-4bb8-838b-786ee4e275ee',
  NULL,
  '4001941859',
  0,
  '2026-01-02T13:30:12',
  '2026-01-02T13:30:12'
);

INSERT INTO property_suppliers (id, property_id, supplier_id, credential_id, contract_id, direct_debit, created_at, updated_at) VALUES (
  '9a51e17a-0b57-471c-9bfa-f38683575962',
  '4351d460-63ae-4e9a-9bc7-65b792d77718',
  '1e0537e9-4242-4e5e-82e2-6fad9e08494f',
  '7b180f8c-b3b1-492e-ac5a-7b0365672037',
  NULL,
  0,
  '2026-01-03T16:35:26',
  '2026-01-03T16:35:26'
);

INSERT INTO property_suppliers (id, property_id, supplier_id, credential_id, contract_id, direct_debit, created_at, updated_at) VALUES (
  'f5ea83f7-daae-4879-aa84-100347f2ad41',
  'b2c07414-e2bb-4515-b568-5f3dd596f14d',
  '1e0537e9-4242-4e5e-82e2-6fad9e08494f',
  '7b180f8c-b3b1-492e-ac5a-7b0365672037',
  'A1FA387',
  0,
  '2026-01-03T20:06:21',
  '2026-01-03T20:06:21'
);

INSERT INTO property_suppliers (id, property_id, supplier_id, credential_id, contract_id, direct_debit, created_at, updated_at) VALUES (
  '8882643f-4def-4f8a-a6d8-f1ca49e83522',
  'a3b56669-a657-481c-b57f-52fd94f1d7e4',
  '1e0537e9-4242-4e5e-82e2-6fad9e08494f',
  '7b180f8c-b3b1-492e-ac5a-7b0365672037',
  '24477',
  0,
  '2026-01-03T20:45:54',
  '2026-01-03T20:45:54'
);

INSERT INTO property_suppliers (id, property_id, supplier_id, credential_id, contract_id, direct_debit, created_at, updated_at) VALUES (
  'afc58013-a26a-4273-9aac-d5c62dc8c37d',
  'e06b83db-1331-4137-a687-3058b969ccae',
  '1e0537e9-4242-4e5e-82e2-6fad9e08494f',
  '7b180f8c-b3b1-492e-ac5a-7b0365672037',
  'A54BB6E',
  0,
  '2026-01-03T20:46:07',
  '2026-01-03T20:46:07'
);

INSERT INTO property_suppliers (id, property_id, supplier_id, credential_id, contract_id, direct_debit, created_at, updated_at) VALUES (
  '491e0ee8-7c77-49bb-82da-0540381dc2fe',
  'b2c07414-e2bb-4515-b568-5f3dd596f14d',
  '5f923979-987f-4bb8-838b-786ee4e275ee',
  NULL,
  '4001585793',
  1,
  '2026-01-05T15:24:35',
  '2026-01-05T15:24:35'
);

INSERT INTO property_suppliers (id, property_id, supplier_id, credential_id, contract_id, direct_debit, created_at, updated_at) VALUES (
  'c47db48f-d2b1-4291-8f1c-9ad096ee061f',
  'b2c07414-e2bb-4515-b568-5f3dd596f14d',
  '07b31939-5944-4f5e-b982-5ee9e1dd1e67',
  NULL,
  '115335242,',
  1,
  '2026-01-05T17:59:40',
  '2026-01-05T17:59:51'
);

-- User Preferences (2 records)
INSERT INTO user_preferences (id, user_id, language, view_mode, rent_warning_days, rent_currency, bill_currency, date_format, phone_number, landlord_name, personal_email, iban, updated_at) VALUES (
  'c3c863d5-b123-41bb-aa97-0ef8afd42828',
  '57ca9597-6a30-4775-bc89-71243d828a98',
  'en',
  'grid',
  5,
  'EUR',
  'RON',
  'DD/Month/YYYY',
  '+40742755724',
  'Ionut Poclitaru',
  'pio.doi@gmail.com',
  'RO95RZBR0000060014291924',
  '2026-01-07T18:26:59'
);

INSERT INTO user_preferences (id, user_id, language, view_mode, rent_warning_days, rent_currency, bill_currency, date_format, phone_number, landlord_name, personal_email, iban, updated_at) VALUES (
  'fa216674-e5a1-4812-a31d-e4c38bdcd1f6',
  '748b8c6a-af3b-4328-b087-277a76d1c930',
  'ro',
  'grid',
  5,
  'EUR',
  'RON',
  'DD/MM/YYYY',
  NULL,
  NULL,
  'piodoi+ll@gmail.com',
  NULL,
  '2026-01-03T15:59:10'
);

-- Re-enable foreign key checks
PRAGMA foreign_keys = ON;

COMMIT;

-- Import complete!
-- Total tables: 9
-- Total records: 68
