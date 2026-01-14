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
INSERT INTO `bills` VALUES ('02416db0-5d62-451d-9f55-9472556c7b2e','a3b56669-a657-481c-b57f-52fd94f1d7e4',NULL,NULL,'ebloc','E-Bloc',0,'RON','2026-01-04 09:07:47',NULL,NULL,NULL,'Noiembrie 2025 Ap.53',NULL,'A000000',NULL,'paid',NULL,'2026-01-04 09:08:20'),('07ab4844-c4ec-4c10-a3fb-5d431ba51466','e06b83db-1331-4137-a687-3058b969ccae','5090eafa-f0b3-46d3-804e-06bffb59f37a',NULL,'rent','Ianuarie 2026',405,'EUR','2026-01-08 00:00:00',NULL,NULL,NULL,'01',NULL,NULL,NULL,'paid',NULL,'2026-01-03 17:44:42'),('220a3077-d18a-4556-897c-fc6b822a172a','1305a3b8-2509-4cf4-a93a-fe9a868de4c6',NULL,NULL,'utilities','Hidroelectrica',124.68,'RON','2026-01-29 00:00:00',NULL,NULL,NULL,'25110727979','220e67e4-8d81-487c-8d35-639c3ac03a6b','8000970939',NULL,'pending',NULL,'2026-01-01 16:39:32'),('252cdf76-4e39-4af0-b89b-f7fc1180b302','5ad35b8e-e254-435b-bfbc-be5f3777a2dc',NULL,NULL,'utilities','Digi',30.5,'RON','2026-01-31 00:00:00',NULL,NULL,'RO51INGB0001000000018827','14743845','digi',NULL,NULL,'pending',NULL,'2026-01-09 16:31:28'),('3e92a215-0157-4f00-b300-1e13593d5b1c','e06b83db-1331-4137-a687-3058b969ccae',NULL,NULL,'utilities','Hidroelectrica',31.27,'RON','2026-01-30 00:00:00',NULL,NULL,NULL,'25110944560','220e67e4-8d81-487c-8d35-639c3ac03a6b','8000324444',NULL,'paid',NULL,'2026-01-01 15:56:46'),('45e5442b-d715-4c9f-99fc-b4c72775178a','e06b83db-1331-4137-a687-3058b969ccae',NULL,'afc58013-a26a-4273-9aac-d5c62dc8c37d','ebloc','E-bloc',148.43,'RON','2026-01-30 00:00:00','2026-01-12 00:00:00','sociatia de Proprietari Aleea Mizil Nr. 57','RO86INGB0000999909534657','NOIEMBRIE 2025',NULL,'A54BB6E',NULL,'pending',NULL,'2026-01-12 19:00:11'),('486755c0-3645-4354-8ca0-06184fd325fe','e06b83db-1331-4137-a687-3058b969ccae',NULL,NULL,'ebloc','E-bloc',139.54,'RON','2026-01-01 00:00:00',NULL,NULL,NULL,'Octombrie 2025 Ap.8',NULL,'68210',NULL,'paid',NULL,'2026-01-03 23:17:03'),('49b40785-5d6b-4d45-b972-a7b2988aaf78','b2c07414-e2bb-4515-b568-5f3dd596f14d','dd205ad6-b2da-413e-957b-af790c7798d8',NULL,'rent','February 2026',360,'EUR','2026-02-01 00:00:00',NULL,NULL,'RO95RZBR0000060014291924','02',NULL,NULL,NULL,'pending',NULL,'2026-01-09 17:40:13'),('6565967d-80f4-491f-aa45-1026bbc75648','e06b83db-1331-4137-a687-3058b969ccae',NULL,NULL,'other','Vodafone',44.65,'RON','2026-01-21 00:00:00',NULL,NULL,'RO23INGB0001000000000222','VDF760317168','vodafone','271768784',NULL,'paid',NULL,'2026-01-09 18:07:11'),('728b974d-a8f7-44f6-bad3-82e028e79f88','a3b56669-a657-481c-b57f-52fd94f1d7e4',NULL,NULL,'utilities','Hidroelectrica',155.58,'RON','2026-01-30 00:00:00',NULL,NULL,NULL,'25110944550','220e67e4-8d81-487c-8d35-639c3ac03a6b','8000324423',NULL,'paid',NULL,'2026-01-03 23:17:03'),('7ac330e4-491a-40a0-93d2-85750ad5acff','b2c07414-e2bb-4515-b568-5f3dd596f14d',NULL,'07b31939-5944-4f5e-b982-5ee9e1dd1e67','utilities','Engie',29.67,'RON','2026-01-11 00:00:00',NULL,NULL,'RO23RZBR0000060011419498','70900452673 din','engie','115335242,',NULL,'paid',NULL,'2026-01-07 16:32:47'),('88b2dde8-3d6f-4cb6-b99e-d496d89f51f7','b2c07414-e2bb-4515-b568-5f3dd596f14d',NULL,'f5ea83f7-daae-4879-aa84-100347f2ad41','utilities','E-bloc',144.02,'RON','2026-01-08 00:00:00',NULL,NULL,'RO41UGBI0000622002421RON','NOIEMBRIE 2025',NULL,'A1FA387',NULL,'paid',NULL,'2026-01-05 21:18:54'),('9ea781a3-c727-4730-b069-8539661fd10c','7b590e84-affd-4310-962d-d889c42ed137',NULL,NULL,'utilities','Digi',108.75,'RON','2026-01-31 00:00:00',NULL,NULL,'RO51INGB0001000000018827','14744500','digi',NULL,NULL,'pending',NULL,'2026-01-09 16:32:35'),('a3dec734-6bdb-4ed8-9adc-fb43589eec63','a3b56669-a657-481c-b57f-52fd94f1d7e4','f938c711-3209-49df-8580-13f9c96b9fbf',NULL,'rent','January 2026',460,'EUR','2026-01-25 00:00:00',NULL,NULL,'RO95RZBR0000060014291924','01',NULL,NULL,NULL,'pending',NULL,'2026-01-09 21:03:56'),('a55e6f38-0678-4547-8307-465633064f13','1305a3b8-2509-4cf4-a93a-fe9a868de4c6','bf153da6-17f3-4146-ba80-54fd9ece7621',NULL,'rent','February 2026',170,'EUR','2026-02-10 00:00:00',NULL,NULL,'RO95RZBR0000060014291924','02',NULL,NULL,NULL,'pending',NULL,'2026-01-11 09:28:04'),('a5d2ab8d-596d-4583-a9b3-32521e4bb8ff','7b590e84-affd-4310-962d-d889c42ed137',NULL,'46286284-b44b-442c-bd6a-89737d3a4a6a','utilities','PPC Gaze',265.51,'RON','2026-01-08 00:00:00','2025-12-23 00:00:00','PPC Energie S.A.','RO45','93000445050','ppc.gaz','PEYIFCERN053002',NULL,'paid',NULL,'2026-01-12 17:42:08'),('a9b58180-e7cd-40c7-8f02-57df9011dd2e','1305a3b8-2509-4cf4-a93a-fe9a868de4c6',NULL,NULL,'utilities','e-bloc',1125,'RON','2026-02-05 00:00:00',NULL,NULL,'RO40RNCB0089003747230001','NOIEMBRIE 2025',NULL,'A4F80C5',NULL,'pending',NULL,'2026-01-06 15:04:40'),('a9dfa98c-a033-4a4d-a10d-971d2e82a7a6','1305a3b8-2509-4cf4-a93a-fe9a868de4c6','bf153da6-17f3-4146-ba80-54fd9ece7621',NULL,'rent','January 2026',170,'EUR','2026-01-10 00:00:00',NULL,NULL,'RO95RZBR0000060014291924','01',NULL,NULL,NULL,'paid',NULL,'2026-01-09 21:03:56'),('ac0a2a03-e25e-4f0f-b775-bd99a8135d46','7b590e84-affd-4310-962d-d889c42ed137',NULL,'dc09419b-212a-4e3d-914e-17f083911fc5','utilities','Hidroelectrica',769.46,'RON','2026-01-26 00:00:00',NULL,'SPEEH HIDROELECTRICA SA','RO63RNCB0072018331870495','25110487592',NULL,'8000324406',NULL,'pending',NULL,'2026-01-09 20:33:14'),('b7bcfd92-4b91-4ff2-a259-660a2d071fa2','e06b83db-1331-4137-a687-3058b969ccae',NULL,NULL,'utilities','Engie',234.01,'RON','2026-01-19 00:00:00',NULL,NULL,'RO40RZBR0000060010660361','11803290532',NULL,'4001941859',NULL,'paid',NULL,'2026-01-05 17:25:04'),('b9898d7f-4a38-420e-a2ab-a1d934703e91','e06b83db-1331-4137-a687-3058b969ccae','5090eafa-f0b3-46d3-804e-06bffb59f37a',NULL,'rent','February 2026',405,'EUR','2026-02-10 00:00:00',NULL,NULL,'RO95RZBR0000060014291924','02',NULL,NULL,NULL,'pending',NULL,'2026-01-09 18:34:54'),('d3a76075-1d12-4c00-9d55-c9819af580ef','7b590e84-affd-4310-962d-d889c42ed137','eefb3318-cdf2-48f2-9c97-63cde1e563bf',NULL,'rent','February 2026',100,'EUR','2026-02-01 00:00:00',NULL,NULL,'RO95RZBR0000060014291924','02',NULL,NULL,NULL,'pending',NULL,'2026-01-09 17:38:17'),('d870a1ec-06b5-466f-9a9c-f6ca22e9d458','b2c07414-e2bb-4515-b568-5f3dd596f14d',NULL,'491e0ee8-7c77-49bb-82da-0540381dc2fe','utilities','Engie Gaze',172.12,'RON','2026-01-22 00:00:00','2025-12-23 00:00:00','ENGIE Romania S.A. Sediul social: B-dul Mărăşeşti nr. 4 -6, sector 4,','RO40RZBR0000060010660361','11117929360','engie.gaz','4001585793',NULL,'paid',NULL,'2026-01-10 21:02:23'),('e8883020-9209-4cf5-8c01-cc924fa499f8','1305a3b8-2509-4cf4-a93a-fe9a868de4c6','8d9225f3-9d5d-4961-b6e4-2cbb0a4a16ff',NULL,'rent','January 2026',360,'EUR','2026-01-20 00:00:00',NULL,NULL,'RO95RZBR0000060014291924','01',NULL,NULL,NULL,'pending',NULL,'2026-01-09 21:03:56'),('fde3a621-c844-4cf0-bf10-4c8064c00c89','a3b56669-a657-481c-b57f-52fd94f1d7e4',NULL,NULL,'telecom','Telekom',45.83,'RON','2025-12-30 00:00:00','2025-12-16 00:00:00','TELEKOM ROMANIA MOBILE COMMUNICATIONS SA',NULL,'250108897932','telekom','99170010871410',NULL,'paid',NULL,'2026-01-12 18:34:26');
/*!40000 ALTER TABLE `bills` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-01-14 22:00:38
