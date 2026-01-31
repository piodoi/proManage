CREATE DATABASE  IF NOT EXISTS `ultrafinu_promanage` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `ultrafinu_promanage`;
-- MySQL dump 10.13  Distrib 8.0.44, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: ultrafinu_promanage
-- ------------------------------------------------------
-- Server version	8.0.44

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `bills`
--

DROP TABLE IF EXISTS `bills`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bills` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `property_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `renter_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `property_supplier_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bill_type` enum('rent','utilities','telecom','ebloc','other') COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `amount` float NOT NULL,
  `currency` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'RON',
  `due_date` datetime NOT NULL,
  `bill_date` datetime DEFAULT NULL,
  `legal_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iban` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bill_number` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `extraction_pattern_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contract_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `payment_details` text COLLATE utf8mb4_unicode_ci,
  `status` enum('pending','paid','overdue') COLLATE utf8mb4_unicode_ci DEFAULT 'pending',
  `source_email_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_bills_property` (`property_id`),
  KEY `idx_bills_renter` (`renter_id`),
  KEY `idx_bills_due_date` (`due_date`),
  KEY `idx_bills_status` (`status`),
  KEY `idx_bills_type` (`bill_type`),
  KEY `idx_bills_contract` (`contract_id`),
  KEY `idx_bills_property_due` (`property_id`,`due_date`),
  KEY `idx_bills_property_status` (`property_id`,`status`),
  KEY `idx_bills_property_supplier` (`property_supplier_id`),
  CONSTRAINT `bills_ibfk_1` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `bills`
--

LOCK TABLES `bills` WRITE;
/*!40000 ALTER TABLE `bills` DISABLE KEYS */;
INSERT INTO `bills` VALUES ('02416db0-5d62-451d-9f55-9472556c7b2e','a3b56669-a657-481c-b57f-52fd94f1d7e4',NULL,NULL,'ebloc','E-Bloc',0,'RON','2026-01-04 09:07:47',NULL,NULL,NULL,'Noiembrie 2025 Ap.53',NULL,'A000000',NULL,'paid',NULL,'2026-01-04 09:08:20'),('07ab4844-c4ec-4c10-a3fb-5d431ba51466','e06b83db-1331-4137-a687-3058b969ccae','5090eafa-f0b3-46d3-804e-06bffb59f37a',NULL,'rent','Ianuarie 2026',405,'EUR','2026-01-08 00:00:00',NULL,NULL,NULL,'01',NULL,NULL,NULL,'paid',NULL,'2026-01-03 17:44:42'),('1829b1fe-f11c-4a63-a9d7-90217ca50ffa','b2c07414-e2bb-4515-b568-5f3dd596f14d',NULL,'491e0ee8-7c77-49bb-82da-0540381dc2fe','utilities','Engie Gaze',184.74,'RON','2026-02-23 00:00:00','2026-01-23 00:00:00','ENGIE Romania S.A. Sediul social: B-dul Mărăşeşti nr. 4 -6, sector 4,','RO40RZBR0000060010660361','10619377681',NULL,'4001585793',NULL,'pending',NULL,'2026-01-23 22:04:03'),('1ae68411-37e7-4c05-88ff-0eb976eb2773','1305a3b8-2509-4cf4-a93a-fe9a868de4c6','8d9225f3-9d5d-4961-b6e4-2cbb0a4a16ff',NULL,'rent','February 2026',360,'EUR','2026-02-20 00:00:00',NULL,NULL,'RO95RZBR0000060014291924','02',NULL,NULL,NULL,'pending',NULL,'2026-01-22 08:03:36'),('20256aa9-c070-4ff2-bb9a-64deca91496c','a3b56669-a657-481c-b57f-52fd94f1d7e4',NULL,NULL,'telecom','Telekom',33.69,'RON','2026-01-30 00:00:00','2026-01-16 00:00:00','TELEKOM ROMANIA MOBILE COMMUNICATIONS SA',NULL,'260100433013','telekom','99170010871410',NULL,'paid',NULL,'2026-01-19 15:53:10'),('220a3077-d18a-4556-897c-fc6b822a172a','1305a3b8-2509-4cf4-a93a-fe9a868de4c6',NULL,NULL,'utilities','Hidroelectrica',124.68,'RON','2026-01-29 00:00:00',NULL,NULL,NULL,'25110727979','220e67e4-8d81-487c-8d35-639c3ac03a6b','8000970939',NULL,'paid',NULL,'2026-01-01 16:39:32'),('252cdf76-4e39-4af0-b89b-f7fc1180b302','5ad35b8e-e254-435b-bfbc-be5f3777a2dc',NULL,NULL,'utilities','Digi',30.5,'RON','2026-01-31 00:00:00',NULL,NULL,'RO51INGB0001000000018827','14743845','digi',NULL,NULL,'pending',NULL,'2026-01-09 16:31:28'),('2c1e45e0-bf41-44a9-9361-1f24bdb3a71f','a3b56669-a657-481c-b57f-52fd94f1d7e4',NULL,'669c2977-e40d-48ba-b4e4-db35723e311a','utilities','Hidroelectrica',177.02,'RON','2026-03-09 00:00:00','2026-01-22 00:00:00','SPEEH HIDROELECTRICA SA','RO63RNCB0072018331870495','26100303567',NULL,'8000324423',NULL,'pending',NULL,'2026-01-23 06:55:25'),('3e92a215-0157-4f00-b300-1e13593d5b1c','e06b83db-1331-4137-a687-3058b969ccae',NULL,NULL,'utilities','Hidroelectrica',31.27,'RON','2026-01-30 00:00:00',NULL,NULL,NULL,'25110944560','220e67e4-8d81-487c-8d35-639c3ac03a6b','8000324444',NULL,'paid',NULL,'2026-01-01 15:56:46'),('45e5442b-d715-4c9f-99fc-b4c72775178a','e06b83db-1331-4137-a687-3058b969ccae',NULL,'afc58013-a26a-4273-9aac-d5c62dc8c37d','ebloc','E-bloc',148.43,'RON','2026-01-30 00:00:00','2026-01-12 00:00:00','sociatia de Proprietari Aleea Mizil Nr. 57','RO86INGB0000999909534657','NOIEMBRIE 2025',NULL,'A54BB6E',NULL,'paid',NULL,'2026-01-12 19:00:11'),('486755c0-3645-4354-8ca0-06184fd325fe','e06b83db-1331-4137-a687-3058b969ccae',NULL,NULL,'ebloc','E-bloc',139.54,'RON','2026-01-01 00:00:00',NULL,NULL,NULL,'Octombrie 2025 Ap.8',NULL,'68210',NULL,'paid',NULL,'2026-01-03 23:17:03'),('49b40785-5d6b-4d45-b972-a7b2988aaf78','b2c07414-e2bb-4515-b568-5f3dd596f14d','dd205ad6-b2da-413e-957b-af790c7798d8',NULL,'rent','February 2026',360,'EUR','2026-02-01 00:00:00',NULL,NULL,'RO95RZBR0000060014291924','02',NULL,NULL,NULL,'pending',NULL,'2026-01-09 17:40:13'),('4be40050-0763-4cbd-b5e9-2ea5b3292220','e06b83db-1331-4137-a687-3058b969ccae',NULL,'08cea347-a648-4bd3-8be7-c696410e63ab','utilities','Engie Gaze',305.6,'RON','2026-02-23 00:00:00','2026-01-22 00:00:00','ENGIE Romania S.A. Sediul social: B-dul Mărăşeşti nr. 4 -6, sector 4,','RO40RZBR0000060010660361','10325235949','engie.gaz','4001941859',NULL,'paid',NULL,'2026-01-23 10:52:11'),('51e5c416-c514-4255-9900-fc11382d5d05','5ad35b8e-e254-435b-bfbc-be5f3777a2dc',NULL,'07ecbc7b-5885-40eb-b596-e34ed33adb3b','utilities','Hidroelectrica',1013.98,'RON','2026-03-09 00:00:00','2026-01-22 00:00:00','SPEEH HIDROELECTRICA SA','RO63RNCB0072018331870495','26100572475','hidroelectrica','8000882523',NULL,'pending',NULL,'2026-01-23 07:15:30'),('6565967d-80f4-491f-aa45-1026bbc75648','e06b83db-1331-4137-a687-3058b969ccae',NULL,NULL,'other','Vodafone',44.65,'RON','2026-01-21 00:00:00',NULL,NULL,'RO23INGB0001000000000222','VDF760317168','vodafone','271768784',NULL,'paid',NULL,'2026-01-09 18:07:11'),('68348cfa-1270-46a1-a087-7f19f0102929','a3b56669-a657-481c-b57f-52fd94f1d7e4',NULL,'8882643f-4def-4f8a-a6d8-f1ca49e83522','ebloc','e-bloc',574.77,'RON','2026-02-15 00:00:00','2026-01-26 00:00:00','Asociatia de Proprietari Bloc M6','RO71CECEB30834RON0330402','DECEMBRIE 2025',NULL,NULL,NULL,'pending',NULL,'2026-01-27 12:10:01'),('728b974d-a8f7-44f6-bad3-82e028e79f88','a3b56669-a657-481c-b57f-52fd94f1d7e4',NULL,NULL,'utilities','Hidroelectrica',155.58,'RON','2026-01-30 00:00:00',NULL,NULL,NULL,'25110944550','220e67e4-8d81-487c-8d35-639c3ac03a6b','8000324423',NULL,'paid',NULL,'2026-01-03 23:17:03'),('754b5204-67f0-4c12-a10a-a0c0f9fcbee0','b2c07414-e2bb-4515-b568-5f3dd596f14d',NULL,'c47db48f-d2b1-4291-8f1c-9ad096ee061f','utilities','Engie',29.67,'RON','2026-02-18 00:00:00','2026-01-19 00:00:00','ENGIE Romania S.A.','RO23RZBR0000060011419498','70900478766','engie','115335242,',NULL,'paid',NULL,'2026-01-20 18:48:37'),('7ac330e4-491a-40a0-93d2-85750ad5acff','b2c07414-e2bb-4515-b568-5f3dd596f14d',NULL,'07b31939-5944-4f5e-b982-5ee9e1dd1e67','utilities','Engie',29.67,'RON','2026-01-11 00:00:00',NULL,NULL,'RO23RZBR0000060011419498','70900452673 din','engie','115335242,',NULL,'paid',NULL,'2026-01-07 16:32:47'),('82241e5a-644d-4fe2-9584-a6050c610071','e06b83db-1331-4137-a687-3058b969ccae',NULL,'d148ae3c-0e59-40d7-b476-36fcdcb8e4ea','utilities','Hidroelectrica',77.25,'RON','2026-03-09 00:00:00','2026-01-22 00:00:00','SPEEH HIDROELECTRICA SA','RO63RNCB0072018331870495','26100303568','hidroelectrica','8000324444',NULL,'paid',NULL,'2026-01-23 10:46:42'),('88b2dde8-3d6f-4cb6-b99e-d496d89f51f7','b2c07414-e2bb-4515-b568-5f3dd596f14d',NULL,'f5ea83f7-daae-4879-aa84-100347f2ad41','utilities','E-bloc',144.02,'RON','2026-01-05 00:00:00',NULL,NULL,'RO41UGBI0000622002421RON','NOIEMBRIE 2025',NULL,'A1FA387',NULL,'paid',NULL,'2026-01-05 21:18:54'),('95df5fda-7bff-4cb8-9dfd-30707eb892ac','a3b56669-a657-481c-b57f-52fd94f1d7e4','f938c711-3209-49df-8580-13f9c96b9fbf',NULL,'rent','February 2026',460,'EUR','2026-02-25 00:00:00',NULL,NULL,'RO95RZBR0000060014291924','02',NULL,NULL,NULL,'pending',NULL,'2026-01-27 12:09:23'),('9ea781a3-c727-4730-b069-8539661fd10c','7b590e84-affd-4310-962d-d889c42ed137',NULL,NULL,'utilities','Digi',108.75,'RON','2026-01-31 00:00:00',NULL,NULL,'RO51INGB0001000000018827','14744500','digi',NULL,NULL,'pending',NULL,'2026-01-09 16:32:35'),('9f4ed386-8d52-4703-9cd6-9d6d5930e25a','7b590e84-affd-4310-962d-d889c42ed137',NULL,'38fc9ea3-cb4c-4ae8-8dce-239f3fcf8ddb','utilities','Hidroelectrica',1046.5,'RON','2026-03-09 00:00:00','2026-01-21 00:00:00','SPEEH HIDROELECTRICA SA','RO63RNCB0072018331870495','26100143344',NULL,'8000324406',NULL,'pending',NULL,'2026-01-22 08:03:56'),('a3dec734-6bdb-4ed8-9adc-fb43589eec63','a3b56669-a657-481c-b57f-52fd94f1d7e4','f938c711-3209-49df-8580-13f9c96b9fbf',NULL,'rent','January 2026',460,'EUR','2026-01-25 00:00:00',NULL,NULL,'RO95RZBR0000060014291924','01',NULL,NULL,NULL,'paid',NULL,'2026-01-09 21:03:56'),('a55e6f38-0678-4547-8307-465633064f13','1305a3b8-2509-4cf4-a93a-fe9a868de4c6','bf153da6-17f3-4146-ba80-54fd9ece7621',NULL,'rent','February 2026',170,'EUR','2026-02-10 00:00:00',NULL,NULL,'RO95RZBR0000060014291924','02',NULL,NULL,NULL,'pending',NULL,'2026-01-11 09:28:04'),('a5d2ab8d-596d-4583-a9b3-32521e4bb8ff','7b590e84-affd-4310-962d-d889c42ed137',NULL,'46286284-b44b-442c-bd6a-89737d3a4a6a','utilities','PPC Gaze',265.51,'RON','2026-01-08 00:00:00','2025-12-23 00:00:00','PPC Energie S.A.','RO45','93000445050','ppc.gaz','PEYIFCERN053002',NULL,'paid',NULL,'2026-01-12 17:42:08'),('a9b58180-e7cd-40c7-8f02-57df9011dd2e','1305a3b8-2509-4cf4-a93a-fe9a868de4c6',NULL,NULL,'utilities','e-bloc',1125,'RON','2026-02-05 00:00:00',NULL,NULL,'RO40RNCB0089003747230001','NOIEMBRIE 2025',NULL,'A4F80C5',NULL,'paid',NULL,'2026-01-06 15:04:40'),('a9dfa98c-a033-4a4d-a10d-971d2e82a7a6','1305a3b8-2509-4cf4-a93a-fe9a868de4c6','bf153da6-17f3-4146-ba80-54fd9ece7621',NULL,'rent','January 2026',170,'EUR','2026-01-10 00:00:00',NULL,NULL,'RO95RZBR0000060014291924','01',NULL,NULL,NULL,'paid',NULL,'2026-01-09 21:03:56'),('ac0a2a03-e25e-4f0f-b775-bd99a8135d46','7b590e84-affd-4310-962d-d889c42ed137',NULL,'dc09419b-212a-4e3d-914e-17f083911fc5','utilities','Hidroelectrica',769.46,'RON','2026-01-26 00:00:00',NULL,'SPEEH HIDROELECTRICA SA','RO63RNCB0072018331870495','25110487592',NULL,'8000324406',NULL,'paid',NULL,'2026-01-09 20:33:14'),('b7bcfd92-4b91-4ff2-a259-660a2d071fa2','e06b83db-1331-4137-a687-3058b969ccae',NULL,NULL,'utilities','Engie',234.01,'RON','2026-01-19 00:00:00',NULL,NULL,'RO40RZBR0000060010660361','11803290532',NULL,'4001941859',NULL,'paid',NULL,'2026-01-05 17:25:04'),('b9898d7f-4a38-420e-a2ab-a1d934703e91','e06b83db-1331-4137-a687-3058b969ccae','5090eafa-f0b3-46d3-804e-06bffb59f37a',NULL,'rent','February 2026',405,'EUR','2026-02-10 00:00:00',NULL,NULL,'RO95RZBR0000060014291924','02',NULL,NULL,NULL,'pending',NULL,'2026-01-09 18:34:54'),('c7d93cab-dea8-4e5a-9495-fd3043d97e3b','b2c07414-e2bb-4515-b568-5f3dd596f14d',NULL,'f5ea83f7-daae-4879-aa84-100347f2ad41','ebloc','e-bloc',152.5,'RON','2026-02-11 00:00:00','2026-01-14 00:00:00','sociatia de Proprietari Str. Spineni Nr.1','RO41UGBI0000622002421RON','DECEMBRIE 2025',NULL,'A1FA387',NULL,'paid',NULL,'2026-01-18 15:06:47'),('d2da377d-df7b-498c-82e4-57ceaab4889f','7b590e84-affd-4310-962d-d889c42ed137','f58e0f67-8eec-4472-8696-11aa333a5ae2',NULL,'rent','February 2026',10,'EUR','2026-02-01 00:00:00',NULL,NULL,'RO95RZBR0000060014291924','02',NULL,NULL,NULL,'pending',NULL,'2026-01-27 12:09:23'),('d870a1ec-06b5-466f-9a9c-f6ca22e9d458','b2c07414-e2bb-4515-b568-5f3dd596f14d',NULL,'491e0ee8-7c77-49bb-82da-0540381dc2fe','utilities','Engie Gaze',172.12,'RON','2026-01-22 00:00:00','2025-12-23 00:00:00','ENGIE Romania S.A. Sediul social: B-dul Mărăşeşti nr. 4 -6, sector 4,','RO40RZBR0000060010660361','11117929360','engie.gaz','4001585793',NULL,'paid',NULL,'2026-01-10 21:02:23'),('e8883020-9209-4cf5-8c01-cc924fa499f8','1305a3b8-2509-4cf4-a93a-fe9a868de4c6','8d9225f3-9d5d-4961-b6e4-2cbb0a4a16ff',NULL,'rent','January 2026',360,'EUR','2026-01-20 00:00:00',NULL,NULL,'RO95RZBR0000060014291924','01',NULL,NULL,NULL,'overdue',NULL,'2026-01-09 21:03:56'),('fde3a621-c844-4cf0-bf10-4c8064c00c89','a3b56669-a657-481c-b57f-52fd94f1d7e4',NULL,NULL,'telecom','Telekom',45.83,'RON','2025-12-30 00:00:00','2025-12-16 00:00:00','TELEKOM ROMANIA MOBILE COMMUNICATIONS SA',NULL,'250108897932','telekom','99170010871410',NULL,'paid',NULL,'2026-01-12 18:34:26'),('fe50c97c-703a-490b-85ba-14a976792405','1305a3b8-2509-4cf4-a93a-fe9a868de4c6',NULL,'9e39ce60-a853-4947-8d45-db94aa965042','utilities','Hidroelectrica',141.65,'RON','2026-03-09 00:00:00','2026-01-22 00:00:00','SPEEH HIDROELECTRICA SA','RO63RNCB0072018331870495','26100588699',NULL,'8000970939',NULL,'pending',NULL,'2026-01-23 07:04:39');
/*!40000 ALTER TABLE `bills` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `payment_notifications`
--

DROP TABLE IF EXISTS `payment_notifications`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `payment_notifications` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `bill_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `renter_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `landlord_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `amount` float NOT NULL,
  `currency` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'RON',
  `status` enum('pending','confirmed','rejected') COLLATE utf8mb4_unicode_ci DEFAULT 'pending',
  `renter_note` text COLLATE utf8mb4_unicode_ci COMMENT 'Optional note from renter about the payment',
  `landlord_note` text COLLATE utf8mb4_unicode_ci COMMENT 'Optional note from landlord when confirming/rejecting',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `confirmed_at` datetime DEFAULT NULL COMMENT 'When landlord confirmed or rejected',
  `amount_in_bill_currency` double DEFAULT NULL,
  `bill_currency` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `idx_pn_bill` (`bill_id`),
  KEY `idx_pn_renter` (`renter_id`),
  KEY `idx_pn_landlord` (`landlord_id`),
  KEY `idx_pn_status` (`status`),
  KEY `idx_pn_created` (`created_at`),
  KEY `idx_pn_landlord_status` (`landlord_id`,`status`),
  CONSTRAINT `payment_notifications_ibfk_1` FOREIGN KEY (`bill_id`) REFERENCES `bills` (`id`) ON DELETE CASCADE,
  CONSTRAINT `payment_notifications_ibfk_2` FOREIGN KEY (`renter_id`) REFERENCES `renters` (`id`) ON DELETE CASCADE,
  CONSTRAINT `payment_notifications_ibfk_3` FOREIGN KEY (`landlord_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `payment_notifications`
--

LOCK TABLES `payment_notifications` WRITE;
/*!40000 ALTER TABLE `payment_notifications` DISABLE KEYS */;
INSERT INTO `payment_notifications` VALUES ('16055de0-9122-4b83-9118-b6ebf7269c2c','e8883020-9209-4cf5-8c01-cc924fa499f8','8d9225f3-9d5d-4961-b6e4-2cbb0a4a16ff','57ca9597-6a30-4775-bc89-71243d828a98',700,'RON','confirmed',NULL,NULL,'2026-01-22 19:01:07','2026-01-22 19:01:29',137,'EUR'),('a2720e5b-0f38-4c4b-aa92-71e95444bae9','a3dec734-6bdb-4ed8-9adc-fb43589eec63','f938c711-3209-49df-8580-13f9c96b9fbf','57ca9597-6a30-4775-bc89-71243d828a98',2372,'RON','confirmed',NULL,NULL,'2026-01-22 18:41:26','2026-01-22 18:41:45',466,'EUR');
/*!40000 ALTER TABLE `payment_notifications` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `properties`
--

DROP TABLE IF EXISTS `properties`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `properties` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `landlord_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `address` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_properties_landlord` (`landlord_id`),
  KEY `idx_properties_name` (`name`),
  CONSTRAINT `properties_ibfk_1` FOREIGN KEY (`landlord_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `properties`
--

LOCK TABLES `properties` WRITE;
/*!40000 ALTER TABLE `properties` DISABLE KEYS */;
INSERT INTO `properties` VALUES ('1305a3b8-2509-4cf4-a93a-fe9a868de4c6','57ca9597-6a30-4775-bc89-71243d828a98','Str. Plutonier Radu Gheorghe Sc: A Ap: 25','Str. Plutonier Radu Gheorghe','2025-12-31 11:20:21'),('3e404c0f-2361-48c7-b2b8-45d7e7cf3964','748b8c6a-af3b-4328-b087-277a76d1c930','Home','First','2026-01-03 16:46:43'),('5ad35b8e-e254-435b-bfbc-be5f3777a2dc','57ca9597-6a30-4775-bc89-71243d828a98','1 Decembrie Nr 17','Loc Joaca','2026-01-08 11:51:35'),('7b590e84-affd-4310-962d-d889c42ed137','57ca9597-6a30-4775-bc89-71243d828a98','Vlad Tepes 97, Tanganu Ilfov','Vlad Tepes 97','2025-12-31 15:27:03'),('829f0dc3-f009-42a5-b488-4e257b7a6626','68459987-46aa-45b3-9344-919321993eda','home','test ','2026-01-17 20:58:45'),('a3b56669-a657-481c-b57f-52fd94f1d7e4','57ca9597-6a30-4775-bc89-71243d828a98','Strada Trapezului nr.2 Bl: M6 Sc: 2 Ap: 53','Strada Trapezului nr.2','2025-12-31 11:20:21'),('b2c07414-e2bb-4515-b568-5f3dd596f14d','57ca9597-6a30-4775-bc89-71243d828a98','Spineni nr.1, sector 4,Bucuresti Sc: A Ap: 5','Spineni nr.1, sector 4,Bucuresti','2025-12-31 11:20:21'),('e06b83db-1331-4137-a687-3058b969ccae','57ca9597-6a30-4775-bc89-71243d828a98','Str. Mizil nr.57 Sc: C2/1 Ap: 8','Str. Mizil nr.57','2025-12-31 11:20:21');
/*!40000 ALTER TABLE `properties` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `property_suppliers`
--

DROP TABLE IF EXISTS `property_suppliers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `property_suppliers` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `property_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `supplier_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `extraction_pattern_supplier` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contract_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `direct_debit` tinyint(1) DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_ps_property_supplier` (`property_id`,`supplier_id`),
  KEY `idx_ps_property` (`property_id`),
  KEY `idx_ps_supplier` (`supplier_id`),
  KEY `idx_ps_contract` (`contract_id`),
  KEY `idx_ps_extraction_pattern` (`extraction_pattern_supplier`),
  CONSTRAINT `property_suppliers_ibfk_1` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE CASCADE,
  CONSTRAINT `property_suppliers_ibfk_2` FOREIGN KEY (`supplier_id`) REFERENCES `suppliers` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `property_suppliers`
--

LOCK TABLES `property_suppliers` WRITE;
/*!40000 ALTER TABLE `property_suppliers` DISABLE KEYS */;
INSERT INTO `property_suppliers` VALUES ('03163082-a1c0-4791-9f0d-5eece8c383b4','3e404c0f-2361-48c7-b2b8-45d7e7cf3964','f9363812-3e73-4edb-b26f-af721cfdefc6',NULL,NULL,0,'2026-01-17 22:09:15','2026-01-18 00:09:15'),('07ecbc7b-5885-40eb-b596-e34ed33adb3b','5ad35b8e-e254-435b-bfbc-be5f3777a2dc','dc09419b-212a-4e3d-914e-17f083911fc5',NULL,'8000882523',1,'2026-01-08 11:52:16','2026-01-23 09:15:30'),('08cea347-a648-4bd3-8be7-c696410e63ab','e06b83db-1331-4137-a687-3058b969ccae','5f923979-987f-4bb8-838b-786ee4e275ee',NULL,'4001941859',0,'2026-01-02 13:30:12','2026-01-02 13:30:12'),('31aa645e-6304-45cd-8f61-a5c353a3e80c','3e404c0f-2361-48c7-b2b8-45d7e7cf3964','1e0537e9-4242-4e5e-82e2-6fad9e08494f',NULL,NULL,0,'2026-01-17 22:09:36','2026-01-18 00:09:36'),('38fc9ea3-cb4c-4ae8-8dce-239f3fcf8ddb','7b590e84-affd-4310-962d-d889c42ed137','dc09419b-212a-4e3d-914e-17f083911fc5',NULL,'8000324406',1,'2025-12-31 16:01:21','2026-01-02 09:43:52'),('3a68da95-4bf8-4fb9-bd79-91385e9f8b2d','829f0dc3-f009-42a5-b488-4e257b7a6626','07b31939-5944-4f5e-b982-5ee9e1dd1e67',NULL,NULL,0,'2026-01-17 21:02:24','2026-01-17 23:02:24'),('4505eb45-fe60-456c-8dea-87c6d731c120','3e404c0f-2361-48c7-b2b8-45d7e7cf3964','5f923979-987f-4bb8-838b-786ee4e275ee',NULL,NULL,0,'2026-01-17 22:09:09','2026-01-18 00:09:09'),('46286284-b44b-442c-bd6a-89737d3a4a6a','7b590e84-affd-4310-962d-d889c42ed137','0','PPC Energie S.A.','PEYIFCERN053002',1,'2026-01-10 13:55:47','2026-01-11 15:45:20'),('491e0ee8-7c77-49bb-82da-0540381dc2fe','b2c07414-e2bb-4515-b568-5f3dd596f14d','5f923979-987f-4bb8-838b-786ee4e275ee',NULL,'4001585793',1,'2026-01-05 15:24:35','2026-01-05 15:24:35'),('669c2977-e40d-48ba-b4e4-db35723e311a','a3b56669-a657-481c-b57f-52fd94f1d7e4','dc09419b-212a-4e3d-914e-17f083911fc5',NULL,'8000324423',1,'2025-12-31 15:31:52','2026-01-02 09:36:52'),('6df0773b-4127-44d9-be4e-2045d6365633','a3b56669-a657-481c-b57f-52fd94f1d7e4','ee8a274b-837f-4d72-860e-5aad97487958',NULL,NULL,1,'2026-01-02 09:22:42','2026-01-02 09:22:42'),('76d49233-ff9b-4b39-a315-a00e7dade98b','3e404c0f-2361-48c7-b2b8-45d7e7cf3964','dc09419b-212a-4e3d-914e-17f083911fc5',NULL,NULL,0,'2026-01-17 22:09:12','2026-01-18 00:09:12'),('78ef93bb-4dad-43fe-9e32-75472b4ec672','7b590e84-affd-4310-962d-d889c42ed137','ee8a274b-837f-4d72-860e-5aad97487958',NULL,NULL,1,'2026-01-02 09:43:44','2026-01-02 09:43:44'),('7d5fa30c-a9ce-4403-9902-6dd3e777e644','829f0dc3-f009-42a5-b488-4e257b7a6626','1e0537e9-4242-4e5e-82e2-6fad9e08494f',NULL,NULL,0,'2026-01-17 21:02:21','2026-01-17 23:02:21'),('8882643f-4def-4f8a-a6d8-f1ca49e83522','a3b56669-a657-481c-b57f-52fd94f1d7e4','1e0537e9-4242-4e5e-82e2-6fad9e08494f',NULL,NULL,1,'2026-01-03 20:45:54','2026-01-19 19:18:27'),('8ae4fd2e-7827-4652-af89-9b7f2dbd43e0','1305a3b8-2509-4cf4-a93a-fe9a868de4c6','1e0537e9-4242-4e5e-82e2-6fad9e08494f',NULL,'141936',0,'2025-12-31 11:20:21','2025-12-31 11:20:21'),('9a51e17a-0b57-471c-9bfa-f38683575962','4351d460-63ae-4e9a-9bc7-65b792d77718','1e0537e9-4242-4e5e-82e2-6fad9e08494f',NULL,NULL,0,'2026-01-03 16:35:26','2026-01-03 16:35:26'),('9e39ce60-a853-4947-8d45-db94aa965042','1305a3b8-2509-4cf4-a93a-fe9a868de4c6','dc09419b-212a-4e3d-914e-17f083911fc5',NULL,'8000970939',0,'2025-12-31 15:29:29','2025-12-31 15:29:29'),('9edd0df1-2b09-4556-a8a0-a84ca8791d4b','829f0dc3-f009-42a5-b488-4e257b7a6626','dc09419b-212a-4e3d-914e-17f083911fc5',NULL,NULL,0,'2026-01-17 21:02:27','2026-01-17 23:02:27'),('9ee5decf-b072-4c91-8187-c9acced50d6c','e06b83db-1331-4137-a687-3058b969ccae','00ca9f3c-93a9-40b0-940d-416739d12d6e',NULL,NULL,1,'2026-01-02 09:09:47','2026-01-09 20:06:59'),('afc58013-a26a-4273-9aac-d5c62dc8c37d','e06b83db-1331-4137-a687-3058b969ccae','1e0537e9-4242-4e5e-82e2-6fad9e08494f',NULL,'A54BB6E',0,'2026-01-03 20:46:07','2026-01-03 20:46:07'),('c0d5105c-f126-4a3a-b6c9-73c35e9cddb1','829f0dc3-f009-42a5-b488-4e257b7a6626','91a20e9c-ca6a-4a27-91f5-51cae6e1903f',NULL,NULL,0,'2026-01-17 21:02:31','2026-01-17 23:02:31'),('c47db48f-d2b1-4291-8f1c-9ad096ee061f','b2c07414-e2bb-4515-b568-5f3dd596f14d','07b31939-5944-4f5e-b982-5ee9e1dd1e67',NULL,'115335242,',1,'2026-01-05 17:59:40','2026-01-05 17:59:51'),('c9a7751d-04eb-4c86-8706-394742535d0d','829f0dc3-f009-42a5-b488-4e257b7a6626','f9363812-3e73-4edb-b26f-af721cfdefc6',NULL,NULL,0,'2026-01-17 21:02:34','2026-01-17 23:02:34'),('d148ae3c-0e59-40d7-b476-36fcdcb8e4ea','e06b83db-1331-4137-a687-3058b969ccae','dc09419b-212a-4e3d-914e-17f083911fc5',NULL,'8000324444',0,'2025-12-31 15:35:58','2025-12-31 15:35:58'),('d7a6bc07-5888-412f-9120-618f1dee1766','5ad35b8e-e254-435b-bfbc-be5f3777a2dc','ee8a274b-837f-4d72-860e-5aad97487958',NULL,NULL,1,'2026-01-08 11:51:52','2026-01-08 13:51:52'),('f5ea83f7-daae-4879-aa84-100347f2ad41','b2c07414-e2bb-4515-b568-5f3dd596f14d','1e0537e9-4242-4e5e-82e2-6fad9e08494f',NULL,'A1FA387',0,'2026-01-03 20:06:21','2026-01-03 20:06:21');
/*!40000 ALTER TABLE `property_suppliers` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `renters`
--

DROP TABLE IF EXISTS `renters`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `renters` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `property_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `phone` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rent_day` int DEFAULT NULL,
  `start_contract_date` date DEFAULT NULL,
  `rent_amount` float DEFAULT NULL,
  `rent_currency` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'EUR',
  `access_token` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `access_token` (`access_token`),
  KEY `idx_renters_property` (`property_id`),
  KEY `idx_renters_token` (`access_token`),
  KEY `idx_renters_email` (`email`),
  CONSTRAINT `renters_ibfk_1` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `renters`
--

LOCK TABLES `renters` WRITE;
/*!40000 ALTER TABLE `renters` DISABLE KEYS */;
INSERT INTO `renters` VALUES ('5090eafa-f0b3-46d3-804e-06bffb59f37a','e06b83db-1331-4137-a687-3058b969ccae','Miruna Pricopie',NULL,NULL,10,'2025-08-25',405,'EUR','aeb52050-a314-467f-a77c-65e91abb3102','2026-01-01 19:57:56'),('8d9225f3-9d5d-4961-b6e4-2cbb0a4a16ff','1305a3b8-2509-4cf4-a93a-fe9a868de4c6','Zohaib',NULL,'+923365264425',20,'2025-03-16',360,'EUR','74a4a9ad-5b98-4649-8372-c7ff767c5f4f','2026-01-01 20:29:29'),('bf153da6-17f3-4146-ba80-54fd9ece7621','1305a3b8-2509-4cf4-a93a-fe9a868de4c6','Sojib',NULL,'+40 731 470 195',10,'2025-03-19',170,'EUR','24e267fd-e913-4049-ae10-ecb3b75b3251','2026-01-01 20:30:45'),('dd205ad6-b2da-413e-957b-af790c7798d8','b2c07414-e2bb-4515-b568-5f3dd596f14d','Andrei Zdrali',NULL,'+40731733991',1,'2025-09-01',360,'EUR','e49c06f9-85fb-44dc-9bb8-63b57aa6ba70','2026-01-01 19:53:33'),('e893c57c-f607-4a7a-a1e4-e345176997af','3e404c0f-2361-48c7-b2b8-45d7e7cf3964','place',NULL,NULL,5,NULL,100,'EUR','e84a393b-3b2d-48f4-9b97-536dc337b721','2026-01-03 16:47:05'),('f58e0f67-8eec-4472-8696-11aa333a5ae2','7b590e84-affd-4310-962d-d889c42ed137','expire check',NULL,NULL,1,'2025-01-26',10,'EUR','c0fa67ad-a90b-400b-83ff-9800e304ead4','2026-01-26 15:23:57'),('f938c711-3209-49df-8580-13f9c96b9fbf','a3b56669-a657-481c-b57f-52fd94f1d7e4','Hraniceru Viorel',NULL,'+40736739166',25,'2025-10-20',460,'EUR','f725a9cf-cbd6-403a-844a-43a7a1c9d044','2026-01-01 19:23:17');
/*!40000 ALTER TABLE `renters` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `suppliers`
--

DROP TABLE IF EXISTS `suppliers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `suppliers` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `has_api` tinyint(1) DEFAULT '0',
  `bill_type` enum('rent','utilities','telecom','ebloc','other') COLLATE utf8mb4_unicode_ci DEFAULT 'utilities',
  `extraction_pattern_supplier` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `idx_suppliers_name` (`name`),
  KEY `idx_suppliers_pattern` (`extraction_pattern_supplier`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `suppliers`
--

LOCK TABLES `suppliers` WRITE;
/*!40000 ALTER TABLE `suppliers` DISABLE KEYS */;
INSERT INTO `suppliers` VALUES ('0','[Pattern-based Supplier]',0,'other',NULL,'2026-01-10 15:30:59'),('00ca9f3c-93a9-40b0-940d-416739d12d6e','Vodafone',0,'telecom','vodafone','2025-12-31 11:17:45'),('07b31939-5944-4f5e-b982-5ee9e1dd1e67','Engie',0,'utilities','engie','2026-01-05 17:58:31'),('1e0537e9-4242-4e5e-82e2-6fad9e08494f','E-bloc',1,'ebloc','e-bloc','2025-12-31 11:17:45'),('5f923979-987f-4bb8-838b-786ee4e275ee','Engie Gaze',0,'utilities','engie.gaz','2026-01-02 13:26:46'),('91a20e9c-ca6a-4a27-91f5-51cae6e1903f','PPC Gaze',0,'utilities','ppc.gaz','2026-01-11 13:41:47'),('dc09419b-212a-4e3d-914e-17f083911fc5','Hidroelectrica',0,'utilities','hidroelectrica','2025-12-31 11:17:45'),('ee8a274b-837f-4d72-860e-5aad97487958','Digi',0,'utilities','digi','2025-12-31 11:17:45'),('f9363812-3e73-4edb-b26f-af721cfdefc6','Telekom',0,'telecom','telekom','2026-01-12 18:04:26');
/*!40000 ALTER TABLE `suppliers` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user_preferences`
--

DROP TABLE IF EXISTS `user_preferences`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_preferences` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `language` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'en',
  `view_mode` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT 'list',
  `rent_warning_days` int DEFAULT '5',
  `rent_currency` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'EUR',
  `bill_currency` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'RON',
  `date_format` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT 'DD/MM/YYYY',
  `phone_number` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `landlord_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `personal_email` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iban` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `property_order` text COLLATE utf8mb4_unicode_ci COMMENT 'JSON array of property IDs for display order preference',
  `iban_eur` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iban_usd` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  KEY `idx_prefs_user` (`user_id`),
  CONSTRAINT `user_preferences_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_preferences`
--

LOCK TABLES `user_preferences` WRITE;
/*!40000 ALTER TABLE `user_preferences` DISABLE KEYS */;
INSERT INTO `user_preferences` VALUES ('3ee16f6c-f332-42a5-836c-461fecea6ad5','68459987-46aa-45b3-9344-919321993eda','ro','list',5,'EUR','RON','DD/MM/YYYY',NULL,NULL,'piodoi+pp@gmail.com',NULL,'2026-01-18 20:48:16',NULL,NULL,NULL),('c3c863d5-b123-41bb-aa97-0ef8afd42828','57ca9597-6a30-4775-bc89-71243d828a98','en','grid',5,'EUR','RON','DD/MM/YYYY','+40742755724','Ionut Poclitaru','pio.doi@gmail.com','RO95RZBR0000060014291924','2026-01-20 21:55:37','[\"1305a3b8-2509-4cf4-a93a-fe9a868de4c6\", \"a3b56669-a657-481c-b57f-52fd94f1d7e4\", \"b2c07414-e2bb-4515-b568-5f3dd596f14d\", \"e06b83db-1331-4137-a687-3058b969ccae\", \"5ad35b8e-e254-435b-bfbc-be5f3777a2dc\", \"7b590e84-affd-4310-962d-d889c42ed137\"]','RO75REVO0000222259318997',NULL),('fa216674-e5a1-4812-a31d-e4c38bdcd1f6','748b8c6a-af3b-4328-b087-277a76d1c930','ro','list',5,'EUR','RON','DD/MM/YYYY',NULL,NULL,'piodoi+ll@gmail.com',NULL,'2026-01-18 00:08:46',NULL,NULL,NULL);
/*!40000 ALTER TABLE `user_preferences` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` enum('admin','landlord') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'landlord',
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `oauth_provider` enum('google','facebook') COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `oauth_id` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `subscription_tier` int DEFAULT '0',
  `subscription_expires` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`),
  KEY `idx_users_email` (`email`),
  KEY `idx_users_role` (`role`),
  KEY `idx_users_oauth` (`oauth_provider`,`oauth_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES ('57ca9597-6a30-4775-bc89-71243d828a98','pio.doi@gmail.com','PioLand','admin','$2b$12$fPhRbMZJ2ypYpVGt/AAGNuyGXdx089aq8P20hGOvnCk5lGDxj3ENC',NULL,NULL,7,NULL,'2025-12-31 11:13:57'),('68459987-46aa-45b3-9344-919321993eda','piodoi+pp@gmail.com','NoLand','landlord','$2b$12$Ngwc3T6mfF5861YS1SZtMu3ozBHo2oXLwMTFOHKt66B25Jcesy8gK',NULL,NULL,0,NULL,'2026-01-17 20:57:31'),('748b8c6a-af3b-4328-b087-277a76d1c930','piodoi+ll@gmail.com','PioLandL','landlord','$2b$12$2UVy9RuPG7c0MNNrtgvUTuQXTX6domOccMFkDpDehD4zoELLLsuiC',NULL,NULL,1,NULL,'2026-01-01 16:38:22');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-01-31 17:11:14
